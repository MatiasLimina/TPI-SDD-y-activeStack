"""API de sillones contra PostgreSQL real: alta, edición, desactivación y consulta."""

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.infrastructure.db.models import Sillon


def _cantidad(session: Session) -> int:
    session.expire_all()
    return session.scalar(select(func.count()).select_from(Sillon)) or 0


# --- Alta de sillón ----------------------------------------------------------------------


def test_post_sillones_crea_un_sillon_activo(client: TestClient, db_session: Session) -> None:
    respuesta = client.post("/sillones", json={"nombre": "Sillón 3"})

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert set(cuerpo) == {"id", "nombre", "activo"}
    assert cuerpo["nombre"] == "Sillón 3"
    assert cuerpo["activo"] is True
    assert _cantidad(db_session) == 1


def test_post_sillones_dos_altas_generan_ids_distintos(client: TestClient) -> None:
    uno = client.post("/sillones", json={"nombre": "Sillón A"}).json()
    otro = client.post("/sillones", json={"nombre": "Sillón B"}).json()

    assert uno["id"] != otro["id"]


def test_post_sillones_recorta_los_espacios_del_nombre(client: TestClient) -> None:
    respuesta = client.post("/sillones", json={"nombre": "  Sillón 4  "})

    assert respuesta.status_code == 201
    assert respuesta.json()["nombre"] == "Sillón 4"


@pytest.mark.parametrize(
    "body",
    [{"nombre": "   "}, {"nombre": ""}, {}, {"nombre": "x" * 51}],
    ids=["solo-espacios", "vacio", "faltante", "51-caracteres"],
)
def test_post_sillones_con_nombre_invalido_responde_422_y_no_persiste(
    client: TestClient, db_session: Session, body: dict[str, Any]
) -> None:
    respuesta = client.post("/sillones", json=body)

    assert respuesta.status_code == 422
    assert _cantidad(db_session) == 0


def test_post_sillones_acepta_un_nombre_de_50_caracteres(client: TestClient) -> None:
    respuesta = client.post("/sillones", json={"nombre": "x" * 50})

    assert respuesta.status_code == 201


# --- Estado de actividad no editable (alta) ----------------------------------------------


@pytest.mark.parametrize("activo", [True, False])
def test_post_sillones_con_activo_responde_campo_no_editable(
    client: TestClient, db_session: Session, activo: bool
) -> None:
    respuesta = client.post("/sillones", json={"nombre": "Sillón X", "activo": activo})

    assert respuesta.status_code == 422
    assert respuesta.json()["detail"]["codigo"] == "campo_no_editable"
    assert respuesta.json()["detail"]["campos"] == ["activo"]
    assert _cantidad(db_session) == 0


# --- Identificadores naturales duplicados (alta) -----------------------------------------


def test_post_sillones_con_nombre_repetido_responde_409_y_deja_uno_solo(
    client: TestClient, db_session: Session
) -> None:
    client.post("/sillones", json={"nombre": "Sillón 1"})

    respuesta = client.post("/sillones", json={"nombre": " Sillón 1 "})

    assert respuesta.status_code == 409
    assert respuesta.json() == {"detail": {"codigo": "recurso_duplicado", "campo": "nombre"}}
    assert _cantidad(db_session) == 1


def test_post_sillones_sigue_funcionando_despues_de_un_409(client: TestClient) -> None:
    client.post("/sillones", json={"nombre": "Sillón 1"})
    client.post("/sillones", json={"nombre": "Sillón 1"})

    respuesta = client.post("/sillones", json={"nombre": "Sillón 2"})

    assert respuesta.status_code == 201


# --- Edición parcial ---------------------------------------------------------------------


def _sillon(session: Session, nombre: str, *, activo: bool = True) -> Sillon:
    sillon = Sillon(nombre=nombre, activo=activo)
    session.add(sillon)
    session.flush()
    return sillon


def _en_base(session: Session, sillon: Sillon) -> Sillon:
    session.expire_all()
    return session.execute(select(Sillon).where(Sillon.id == sillon.id)).scalar_one()


def test_patch_sillones_cambia_el_nombre(client: TestClient, db_session: Session) -> None:
    sillon = _sillon(db_session, "Sillón 2")

    respuesta = client.patch(f"/sillones/{sillon.id}", json={"nombre": " Sillón Dos "})

    assert respuesta.status_code == 200
    assert respuesta.json() == {"id": str(sillon.id), "nombre": "Sillón Dos", "activo": True}
    assert _en_base(db_session, sillon).nombre == "Sillón Dos"


def test_patch_sillones_con_body_vacio_responde_200_y_no_cambia(
    client: TestClient, db_session: Session
) -> None:
    sillon = _sillon(db_session, "Sillón 2")

    respuesta = client.patch(f"/sillones/{sillon.id}", json={})

    assert respuesta.status_code == 200
    assert respuesta.json()["nombre"] == "Sillón 2"
    assert _en_base(db_session, sillon).nombre == "Sillón 2"


