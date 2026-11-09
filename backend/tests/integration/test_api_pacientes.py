"""API de pacientes (escritura) contra PostgreSQL real: alta, validaciones, edición y estado."""

from typing import Any
from uuid import UUID

import pytest
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


# --- Campos mínimos y textos normalizados -------------------------------------------------

TEXTOS = ["nombre", "apellido", "documento", "telefono", "email"]
LARGOS = {"nombre": 100, "apellido": 100, "documento": 20, "telefono": 30, "email": 254}


def _email_de(largo: int) -> str:
    """Email bien formado con exactamente `largo` caracteres."""
    return "a" * (largo - len("@example.com")) + "@example.com"


def _valor_de_largo(campo: str, largo: int) -> str:
    return _email_de(largo) if campo == "email" else "x" * largo


@pytest.mark.parametrize("campo", ["nombre", "apellido", "documento", "telefono"])
def test_post_pacientes_sin_un_campo_obligatorio_responde_422_y_no_persiste(
    client: TestClient, db_session: Session, campo: str
) -> None:
    body = _body()
    del body[campo]

    respuesta = client.post("/pacientes", json=body)

    assert respuesta.status_code == 422
    assert _cantidad(db_session) == 0


@pytest.mark.parametrize("campo", ["nombre", "apellido", "documento", "telefono"])
@pytest.mark.parametrize("valor", ["   ", ""])
def test_post_pacientes_con_un_obligatorio_en_blanco_responde_422(
    client: TestClient, db_session: Session, campo: str, valor: str
) -> None:
    respuesta = client.post("/pacientes", json=_body(**{campo: valor}))

    assert respuesta.status_code == 422
    assert _cantidad(db_session) == 0


@pytest.mark.parametrize("campo", TEXTOS)
def test_post_pacientes_con_un_texto_mas_largo_que_su_columna_responde_422_no_500(
    client: TestClient, db_session: Session, campo: str
) -> None:
    respuesta = client.post(
        "/pacientes", json=_body(**{campo: _valor_de_largo(campo, LARGOS[campo] + 1)})
    )

    assert respuesta.status_code == 422
    assert _cantidad(db_session) == 0


def test_post_pacientes_acepta_los_cinco_textos_con_su_largo_maximo(client: TestClient) -> None:
    textos = {campo: _valor_de_largo(campo, largo) for campo, largo in LARGOS.items()}

    respuesta = client.post("/pacientes", json=_body(**textos))

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert {campo: cuerpo[campo] for campo in textos} == textos


def test_post_pacientes_recorta_los_espacios_extremos(client: TestClient) -> None:
    respuesta = client.post(
        "/pacientes",
        json=_body(
            nombre="  Elena  ",
            apellido="\tImaginaria ",
            documento=" FIC-0103 ",
            telefono="  +54 11 5555-0103 ",
            email="  elena@example.com ",
        ),
    )

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["nombre"] == "Elena"
    assert cuerpo["apellido"] == "Imaginaria"
    assert cuerpo["documento"] == "FIC-0103"
    assert cuerpo["telefono"] == "+54 11 5555-0103"
    assert cuerpo["email"] == "elena@example.com"


def test_post_pacientes_no_recorta_los_espacios_internos(client: TestClient) -> None:
    respuesta = client.post("/pacientes", json=_body(nombre="Ana  María"))

    assert respuesta.json()["nombre"] == "Ana  María"


@pytest.mark.parametrize("email", ["   ", ""])
def test_post_pacientes_con_email_en_blanco_lo_guarda_como_nulo(
    client: TestClient, db_session: Session, email: str
) -> None:
    respuesta = client.post("/pacientes", json=_body(email=email))

    assert respuesta.status_code == 201
    assert respuesta.json()["email"] is None
    assert _en_base(db_session, respuesta.json()["id"]).email is None


def test_post_pacientes_con_email_nulo_explicito_lo_guarda_como_nulo(client: TestClient) -> None:
    respuesta = client.post("/pacientes", json=_body(email=None))

    assert respuesta.status_code == 201
    assert respuesta.json()["email"] is None


def test_post_pacientes_no_exige_formato_a_documento_ni_telefono(client: TestClient) -> None:
    numerico = client.post(
        "/pacientes", json=_body(documento="00000104", telefono="11 5555-0104", email=None)
    )
    con_prefijo = client.post(
        "/pacientes",
        json=_body(documento="FIC-0104", telefono="+54 (11) 5555 0105", email=None),
    )

    assert numerico.status_code == 201
    assert (numerico.json()["documento"], numerico.json()["telefono"]) == (
        "00000104",
        "11 5555-0104",
    )
    assert con_prefijo.status_code == 201
    assert (con_prefijo.json()["documento"], con_prefijo.json()["telefono"]) == (
        "FIC-0104",
        "+54 (11) 5555 0105",
    )


@pytest.mark.parametrize("campo", TEXTOS)
def test_post_pacientes_con_caracter_nulo_responde_422_no_500(
    client: TestClient, db_session: Session, campo: str
) -> None:
    valor = "a\x00b@example.com" if campo == "email" else "a\x00b"

    respuesta = client.post("/pacientes", json=_body(**{campo: valor}))

    assert respuesta.status_code == 422
    assert _cantidad(db_session) == 0


# --- Formato mínimo del email -------------------------------------------------------------


@pytest.mark.parametrize(
    "email",
    [
        "carla.example.com",
        "carla @example.com",
        "carla@exam ple.com",
        "@example.com",
        "carla@",
        "carla@a@example.com",
        "carla\t@example.com",
    ],
    ids=[
        "sin-arroba",
        "espacio-local",
        "espacio-dominio",
        "sin-local",
        "sin-dominio",
        "dos",
        "tab",
    ],
)
def test_post_pacientes_con_email_mal_formado_responde_422_y_no_persiste(
    client: TestClient, db_session: Session, email: str
) -> None:
    respuesta = client.post("/pacientes", json=_body(email=email))

    assert respuesta.status_code == 422
    assert _cantidad(db_session) == 0


def test_post_pacientes_guarda_el_email_como_se_envio_sin_cambiar_mayusculas(
    client: TestClient,
) -> None:
    respuesta = client.post("/pacientes", json=_body(email="Carla.Imaginaria@Example.COM"))

    assert respuesta.status_code == 201
    assert respuesta.json()["email"] == "Carla.Imaginaria@Example.COM"


def test_post_pacientes_admite_un_email_repetido_entre_pacientes(
    client: TestClient, db_session: Session
) -> None:
    uno = _crear(client, email="familia@example.com")
    otro = _crear(client, documento="FIC-0102", email="familia@example.com")

    assert uno["id"] != otro["id"]
    assert _en_base(db_session, uno["id"]).email == "familia@example.com"
    assert _en_base(db_session, otro["id"]).email == "familia@example.com"
