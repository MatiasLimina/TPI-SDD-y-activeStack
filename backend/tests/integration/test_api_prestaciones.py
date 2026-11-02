"""API de prestaciones contra PostgreSQL real: alta, edición, desactivación y consulta."""

from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.infrastructure.db.models import Prestacion


def _cantidad(session: Session) -> int:
    session.expire_all()
    return session.scalar(select(func.count()).select_from(Prestacion)) or 0


# --- Alta de prestación con duración por defecto -----------------------------------------


def test_post_prestaciones_sin_requiere_sillon_lo_deja_en_true(
    client: TestClient, db_session: Session
) -> None:
    respuesta = client.post(
        "/prestaciones", json={"nombre": "Endodoncia ficticia", "duracion_min": 90}
    )

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert set(cuerpo) == {"id", "nombre", "duracion_min", "requiere_sillon", "activa"}
    assert cuerpo["duracion_min"] == 90
    assert cuerpo["requiere_sillon"] is True
    assert cuerpo["activa"] is True
    assert _cantidad(db_session) == 1


def test_post_prestaciones_sin_sillon_respeta_requiere_sillon_false(client: TestClient) -> None:
    respuesta = client.post(
        "/prestaciones", json={"nombre": "Control", "duracion_min": 15, "requiere_sillon": False}
    )

    assert respuesta.status_code == 201
    assert respuesta.json()["requiere_sillon"] is False


def test_post_prestaciones_recorta_el_nombre(client: TestClient) -> None:
    respuesta = client.post(
        "/prestaciones", json={"nombre": "  Blanqueamiento ficticio  ", "duracion_min": 60}
    )

    assert respuesta.status_code == 201
    assert respuesta.json()["nombre"] == "Blanqueamiento ficticio"


@pytest.mark.parametrize(
    "body",
    [
        {"duracion_min": 30},
        {"nombre": "Sin duración"},
        {"nombre": "   ", "duracion_min": 30},
        {"nombre": "x" * 101, "duracion_min": 30},
        {"nombre": "Texto", "duracion_min": "abc"},
    ],
    ids=["sin-nombre", "sin-duracion", "nombre-espacios", "nombre-101", "duracion-texto"],
)
def test_post_prestaciones_invalida_responde_422_y_no_persiste(
    client: TestClient, db_session: Session, body: dict[str, Any]
) -> None:
    respuesta = client.post("/prestaciones", json=body)

    assert respuesta.status_code == 422
    assert _cantidad(db_session) == 0


# --- Duración de la prestación validada por la API ---------------------------------------


def _error_duracion(respuesta: Any) -> None:
    assert respuesta.status_code == 422
    detalle = respuesta.json()["detail"]
    assert detalle["codigo"] == "duracion_invalida"
    assert detalle["mensaje"]


@pytest.mark.parametrize("duracion", [0, 485, 7, -5])
def test_post_prestaciones_con_duracion_fuera_de_la_grilla_responde_duracion_invalida(
    client: TestClient, db_session: Session, duracion: int
) -> None:
    respuesta = client.post("/prestaciones", json={"nombre": "Control", "duracion_min": duracion})

    _error_duracion(respuesta)
    assert _cantidad(db_session) == 0


@pytest.mark.parametrize("duracion", [5, 480])
def test_post_prestaciones_acepta_los_extremos_de_la_grilla(
    client: TestClient, duracion: int
) -> None:
    respuesta = client.post("/prestaciones", json={"nombre": "Extremo", "duracion_min": duracion})

    assert respuesta.status_code == 201
    assert respuesta.json()["duracion_min"] == duracion


def test_post_prestaciones_acepta_un_decimal_entero_y_rechaza_uno_con_fraccion(
    client: TestClient, db_session: Session
) -> None:
    entero = client.post("/prestaciones", json={"nombre": "Entera", "duracion_min": 45.0})
    fraccion = client.post("/prestaciones", json={"nombre": "Fracción", "duracion_min": 45.5})

    assert entero.status_code == 201
    assert entero.json()["duracion_min"] == 45
    assert fraccion.status_code == 422
    assert _cantidad(db_session) == 1


# --- Estado de actividad no editable (alta) ----------------------------------------------


def test_post_prestaciones_con_activa_responde_campo_no_editable(
    client: TestClient, db_session: Session
) -> None:
    respuesta = client.post(
        "/prestaciones",
        json={"nombre": "Consulta de urgencia", "duracion_min": 30, "activa": False},
    )

    assert respuesta.status_code == 422
    detalle = respuesta.json()["detail"]
    assert detalle["codigo"] == "campo_no_editable"
    assert detalle["campos"] == ["activa"]
    assert "/desactivar" in detalle["mensaje"]
    assert _cantidad(db_session) == 0


def test_post_prestaciones_con_activa_true_tambien_se_rechaza(client: TestClient) -> None:
    respuesta = client.post(
        "/prestaciones", json={"nombre": "Otra", "duracion_min": 30, "activa": True}
    )

    assert respuesta.status_code == 422
    assert respuesta.json()["detail"]["campos"] == ["activa"]


# --- Identificadores naturales duplicados (alta) -----------------------------------------


def test_post_prestaciones_con_nombre_repetido_responde_409_y_conserva_la_original(
    client: TestClient, db_session: Session
) -> None:
    client.post("/prestaciones", json={"nombre": "Limpieza", "duracion_min": 45})

    respuesta = client.post("/prestaciones", json={"nombre": "Limpieza", "duracion_min": 30})

    assert respuesta.status_code == 409
    assert respuesta.json() == {"detail": {"codigo": "recurso_duplicado", "campo": "nombre"}}
    db_session.expire_all()
    filas = db_session.scalars(select(Prestacion)).all()
    assert [(p.nombre, p.duracion_min) for p in filas] == [("Limpieza", 45)]


