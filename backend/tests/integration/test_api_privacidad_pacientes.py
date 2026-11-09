"""Errores de /pacientes sin datos personales: app real, PostgreSQL real."""

from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.infrastructure.db.models import Paciente

VALOR_PRIVADO = "texto-privado-9f3c"


def _paciente(session: Session) -> Paciente:
    paciente = Paciente(
        nombre="Carla",
        apellido="Imaginaria",
        documento="FIC-0101",
        telefono="+54 11 5555-0101",
        email="carla@example.com",
    )
    session.add(paciente)
    session.flush()
    return paciente


def _campos(respuesta: Any) -> list[str]:
    """Los `loc` de cada error de validación, como texto."""
    return [".".join(str(parte) for parte in error["loc"]) for error in respuesta.json()["detail"]]


def test_422_por_campo_faltante_indica_el_campo_y_no_reproduce_lo_enviado(
    client: TestClient,
) -> None:
    respuesta = client.post(
        "/pacientes", json={"nombre": "Carla", "apellido": "Imaginaria", "documento": "FIC-0101"}
    )

    assert respuesta.status_code == 422
    assert "body.telefono" in _campos(respuesta)
    for dato in ["Carla", "Imaginaria", "FIC-0101"]:
        assert dato not in respuesta.text


def test_cada_error_de_validacion_trae_solo_type_loc_y_msg(client: TestClient) -> None:
    respuesta = client.post("/pacientes", json={"nombre": VALOR_PRIVADO})

    assert respuesta.status_code == 422
    errores = respuesta.json()["detail"]
    assert errores
    for error in errores:
        assert set(error) == {"type", "loc", "msg"}
    assert VALOR_PRIVADO not in respuesta.text


def test_422_por_email_invalido_en_el_alta_no_reproduce_el_valor(client: TestClient) -> None:
    respuesta = client.post(
        "/pacientes",
        json={
            "nombre": "Carla",
            "apellido": "Imaginaria",
            "documento": "FIC-0101",
            "telefono": "+54 11 5555-0101",
            "email": "no-es-un-email",
        },
    )

    assert respuesta.status_code == 422
    assert "body.email" in _campos(respuesta)
    assert "no-es-un-email" not in respuesta.text


def test_422_por_email_invalido_en_la_edicion_no_reproduce_el_valor(
    client: TestClient, db_session: Session
) -> None:
    paciente = _paciente(db_session)

    respuesta = client.patch(f"/pacientes/{paciente.id}", json={"email": "no-es-un-email"})

    assert respuesta.status_code == 422
    assert "body.email" in _campos(respuesta)
    assert "no-es-un-email" not in respuesta.text


@pytest.mark.parametrize("campo", ["nombre", "apellido", "documento", "telefono"])
def test_422_por_texto_demasiado_largo_no_reproduce_el_valor(
    client: TestClient, db_session: Session, campo: str
) -> None:
    paciente = _paciente(db_session)
    largo = VALOR_PRIVADO + "x" * 120

    respuesta = client.patch(f"/pacientes/{paciente.id}", json={campo: largo})

    assert respuesta.status_code == 422
    assert f"body.{campo}" in " ".join(_campos(respuesta))
    assert VALOR_PRIVADO not in respuesta.text


def test_422_por_caracter_nulo_no_reproduce_el_valor(client: TestClient) -> None:
    respuesta = client.post(
        "/pacientes",
        json={
            "nombre": f"{VALOR_PRIVADO}\x00",
            "apellido": "Imaginaria",
            "documento": "FIC-0101",
            "telefono": "+54 11 5555-0101",
        },
    )

    assert respuesta.status_code == 422
    assert VALOR_PRIVADO not in respuesta.text


def test_422_por_identificador_mal_formado_no_reproduce_el_valor(client: TestClient) -> None:
    respuesta = client.get("/pacientes/no-es-un-id")

    assert respuesta.status_code == 422
    assert "path.paciente_id" in _campos(respuesta)
    assert "no-es-un-id" not in respuesta.text
    # pydantic cita el primer carácter inválido: el manejador lo reemplaza por un mensaje fijo
    assert respuesta.json()["detail"][0]["msg"] == "Input should be a valid UUID"


@pytest.mark.parametrize(
    ("metodo", "ruta"),
    [("PATCH", "/pacientes/{}"), ("POST", "/pacientes/{}/desactivar")],
)
def test_422_por_identificador_mal_formado_en_edicion_y_desactivacion(
    client: TestClient, metodo: str, ruta: str
) -> None:
    respuesta = client.request(metodo, ruta.format("id-privado-de-prueba"), json={})

    assert respuesta.status_code == 422
    assert "id-privado-de-prueba" not in respuesta.text


def test_422_por_busqueda_demasiado_larga_no_reproduce_el_texto(client: TestClient) -> None:
    texto = VALOR_PRIVADO + "a" * 100

    respuesta = client.get("/pacientes", params={"q": texto})

    assert respuesta.status_code == 422
    assert "query.q" in _campos(respuesta)
    assert VALOR_PRIVADO not in respuesta.text


def test_422_por_limite_invalido_indica_el_parametro(client: TestClient) -> None:
    respuesta = client.get("/pacientes?limite=abc-privado")

    assert respuesta.status_code == 422
    assert "query.limite" in _campos(respuesta)
    assert "abc-privado" not in respuesta.text


def test_422_por_json_invalido_no_reproduce_el_body(client: TestClient) -> None:
    respuesta = client.post(
        "/pacientes",
        content='{"nombre": "' + VALOR_PRIVADO + '", ',
        headers={"Content-Type": "application/json"},
    )

    assert respuesta.status_code == 422
    assert VALOR_PRIVADO not in respuesta.text


def test_409_por_documento_repetido_no_incluye_el_documento_ni_datos_del_existente(
    client: TestClient, db_session: Session
) -> None:
    _paciente(db_session)

    respuesta = client.post(
        "/pacientes",
        json={
            "nombre": "Otra",
            "apellido": "Persona",
            "documento": "FIC-0101",
            "telefono": "+54 11 5555-0000",
        },
    )

    assert respuesta.status_code == 409
    assert respuesta.json() == {"detail": {"codigo": "recurso_duplicado", "campo": "documento"}}
    for dato in ["FIC-0101", "Carla", "Imaginaria", "carla@example.com", "5555-0101"]:
        assert dato not in respuesta.text


def test_las_otras_rutas_conservan_el_422_por_defecto_con_input(client: TestClient) -> None:
    respuesta = client.post("/sillones", json={})

    assert respuesta.status_code == 422
    error = respuesta.json()["detail"][0]
    assert error["input"] == {}
    assert error["type"] == "missing"


def test_otra_ruta_con_valor_invalido_sigue_devolviendo_el_input_enviado(
    client: TestClient,
) -> None:
    respuesta = client.post("/sillones", json={"nombre": "x" * 51})

    assert respuesta.status_code == 422
    assert respuesta.json()["detail"][0]["input"] == "x" * 51


def test_una_ruta_con_prefijo_parecido_no_cae_en_el_manejador_de_pacientes(
    client: TestClient,
) -> None:
    respuesta = client.get("/profesionales/no-es-un-id")

    assert respuesta.status_code == 422
    assert respuesta.json()["detail"][0]["input"] == "no-es-un-id"
