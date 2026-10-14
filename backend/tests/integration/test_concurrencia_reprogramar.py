"""Concurrencia de la reprogramación, cada operación en su propia conexión (PostgreSQL real)."""

import threading
import time
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Engine, delete, select, text
from sqlalchemy.orm import Session, sessionmaker

from app.application.cancelar_turno import CancelarTurno
from app.application.crear_turno import CrearTurno, SolicitudTurno
from app.application.reprogramar_turno import ReprogramarTurno, SolicitudReprogramacion
from app.domain.turnos import SolapamientoError, TurnoNoModificableError, TurnoRegistrado
from app.infrastructure.db.models import Paciente, Turno
from app.infrastructure.db.repositorio_turnos import RepositorioTurnos
from tests.integration.factories import Catalogo

AHORA = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)
INICIO = datetime(2026, 10, 8, 13, 0, tzinfo=UTC)  # 10:00 hora local
HUECO = INICIO + timedelta(hours=10)  # 20:00 hora local, libre para todos
HILOS = 5
ESPERA_S = 15


@pytest.fixture
def pacientes_extra(
    motor_concurrente: Engine, catalogo_commiteado: Catalogo
) -> Iterator[list[Any]]:
    """Pacientes ficticios adicionales (commiteados) para que cada turno tenga el suyo."""
    with Session(motor_concurrente) as sesion:
        extra = [
            Paciente(
                nombre=f"Extra{i}",
                apellido="Ficticio",
                documento=f"FX-{uuid4().hex[:12]}-{i}",
                telefono="+54 11 5555-0003",
            )
            for i in range(HILOS)
        ]
        sesion.add_all(extra)
        sesion.commit()
        ids = [p.id for p in extra]
    try:
        yield ids
    finally:
        with Session(motor_concurrente) as sesion:
            profesionales = [p.id for p in catalogo_commiteado.profesionales]
            sesion.execute(delete(Turno).where(Turno.profesional_id.in_(profesionales)))
            sesion.execute(delete(Paciente).where(Paciente.id.in_(ids)))
            sesion.commit()


def _crear_commiteado(motor: Engine, **datos: Any) -> UUID:
    with Session(motor) as sesion:
        creado = CrearTurno(RepositorioTurnos(sesion), reloj=lambda: AHORA).ejecutar(
            SolicitudTurno(**datos)
        )
        return creado.id


def _leer(motor: Engine, turno_id: UUID) -> tuple[datetime, datetime, str]:
    with Session(motor) as sesion:
        return (
            sesion.execute(
                select(Turno.inicio, Turno.fin, Turno.estado).where(Turno.id == turno_id)
            )
            .one()
            ._tuple()
        )


# --- 8.1 turnos distintos hacia el mismo hueco ---------------------------------------------


def test_turnos_distintos_hacia_el_mismo_hueco_dejan_exactamente_un_exito(
    motor_concurrente: Engine, catalogo_commiteado: Catalogo, pacientes_extra: list[UUID]
) -> None:
    profesional = catalogo_commiteado.profesionales[0].id
    iniciales = [INICIO + timedelta(hours=i) for i in range(HILOS)]
    ids = [
        _crear_commiteado(
            motor_concurrente,
            profesional_id=profesional,
            paciente_id=pacientes_extra[i],
            prestacion_id=catalogo_commiteado.consulta.id,  # sin sillón: solo comparten profesional
            sillon_id=None,
            inicio=iniciales[i],
        )
        for i in range(HILOS)
    ]
    fabrica = sessionmaker(bind=motor_concurrente, expire_on_commit=False)
    barrera = threading.Barrier(HILOS)
    resultados: list[Any] = [None] * HILOS

    def trabajar(indice: int) -> None:
        with fabrica() as sesion:
            caso = ReprogramarTurno(RepositorioTurnos(sesion), reloj=lambda: AHORA)
            barrera.wait(timeout=10)
            try:
                resultados[indice] = caso.ejecutar(
                    ids[indice], SolicitudReprogramacion(inicio=HUECO)
                )
            except Exception as error:  # se inspecciona en el hilo principal
                resultados[indice] = error

    hilos = [threading.Thread(target=trabajar, args=(i,)) for i in range(HILOS)]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join(timeout=30)

    exitos = [i for i, r in enumerate(resultados) if isinstance(r, TurnoRegistrado)]
    perdedores = [i for i in range(HILOS) if i not in exitos]
    assert len(exitos) == 1, resultados
    for i in perdedores:
        assert isinstance(resultados[i], SolapamientoError), resultados[i]
        assert resultados[i].recursos == ("profesional",)
    en_el_hueco = [i for i in range(HILOS) if _leer(motor_concurrente, ids[i])[0] == HUECO]
    assert en_el_hueco == exitos
    for i in perdedores:
        inicio, fin, estado = _leer(motor_concurrente, ids[i])
        assert (inicio, fin, estado) == (
            iniciales[i],
            iniciales[i] + timedelta(minutes=30),
            "programado",
        )


# --- 8.2 y 8.3 reprogramar vs cancelar el mismo turno --------------------------------------


