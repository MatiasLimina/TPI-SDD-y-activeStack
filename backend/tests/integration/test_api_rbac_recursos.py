"""RBAC de las rutas del catálogo: app real, PostgreSQL real, tokens reales."""

from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.infrastructure.db.models import Prestacion, Profesional, Sillon, Usuario
from app.infrastructure.security.tokens import EmisorTokens

CUERPO_401 = {"detail": {"codigo": "no_autenticado", "mensaje": "No autenticado"}}
CUERPO_403 = {"detail": {"codigo": "rol_insuficiente", "mensaje": "Rol insuficiente"}}

Peticion = tuple[str, str, dict[str, Any] | None]


@pytest.fixture
def sillon(db_session: Session) -> Sillon:
    sillon = Sillon(nombre="Sillón 1")
    db_session.add(sillon)
    db_session.flush()
    return sillon


@pytest.fixture
def prestacion(db_session: Session) -> Prestacion:
    prestacion = Prestacion(nombre="Limpieza", duracion_min=45)
    db_session.add(prestacion)
    db_session.flush()
    return prestacion


def _escrituras(
    profesional_id: object, sillon_id: object, prestacion_id: object
) -> dict[str, Peticion]:
    """Las 9 rutas de escritura, con un body válido en cada una."""
    return {
        "post-profesionales": (
            "POST",
            "/profesionales",
            {"nombre": "Nuevo", "apellido": "Ficticio"},
        ),
        "patch-profesionales": (
            "PATCH",
            f"/profesionales/{profesional_id}",
            {"apellido": "Cambiado"},
        ),
        "desactivar-profesionales": ("POST", f"/profesionales/{profesional_id}/desactivar", None),
        "post-sillones": ("POST", "/sillones", {"nombre": "Sillón Nuevo"}),
        "patch-sillones": ("PATCH", f"/sillones/{sillon_id}", {"nombre": "Cambiado"}),
        "desactivar-sillones": ("POST", f"/sillones/{sillon_id}/desactivar", None),
        "post-prestaciones": ("POST", "/prestaciones", {"nombre": "Nueva", "duracion_min": 30}),
        "patch-prestaciones": ("PATCH", f"/prestaciones/{prestacion_id}", {"duracion_min": 60}),
        "desactivar-prestaciones": ("POST", f"/prestaciones/{prestacion_id}/desactivar", None),
    }


RUTAS = list(_escrituras(0, 0, 0))


def _bearer(usuario: Usuario, emisor: EmisorTokens) -> dict[str, str]:
    return {"Authorization": f"Bearer {emisor.emitir(usuario)}"}


def _estado(session: Session) -> dict[str, Any]:
    """Foto del catálogo: cantidades y los valores que las escrituras podrían tocar."""
    session.expire_all()
    return {
        "profesionales": sorted(
            (p.apellido, p.activo) for p in session.scalars(select(Profesional))
        ),
        "sillones": sorted((s.nombre, s.activo) for s in session.scalars(select(Sillon))),
        "prestaciones": sorted(
            (p.nombre, p.duracion_min, p.activa) for p in session.scalars(select(Prestacion))
        ),
    }


@pytest.fixture
def anonimo(client: TestClient, cliente_anonimo: TestClient) -> TestClient:
    return cliente_anonimo


# --- Escritura reservada a la recepcionista ----------------------------------------------


@pytest.mark.parametrize("ruta", RUTAS)
def test_escritura_de_un_odontologo_responde_403_y_la_base_no_cambia(
    anonimo: TestClient,
    db_session: Session,
    odontologo: Usuario,
    emisor_test: EmisorTokens,
    sillon: Sillon,
    prestacion: Prestacion,
    ruta: str,
) -> None:
    metodo, url, body = _escrituras(odontologo.profesional_id, sillon.id, prestacion.id)[ruta]
    antes = _estado(db_session)

    respuesta = anonimo.request(metodo, url, json=body, headers=_bearer(odontologo, emisor_test))

    assert respuesta.status_code == 403
    assert respuesta.json() == CUERPO_403
    assert _estado(db_session) == antes


@pytest.mark.parametrize("ruta", RUTAS)
def test_escritura_sin_token_responde_401_y_la_base_no_cambia(
    anonimo: TestClient,
    db_session: Session,
    odontologo: Usuario,
    sillon: Sillon,
    prestacion: Prestacion,
    ruta: str,
) -> None:
    metodo, url, body = _escrituras(odontologo.profesional_id, sillon.id, prestacion.id)[ruta]
    antes = _estado(db_session)

    respuesta = anonimo.request(metodo, url, json=body)

    assert respuesta.status_code == 401
    assert respuesta.json() == CUERPO_401
    assert respuesta.headers["WWW-Authenticate"] == "Bearer"
    assert _estado(db_session) == antes


def test_la_recepcionista_si_puede_escribir_en_las_9_rutas(
    client: TestClient, odontologo: Usuario, sillon: Sillon, prestacion: Prestacion
) -> None:
    peticiones = _escrituras(odontologo.profesional_id, sillon.id, prestacion.id)

    codigos = {
        ruta: client.request(metodo, url, json=body).status_code
        for ruta, (metodo, url, body) in peticiones.items()
    }

    assert all(codigo in (200, 201) for codigo in codigos.values()), codigos


def test_odontologo_con_body_que_el_schema_rechaza_recibe_403_y_no_422(
    anonimo: TestClient, db_session: Session, odontologo: Usuario, emisor_test: EmisorTokens
) -> None:
    respuesta = anonimo.post("/sillones", json={}, headers=_bearer(odontologo, emisor_test))

    assert respuesta.status_code == 403
    assert db_session.scalar(select(func.count()).select_from(Sillon)) == 0


