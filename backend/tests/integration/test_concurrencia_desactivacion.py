"""Desactivar un recurso vs alta o reprogramación de turno, cada operación en su conexión."""

import threading
import time
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import Engine, select, text
from sqlalchemy.orm import Session, sessionmaker

from app.application.crear_turno import CrearTurno, SolicitudTurno
from app.application.gestion_recursos import DesactivarRecurso
from app.application.reprogramar_turno import ReprogramarTurno, SolicitudReprogramacion
from app.domain.turnos import ReferenciaInvalidaError, TurnoPropuesto
from app.infrastructure.db.models import Sillon, Turno
from app.infrastructure.db.repositorio_recursos import DEFINICION_SILLON, RepositorioRecursos
from app.infrastructure.db.repositorio_turnos import RepositorioTurnos
from tests.integration.factories import Catalogo

AHORA = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)
INICIO = datetime(2026, 10, 8, 13, 0, tzinfo=UTC)  # 10:00 hora local
OTRO_INICIO = INICIO + timedelta(hours=5)
ESPERA_S = 15


def _esperar_bloqueo(motor: Engine, consulta_bloqueada: str) -> None:
    """Espera a que otra conexión esté bloqueada esperando un lock en una consulta como esta."""
    limite = time.monotonic() + ESPERA_S
    consulta = text(
        "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database() "
        "AND wait_event_type = 'Lock' AND query ILIKE :patron"
    )
    while time.monotonic() < limite:
        with motor.connect() as conexion:
            if conexion.execute(consulta, {"patron": f"%{consulta_bloqueada}%"}).scalar_one():
                return
        time.sleep(0.05)
    raise AssertionError(
        f"ninguna conexión quedó bloqueada en una consulta con {consulta_bloqueada}"
    )


def _desactivar_sin_confirmar(sesion: Session, sillon_id: UUID) -> None:
    """Desactiva el sillón en una transacción que queda abierta, con la fila bloqueada."""
    repo = RepositorioRecursos(sesion, DEFINICION_SILLON)
    sillon = repo.obtener_para_actualizar(sillon_id)
    assert sillon is not None
    repo.modificar(sillon, {"activo": False})
    repo.guardar()


def _solicitud(catalogo: Catalogo, sillon_id: UUID) -> SolicitudTurno:
    return SolicitudTurno(
        profesional_id=catalogo.profesionales[0].id,
        paciente_id=catalogo.pacientes[0].id,
        prestacion_id=catalogo.limpieza.id,
        sillon_id=sillon_id,
        inicio=INICIO,
    )


def _turnos_del_profesional(motor: Engine, catalogo: Catalogo) -> list[Turno]:
    with Session(motor) as sesion:
        return list(
            sesion.scalars(
                select(Turno).where(Turno.profesional_id == catalogo.profesionales[0].id)
            )
        )


def _activo(motor: Engine, sillon_id: UUID) -> bool:
    with Session(motor) as sesion:
        return bool(sesion.scalar(select(Sillon.activo).where(Sillon.id == sillon_id)))


def test_alta_de_turno_espera_a_una_desactivacion_en_curso_y_responde_inactiva(
    motor_concurrente: Engine, catalogo_commiteado: Catalogo
) -> None:
    sillon = catalogo_commiteado.sillones[0]
    fabrica = sessionmaker(bind=motor_concurrente, expire_on_commit=False)
    resultado: dict[str, Any] = {}
    terminada = threading.Event()

    def crear() -> None:
        with fabrica() as sesion:
            try:
                resultado["alta"] = CrearTurno(
                    RepositorioTurnos(sesion), reloj=lambda: AHORA
                ).ejecutar(_solicitud(catalogo_commiteado, sillon.id))
            except Exception as error:
                resultado["alta"] = error
        terminada.set()

    with fabrica() as desactivadora:
        _desactivar_sin_confirmar(desactivadora, sillon.id)
        hilo = threading.Thread(target=crear)
        hilo.start()
        _esperar_bloqueo(motor_concurrente, "FOR SHARE")
        assert not terminada.is_set()
        desactivadora.commit()
    hilo.join(timeout=30)

    error = resultado["alta"]
    assert isinstance(error, ReferenciaInvalidaError), error
    assert (error.referencia, error.motivo) == ("sillon", "inactiva")
    assert _turnos_del_profesional(motor_concurrente, catalogo_commiteado) == []


