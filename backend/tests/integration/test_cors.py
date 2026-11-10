"""CORS de la API (C-14, spec `app-configuration`): `create_app()` real, sin mocks."""

from collections.abc import Callable, Iterator

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.infrastructure.db.session import get_session
from app.main import create_app

ORIGEN = "http://localhost:5173"
ORIGEN_AJENO = "http://sitio-ajeno.example.com"
ID_PACIENTE = "00000000-0000-4000-8000-000000000001"
ID_BLOQUEO = "00000000-0000-4000-8000-000000000002"
CONSULTA_AGENDA = "/turnos?desde=2026-11-09&hasta=2026-11-09"


@pytest.fixture
def cliente_con_cors(
    monkeypatch: pytest.MonkeyPatch, db_session: Session
) -> Iterator[Callable[[str], TestClient]]:
    """Construye la app con `CORS_ORIGINS` por entorno, que gana sobre el `.env`."""
    clientes: list[TestClient] = []

    def construir(cors_origins: str) -> TestClient:
        monkeypatch.setenv("CORS_ORIGINS", cors_origins)
        app = create_app()
        app.dependency_overrides[get_session] = lambda: db_session
        cliente = TestClient(app)
        cliente.__enter__()
        clientes.append(cliente)
        return cliente

    yield construir
    for cliente in clientes:
        cliente.__exit__(None, None, None)


def preflight(
    cliente: TestClient,
    ruta: str,
    metodo: str,
    encabezados: str | None = None,
    origen: str = ORIGEN,
):
    pedido = {"Origin": origen, "Access-Control-Request-Method": metodo}
    if encabezados is not None:
        pedido["Access-Control-Request-Headers"] = encabezados
    return cliente.options(ruta, headers=pedido)


def test_preflight_get_with_authorization_from_allowed_origin(
    cliente_con_cors: Callable[[str], TestClient],
) -> None:
    respuesta = preflight(cliente_con_cors(ORIGEN), "/turnos", "GET", "authorization")

    assert respuesta.status_code == 200
    assert respuesta.headers["access-control-allow-origin"] == ORIGEN
    assert "authorization" in respuesta.headers["access-control-allow-headers"].lower()
    assert "access-control-allow-credentials" not in respuesta.headers


def test_preflight_of_login_allows_post_with_content_type(
    cliente_con_cors: Callable[[str], TestClient],
) -> None:
    respuesta = preflight(cliente_con_cors(ORIGEN), "/auth/login", "POST", "content-type")

    assert respuesta.status_code == 200
    assert respuesta.headers["access-control-allow-origin"] == ORIGEN
    assert "content-type" in respuesta.headers["access-control-allow-headers"].lower()
    assert "POST" in respuesta.headers["access-control-allow-methods"]
    assert "access-control-allow-credentials" not in respuesta.headers


@pytest.mark.parametrize(
    ("ruta", "metodo", "encabezados"),
    [
        (f"/pacientes/{ID_PACIENTE}", "PATCH", "authorization, content-type"),
        (f"/bloqueos/{ID_BLOQUEO}", "DELETE", "authorization"),
    ],
)
def test_preflight_allows_patch_and_delete(
    cliente_con_cors: Callable[[str], TestClient], ruta: str, metodo: str, encabezados: str
) -> None:
    respuesta = preflight(cliente_con_cors(ORIGEN), ruta, metodo, encabezados)

    assert respuesta.status_code == 200
    assert respuesta.headers["access-control-allow-origin"] == ORIGEN
    assert "access-control-allow-credentials" not in respuesta.headers


@pytest.mark.parametrize(("metodo", "encabezados"), [("PUT", None), ("GET", "x-otro")])
def test_preflight_with_method_or_header_not_allowed_is_400(
    cliente_con_cors: Callable[[str], TestClient], metodo: str, encabezados: str | None
) -> None:
    respuesta = preflight(cliente_con_cors(ORIGEN), "/turnos", metodo, encabezados)

    # Estas respuestas sí llevan Access-Control-Allow-Origin: lo que rechaza es el estado
    assert respuesta.status_code == 400
    assert respuesta.headers["access-control-allow-origin"] == ORIGEN


def test_preflight_from_other_origin_is_400_without_allow_origin(
    cliente_con_cors: Callable[[str], TestClient],
) -> None:
    respuesta = preflight(cliente_con_cors(ORIGEN), "/turnos", "GET", origen=ORIGEN_AJENO)

    assert respuesta.status_code == 400
    assert "access-control-allow-origin" not in respuesta.headers


def test_several_origins_with_spaces_are_allowed(
    cliente_con_cors: Callable[[str], TestClient],
) -> None:
    cliente = cliente_con_cors("http://localhost:5173, http://consultorio.example.com")

    segundo = preflight(cliente, "/turnos", "GET", origen="http://consultorio.example.com")
    primero = preflight(cliente, "/turnos", "GET")

    assert segundo.headers["access-control-allow-origin"] == "http://consultorio.example.com"
    assert primero.headers["access-control-allow-origin"] == ORIGEN


def test_empty_list_allows_no_origin(cliente_con_cors: Callable[[str], TestClient]) -> None:
    respuesta = preflight(cliente_con_cors(""), "/turnos", "GET")

    assert respuesta.status_code == 400
    assert "access-control-allow-origin" not in respuesta.headers


def test_authentication_error_is_readable_by_the_allowed_origin(
    cliente_con_cors: Callable[[str], TestClient],
) -> None:
    respuesta = cliente_con_cors(ORIGEN).get(CONSULTA_AGENDA, headers={"Origin": ORIGEN})

    assert respuesta.status_code == 401
    assert respuesta.json()["detail"]["codigo"] == "no_autenticado"
    assert respuesta.headers["access-control-allow-origin"] == ORIGEN
    assert "access-control-allow-credentials" not in respuesta.headers


def test_other_origin_does_not_skip_authentication_nor_get_allow_origin(
    cliente_con_cors: Callable[[str], TestClient],
) -> None:
    respuesta = cliente_con_cors(ORIGEN).get(CONSULTA_AGENDA, headers={"Origin": ORIGEN_AJENO})

    assert respuesta.status_code == 401
    assert "access-control-allow-origin" not in respuesta.headers


def test_request_without_origin_gets_no_cors_headers(
    cliente_con_cors: Callable[[str], TestClient],
) -> None:
    respuesta = cliente_con_cors(ORIGEN).get("/health")

    assert respuesta.status_code == 200
    assert "access-control-allow-origin" not in respuesta.headers


@pytest.mark.parametrize("valor", ["*", "http://localhost:5173, *"])
def test_wildcard_makes_startup_fail_naming_the_variable(
    monkeypatch: pytest.MonkeyPatch, valor: str
) -> None:
    monkeypatch.setenv("CORS_ORIGINS", valor)
    app = create_app()

    with pytest.raises(ValidationError, match="CORS_ORIGINS"):
        with TestClient(app):
            pass


def test_wildcard_does_not_break_creating_the_app_nor_allow_origins(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "*")

    app = create_app()
    respuesta = preflight(TestClient(app), "/turnos", "GET", origen=ORIGEN_AJENO)

    assert "access-control-allow-origin" not in respuesta.headers
