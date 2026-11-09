"""Pacientes con operaciones simultáneas, cada una en su propia conexión y por la API real.

Escenarios deterministas por orden de llegada: la primera transacción queda abierta sin confirmar,
la segunda corre en un hilo, `_esperar_bloqueo` confirma que quedó esperando el lock y recién
entonces se deja confirmar a la primera.
"""

import threading
import time
from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, delete, func, select, text
from sqlalchemy.orm import Session, sessionmaker

from app.api.auth import get_emisor_tokens, get_hasher
from app.application.crear_turno import CrearTurno, SolicitudTurno
from app.application.gestion_recursos import DesactivarRecurso
from app.application.reprogramar_turno import ReprogramarTurno, SolicitudReprogramacion
from app.domain.turnos import ReferenciaInvalidaError, TurnoPropuesto
from app.infrastructure.db.models import Paciente, Turno, Usuario
from app.infrastructure.db.repositorio_pacientes import RepositorioPacientes
from app.infrastructure.db.repositorio_turnos import RepositorioTurnos
from app.infrastructure.db.session import get_session
from app.infrastructure.security.contrasenas import Hasher
from app.infrastructure.security.tokens import EmisorTokens
from app.main import create_app
from tests.integration.factories import Catalogo

ESPERA_S = 15
AHORA = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)  # 2026-10-07 09:00 hora local
INICIO = datetime(2026, 10, 8, 13, 0, tzinfo=UTC)  # 10:00 hora local
OTRO_INICIO = INICIO + timedelta(hours=5)
DOCUMENTO = "FIC-CONC-0101"


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


_HILOS: list[threading.Thread] = []


class Hilo:
    """Una operación en su propio hilo: guarda el resultado o la excepción y avisa al terminar."""

    def __init__(self, operacion: Callable[[], Any]) -> None:
        self.resultado: Any = None
        self.terminada = threading.Event()
        self._operacion = operacion
        self._hilo = threading.Thread(target=self._correr)
        _HILOS.append(self._hilo)
        self._hilo.start()

    def _correr(self) -> None:
        try:
            self.resultado = self._operacion()
        except Exception as error:
            self.resultado = error
        finally:
            self.terminada.set()

    def esperar(self) -> Any:
        self._hilo.join(timeout=30)
        assert self.terminada.is_set(), "la operación no terminó"
        return self.resultado


@pytest.fixture
def fabrica(motor_concurrente: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=motor_concurrente, expire_on_commit=False)


@pytest.fixture(autouse=True)
def esperar_hilos() -> Iterator[None]:
    """Espera a los hilos al terminar, también si el test falla, antes de borrar los datos."""
    yield
    while _HILOS:
        _HILOS.pop().join(timeout=30)


@pytest.fixture
def documentos_a_borrar(motor_concurrente: Engine) -> Iterator[list[str]]:
    """Los pacientes que un test deja commiteados se borran al final por su documento."""
    documentos: list[str] = []
    yield documentos
    with Session(motor_concurrente) as sesion:
        sesion.execute(delete(Paciente).where(Paciente.documento.in_(documentos)))
        sesion.commit()


@pytest.fixture
def cliente_real(
    fabrica: sessionmaker[Session],
    hasher_test: Hasher,
    emisor_test: EmisorTokens,
    recepcionista_commiteada: Usuario,
) -> TestClient:
    """App real con una sesión nueva por request, sobre el motor concurrente."""
    app = create_app()

    def sesion_nueva() -> Iterator[Session]:
        with fabrica() as sesion:
            yield sesion

    app.dependency_overrides[get_session] = sesion_nueva
    app.dependency_overrides[get_hasher] = lambda: hasher_test
    app.dependency_overrides[get_emisor_tokens] = lambda: emisor_test
    encabezados = {"Authorization": f"Bearer {emisor_test.emitir(recepcionista_commiteada)}"}
    return TestClient(app, headers=encabezados)


def _cantidad_con_documento(motor: Engine, documento: str) -> int:
    with Session(motor) as sesion:
        return (
            sesion.scalar(
                select(func.count()).select_from(Paciente).where(Paciente.documento == documento)
            )
            or 0
        )


def _paciente(documento: str) -> Paciente:
    return Paciente(
        nombre="Carla", apellido="Concurrente", documento=documento, telefono="+54 11 5555-0000"
    )


def test_altas_simultaneas_con_el_mismo_documento_el_segundo_responde_409_no_500(
    motor_concurrente: Engine,
    fabrica: sessionmaker[Session],
    cliente_real: TestClient,
    documentos_a_borrar: list[str],
) -> None:
    documentos_a_borrar.append(DOCUMENTO)
    body = {
        "nombre": "Diego",
        "apellido": "Concurrente",
        "documento": DOCUMENTO,
        "telefono": "+54 11 5555-0102",
    }

    with fabrica() as primera:
        primera.add(_paciente(DOCUMENTO))
        primera.flush()  # el INSERT tomó el índice único y la transacción sigue abierta
        alta = Hilo(lambda: cliente_real.post("/pacientes", json=body))
        _esperar_bloqueo(motor_concurrente, "INSERT INTO paciente")
        assert not alta.terminada.is_set()
        primera.commit()
    respuesta = alta.esperar()

    assert not isinstance(respuesta, Exception), respuesta
    assert respuesta.status_code == 409, respuesta.text
    assert respuesta.json() == {"detail": {"codigo": "recurso_duplicado", "campo": "documento"}}
    assert _cantidad_con_documento(motor_concurrente, DOCUMENTO) == 1


# --- Desactivación de paciente simultánea con un alta o una reprogramación de turno ---------