def test_desactivacion_espera_a_un_alta_en_curso_y_el_turno_conserva_el_sillon(
    motor_concurrente: Engine, catalogo_commiteado: Catalogo
) -> None:
    sillon = catalogo_commiteado.sillones[0]
    fabrica = sessionmaker(bind=motor_concurrente, expire_on_commit=False)
    detenida = threading.Event()
    confirmar_alta = threading.Event()
    desactivacion_terminada = threading.Event()
    resultado: dict[str, Any] = {}

    def detener_tras_validar_referencias(_: TurnoPropuesto) -> None:
        # Las referencias ya se cargaron (y bloquearon); el INSERT del turno todavía no ocurrió
        detenida.set()
        confirmar_alta.wait(timeout=ESPERA_S)

    def crear() -> None:
        with fabrica() as sesion:
            try:
                resultado["alta"] = CrearTurno(
                    RepositorioTurnos(sesion),
                    reloj=lambda: AHORA,
                    validadores=[detener_tras_validar_referencias],
                ).ejecutar(_solicitud(catalogo_commiteado, sillon.id))
            except Exception as error:
                resultado["alta"] = error

    def desactivar() -> None:
        with fabrica() as sesion:
            try:
                resultado["baja"] = DesactivarRecurso(
                    RepositorioRecursos(sesion, DEFINICION_SILLON)
                ).ejecutar(sillon.id)
            except Exception as error:
                resultado["baja"] = error
        desactivacion_terminada.set()

    alta = threading.Thread(target=crear)
    alta.start()
    assert detenida.wait(timeout=ESPERA_S)
    baja = threading.Thread(target=desactivar)
    baja.start()
    _esperar_bloqueo(motor_concurrente, "FOR UPDATE")
    assert not desactivacion_terminada.is_set()
    assert _activo(motor_concurrente, sillon.id) is True

    confirmar_alta.set()
    alta.join(timeout=30)
    baja.join(timeout=30)

    assert not isinstance(resultado["alta"], Exception), resultado["alta"]
    assert not isinstance(resultado["baja"], Exception), resultado["baja"]
    turnos = _turnos_del_profesional(motor_concurrente, catalogo_commiteado)
    assert [t.sillon_id for t in turnos] == [sillon.id]
    assert _activo(motor_concurrente, sillon.id) is False


def test_reprogramacion_espera_a_una_desactivacion_en_curso_y_el_turno_no_se_mueve(
    motor_concurrente: Engine, catalogo_commiteado: Catalogo
) -> None:
    sillon_origen, sillon_destino = catalogo_commiteado.sillones
    fabrica = sessionmaker(bind=motor_concurrente, expire_on_commit=False)
    with fabrica() as sesion:
        turno = CrearTurno(RepositorioTurnos(sesion), reloj=lambda: AHORA).ejecutar(
            _solicitud(catalogo_commiteado, sillon_origen.id)
        )
    resultado: dict[str, Any] = {}
    terminada = threading.Event()

    def reprogramar() -> None:
        with fabrica() as sesion:
            try:
                resultado["cambio"] = ReprogramarTurno(
                    RepositorioTurnos(sesion), reloj=lambda: AHORA
                ).ejecutar(
                    turno.id,
                    SolicitudReprogramacion(sillon_id=sillon_destino.id, inicio=OTRO_INICIO),
                )
            except Exception as error:
                resultado["cambio"] = error
        terminada.set()

    with fabrica() as desactivadora:
        _desactivar_sin_confirmar(desactivadora, sillon_destino.id)
        hilo = threading.Thread(target=reprogramar)
        hilo.start()
        _esperar_bloqueo(motor_concurrente, "FOR SHARE")
        assert not terminada.is_set()
        desactivadora.commit()
    hilo.join(timeout=30)

    error = resultado["cambio"]
    assert isinstance(error, ReferenciaInvalidaError), error
    assert (error.referencia, error.motivo) == ("sillon", "inactiva")
    (guardado,) = _turnos_del_profesional(motor_concurrente, catalogo_commiteado)
    assert (guardado.sillon_id, guardado.inicio) == (sillon_origen.id, INICIO)
