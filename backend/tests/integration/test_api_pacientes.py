"""API de pacientes (escritura) contra PostgreSQL real: alta, validaciones, edición y estado."""

from typing import Any
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.infrastructure.db.models import Paciente

CLAVES_PACIENTE = {"id", "nombre", "apellido", "documento", "telefono", "email", "activo"}


def _body(**cambios: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "nombre": "Carla",
        "apellido": "Imaginaria",
        "documento": "FIC-0101",
        "telefono": "+54 11 5555-0101",
        "email": "carla.imaginaria@example.com",
    }
    body.update(cambios)
    return body


def _cantidad(session: Session) -> int:
    session.expire_all()
    return session.scalar(select(func.count()).select_from(Paciente)) or 0


def _en_base(session: Session, paciente_id: str | UUID) -> Paciente:
    session.expire_all()
    return session.execute(
        select(Paciente).where(Paciente.id == UUID(str(paciente_id)))
    ).scalar_one()


def _crear(client: TestClient, **cambios: Any) -> dict[str, Any]:
    respuesta = client.post("/pacientes", json=_body(**cambios))
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


# --- Alta de paciente --------------------------------------------------------------------


def test_post_pacientes_con_email_crea_un_paciente_activo(
    client: TestClient, db_session: Session
) -> None:
    respuesta = client.post("/pacientes", json=_body())

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["id"]
    assert {k: v for k, v in cuerpo.items() if k != "id"} == {
        "nombre": "Carla",
        "apellido": "Imaginaria",
        "documento": "FIC-0101",
        "telefono": "+54 11 5555-0101",
        "email": "carla.imaginaria@example.com",
        "activo": True,
    }
    guardado = _en_base(db_session, cuerpo["id"])
    assert (guardado.documento, guardado.activo) == ("FIC-0101", True)


def test_post_pacientes_sin_email_responde_email_nulo(client: TestClient) -> None:
    body = _body(nombre="Diego", apellido="Supuesto", documento="FIC-0102")
    del body["email"]

    respuesta = client.post("/pacientes", json=body)

    assert respuesta.status_code == 201
    assert respuesta.json()["email"] is None
    assert respuesta.json()["activo"] is True


def test_post_pacientes_responde_exactamente_las_siete_claves(client: TestClient) -> None:
    respuesta = client.post("/pacientes", json=_body())

    assert respuesta.status_code == 201
    assert set(respuesta.json()) == CLAVES_PACIENTE


def test_post_pacientes_dos_altas_generan_ids_distintos(client: TestClient) -> None:
    uno = _crear(client)
    otro = _crear(client, documento="FIC-0102")

    assert uno["id"] != otro["id"]
