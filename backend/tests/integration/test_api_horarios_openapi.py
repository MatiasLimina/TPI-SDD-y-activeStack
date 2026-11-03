"""Contrato OpenAPI de las rutas de horarios (D1, D6, D9)."""

from typing import Any

import pytest
from fastapi.testclient import TestClient

RUTAS_ESPERADAS = {
    ("GET", "/profesionales/{profesional_id}/horarios"),
    ("POST", "/profesionales/{profesional_id}/horarios"),
    ("PATCH", "/profesionales/{profesional_id}/horarios/{horario_id}"),
    ("DELETE", "/profesionales/{profesional_id}/horarios/{horario_id}"),
}


@pytest.fixture
def openapi(client: TestClient) -> dict[str, Any]:
    return client.get("/openapi.json").json()  # type: ignore[no-any-return]


def test_openapi_expone_exactamente_las_rutas_de_horarios_sin_put(
    openapi: dict[str, Any],
) -> None:
    publicadas = {
        (metodo.upper(), ruta)
        for ruta, operaciones in openapi["paths"].items()
        if ruta.startswith("/profesionales/{profesional_id}/horarios")
        for metodo in operaciones
    }

    assert publicadas == RUTAS_ESPERADAS


@pytest.mark.parametrize("esquema", ["FranjaIn", "FranjaCambios", "FranjaOut"])
def test_la_descripcion_de_dia_semana_documenta_la_convencion(
    openapi: dict[str, Any], esquema: str
) -> None:
    propiedad = openapi["components"]["schemas"][esquema]["properties"]["dia_semana"]

    assert "0 = lunes … 6 = domingo" in propiedad["description"]


@pytest.mark.parametrize(
    ("ruta", "metodo"),
    [
        ("/profesionales/{profesional_id}/horarios", "post"),
        ("/profesionales/{profesional_id}/horarios/{horario_id}", "patch"),
    ],
)
def test_alta_y_edicion_aclaran_que_un_turno_debe_caber_en_una_unica_franja(
    openapi: dict[str, Any], ruta: str, metodo: str
) -> None:
    descripcion = openapi["paths"][ruta][metodo]["description"]

    assert "caber completo en una única franja" in descripcion
