"""Filtro del log de acceso de uvicorn: la búsqueda de /pacientes no queda en los logs (DD-31 o)."""

import logging
from typing import Any

import pytest

from app.infrastructure.log_acceso import FiltroLogAcceso

FORMATO_UVICORN = '%s - "%s %s HTTP/%s" %d'


def _registro(ruta_con_query: str, *, metodo: str = "GET", status: int = 200) -> logging.LogRecord:
    """Un `LogRecord` con la forma exacta que arma `uvicorn.access`."""
    return logging.LogRecord(
        name="uvicorn.access",
        level=logging.INFO,
        pathname=__file__,
        lineno=0,
        msg=FORMATO_UVICORN,
        args=("127.0.0.1:50000", metodo, ruta_con_query, "1.1", status),
        exc_info=None,
    )


@pytest.mark.parametrize(
    ("entrada", "esperada"),
    [
        ("/pacientes?q=FIC-0101&limite=10", "/pacientes"),
        ("/pacientes?q=Carla%20Imaginaria", "/pacientes"),
        (
            "/pacientes/3b241101-e2bb-4255-8caf-4136c566a962?x=dato",
            "/pacientes/3b241101-e2bb-4255-8caf-4136c566a962",
        ),
        ("/pacientes/?q=FIC-0101", "/pacientes/"),
        ("/Pacientes?q=FIC-0101", "/Pacientes"),
    ],
)
def test_recorta_la_query_de_las_rutas_de_pacientes(entrada: str, esperada: str) -> None:
    registro = _registro(entrada)

    resultado = FiltroLogAcceso().filter(registro)

    assert resultado is True
    assert registro.args == ("127.0.0.1:50000", "GET", esperada, "1.1", 200)
    mensaje = registro.getMessage()
    assert mensaje == f'127.0.0.1:50000 - "GET {esperada} HTTP/1.1" 200'
    assert "FIC-0101" not in mensaje
    assert "?" not in mensaje


@pytest.mark.parametrize(
    "ruta",
    [
        "/bloqueos?profesional_id=00000000-0000-4000-8000-000000000101",
        "/turnos?desde=2026-10-08",
        "/pacientes-otra?q=algo",  # prefijo parecido, no es /pacientes ni /pacientes/...
        "/profesionales/pacientes?q=algo",
        "/pacientes",  # sin query: nada que recortar
        "/health",
    ],
)
def test_no_toca_las_demas_rutas(ruta: str) -> None:
    registro = _registro(ruta)
    argumentos = registro.args

    resultado = FiltroLogAcceso().filter(registro)

    assert resultado is True
    assert registro.args == argumentos
    assert ruta in registro.getMessage()


def test_conserva_metodo_estado_y_cliente() -> None:
    registro = _registro("/pacientes?q=algo", metodo="POST", status=422)

    FiltroLogAcceso().filter(registro)

    assert registro.getMessage() == '127.0.0.1:50000 - "POST /pacientes HTTP/1.1" 422'


@pytest.mark.parametrize(
    "args",
    [
        (),
        None,
        ("solo", "tres", "argumentos"),
        ("127.0.0.1", "GET", 123, "1.1", 200),  # la ruta no es texto
        ("127.0.0.1", "GET", "/pacientes?q=a", "1.1", 200, "uno-de-mas"),
        ({"ruta": "/pacientes?q=a"},),  # LogRecord lo guarda como un dict
    ],
    ids=["vacios", "ninguno", "tres", "ruta-no-texto", "seis", "dict"],
)
def test_ante_registros_con_otra_forma_no_falla_ni_los_descarta(args: Any) -> None:
    registro = logging.LogRecord(
        name="uvicorn.access",
        level=logging.INFO,
        pathname=__file__,
        lineno=0,
        msg="otro mensaje",
        args=args,
        exc_info=None,
    )
    original = registro.args

    resultado = FiltroLogAcceso().filter(registro)

    assert resultado is True
    assert registro.args == original
