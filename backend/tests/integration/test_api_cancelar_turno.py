"""POST /turnos/{id}/cancelar de punta a punta: FastAPI + caso de uso + PostgreSQL real."""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.api.turnos import get_reloj
from app.infrastructure.db.models import Turno
from tests.integration.factories import Catalogo, crear_catalogo

AHORA = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)  # 2026-10-07 09:00 hora local
INICIO_LOCAL = "2026-10-08T10:00:00-03:00"
INICIO = datetime(2026, 10, 8, 13, 0, tzinfo=UTC)


@pytest.fixture
def catalogo(db_session: Session) -> Catalogo:
    return crear_catalogo(db_session)


@pytest.fixture
def api(client: TestClient) -> TestClient:
    _fijar_reloj(client, AHORA)
    return client


def _fijar_reloj(client: TestClient, ahora: datetime) -> None:
    client.app.dependency_overrides[get_reloj] = lambda: lambda: ahora  # type: ignore[attr-defined]


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


def _crear(api: TestClient, c: Catalogo, **cambios: Any) -> str:
    respuesta = api.post("/turnos", json=_body(c, **cambios))
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()["id"]


def _fila(session: Session, turno_id: str) -> tuple[str, str | None]:
    session.expire_all()
    estado, motivo = session.execute(
        select(Turno.estado, Turno.motivo_cancelacion).where(Turno.id == turno_id)
    ).one()
    return estado, motivo


# --- 5.1 cancelación válida --------------------------------------------------------------


def test_cancelar_turno_futuro_responde_200_y_conserva_la_fila(
    api: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    turno_id = _crear(api, catalogo)

    respuesta = api.post(f"/turnos/{turno_id}/cancelar", json={"motivo": "Viaje imprevisto"})

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["id"] == turno_id
    assert cuerpo["estado"] == "cancelado"
    assert cuerpo["motivo_cancelacion"] == "Viaje imprevisto"
    assert cuerpo["inicio"] == INICIO_LOCAL
    assert cuerpo["fin"] == "2026-10-08T10:45:00-03:00"
    fila = db_session.execute(
        text("SELECT estado, profesional_id, inicio FROM turno WHERE id = :id"), {"id": turno_id}
    ).one()
    assert fila.estado == "cancelado"
    assert fila.profesional_id == catalogo.profesionales[0].id
    assert fila.inicio == INICIO


def test_alta_de_turno_responde_motivo_cancelacion_nulo(
    api: TestClient, catalogo: Catalogo
) -> None:
    respuesta = api.post("/turnos", json=_body(catalogo))

    assert respuesta.status_code == 201
    assert respuesta.json()["motivo_cancelacion"] is None


# --- 5.2 motivo --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("kwargs", "esperado"),
    [
        ({}, None),  # sin body
        ({"json": {}}, None),
        ({"json": {"motivo": None}}, None),
        ({"json": {"motivo": "   "}}, None),
        (
            {"json": {"motivo": "  El paciente avisó que está con fiebre  "}},
            "El paciente avisó que está con fiebre",
        ),
    ],
    ids=["sin-body", "objeto-vacio", "motivo-null", "en-blanco", "con-espacios"],
)
def test_motivo_opcional_y_normalizado(
    api: TestClient,
    db_session: Session,
    catalogo: Catalogo,
    kwargs: dict[str, Any],
    esperado: str | None,
) -> None:
    turno_id = _crear(api, catalogo)

    respuesta = api.post(f"/turnos/{turno_id}/cancelar", **kwargs)

    assert respuesta.status_code == 200
    assert respuesta.json()["motivo_cancelacion"] == esperado
    assert _fila(db_session, turno_id) == ("cancelado", esperado)


