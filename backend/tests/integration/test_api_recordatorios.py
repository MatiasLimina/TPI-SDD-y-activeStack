"""Recordatorios por la API: FastAPI + casos de uso + PostgreSQL real + cola en memoria."""

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.turnos import get_cola_recordatorios, get_reloj
from tests.fakes import ColaEnMemoria, ColaQueFalla
from tests.integration.factories import Catalogo, crear_catalogo
from tests.integration.helpers_recordatorios import contar_recordatorios, recordatorios_de

AHORA = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)  # 2026-10-07 09:00 hora local
INICIO_LOCAL = "2026-10-09T10:00:00-03:00"
PROGRAMADO_PARA = datetime(2026, 10, 8, 13, 0, tzinfo=UTC)
NUEVO_INICIO_LOCAL = "2026-10-12T15:00:00-03:00"
NUEVO_PROGRAMADO = datetime(2026, 10, 11, 18, 0, tzinfo=UTC)


@pytest.fixture
def catalogo(db_session: Session) -> Catalogo:
    return crear_catalogo(db_session)


@pytest.fixture
def api(client: TestClient) -> TestClient:
    client.app.dependency_overrides[get_reloj] = lambda: lambda: AHORA  # type: ignore[attr-defined]
    return client


def _body(c: Catalogo, **cambios: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "profesional_id": str(c.profesionales[0].id),
        "paciente_id": str(c.pacientes[0].id),
        "prestacion_id": str(c.limpieza.id),
        "sillon_id": str(c.sillones[0].id),
        "inicio": INICIO_LOCAL,
    }
    body.update(cambios)
    return body


def _crear(api: TestClient, c: Catalogo, **cambios: Any) -> UUID:
    respuesta = api.post("/turnos", json=_body(c, **cambios))
    assert respuesta.status_code == 201, respuesta.text
    return UUID(respuesta.json()["id"])