def test_odontologo_con_duracion_que_rechaza_el_dominio_recibe_403_y_no_422(
    anonimo: TestClient, db_session: Session, odontologo: Usuario, emisor_test: EmisorTokens
) -> None:
    respuesta = anonimo.post(
        "/prestaciones",
        json={"nombre": "Control", "duracion_min": 7},
        headers=_bearer(odontologo, emisor_test),
    )

    assert respuesta.status_code == 403
    assert db_session.scalar(select(func.count()).select_from(Prestacion)) == 0


def test_odontologo_desactivando_un_uuid_inexistente_recibe_403_y_no_404(
    anonimo: TestClient, odontologo: Usuario, emisor_test: EmisorTokens
) -> None:
    respuesta = anonimo.post(
        f"/sillones/{uuid4()}/desactivar", headers=_bearer(odontologo, emisor_test)
    )

    assert respuesta.status_code == 403


def test_odontologo_no_puede_desactivar_su_propio_profesional(
    anonimo: TestClient, db_session: Session, odontologo: Usuario, emisor_test: EmisorTokens
) -> None:
    respuesta = anonimo.post(
        f"/profesionales/{odontologo.profesional_id}/desactivar",
        headers=_bearer(odontologo, emisor_test),
    )

    assert respuesta.status_code == 403
    db_session.expire_all()
    propio = db_session.get(Profesional, odontologo.profesional_id)
    assert propio is not None
    assert propio.activo is True


# --- Lectura para ambos roles ------------------------------------------------------------


def test_odontologo_lee_los_tres_listados_y_ve_a_todos_los_profesionales(
    anonimo: TestClient,
    db_session: Session,
    odontologo: Usuario,
    emisor_test: EmisorTokens,
    sillon: Sillon,
    prestacion: Prestacion,
) -> None:
    db_session.add(Profesional(nombre="Bruno", apellido="Inventado"))
    db_session.flush()
    encabezados = _bearer(odontologo, emisor_test)

    profesionales = anonimo.get("/profesionales", headers=encabezados)
    sillones = anonimo.get("/sillones", headers=encabezados)
    prestaciones = anonimo.get("/prestaciones", headers=encabezados)

    assert (profesionales.status_code, sillones.status_code, prestaciones.status_code) == (
        200,
        200,
        200,
    )
    assert {p["apellido"] for p in profesionales.json()} == {"Ficticia", "Inventado"}


@pytest.mark.parametrize("ruta", ["/profesionales", "/sillones", "/prestaciones"])
def test_get_sin_token_responde_401_con_www_authenticate(anonimo: TestClient, ruta: str) -> None:
    respuesta = anonimo.get(ruta)

    assert respuesta.status_code == 401
    assert respuesta.json() == CUERPO_401
    assert respuesta.headers["WWW-Authenticate"] == "Bearer"


def test_get_con_id_mal_formado_sin_token_responde_401_y_no_422(anonimo: TestClient) -> None:
    assert anonimo.get("/sillones/no-es-un-id").status_code == 401


@pytest.mark.parametrize("recurso", ["profesionales", "sillones", "prestaciones"])
@pytest.mark.parametrize("metodo", ["PUT", "DELETE"])
def test_put_y_delete_sobre_un_recurso_responden_405(
    client: TestClient, recurso: str, metodo: str
) -> None:
    respuesta = client.request(metodo, f"/{recurso}/{uuid4()}")

    assert respuesta.status_code == 405


# --- Documentación de la API -------------------------------------------------------------

RUTAS_ESPERADAS = {
    ("GET", "/profesionales"),
    ("POST", "/profesionales"),
    ("GET", "/profesionales/{recurso_id}"),
    ("PATCH", "/profesionales/{recurso_id}"),
    ("POST", "/profesionales/{recurso_id}/desactivar"),
    ("GET", "/sillones"),
    ("POST", "/sillones"),
    ("GET", "/sillones/{recurso_id}"),
    ("PATCH", "/sillones/{recurso_id}"),
    ("POST", "/sillones/{recurso_id}/desactivar"),
    ("GET", "/prestaciones"),
    ("POST", "/prestaciones"),
    ("GET", "/prestaciones/{recurso_id}"),
    ("PATCH", "/prestaciones/{recurso_id}"),
    ("POST", "/prestaciones/{recurso_id}/desactivar"),
}


def test_openapi_expone_exactamente_las_15_rutas_del_catalogo(client: TestClient) -> None:
    caminos = client.get("/openapi.json").json()["paths"]

    publicadas = {
        (metodo.upper(), ruta)
        for ruta, operaciones in caminos.items()
        if ruta.split("/")[1] in {"profesionales", "sillones", "prestaciones"}
        and not ruta.endswith("/horarios")  # los horarios son de C-10 (test_api_horarios_openapi)
        and "/horarios/" not in ruta
        for metodo in operaciones
    }

    assert publicadas == RUTAS_ESPERADAS


@pytest.mark.parametrize(
    ("ruta", "esquema"),
    [
        ("/profesionales/{recurso_id}", "ProfesionalOut"),
        ("/sillones/{recurso_id}", "SillonOut"),
        ("/prestaciones/{recurso_id}", "PrestacionOut"),
    ],
)
def test_openapi_usa_el_schema_de_respuesta_propio_de_cada_recurso(
    client: TestClient, ruta: str, esquema: str
) -> None:
    operaciones = client.get("/openapi.json").json()["paths"][ruta]

    for metodo in ("get", "patch"):
        referencia = operaciones[metodo]["responses"]["200"]["content"]["application/json"]
        assert referencia["schema"]["$ref"].endswith(f"/{esquema}")
