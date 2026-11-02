"""Lectura del catálogo: GET de listado y detalle para ambos roles."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.infrastructure.db.models import Prestacion, Profesional, Sillon


def test_get_sillones_lista_inactivos_y_ordena_por_nombre(
    client: TestClient, db_session: Session
) -> None:
    db_session.add_all([Sillon(nombre="Sillón 2"), Sillon(nombre="Sillón 1", activo=False)])
    db_session.flush()

    respuesta = client.get("/sillones")

    assert respuesta.status_code == 200
    assert [(s["nombre"], s["activo"]) for s in respuesta.json()] == [
        ("Sillón 1", False),
        ("Sillón 2", True),
    ]


def test_get_sillones_sin_recursos_devuelve_lista_vacia(client: TestClient) -> None:
    respuesta = client.get("/sillones")

    assert respuesta.status_code == 200
    assert respuesta.json() == []


def test_get_profesionales_ordena_por_apellido_y_luego_nombre(
    client: TestClient, db_session: Session
) -> None:
    db_session.add_all(
        [
            Profesional(nombre="Ana", apellido="Beta"),
            Profesional(nombre="Zoe", apellido="Alfa"),
            Profesional(nombre="Abel", apellido="Beta"),
        ]
    )
    db_session.flush()

    respuesta = client.get("/profesionales")

    assert [(p["apellido"], p["nombre"]) for p in respuesta.json()] == [
        ("Alfa", "Zoe"),
        ("Beta", "Abel"),
        ("Beta", "Ana"),
    ]


def test_get_prestaciones_ordena_por_nombre_e_incluye_inactivas(
    client: TestClient, db_session: Session
) -> None:
    db_session.add_all(
        [
            Prestacion(nombre="Limpieza", duracion_min=45),
            Prestacion(nombre="Consulta", duracion_min=30, activa=False),
        ]
    )
    db_session.flush()

    respuesta = client.get("/prestaciones")

    assert [(p["nombre"], p["activa"]) for p in respuesta.json()] == [
        ("Consulta", False),
        ("Limpieza", True),
    ]


def test_get_prestacion_por_id_devuelve_los_cinco_campos(
    client: TestClient, db_session: Session
) -> None:
    consulta = Prestacion(nombre="Consulta", duracion_min=30, requiere_sillon=False)
    db_session.add(consulta)
    db_session.flush()

    respuesta = client.get(f"/prestaciones/{consulta.id}")

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "id": str(consulta.id),
        "nombre": "Consulta",
        "duracion_min": 30,
        "requiere_sillon": False,
        "activa": True,
    }


def test_get_profesional_desactivado_sigue_consultable(
    client: TestClient, db_session: Session
) -> None:
    ana = Profesional(nombre="Ana", apellido="Ficticia", activo=False)
    db_session.add(ana)
    db_session.flush()

    respuesta = client.get(f"/profesionales/{ana.id}")

    assert respuesta.status_code == 200
    assert respuesta.json()["activo"] is False


@pytest.mark.parametrize(
    ("ruta", "recurso"),
    [("profesionales", "profesional"), ("sillones", "sillon"), ("prestaciones", "prestacion")],
)
def test_get_detalle_inexistente_responde_404_con_el_recurso_del_path(
    client: TestClient, ruta: str, recurso: str
) -> None:
    respuesta = client.get(f"/{ruta}/{uuid4()}")

    assert respuesta.status_code == 404
    assert respuesta.json() == {"detail": {"codigo": "recurso_inexistente", "recurso": recurso}}


@pytest.mark.parametrize("ruta", ["profesionales", "sillones", "prestaciones"])
def test_get_detalle_con_id_mal_formado_responde_422(client: TestClient, ruta: str) -> None:
    assert client.get(f"/{ruta}/no-es-un-id").status_code == 422