def test_alta_con_mas_de_24h_responde_201_y_deja_un_recordatorio_pendiente(
    api: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    turno_id = _crear(api, catalogo)

    (recordatorio,) = recordatorios_de(db_session, turno_id)

    assert recordatorio["estado"] == "pendiente"
    assert recordatorio["canal"] == "mock"
    assert recordatorio["intentos"] == 0
    assert recordatorio["programado_para"] == PROGRAMADO_PARA


def test_alta_con_menos_de_24h_responde_201_sin_recordatorio_ni_encolado(
    api: TestClient, db_session: Session, catalogo: Catalogo, cola: ColaEnMemoria
) -> None:
    turno_id = _crear(api, catalogo, inicio="2026-10-08T08:55:00-03:00")  # 23 h 55 min

    assert recordatorios_de(db_session, turno_id) == []
    assert cola.elementos == {}


def test_alta_encola_el_recordatorio_con_su_vencimiento(
    api: TestClient, db_session: Session, catalogo: Catalogo, cola: ColaEnMemoria
) -> None:
    turno_id = _crear(api, catalogo)

    (recordatorio,) = recordatorios_de(db_session, turno_id)

    assert cola.elementos == {recordatorio["id"]: PROGRAMADO_PARA}


def test_reprogramar_encola_el_recordatorio_nuevo_con_su_vencimiento(
    api: TestClient, db_session: Session, catalogo: Catalogo, cola: ColaEnMemoria
) -> None:
    turno_id = _crear(api, catalogo)
    (original,) = recordatorios_de(db_session, turno_id)

    respuesta = api.patch(f"/turnos/{turno_id}/reprogramar", json={"inicio": NUEVO_INICIO_LOCAL})

    assert respuesta.status_code == 200
    original_cancelado, nuevo = recordatorios_de(db_session, turno_id)
    assert original_cancelado["id"] == original["id"]
    assert original_cancelado["estado"] == "cancelado"
    assert nuevo["estado"] == "pendiente"
    assert cola.elementos[nuevo["id"]] == NUEVO_PROGRAMADO


def test_reprogramar_sin_cambio_de_inicio_no_encola_nada_nuevo(
    api: TestClient, catalogo: Catalogo, cola: ColaEnMemoria
) -> None:
    turno_id = _crear(api, catalogo)
    antes = dict(cola.elementos)

    respuesta = api.patch(
        f"/turnos/{turno_id}/reprogramar", json={"sillon_id": str(catalogo.sillones[1].id)}
    )

    assert respuesta.status_code == 200
    assert cola.elementos == antes


def test_cancelar_por_api_deja_el_recordatorio_cancelado(
    api: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    turno_id = _crear(api, catalogo)

    respuesta = api.post(f"/turnos/{turno_id}/cancelar")

    assert respuesta.status_code == 200
    (recordatorio,) = recordatorios_de(db_session, turno_id)
    assert recordatorio["estado"] == "cancelado"
    assert recordatorio["programado_para"] == PROGRAMADO_PARA
    assert recordatorio["intentos"] == 0


# --- 8.3 cola no disponible y operaciones rechazadas ------------------------------------------


def test_cola_no_disponible_al_crear_responde_201_deja_pendiente_y_registra_warning(
    api: TestClient, db_session: Session, catalogo: Catalogo, caplog: pytest.LogCaptureFixture
) -> None:
    api.app.dependency_overrides[get_cola_recordatorios] = ColaQueFalla  # type: ignore[attr-defined]

    with caplog.at_level(logging.WARNING):
        turno_id = _crear(api, catalogo)

    (recordatorio,) = recordatorios_de(db_session, turno_id)
    assert recordatorio["estado"] == "pendiente"
    advertencias = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(advertencias) == 1
    mensaje = advertencias[0].getMessage()
    assert str(recordatorio["id"]) in mensaje
    assert str(catalogo.pacientes[0].id) not in mensaje
    assert str(turno_id) not in mensaje


def test_cola_no_disponible_al_reprogramar_responde_200_con_anterior_cancelado_y_nuevo_pendiente(
    api: TestClient, db_session: Session, catalogo: Catalogo, caplog: pytest.LogCaptureFixture
) -> None:
    turno_id = _crear(api, catalogo)
    api.app.dependency_overrides[get_cola_recordatorios] = ColaQueFalla  # type: ignore[attr-defined]

    with caplog.at_level(logging.WARNING):
        respuesta = api.patch(
            f"/turnos/{turno_id}/reprogramar", json={"inicio": NUEVO_INICIO_LOCAL}
        )

    assert respuesta.status_code == 200
    anterior, nuevo = recordatorios_de(db_session, turno_id)
    assert anterior["estado"] == "cancelado"
    assert nuevo["estado"] == "pendiente"
    assert nuevo["programado_para"] == NUEVO_PROGRAMADO
    assert [r.levelno for r in caplog.records if r.levelno >= logging.WARNING] == [logging.WARNING]


def test_alta_rechazada_no_encola_ni_crea_recordatorios(
    api: TestClient, db_session: Session, catalogo: Catalogo, cola: ColaEnMemoria
) -> None:
    _crear(api, catalogo)
    encolado = dict(cola.elementos)
    antes = contar_recordatorios(db_session)

    respuesta = api.post(
        "/turnos",
        json=_body(
            catalogo, inicio="2026-10-09T10:30:00-03:00", paciente_id=str(catalogo.pacientes[1].id)
        ),
    )

    assert respuesta.status_code == 409
    assert cola.elementos == encolado
    assert contar_recordatorios(db_session) == antes


def test_reprogramacion_rechazada_no_encola_y_conserva_el_recordatorio(
    api: TestClient, db_session: Session, catalogo: Catalogo, cola: ColaEnMemoria
) -> None:
    primero = _crear(api, catalogo)
    _crear(
        api,
        catalogo,
        inicio=NUEVO_INICIO_LOCAL,
        paciente_id=str(catalogo.pacientes[1].id),
    )
    (original,) = recordatorios_de(db_session, primero)
    encolado = dict(cola.elementos)

    respuesta = api.patch(
        f"/turnos/{primero}/reprogramar", json={"inicio": "2026-10-12T15:30:00-03:00"}
    )

    assert respuesta.status_code == 409
    assert cola.elementos == encolado
    assert recordatorios_de(db_session, primero) == [original]


def test_operaciones_rechazadas_por_api_no_tocan_recordatorios(
    api: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    turno_id = _crear(api, catalogo)
    (original,) = recordatorios_de(db_session, turno_id)
    antes = contar_recordatorios(db_session)

    solape = api.post(
        "/turnos",
        json=_body(
            catalogo, inicio="2026-10-09T10:30:00-03:00", paciente_id=str(catalogo.pacientes[1].id)
        ),
    )
    duracion = api.patch(f"/turnos/{turno_id}/reprogramar", json={"duracion_min": 7})

    assert (solape.status_code, duracion.status_code) == (409, 422)
    assert recordatorios_de(db_session, turno_id) == [original]

    assert api.post(f"/turnos/{turno_id}/cancelar").status_code == 200
    (cancelado,) = recordatorios_de(db_session, turno_id)
    segunda = api.post(f"/turnos/{turno_id}/cancelar")

    assert segunda.status_code == 409
    assert segunda.json()["detail"]["codigo"] == "turno_ya_cancelado"
    assert recordatorios_de(db_session, turno_id) == [cancelado]
    assert cancelado["estado"] == "cancelado"
    assert contar_recordatorios(db_session) == antes
