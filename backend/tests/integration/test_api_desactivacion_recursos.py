"""Desactivar recursos y su efecto en los turnos: app real, PostgreSQL real, reloj fijo."""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
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


def _crear_turno(api: TestClient, c: Catalogo, **cambios: Any) -> str:
    respuesta = api.post("/turnos", json=_body(c, **cambios))
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()["id"]


def _desactivar(api: TestClient, ruta: str, recurso_id: UUID) -> None:
    respuesta = api.post(f"/{ruta}/{recurso_id}/desactivar")
    assert respuesta.status_code == 200, respuesta.text


def _turnos(session: Session) -> int:
    session.expire_all()
    return session.scalar(select(func.count()).select_from(Turno)) or 0


def _turno(session: Session, turno_id: str) -> Turno:
    session.expire_all()
    return session.execute(select(Turno).where(Turno.id == UUID(turno_id))).scalar_one()


# --- Un recurso desactivado no admite turnos nuevos --------------------------------------


def test_alta_con_un_sillon_desactivado_responde_referencia_inactiva_y_no_persiste(
    api: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    _desactivar(api, "sillones", catalogo.sillones[0].id)

    respuesta = api.post("/turnos", json=_body(catalogo))

    assert respuesta.status_code == 422
    assert respuesta.json() == {
        "detail": {"codigo": "referencia_invalida", "referencia": "sillon", "motivo": "inactiva"}
    }
    assert _turnos(db_session) == 0


def test_alta_con_una_prestacion_desactivada_responde_referencia_inactiva(
    api: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    _desactivar(api, "prestaciones", catalogo.limpieza.id)

    respuesta = api.post("/turnos", json=_body(catalogo))

    assert respuesta.status_code == 422
    detalle = respuesta.json()["detail"]
    assert (detalle["referencia"], detalle["motivo"]) == ("prestacion", "inactiva")
    assert _turnos(db_session) == 0


def test_alta_con_un_profesional_desactivado_responde_referencia_inactiva(
    api: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    _desactivar(api, "profesionales", catalogo.profesionales[0].id)

    respuesta = api.post("/turnos", json=_body(catalogo))

    assert respuesta.status_code == 422
    assert respuesta.json()["detail"]["referencia"] == "profesional"
    assert _turnos(db_session) == 0


def test_alta_con_otro_sillon_activo_sigue_funcionando_tras_desactivar_uno(
    api: TestClient, catalogo: Catalogo
) -> None:
    _desactivar(api, "sillones", catalogo.sillones[0].id)

    respuesta = api.post("/turnos", json=_body(catalogo, sillon_id=str(catalogo.sillones[1].id)))

    assert respuesta.status_code == 201


def test_reprogramar_hacia_un_profesional_desactivado_responde_422_y_el_turno_sigue(
    api: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    turno_id = _crear_turno(api, catalogo)
    _desactivar(api, "profesionales", catalogo.profesionales[1].id)

    respuesta = api.patch(
        f"/turnos/{turno_id}/reprogramar",
        json={"profesional_id": str(catalogo.profesionales[1].id)},
    )

    assert respuesta.status_code == 422
    assert respuesta.json()["detail"]["referencia"] == "profesional"
    assert _turno(db_session, turno_id).profesional_id == catalogo.profesionales[0].id


# --- Un recurso desactivado conserva sus turnos ------------------------------------------


def test_desactivar_el_profesional_deja_intacto_su_turno_futuro(
    api: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    turno_id = _crear_turno(api, catalogo)

    _desactivar(api, "profesionales", catalogo.profesionales[0].id)

    turno = _turno(db_session, turno_id)
    assert turno.estado == "programado"
    assert turno.profesional_id == catalogo.profesionales[0].id
    assert turno.sillon_id == catalogo.sillones[0].id
    assert (turno.inicio, turno.fin) == (INICIO, INICIO + timedelta(minutes=45))


def test_cancelar_un_turno_cuyo_sillon_fue_desactivado_responde_200(
    api: TestClient, catalogo: Catalogo
) -> None:
    turno_id = _crear_turno(api, catalogo)
    _desactivar(api, "sillones", catalogo.sillones[0].id)

    respuesta = api.post(f"/turnos/{turno_id}/cancelar")

    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "cancelado"


def test_desactivar_la_prestacion_deja_intacto_un_turno_cancelado(
    api: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    turno_id = _crear_turno(api, catalogo)
    api.post(f"/turnos/{turno_id}/cancelar", json={"motivo": "Viaje"})

    _desactivar(api, "prestaciones", catalogo.limpieza.id)

    turno = _turno(db_session, turno_id)
    assert turno.estado == "cancelado"
    assert turno.prestacion_id == catalogo.limpieza.id
    assert turno.motivo_cancelacion == "Viaje"


# --- Editar una prestación no altera los turnos existentes -------------------------------


def test_cambiar_la_duracion_de_la_prestacion_no_altera_los_turnos_existentes(
    api: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    turno_id = _crear_turno(api, catalogo)

    cambio = api.patch(f"/prestaciones/{catalogo.limpieza.id}", json={"duracion_min": 60})
    nuevo_id = _crear_turno(
        api,
        catalogo,
        inicio="2026-10-08T15:00:00-03:00",
        paciente_id=str(catalogo.pacientes[1].id),
    )

    assert cambio.status_code == 200
    viejo = _turno(db_session, turno_id)
    assert viejo.duracion_min == 45
    assert (viejo.inicio, viejo.fin) == (INICIO, INICIO + timedelta(minutes=45))
    nuevo = _turno(db_session, nuevo_id)
    assert nuevo.duracion_min == 60
    assert nuevo.fin - nuevo.inicio == timedelta(minutes=60)
