"""API de profesionales contra PostgreSQL real: alta, edición, desactivación y consulta."""

from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.infrastructure.db.models import Profesional, Usuario


def _cantidad(session: Session) -> int:
    session.expire_all()
    return session.scalar(select(func.count()).select_from(Profesional)) or 0


# --- Alta de profesional -----------------------------------------------------------------


def test_post_profesionales_con_matricula_crea_un_profesional_activo(
    client: TestClient, db_session: Session
) -> None:
    respuesta = client.post(
        "/profesionales", json={"nombre": "Ana", "apellido": "Ficticia", "matricula": "MN-0001"}
    )

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert set(cuerpo) == {"id", "nombre", "apellido", "matricula", "activo"}
    assert (cuerpo["nombre"], cuerpo["apellido"], cuerpo["matricula"]) == (
        "Ana",
        "Ficticia",
        "MN-0001",
    )
    assert cuerpo["activo"] is True
    en_base = db_session.execute(select(Profesional)).scalar_one()
    assert (en_base.matricula, en_base.activo) == ("MN-0001", True)


def test_post_profesionales_sin_matricula_la_deja_nula(client: TestClient) -> None:
    respuesta = client.post("/profesionales", json={"nombre": "Bruno", "apellido": "Inventado"})

    assert respuesta.status_code == 201
    assert respuesta.json()["matricula"] is None
    assert respuesta.json()["activo"] is True


@pytest.mark.parametrize("matricula", ["  ", "", None], ids=["espacios", "vacia", "nula"])
def test_post_profesionales_con_matricula_vacia_la_guarda_nula_y_admite_varios(
    client: TestClient, db_session: Session, matricula: str | None
) -> None:
    sin_matricula = client.post("/profesionales", json={"nombre": "Ana", "apellido": "Previa"})
    assert sin_matricula.status_code == 201

    respuesta = client.post(
        "/profesionales", json={"nombre": "Carla", "apellido": "Supuesta", "matricula": matricula}
    )

    assert respuesta.status_code == 201
    assert respuesta.json()["matricula"] is None
    assert _cantidad(db_session) == 2


def test_post_profesionales_recorta_los_espacios_de_los_textos(client: TestClient) -> None:
    respuesta = client.post(
        "/profesionales",
        json={"nombre": " Ana ", "apellido": " Ficticia ", "matricula": " MN-0007 "},
    )

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert (cuerpo["nombre"], cuerpo["apellido"], cuerpo["matricula"]) == (
        "Ana",
        "Ficticia",
        "MN-0007",
    )


@pytest.mark.parametrize(
    "body",
    [
        {"nombre": "Ana"},
        {"apellido": "Ficticia"},
        {"nombre": "  ", "apellido": "Ficticia"},
        {"nombre": "Ana", "apellido": ""},
        {"nombre": "x" * 101, "apellido": "Ficticia"},
        {"nombre": "Ana", "apellido": "x" * 101},
        {"nombre": "Ana", "apellido": "Ficticia", "matricula": "M" * 31},
    ],
    ids=[
        "sin-apellido",
        "sin-nombre",
        "nombre-solo-espacios",
        "apellido-vacio",
        "nombre-101",
        "apellido-101",
        "matricula-31",
    ],
)
def test_post_profesionales_invalido_responde_422_y_no_persiste(
    client: TestClient, db_session: Session, body: dict[str, Any]
) -> None:
    respuesta = client.post("/profesionales", json=body)

    assert respuesta.status_code == 422
    assert _cantidad(db_session) == 0


# --- Estado de actividad no editable y duplicados (alta) ---------------------------------


def test_post_profesionales_con_activo_responde_campo_no_editable(
    client: TestClient, db_session: Session
) -> None:
    respuesta = client.post(
        "/profesionales", json={"nombre": "Ana", "apellido": "Ficticia", "activo": False}
    )

    assert respuesta.status_code == 422
    assert respuesta.json()["detail"]["codigo"] == "campo_no_editable"
    assert respuesta.json()["detail"]["campos"] == ["activo"]
    assert _cantidad(db_session) == 0


def test_post_profesionales_con_matricula_repetida_responde_409_y_no_persiste_al_nuevo(
    client: TestClient, db_session: Session
) -> None:
    client.post("/profesionales", json={"nombre": "Ana", "apellido": "A", "matricula": "MN-0001"})

    respuesta = client.post(
        "/profesionales", json={"nombre": "Bruno", "apellido": "B", "matricula": "MN-0001 "}
    )

    assert respuesta.status_code == 409
    assert respuesta.json() == {"detail": {"codigo": "recurso_duplicado", "campo": "matricula"}}
    assert _cantidad(db_session) == 1


# --- Edición parcial ---------------------------------------------------------------------


def _profesional(
    session: Session, nombre: str, apellido: str, matricula: str | None = None
) -> Profesional:
    profesional = Profesional(nombre=nombre, apellido=apellido, matricula=matricula)
    session.add(profesional)
    session.flush()
    return profesional


def _en_base(session: Session, profesional: Profesional) -> Profesional:
    session.expire_all()
    return session.execute(select(Profesional).where(Profesional.id == profesional.id)).scalar_one()


