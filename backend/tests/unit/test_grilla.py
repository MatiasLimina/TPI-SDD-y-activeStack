"""Regla de duración compartida por turnos y prestaciones (DD-15), sin base de datos."""

import ast
from pathlib import Path

import pytest

from app.domain import grilla
from app.domain.grilla import duracion_en_grilla


@pytest.mark.parametrize("duracion_min", [5, 45, 480])
def test_duracion_en_grilla_acepta_multiplos_de_5_hasta_480(duracion_min: int) -> None:
    assert duracion_en_grilla(duracion_min) is True


@pytest.mark.parametrize("duracion_min", [0, -5, 7, 42, 485])
def test_duracion_en_grilla_rechaza_cero_negativos_fuera_de_grilla_y_mayores_a_480(
    duracion_min: int,
) -> None:
    assert duracion_en_grilla(duracion_min) is False


def test_constantes_de_la_grilla_tienen_los_valores_de_dd_15() -> None:
    assert grilla.GRILLA_MIN == 5
    assert grilla.DURACION_MAX_MIN == 480
    assert "5" in grilla.MENSAJE_DURACION_INVALIDA
    assert "480" in grilla.MENSAJE_DURACION_INVALIDA


def test_modulo_de_grilla_no_importa_sqlalchemy_ni_fastapi() -> None:
    arbol = ast.parse(Path(grilla.__file__).read_text(encoding="utf-8"))
    importados = {
        (nodo.module or "").split(".")[0] if isinstance(nodo, ast.ImportFrom) else alias.name
        for nodo in ast.walk(arbol)
        if isinstance(nodo, ast.Import | ast.ImportFrom)
        for alias in (nodo.names if isinstance(nodo, ast.Import) else [None])
    }
    assert not {"sqlalchemy", "fastapi"} & importados