def test_patch_sillones_ignora_un_campo_desconocido(
    client: TestClient, db_session: Session
) -> None:
    sillon = _sillon(db_session, "Sillón 2")

    respuesta = client.patch(f"/sillones/{sillon.id}", json={"color": "azul"})

    assert respuesta.status_code == 200
    assert respuesta.json()["nombre"] == "Sillón 2"
    assert "color" not in respuesta.json()
    assert _en_base(db_session, sillon).nombre == "Sillón 2"


@pytest.mark.parametrize("cuerpo", [{"nombre": None}, {"nombre": "  "}, {"nombre": "x" * 51}])
def test_patch_sillones_con_nombre_invalido_responde_422_y_no_cambia(
    client: TestClient, db_session: Session, cuerpo: dict[str, Any]
) -> None:
    sillon = _sillon(db_session, "Sillón 2")

    respuesta = client.patch(f"/sillones/{sillon.id}", json=cuerpo)

    assert respuesta.status_code == 422
    assert _en_base(db_session, sillon).nombre == "Sillón 2"


def test_patch_sillones_inexistente_responde_404(client: TestClient) -> None:
    respuesta = client.patch(f"/sillones/{uuid4()}", json={"nombre": "Nuevo"})

    assert respuesta.status_code == 404
    assert respuesta.json() == {"detail": {"codigo": "recurso_inexistente", "recurso": "sillon"}}


def test_patch_sillones_con_body_invalido_sobre_id_inexistente_responde_422_y_no_404(
    client: TestClient,
) -> None:
    respuesta = client.patch(f"/sillones/{uuid4()}", json={"nombre": None})

    assert respuesta.status_code == 422


def test_patch_sillones_inactivo_con_activo_true_responde_campo_no_editable(
    client: TestClient, db_session: Session
) -> None:
    sillon = _sillon(db_session, "Sillón 1", activo=False)

    respuesta = client.patch(f"/sillones/{sillon.id}", json={"activo": True})

    assert respuesta.status_code == 422
    assert respuesta.json()["detail"]["codigo"] == "campo_no_editable"
    assert respuesta.json()["detail"]["campos"] == ["activo"]
    assert _en_base(db_session, sillon).activo is False


def test_patch_sillones_con_nombre_de_otro_responde_409_y_no_cambia(
    client: TestClient, db_session: Session
) -> None:
    uno = _sillon(db_session, "Sillón 1")
    dos = _sillon(db_session, "Sillón 2")

    respuesta = client.patch(f"/sillones/{dos.id}", json={"nombre": "Sillón 1"})

    assert respuesta.status_code == 409
    assert respuesta.json() == {"detail": {"codigo": "recurso_duplicado", "campo": "nombre"}}
    assert _en_base(db_session, dos).nombre == "Sillón 2"
    assert _en_base(db_session, uno).nombre == "Sillón 1"


def test_patch_sillones_con_id_mal_formado_responde_422(client: TestClient) -> None:
    respuesta = client.patch("/sillones/no-es-un-id", json={})

    assert respuesta.status_code == 422


# --- Desactivación lógica ----------------------------------------------------------------


def test_desactivar_sillon_responde_200_inactivo_y_la_fila_sigue_existiendo(
    client: TestClient, db_session: Session
) -> None:
    sillon = _sillon(db_session, "Sillón 1")

    respuesta = client.post(f"/sillones/{sillon.id}/desactivar")

    assert respuesta.status_code == 200
    assert respuesta.json() == {"id": str(sillon.id), "nombre": "Sillón 1", "activo": False}
    assert _en_base(db_session, sillon).activo is False
    assert _cantidad(db_session) == 1


def test_desactivar_sillon_ya_inactivo_responde_200_y_no_cambia_actualizado_en(
    client: TestClient, db_session: Session
) -> None:
    sillon = _sillon(db_session, "Sillón 1", activo=False)
    db_session.execute(
        update(Sillon)
        .where(Sillon.id == sillon.id)
        .values(actualizado_en=datetime(2026, 1, 1, tzinfo=UTC))
    )
    db_session.flush()

    respuesta = client.post(f"/sillones/{sillon.id}/desactivar")

    assert respuesta.status_code == 200
    assert respuesta.json()["activo"] is False
    assert _en_base(db_session, sillon).actualizado_en == datetime(2026, 1, 1, tzinfo=UTC)


def test_desactivar_sillon_inexistente_responde_404(client: TestClient) -> None:
    respuesta = client.post(f"/sillones/{uuid4()}/desactivar")

    assert respuesta.status_code == 404
    assert respuesta.json() == {"detail": {"codigo": "recurso_inexistente", "recurso": "sillon"}}


def test_desactivar_sillon_con_id_mal_formado_responde_422(client: TestClient) -> None:
    assert client.post("/sillones/no-es-un-id/desactivar").status_code == 422
