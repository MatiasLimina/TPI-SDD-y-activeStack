"""Contrato OpenAPI de las rutas de pacientes."""

from typing import Any

import pytest
from fastapi.testclient import TestClient

RUTAS_ESPERADAS = {
    ("GET", "/pacientes"),
    ("POST", "/pacientes"),
    ("GET", "/pacientes/{paciente_id}"),
    ("PATCH", "/pacientes/{paciente_id}"),
    ("POST", "/pacientes/{paciente_id}/desactivar"),
}


@pytest.fixture
def openapi(client: TestClient) -> dict[str, Any]:
    return client.get("/openapi.json").json()  # type: ignore[no-any-return]


def _parametro(openapi: dict[str, Any], nombre: str) -> dict[str, Any]:
    parametros = openapi["paths"]["/pacientes"]["get"]["parameters"]
    (encontrado,) = [p for p in parametros if p["name"] == nombre]
    return encontrado  # type: ignore[no-any-return]


def test_openapi_expone_exactamente_las_cinco_rutas_de_pacientes(
    openapi: dict[str, Any],
) -> None:
    publicadas = {
        (metodo.upper(), ruta)
        for ruta, operaciones in openapi["paths"].items()
        if ruta == "/pacientes" or ruta.startswith("/pacientes/")
        for metodo in operaciones
    }

    assert publicadas == RUTAS_ESPERADAS


def test_openapi_de_pacientes_no_publica_put_ni_delete(openapi: dict[str, Any]) -> None:
    metodos = {
        metodo
        for ruta, operaciones in openapi["paths"].items()
        if ruta.startswith("/pacientes")
        for metodo in operaciones
    }

    assert {"put", "delete"}.isdisjoint(metodos)


def test_q_documenta_los_terminos_el_plegado_y_el_maximo(openapi: dict[str, Any]) -> None:
    q = _parametro(openapi, "q")

    assert q["required"] is False
    assert "nombre, apellido o documento" in q["description"]
    assert "acentos" in q["description"]
    assert "mayúsculas" in q["description"]
    assert "espacios" in q["description"]
    assert any(opcion.get("maxLength") == 100 for opcion in q["schema"]["anyOf"])


def test_limite_documenta_su_rango_y_su_valor_por_defecto(openapi: dict[str, Any]) -> None:
    limite = _parametro(openapi, "limite")

    assert "1 a 100" in limite["description"]
    assert limite["schema"]["default"] == 50
    assert (limite["schema"]["minimum"], limite["schema"]["maximum"]) == (1, 100)


def test_desplazamiento_documenta_que_saltea_y_su_valor_por_defecto(
    openapi: dict[str, Any],
) -> None:
    desplazamiento = _parametro(openapi, "desplazamiento")

    assert "saltear" in desplazamiento["description"]
    assert desplazamiento["schema"]["default"] == 0
    assert desplazamiento["schema"]["minimum"] == 0


def test_el_detalle_documenta_la_ficha_completa_y_el_resumen(openapi: dict[str, Any]) -> None:
    respuesta = openapi["paths"]["/pacientes/{paciente_id}"]["get"]["responses"]["200"]
    opciones = respuesta["content"]["application/json"]["schema"]["anyOf"]
    esquemas = openapi["components"]["schemas"]

    referenciados = [opcion["$ref"].rsplit("/", 1)[-1] for opcion in opciones]
    assert referenciados == ["PacienteOut", "PacienteResumenOut"]
    assert set(esquemas["PacienteResumenOut"]["properties"]) == {"id", "nombre", "apellido"}
    assert set(esquemas["PacienteOut"]["properties"]) == {
        "id",
        "nombre",
        "apellido",
        "documento",
        "telefono",
        "email",
        "activo",
    }