def _esperar_bloqueo_de_fila(motor: Engine) -> None:
    """Espera a que otra conexión esté bloqueada en un SELECT ... FOR UPDATE de turno."""
    limite = time.monotonic() + ESPERA_S
    consulta = text(
        "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database() "
        "AND wait_event_type = 'Lock' AND query ILIKE '%FOR UPDATE%'"
    )
    while time.monotonic() < limite:
        with motor.connect() as conexion:
            if conexion.execute(consulta).scalar_one() >= 1:
                return
        time.sleep(0.05)
    raise AssertionError("la segunda operación no quedó bloqueada en FOR UPDATE")


def _carrera(motor: Engine, turno_id: UUID, *, reprograma_primero: bool) -> tuple[Any, Any, bool]:
    """Corre cancelar y reprogramar (15:00 local) con la primera retenida con la fila bloqueada.

    La primera operación recibe un observador que, con la fila ya bloqueada, avisa y espera;
    mientras tanto se lanza la segunda y se comprueba que queda bloqueada sin terminar.
    """
    fabrica = sessionmaker(bind=motor, expire_on_commit=False)
    bloqueada = threading.Event()
    liberar = threading.Event()
    terminada = {"cancelar": threading.Event(), "reprogramar": threading.Event()}
    resultados: dict[str, Any] = {}
    nuevo_inicio = INICIO + timedelta(hours=5)

    def retener(*_: Any) -> None:
        bloqueada.set()
        liberar.wait(timeout=ESPERA_S)

    def cancelar(observadores: list[Any]) -> None:
        with fabrica() as sesion:
            caso = CancelarTurno(
                RepositorioTurnos(sesion), reloj=lambda: AHORA, observadores=observadores
            )
            try:
                resultados["cancelar"] = caso.ejecutar(turno_id, "Viaje")
            except Exception as error:
                resultados["cancelar"] = error
        terminada["cancelar"].set()

    def reprogramar(observadores: list[Any]) -> None:
        with fabrica() as sesion:
            caso = ReprogramarTurno(
                RepositorioTurnos(sesion), reloj=lambda: AHORA, observadores=observadores
            )
            try:
                resultados["reprogramar"] = caso.ejecutar(
                    turno_id, SolicitudReprogramacion(inicio=nuevo_inicio)
                )
            except Exception as error:
                resultados["reprogramar"] = error
        terminada["reprogramar"].set()

    if reprograma_primero:
        primero = threading.Thread(target=reprogramar, args=([retener],))
        segundo = threading.Thread(target=cancelar, args=([],))
        nombre_segundo = "cancelar"
    else:
        primero = threading.Thread(target=cancelar, args=([retener],))
        segundo = threading.Thread(target=reprogramar, args=([],))
        nombre_segundo = "reprogramar"

    primero.start()
    assert bloqueada.wait(timeout=ESPERA_S), "la primera operación no tomó el bloqueo"
    segundo.start()
    _esperar_bloqueo_de_fila(motor)
    segundo_termino_antes = terminada[nombre_segundo].is_set()
    liberar.set()
    primero.join(timeout=30)
    segundo.join(timeout=30)
    return resultados["cancelar"], resultados["reprogramar"], segundo_termino_antes


def test_cancelar_primero_la_reprogramacion_espera_y_responde_ya_cancelado(
    motor_concurrente: Engine, catalogo_commiteado: Catalogo
) -> None:
    turno_id = _crear_commiteado(
        motor_concurrente,
        profesional_id=catalogo_commiteado.profesionales[0].id,
        paciente_id=catalogo_commiteado.pacientes[0].id,
        prestacion_id=catalogo_commiteado.limpieza.id,
        sillon_id=catalogo_commiteado.sillones[0].id,
        inicio=INICIO,
    )

    cancelacion, reprogramacion, termino_antes = _carrera(
        motor_concurrente, turno_id, reprograma_primero=False
    )

    assert termino_antes is False
    assert isinstance(cancelacion, TurnoRegistrado)
    assert isinstance(reprogramacion, TurnoNoModificableError)
    assert reprogramacion.codigo == "turno_ya_cancelado"
    assert _leer(motor_concurrente, turno_id) == (
        INICIO,
        INICIO + timedelta(minutes=45),
        "cancelado",
    )


def test_reprogramar_primero_la_cancelacion_espera_y_cancela_el_turno_movido(
    motor_concurrente: Engine, catalogo_commiteado: Catalogo
) -> None:
    turno_id = _crear_commiteado(
        motor_concurrente,
        profesional_id=catalogo_commiteado.profesionales[0].id,
        paciente_id=catalogo_commiteado.pacientes[0].id,
        prestacion_id=catalogo_commiteado.limpieza.id,
        sillon_id=catalogo_commiteado.sillones[0].id,
        inicio=INICIO,
    )

    cancelacion, reprogramacion, termino_antes = _carrera(
        motor_concurrente, turno_id, reprograma_primero=True
    )

    assert termino_antes is False
    assert isinstance(reprogramacion, TurnoRegistrado)
    assert isinstance(cancelacion, TurnoRegistrado)
    nuevo = INICIO + timedelta(hours=5)  # 15:00 hora local
    assert _leer(motor_concurrente, turno_id) == (nuevo, nuevo + timedelta(minutes=45), "cancelado")
