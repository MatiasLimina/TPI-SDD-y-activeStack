"""POST /auth/login de punta a punta: app real, PostgreSQL real, hasher y emisor de test."""

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.infrastructure.db.models import Profesional, Usuario
from app.infrastructure.security.contrasenas import Hasher
from tests.conftest import CONTRASENA_RECEPCIONISTA, SECRETO_TEST

RUTA = "/auth/login"
CUERPO_401 = {"detail": {"codigo": "credenciales_invalidas", "mensaje": "Credenciales inválidas"}}


@pytest.fixture
def usuarios(db_session: Session, hasher_test: Hasher, recepcionista: Usuario) -> None:
    """Se suman a `recepcionista` (activa): un inactivo (B) y un odontólogo."""
    profesional = Profesional(nombre="Ana", apellido="Ficticia")
    db_session.add(profesional)
    db_session.flush()
    db_session.add_all(
        [
            Usuario(
                email="inactivo@example.com",
                password_hash=hasher_test.hash("clave-ficticia-b"),
                rol="recepcionista",
                activo=False,
            ),
            Usuario(
                email="ana.ficticia@example.com",
                password_hash=hasher_test.hash("clave-ficticia-ana"),
                rol="odontologo",
                profesional_id=profesional.id,
            ),
        ]
    )
    db_session.flush()


def _login(cliente: TestClient, email: str, password: str, **kwargs: object):  # type: ignore[no-untyped-def]
    return cliente.post(RUTA, json={"email": email, "password": password}, **kwargs)


def test_login_valido_responde_200_con_exactamente_token_y_tipo(
    cliente_anonimo: TestClient, usuarios: None, recepcionista: Usuario
) -> None:
    respuesta = _login(cliente_anonimo, "recepcion@example.com", CONTRASENA_RECEPCIONISTA)

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert set(cuerpo) == {"access_token", "token_type"}
    assert cuerpo["token_type"] == "bearer"
    claims = jwt.decode(cuerpo["access_token"], SECRETO_TEST, algorithms=["HS256"])
    assert claims["sub"] == str(recepcionista.id)


def test_login_del_odontologo_devuelve_su_rol_y_profesional(
    cliente_anonimo: TestClient, usuarios: None, db_session: Session
) -> None:
    respuesta = _login(cliente_anonimo, "ana.ficticia@example.com", "clave-ficticia-ana")

    assert respuesta.status_code == 200
    claims = jwt.decode(respuesta.json()["access_token"], SECRETO_TEST, algorithms=["HS256"])
    assert claims["rol"] == "odontologo"
    assert claims["profesional_id"] is not None


def test_login_con_email_con_mayusculas_y_espacios(
    cliente_anonimo: TestClient, usuarios: None
) -> None:
    respuesta = _login(cliente_anonimo, "  Recepcion@Example.COM ", CONTRASENA_RECEPCIONISTA)

    assert respuesta.status_code == 200
    assert respuesta.json()["access_token"]


CASOS_DE_RECHAZO = {
    "contrasena-incorrecta": ("recepcion@example.com", "contrasena-incorrecta"),
    "inactivo-con-su-contrasena": ("inactivo@example.com", "clave-ficticia-b"),
    "email-inexistente": ("nadie@example.com", "clave-ficticia-b"),
    "contrasena-vacia": ("recepcion@example.com", ""),
}
RECHAZOS = [pytest.param(*datos, id=nombre) for nombre, datos in CASOS_DE_RECHAZO.items()]


@pytest.mark.parametrize(("email", "password"), RECHAZOS)
def test_cada_rechazo_responde_401_con_encabezado_y_cuerpo_constantes(
    cliente_anonimo: TestClient, usuarios: None, email: str, password: str
) -> None:
    respuesta = _login(cliente_anonimo, email, password)

    assert respuesta.status_code == 401
    assert respuesta.headers["www-authenticate"] == "Bearer"
    assert respuesta.json() == CUERPO_401
    assert "access_token" not in respuesta.text


def test_los_rechazos_son_indistinguibles_byte_a_byte(
    cliente_anonimo: TestClient, usuarios: None
) -> None:
    respuestas = [
        _login(cliente_anonimo, email, password) for email, password in CASOS_DE_RECHAZO.values()
    ]

    assert {r.status_code for r in respuestas} == {401}
    assert len({r.content for r in respuestas}) == 1
    assert len({tuple(sorted(r.headers.items())) for r in respuestas}) == 1


def test_el_rechazo_no_filtra_la_contrasena_enviada(
    cliente_anonimo: TestClient, usuarios: None
) -> None:
    respuesta = _login(cliente_anonimo, "nadie@example.com", "secreto-ficticio-visible")

    assert "secreto-ficticio-visible" not in respuesta.text
    assert "secreto-ficticio-visible" not in str(respuesta.headers)


@pytest.mark.parametrize(
    "cuerpo",
    [
        {"email": "recepcion@example.com"},
        {"password": CONTRASENA_RECEPCIONISTA},
        {},
        {"email": 123, "password": CONTRASENA_RECEPCIONISTA},
    ],
    ids=["sin-password", "sin-email", "vacio", "email-no-texto"],
)
def test_body_incompleto_o_con_tipos_invalidos_responde_422_sin_token(
    cliente_anonimo: TestClient, usuarios: None, cuerpo: dict[str, object]
) -> None:
    respuesta = cliente_anonimo.post(RUTA, json=cuerpo)

    assert respuesta.status_code == 422
    assert "access_token" not in respuesta.text


def test_el_login_ignora_un_authorization_invalido(
    cliente_anonimo: TestClient, usuarios: None
) -> None:
    respuesta = _login(
        cliente_anonimo,
        "recepcion@example.com",
        CONTRASENA_RECEPCIONISTA,
        headers={"Authorization": "Bearer no-es-un-jwt"},
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["access_token"]


def test_el_login_con_credenciales_invalidas_ignora_un_authorization_valido(
    client: TestClient, usuarios: None
) -> None:
    """`client` ya trae un token válido de la recepcionista: no habilita un login erróneo."""
    respuesta = _login(client, "recepcion@example.com", "contrasena-incorrecta")

    assert respuesta.status_code == 401
    assert respuesta.json() == CUERPO_401
