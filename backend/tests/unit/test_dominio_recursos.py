"""Reglas de dominio del catálogo (profesionales, sillones, prestaciones), sin base de datos."""

import ast
from pathlib import Path

import pytest

from app.domain import recursos
from app.domain.grilla import MENSAJE_DURACION_INVALIDA
from app.domain.recursos import (
    EstadoNoEditableError,
    RecursoDuplicadoError,
    RecursoInexistenteError,
    RecursoInvalidoError,
    TipoRecurso,
    normalizar_matricula,
    validar_duracion_prestacion,
)


@pytest.mark.parametrize("duracion_min", [5, 45, 480])
def test_validar_duracion_prestacion_acepta_duraciones_de_la_grilla(duracion_min: int) -> None:
    validar_duracion_prestacion(duracion_min)


@pytest.mark.parametrize("duracion_min", [0, -5, 7, 485])
def test_validar_duracion_prestacion_rechaza_con_el_mismo_codigo_y_mensaje_que_los_turnos(
    duracion_min: int,
) -> None:
    with pytest.raises(RecursoInvalidoError) as excinfo:
        validar_duracion_prestacion(duracion_min)

    assert excinfo.value.codigo == "duracion_invalida"
    assert excinfo.value.mensaje == MENSAJE_DURACION_INVALIDA


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        ("  MN-0001 ", "MN-0001"),
        ("MN-0002", "MN-0002"),
        ("", None),
        ("   ", None),
        (None, None),
    ],
)
def test_normalizar_matricula_recorta_y_convierte_vacia_en_nula(
    valor: str | None, esperado: str | None
) -> None:
    assert normalizar_matricula(valor) == esperado


def test_estado_no_editable_expone_los_campos_y_apunta_a_desactivar() -> None:
    error = EstadoNoEditableError(["activa"])

    assert error.campos == ("activa",)
    assert "/desactivar" in error.mensaje


def test_estado_no_editable_conserva_todos_los_campos_recibidos() -> None:
    assert EstadoNoEditableError(["activo", "activa"]).campos == ("activo", "activa")


@pytest.mark.parametrize("tipo", list(TipoRecurso))
def test_recurso_inexistente_expone_el_tipo(tipo: TipoRecurso) -> None:
    assert RecursoInexistenteError(tipo).tipo is tipo


def test_recurso_duplicado_expone_tipo_y_campo() -> None:
    error = RecursoDuplicadoError(TipoRecurso.PROFESIONAL, "matricula")

    assert error.tipo is TipoRecurso.PROFESIONAL
    assert error.campo == "matricula"


def test_los_valores_de_tipo_recurso_son_los_del_contrato_http() -> None:
    assert [tipo.value for tipo in TipoRecurso] == [
        "profesional",
        "sillon",
        "prestacion",
        "horario",
        "bloqueo",
    ]


def test_modulo_de_recursos_no_importa_sqlalchemy_ni_fastapi() -> None:
    arbol = ast.parse(Path(recursos.__file__).read_text(encoding="utf-8"))
    importados: set[str] = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            importados |= {alias.name.split(".")[0] for alias in nodo.names}
        elif isinstance(nodo, ast.ImportFrom) and nodo.module:
            importados.add(nodo.module.split(".")[0])
    assert not {"sqlalchemy", "fastapi"} & importados
