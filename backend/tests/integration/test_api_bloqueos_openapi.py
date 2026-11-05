"""Contrato OpenAPI de las rutas de bloqueos (D1, D3, D7)."""

from typing import Any

import pytest
from fastapi.testclient import TestClient

RUTAS_ESPERADAS = {
    ("GET", "/bloqueos"),
    ("POST", "/bloqueos"),
    ("DELETE", "/bloqueos/{bloqueo_id}"),
}


@pytest.fixture
def openapi(client: TestClient) -> dict[str, Any]:
    return client.get("/openapi.json").json()  # type: ignore[no-any-return]


def test_openapi_expone_exactamente_las_rutas_de_bloqueos_sin_patch_ni_put(
    openapi: dict[str, Any],
) -> None:
    publicadas = {
        (metodo.upper(), ruta)
        for ruta, operaciones in openapi["paths"].items()
        if ruta.startswith("/bloqueos")
        for metodo in operaciones
    }

    assert publicadas == RUTAS_ESPERADAS


def test_la_descripcion_de_profesional_id_documenta_que_el_odontologo_puede_omitirlo(
    openapi: dict[str, Any],
) -> None:
    descripcion = openapi["components"]["schemas"]["BloqueoIn"]["properties"]["profesional_id"][
        "description"
    ]

    assert "odontólogo puede omitirlo" in descripcion
    assert "403" in descripcion


@pytest.mark.parametrize("campo", ["inicio", "fin"])
def test_la_descripcion_de_inicio_y_fin_documenta_el_intervalo_semiabierto_con_zona_horaria(
    openapi: dict[str, Any], campo: str
) -> None:
    descripcion = openapi["components"]["schemas"]["BloqueoIn"]["properties"][campo]["description"]

    assert "[inicio, fin)" in descripcion
    assert "zona horaria" in descripcion


def test_el_filtro_de_la_consulta_documenta_la_restriccion_del_odontologo(
    openapi: dict[str, Any],
) -> None:
    parametros = openapi["paths"]["/bloqueos"]["get"]["parameters"]
    filtro = next(p for p in parametros if p["name"] == "profesional_id")

    assert "odontólogo solo puede indicar el suyo" in filtro["description"]
    assert filtro["required"] is False
