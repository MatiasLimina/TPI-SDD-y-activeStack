"""Reglas de dominio de pacientes (búsqueda, email), sin base de datos ni HTTP."""

import ast
from pathlib import Path

import pytest

from app.domain import pacientes
from app.domain.pacientes import PacienteAjenoError, email_valido, terminos_busqueda
from app.domain.recursos import TipoRecurso


@pytest.mark.parametrize("texto", [None, "", "   ", "\t \n"])
def test_terminos_busqueda_sin_texto_devuelve_lista_vacia(texto: str | None) -> None:
    assert terminos_busqueda(texto) == []


def test_terminos_busqueda_separa_por_espacios_sin_vacios() -> None:
    assert terminos_busqueda("  imag   carla ") == ["imag", "carla"]


def test_terminos_busqueda_pasa_a_minusculas() -> None:
    assert terminos_busqueda("IMAGINARIA Fic-0101") == ["imaginaria", "fic-0101"]


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("Pérez", ["perez"]),
        ("PÉREZ", ["perez"]),
        ("Nuñez", ["nunez"]),
        ("NUÑEZ", ["nunez"]),
        ("Güemes", ["guemes"]),
        ("ÁÉÍÓÚ áéíóú", ["aeiou", "aeiou"]),
    ],
)
def test_terminos_busqueda_pliega_acentos_dieresis_y_enie(texto: str, esperado: list[str]) -> None:
    assert terminos_busqueda(texto) == esperado


def test_terminos_busqueda_normaliza_a_nfc_antes_de_plegar() -> None:
    # "e" + U+0301 (acento combinante) es el mismo "é" que la forma compuesta
    descompuesta = "Pérez"

    assert terminos_busqueda(descompuesta) == ["perez"]


def test_terminos_busqueda_conserva_los_comodines_como_texto() -> None:
    # El escape de `%`, `_` y `\` es del repositorio: el dominio no los toca
    assert terminos_busqueda("FIC_ 100% a\\b") == ["fic_", "100%", "a\\b"]


@pytest.mark.parametrize(
    "email", ["carla@example.com", "a@b", "carla.imaginaria+turnos@example.com"]
)
def test_email_valido_acepta_una_arroba_con_texto_a_ambos_lados(email: str) -> None:
    assert email_valido(email) is True


@pytest.mark.parametrize(
    "email",
    [
        "carla.example.com",  # sin arroba
        "carla@a@example.com",  # dos arrobas
        "carla @example.com",  # espacio interno
        "carla@exa mple.com",
        "carla@example.com\t",  # cualquier espacio en blanco, no solo el común
        "@example.com",  # sin parte local
        "carla@",  # sin dominio
        "@",
        "",
    ],
)
def test_email_valido_rechaza_arroba_ausente_o_repetida_espacios_y_lados_vacios(
    email: str,
) -> None:
    assert email_valido(email) is False


def test_paciente_ajeno_error_lleva_el_mensaje_del_contrato() -> None:
    error = PacienteAjenoError()

    assert error.mensaje == "Solo podés consultar pacientes de tus turnos"
    assert str(error) == error.mensaje


def test_tipo_recurso_paciente_vale_paciente() -> None:
    assert TipoRecurso.PACIENTE.value == "paciente"


def test_tabla_de_plegado_tiene_igual_largo_en_origen_y_destino() -> None:
    # `translate` de PostgreSQL empareja posición a posición: un desfase corrompería la búsqueda
    assert len(pacientes.CARACTERES_CON_ACENTO) == len(pacientes.CARACTERES_SIN_ACENTO)
    assert len(set(pacientes.CARACTERES_CON_ACENTO)) == len(pacientes.CARACTERES_CON_ACENTO)


def test_modulo_de_pacientes_no_importa_sqlalchemy_ni_fastapi() -> None:
    arbol = ast.parse(Path(pacientes.__file__).read_text(encoding="utf-8"))
    importados: set[str] = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            importados |= {alias.name.split(".")[0] for alias in nodo.names}
        elif isinstance(nodo, ast.ImportFrom) and nodo.module:
            importados.add(nodo.module.split(".")[0])
    assert not {"sqlalchemy", "fastapi"} & importados