# --- Edición parcial ---------------------------------------------------------------------


def _prestacion(
    session: Session,
    nombre: str,
    duracion_min: int,
    *,
    requiere_sillon: bool = True,
    activa: bool = True,
) -> Prestacion:
    prestacion = Prestacion(
        nombre=nombre, duracion_min=duracion_min, requiere_sillon=requiere_sillon, activa=activa
    )
    session.add(prestacion)
    session.flush()
    return prestacion


def _en_base(session: Session, prestacion: Prestacion) -> Prestacion:
    session.expire_all()
    return session.execute(select(Prestacion).where(Prestacion.id == prestacion.id)).scalar_one()


def test_patch_prestaciones_cambia_requiere_sillon_y_conserva_la_duracion(
    client: TestClient, db_session: Session
) -> None:
    control = _prestacion(db_session, "Control", 15, requiere_sillon=False)

    respuesta = client.patch(f"/prestaciones/{control.id}", json={"requiere_sillon": True})

    assert respuesta.status_code == 200
    assert respuesta.json()["requiere_sillon"] is True
    assert respuesta.json()["duracion_min"] == 15
    assert _en_base(db_session, control).requiere_sillon is True


def test_patch_prestaciones_cambia_la_duracion_dentro_de_la_grilla(
    client: TestClient, db_session: Session
) -> None:
    limpieza = _prestacion(db_session, "Limpieza", 45)

    respuesta = client.patch(f"/prestaciones/{limpieza.id}", json={"duracion_min": 60})

    assert respuesta.status_code == 200
    assert respuesta.json()["duracion_min"] == 60
    assert _en_base(db_session, limpieza).duracion_min == 60


@pytest.mark.parametrize("duracion", [485, 7, 0])
def test_patch_prestaciones_con_duracion_invalida_responde_422_y_conserva_la_duracion(
    client: TestClient, db_session: Session, duracion: int
) -> None:
    limpieza = _prestacion(db_session, "Limpieza", 45)

    respuesta = client.patch(f"/prestaciones/{limpieza.id}", json={"duracion_min": duracion})

    _error_duracion(respuesta)
    assert _en_base(db_session, limpieza).duracion_min == 45


@pytest.mark.parametrize("campo", ["nombre", "duracion_min", "requiere_sillon"])
def test_patch_prestaciones_con_nulo_en_campo_obligatorio_responde_422_y_no_cambia(
    client: TestClient, db_session: Session, campo: str
) -> None:
    limpieza = _prestacion(db_session, "Limpieza", 45)

    respuesta = client.patch(f"/prestaciones/{limpieza.id}", json={campo: None})

    assert respuesta.status_code == 422
    en_base = _en_base(db_session, limpieza)
    assert (en_base.nombre, en_base.duracion_min, en_base.requiere_sillon) == ("Limpieza", 45, True)


def test_patch_prestaciones_con_activa_responde_campo_no_editable(
    client: TestClient, db_session: Session
) -> None:
    vieja = _prestacion(db_session, "Vieja", 30, activa=False)

    respuesta = client.patch(f"/prestaciones/{vieja.id}", json={"activa": True})

    assert respuesta.status_code == 422
    assert respuesta.json()["detail"]["campos"] == ["activa"]
    assert _en_base(db_session, vieja).activa is False


def test_patch_prestaciones_con_nombre_de_otra_responde_409(
    client: TestClient, db_session: Session
) -> None:
    _prestacion(db_session, "Limpieza", 45)
    consulta = _prestacion(db_session, "Consulta", 30)

    respuesta = client.patch(f"/prestaciones/{consulta.id}", json={"nombre": "Limpieza"})

    assert respuesta.status_code == 409
    assert respuesta.json()["detail"]["campo"] == "nombre"
    assert _en_base(db_session, consulta).nombre == "Consulta"


def test_patch_prestaciones_inexistente_responde_404_con_el_recurso_correcto(
    client: TestClient,
) -> None:
    respuesta = client.patch(f"/prestaciones/{uuid4()}", json={"requiere_sillon": False})

    assert respuesta.status_code == 404
    assert respuesta.json()["detail"]["recurso"] == "prestacion"


# --- Desactivación lógica ----------------------------------------------------------------


def test_desactivar_prestacion_responde_200_inactiva(
    client: TestClient, db_session: Session
) -> None:
    limpieza = _prestacion(db_session, "Limpieza", 45)

    respuesta = client.post(f"/prestaciones/{limpieza.id}/desactivar")

    assert respuesta.status_code == 200
    assert respuesta.json()["activa"] is False
    assert _en_base(db_session, limpieza).activa is False


def test_desactivar_prestacion_ya_inactiva_responde_200_sin_cambios(
    client: TestClient, db_session: Session
) -> None:
    vieja = _prestacion(db_session, "Vieja", 30, activa=False)

    respuesta = client.post(f"/prestaciones/{vieja.id}/desactivar")

    assert respuesta.status_code == 200
    assert respuesta.json()["activa"] is False
    assert respuesta.json()["duracion_min"] == 30


def test_desactivar_prestacion_inexistente_responde_404_con_el_recurso_correcto(
    client: TestClient,
) -> None:
    respuesta = client.post(f"/prestaciones/{uuid4()}/desactivar")

    assert respuesta.status_code == 404
    assert respuesta.json()["detail"]["recurso"] == "prestacion"