def test_motivo_de_256_caracteres_responde_422_y_de_255_se_acepta(
    api: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    turno_id = _crear(api, catalogo)

    largo = api.post(f"/turnos/{turno_id}/cancelar", json={"motivo": "x" * 256})

    assert largo.status_code == 422
    assert _fila(db_session, turno_id) == ("programado", None)
    limite = api.post(f"/turnos/{turno_id}/cancelar", json={"motivo": "x" * 255})
    assert limite.status_code == 200


# --- 5.3 errores -------------------------------------------------------------------------


def test_turno_inexistente_responde_404(api: TestClient) -> None:
    respuesta = api.post(f"/turnos/{uuid4()}/cancelar")

    assert respuesta.status_code == 404
    assert respuesta.json()["detail"]["codigo"] == "turno_inexistente"


def test_id_con_formato_invalido_responde_422(api: TestClient) -> None:
    assert api.post("/turnos/no-es-un-id/cancelar").status_code == 422


def test_segunda_cancelacion_responde_409_y_no_cambia_el_motivo(
    api: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    turno_id = _crear(api, catalogo)
    api.post(f"/turnos/{turno_id}/cancelar", json={"motivo": "Viaje imprevisto"})

    respuesta = api.post(f"/turnos/{turno_id}/cancelar", json={"motivo": "Otro motivo"})

    assert respuesta.status_code == 409
    assert respuesta.json()["detail"]["codigo"] == "turno_ya_cancelado"
    assert _fila(db_session, turno_id) == ("cancelado", "Viaje imprevisto")


# --- 5.4 solo antes del inicio -----------------------------------------------------------


def test_cancelar_un_minuto_antes_del_inicio_responde_200(
    api: TestClient, catalogo: Catalogo
) -> None:
    turno_id = _crear(api, catalogo)
    _fijar_reloj(api, INICIO - timedelta(minutes=1))

    assert api.post(f"/turnos/{turno_id}/cancelar").status_code == 200


@pytest.mark.parametrize(
    "ahora",
    [INICIO, INICIO + timedelta(minutes=20), INICIO + timedelta(days=1)],
    ids=["limite-exacto", "en-curso", "dia-posterior"],
)
def test_turno_iniciado_o_pasado_responde_409_y_no_cambia(
    api: TestClient, db_session: Session, catalogo: Catalogo, ahora: datetime
) -> None:
    turno_id = _crear(api, catalogo)
    _fijar_reloj(api, ahora)

    respuesta = api.post(f"/turnos/{turno_id}/cancelar", json={"motivo": "Tarde"})

    assert respuesta.status_code == 409
    assert respuesta.json()["detail"]["codigo"] == "turno_ya_iniciado"
    assert _fila(db_session, turno_id) == ("programado", None)


def test_turno_cancelado_y_pasado_responde_409_ya_cancelado(
    api: TestClient, catalogo: Catalogo
) -> None:
    turno_id = _crear(api, catalogo)
    api.post(f"/turnos/{turno_id}/cancelar")
    _fijar_reloj(api, INICIO + timedelta(days=1))

    respuesta = api.post(f"/turnos/{turno_id}/cancelar")

    assert respuesta.status_code == 409
    assert respuesta.json()["detail"]["codigo"] == "turno_ya_cancelado"


# --- 5.5 liberación del horario (RN-AG-07) -----------------------------------------------


def test_antes_de_cancelar_el_mismo_profesional_y_horario_da_409(
    api: TestClient, catalogo: Catalogo
) -> None:
    _crear(api, catalogo)

    respuesta = api.post(
        "/turnos",
        json=_body(
            catalogo,
            paciente_id=str(catalogo.pacientes[1].id),
            sillon_id=str(catalogo.sillones[1].id),
        ),
    )

    assert respuesta.status_code == 409
    assert respuesta.json()["detail"]["recursos"] == ["profesional"]


def test_tras_cancelar_se_puede_reservar_el_mismo_horario_y_recursos(
    api: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    turno_id = _crear(api, catalogo)
    assert api.post(f"/turnos/{turno_id}/cancelar").status_code == 200

    nuevo = api.post("/turnos", json=_body(catalogo))

    assert nuevo.status_code == 201
    estados = db_session.scalars(
        select(Turno.estado).where(Turno.profesional_id == catalogo.profesionales[0].id)
    ).all()
    assert sorted(estados) == ["cancelado", "programado"]


def test_tras_cancelar_otro_paciente_toma_el_horario_liberado(
    api: TestClient, catalogo: Catalogo
) -> None:
    turno_id = _crear(api, catalogo)
    api.post(f"/turnos/{turno_id}/cancelar")

    otro = api.post(
        "/turnos",
        json=_body(
            catalogo,
            paciente_id=str(catalogo.pacientes[1].id),
            inicio="2026-10-08T10:15:00-03:00",
        ),
    )

    assert otro.status_code == 201