def _solicitud(catalogo: Catalogo) -> SolicitudTurno:
    return SolicitudTurno(
        profesional_id=catalogo.profesionales[0].id,
        paciente_id=catalogo.pacientes[0].id,
        prestacion_id=catalogo.limpieza.id,
        sillon_id=catalogo.sillones[0].id,
        inicio=INICIO,
    )


def _desactivar_sin_confirmar(sesion: Session, paciente_id: UUID) -> None:
    """Desactiva al paciente en una transacción que queda abierta, con la fila bloqueada."""
    repo = RepositorioPacientes(sesion)
    paciente = repo.obtener_para_actualizar(paciente_id)
    assert paciente is not None
    repo.modificar(paciente, {"activo": False})
    repo.guardar()


def _turnos_del_profesional(motor: Engine, catalogo: Catalogo) -> list[Turno]:
    with Session(motor) as sesion:
        return list(
            sesion.scalars(
                select(Turno).where(Turno.profesional_id == catalogo.profesionales[0].id)
            )
        )


def _activo(motor: Engine, paciente_id: UUID) -> bool:
    with Session(motor) as sesion:
        return bool(sesion.scalar(select(Paciente.activo).where(Paciente.id == paciente_id)))


def test_alta_de_turno_espera_a_una_desactivacion_de_paciente_en_curso_y_responde_inactiva(
    motor_concurrente: Engine, fabrica: sessionmaker[Session], catalogo_commiteado: Catalogo
) -> None:
    paciente = catalogo_commiteado.pacientes[0]

    with fabrica() as desactivadora:
        _desactivar_sin_confirmar(desactivadora, paciente.id)
        alta = Hilo(
            lambda: _con_sesion(
                fabrica,
                lambda sesion: CrearTurno(RepositorioTurnos(sesion), reloj=lambda: AHORA).ejecutar(
                    _solicitud(catalogo_commiteado)
                ),
            )
        )
        _esperar_bloqueo(motor_concurrente, "FOR SHARE")
        assert not alta.terminada.is_set()
        desactivadora.commit()
    error = alta.esperar()

    assert isinstance(error, ReferenciaInvalidaError), error
    assert (error.referencia, error.motivo) == ("paciente", "inactiva")
    assert _turnos_del_profesional(motor_concurrente, catalogo_commiteado) == []


def test_desactivacion_de_paciente_espera_a_un_alta_en_curso_y_el_turno_conserva_al_paciente(
    motor_concurrente: Engine, fabrica: sessionmaker[Session], catalogo_commiteado: Catalogo
) -> None:
    paciente = catalogo_commiteado.pacientes[0]
    detenida = threading.Event()
    confirmar_alta = threading.Event()

    def detener_tras_validar_referencias(_: TurnoPropuesto) -> None:
        # Las referencias ya se cargaron (y bloquearon); el INSERT del turno todavía no ocurrió
        detenida.set()
        confirmar_alta.wait(timeout=ESPERA_S)

    alta = Hilo(
        lambda: _con_sesion(
            fabrica,
            lambda sesion: CrearTurno(
                RepositorioTurnos(sesion),
                reloj=lambda: AHORA,
                validadores=[detener_tras_validar_referencias],
            ).ejecutar(_solicitud(catalogo_commiteado)),
        )
    )
    assert detenida.wait(timeout=ESPERA_S)
    baja = Hilo(
        lambda: _con_sesion(
            fabrica,
            lambda sesion: DesactivarRecurso(RepositorioPacientes(sesion)).ejecutar(paciente.id),
        )
    )
    _esperar_bloqueo(motor_concurrente, "FOR UPDATE")
    assert not baja.terminada.is_set()
    assert _activo(motor_concurrente, paciente.id) is True

    confirmar_alta.set()
    resultado_alta, resultado_baja = alta.esperar(), baja.esperar()

    assert not isinstance(resultado_alta, Exception), resultado_alta
    assert not isinstance(resultado_baja, Exception), resultado_baja
    turnos = _turnos_del_profesional(motor_concurrente, catalogo_commiteado)
    assert [t.paciente_id for t in turnos] == [paciente.id]
    assert _activo(motor_concurrente, paciente.id) is False


def test_reprogramacion_espera_a_una_desactivacion_de_paciente_y_el_turno_no_se_mueve(
    motor_concurrente: Engine, fabrica: sessionmaker[Session], catalogo_commiteado: Catalogo
) -> None:
    paciente = catalogo_commiteado.pacientes[0]
    turno = _con_sesion(
        fabrica,
        lambda sesion: CrearTurno(RepositorioTurnos(sesion), reloj=lambda: AHORA).ejecutar(
            _solicitud(catalogo_commiteado)
        ),
    )

    with fabrica() as desactivadora:
        _desactivar_sin_confirmar(desactivadora, paciente.id)
        cambio = Hilo(
            lambda: _con_sesion(
                fabrica,
                lambda sesion: ReprogramarTurno(
                    RepositorioTurnos(sesion), reloj=lambda: AHORA
                ).ejecutar(turno.id, SolicitudReprogramacion(inicio=OTRO_INICIO)),
            )
        )
        _esperar_bloqueo(motor_concurrente, "FOR SHARE")
        assert not cambio.terminada.is_set()
        desactivadora.commit()
    error = cambio.esperar()

    assert isinstance(error, ReferenciaInvalidaError), error
    assert (error.referencia, error.motivo) == ("paciente", "inactiva")
    (guardado,) = _turnos_del_profesional(motor_concurrente, catalogo_commiteado)
    assert guardado.inicio == INICIO


def _con_sesion[T](fabrica: sessionmaker[Session], operacion: Callable[[Session], T]) -> T:
    """Corre la operación en una sesión propia, como un request."""
    with fabrica() as sesion:
        return operacion(sesion)
