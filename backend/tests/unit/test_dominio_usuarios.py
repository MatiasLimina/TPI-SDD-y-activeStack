import ast
from pathlib import Path
from uuid import uuid4

import pytest

from app.domain.usuarios import (
    AltaUsuarioInvalidaError,
    Rol,
    normalizar_email,
    validar_alta,
    validar_forma_email,
)


@pytest.mark.parametrize(
    ("crudo", "esperado"),
    [
        ("  Recepcion@Example.COM  ", "recepcion@example.com"),
        ("ya@normalizado.com", "ya@normalizado.com"),
        ("\tMAYUS@X.com\n", "mayus@x.com"),
    ],
)
def test_normalizar_email_quita_espacios_y_pasa_a_minusculas(crudo: str, esperado: str) -> None:
    assert normalizar_email(crudo) == esperado


@pytest.mark.parametrize("email", ["a@b", "recepcion@example.com", "a.b+c@d.e.f"])
def test_validar_forma_email_acepta_formas_validas(email: str) -> None:
    validar_forma_email(email)


@pytest.mark.parametrize(
    "email",
    [
        "",
        "sin-arroba",
        "a@",
        "@b",
        "a@@b",
        "a b@c",
        "a\t@b",
        "a\x00@b",
        "a@b\n",
    ],
)
def test_validar_forma_email_rechaza_formas_invalidas(email: str) -> None:
    with pytest.raises(AltaUsuarioInvalidaError) as error:
        validar_forma_email(email)

    assert error.value.codigo == "email_invalido"


def test_rol_es_un_str_con_los_dos_valores_del_dominio() -> None:
    assert Rol.RECEPCIONISTA == "recepcionista"
    assert Rol.ODONTOLOGO == "odontologo"
    assert {rol.value for rol in Rol} == {"recepcionista", "odontologo"}
    assert isinstance(Rol.RECEPCIONISTA, str)


def test_validar_alta_acepta_recepcionista_sin_profesional() -> None:
    validar_alta("recepcionista", None)


def test_validar_alta_acepta_odontologo_con_profesional() -> None:
    validar_alta("odontologo", uuid4())


def test_validar_alta_acepta_el_enum() -> None:
    validar_alta(Rol.RECEPCIONISTA, None)
    validar_alta(Rol.ODONTOLOGO, uuid4())


@pytest.mark.parametrize(
    ("rol", "profesional_id", "codigo"),
    [
        ("odontologo", None, "profesional_requerido"),
        ("recepcionista", uuid4(), "profesional_no_permitido"),
        ("administrador", None, "rol_invalido"),
        ("", None, "rol_invalido"),
        ("administrador", uuid4(), "rol_invalido"),
    ],
)
def test_validar_alta_rechaza_combinaciones_invalidas_con_codigo_propio(
    rol: str, profesional_id: object, codigo: str
) -> None:
    with pytest.raises(AltaUsuarioInvalidaError) as error:
        validar_alta(rol, profesional_id)  # type: ignore[arg-type]

    assert error.value.codigo == codigo
    assert error.value.mensaje
    assert str(error.value) == error.value.mensaje


def test_el_modulo_de_usuarios_no_importa_sqlalchemy_ni_fastapi() -> None:
    ruta = Path(__file__).parents[2] / "app" / "domain" / "usuarios.py"
    importados: set[str] = set()
    for nodo in ast.walk(ast.parse(ruta.read_text("utf-8"))):
        if isinstance(nodo, ast.Import):
            importados.update(alias.name.split(".")[0] for alias in nodo.names)
        elif isinstance(nodo, ast.ImportFrom) and nodo.module and nodo.level == 0:
            importados.add(nodo.module.split(".")[0])

    assert "uuid" in importados  # el parseo detecta imports reales
    assert importados.isdisjoint({"sqlalchemy", "fastapi", "starlette"})
