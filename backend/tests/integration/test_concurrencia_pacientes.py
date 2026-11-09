"""Pacientes con operaciones simultáneas, cada una en su propia conexión y por la API real.

Escenarios deterministas por orden de llegada: la primera transacción queda abierta sin confirmar,
la segunda corre en un hilo, `_esperar_bloqueo` confirma que quedó esperando el lock y recién
entonces se deja confirmar a la primera.
"""

import threading
import time
from collections.abc import Callable, Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, delete, func, select, text
from sqlalchemy.orm import Session, sessionmaker

from app.api.auth import get_emisor_tokens, get_hasher
from app.infrastructure.db.models import Paciente, Usuario
from app.infrastructure.db.session import get_session
from app.infrastructure.security.contrasenas import Hasher
from app.infrastructure.security.tokens import EmisorTokens
from app.main import create_app

ESPERA_S = 15
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