def test_patch_profesionales_modifica_solo_el_campo_enviado(
    client: TestClient, db_session: Session
) -> None:
    ana = _profesional(db_session, "Ana", "Ficticia", "MN-0001")

    respuesta = client.patch(f"/profesionales/{ana.id}", json={"apellido": "Ficticia Segunda"})

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert (cuerpo["nombre"], cuerpo["apellido"], cuerpo["matricula"]) == (
        "Ana",
        "Ficticia Segunda",
        "MN-0001",
    )
    assert _en_base(db_session, ana).apellido == "Ficticia Segunda"


def test_patch_profesionales_con_matricula_nula_la_quita(
    client: TestClient, db_session: Session
) -> None:
    ana = _profesional(db_session, "Ana", "Ficticia", "MN-0001")

    respuesta = client.patch(f"/profesionales/{ana.id}", json={"matricula": None})

    assert respuesta.status_code == 200
    assert respuesta.json()["matricula"] is None
    assert _en_base(db_session, ana).matricula is None


def test_patch_profesionales_con_matricula_vacia_la_quita(
    client: TestClient, db_session: Session
) -> None:
    ana = _profesional(db_session, "Ana", "Ficticia", "MN-0001")

    respuesta = client.patch(f"/profesionales/{ana.id}", json={"matricula": "  "})

    assert respuesta.status_code == 200
    assert respuesta.json()["matricula"] is None


@pytest.mark.parametrize("campo", ["nombre", "apellido"])
def test_patch_profesionales_con_nulo_en_campo_obligatorio_responde_422_y_no_cambia(
    client: TestClient, db_session: Session, campo: str
) -> None:
    ana = _profesional(db_session, "Ana", "Ficticia", "MN-0001")

    respuesta = client.patch(f"/profesionales/{ana.id}", json={campo: None})

    assert respuesta.status_code == 422
    en_base = _en_base(db_session, ana)
    assert (en_base.nombre, en_base.apellido) == ("Ana", "Ficticia")


def test_patch_profesionales_con_matricula_de_otro_responde_409_y_conserva_la_suya(
    client: TestClient, db_session: Session
) -> None:
    _profesional(db_session, "Ana", "A", "MN-0001")
    bruno = _profesional(db_session, "Bruno", "B", "MN-0002")

    respuesta = client.patch(f"/profesionales/{bruno.id}", json={"matricula": "MN-0001"})

    assert respuesta.status_code == 409
    assert respuesta.json() == {"detail": {"codigo": "recurso_duplicado", "campo": "matricula"}}
    assert _en_base(db_session, bruno).matricula == "MN-0002"


def test_patch_profesionales_con_su_propia_matricula_no_es_duplicado(
    client: TestClient, db_session: Session
) -> None:
    ana = _profesional(db_session, "Ana", "Ficticia", "MN-0001")

    respuesta = client.patch(f"/profesionales/{ana.id}", json={"matricula": "MN-0001"})

    assert respuesta.status_code == 200


def test_patch_profesionales_inexistente_responde_404_con_el_recurso_correcto(
    client: TestClient,
) -> None:
    respuesta = client.patch(f"/profesionales/{uuid4()}", json={"nombre": "Nadie"})

    assert respuesta.status_code == 404
    assert respuesta.json() == {
        "detail": {"codigo": "recurso_inexistente", "recurso": "profesional"}
    }


def test_patch_profesionales_con_activo_responde_campo_no_editable(
    client: TestClient, db_session: Session
) -> None:
    ana = _profesional(db_session, "Ana", "Ficticia")

    respuesta = client.patch(f"/profesionales/{ana.id}", json={"activo": False})

    assert respuesta.status_code == 422
    assert respuesta.json()["detail"]["campos"] == ["activo"]
    assert _en_base(db_session, ana).activo is True


# --- Desactivación lógica ----------------------------------------------------------------


def test_desactivar_profesional_responde_200_inactivo_y_la_fila_sigue_existiendo(
    client: TestClient, db_session: Session
) -> None:
    ana = _profesional(db_session, "Ana", "Ficticia", "MN-0001")

    respuesta = client.post(f"/profesionales/{ana.id}/desactivar")

    assert respuesta.status_code == 200
    assert respuesta.json()["activo"] is False
    assert respuesta.json()["matricula"] == "MN-0001"
    assert _en_base(db_session, ana).activo is False


def test_desactivar_profesional_inexistente_responde_404_con_el_recurso_correcto(
    client: TestClient,
) -> None:
    respuesta = client.post(f"/profesionales/{uuid4()}/desactivar")

    assert respuesta.status_code == 404
    assert respuesta.json() == {
        "detail": {"codigo": "recurso_inexistente", "recurso": "profesional"}
    }


def test_desactivar_profesional_no_toca_al_usuario_odontologo_vinculado(
    client: TestClient, db_session: Session, odontologo: Usuario
) -> None:
    respuesta = client.post(f"/profesionales/{odontologo.profesional_id}/desactivar")

    assert respuesta.status_code == 200
    db_session.expire_all()
    usuario = db_session.get(Usuario, odontologo.id)
    assert usuario is not None
    assert usuario.activo is True
    assert usuario.profesional_id == odontologo.profesional_id
