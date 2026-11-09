"""El `lifespan` de la app instala el filtro del log de acceso, una sola vez."""

import logging
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.infrastructure.log_acceso import LOGGER_ACCESO, FiltroLogAcceso, instalar_filtro_log_acceso
from app.main import create_app


@pytest.fixture
def logger_de_acceso() -> Iterator[logging.Logger]:
    """El logger de uvicorn sin filtros nuestros, y restaurado al terminar el test."""
    logger = logging.getLogger(LOGGER_ACCESO)
    originales = list(logger.filters)
    logger.filters = [f for f in logger.filters if not isinstance(f, FiltroLogAcceso)]
    yield logger
    logger.filters = originales


def _del_filtro(logger: logging.Logger) -> list[logging.Filter]:
    return [f for f in logger.filters if isinstance(f, FiltroLogAcceso)]


def test_el_lifespan_instala_el_filtro_en_el_logger_de_acceso(
    logger_de_acceso: logging.Logger,
) -> None:
    assert _del_filtro(logger_de_acceso) == []

    with TestClient(create_app()):
        assert len(_del_filtro(logger_de_acceso)) == 1


def test_arrancar_la_app_varias_veces_no_duplica_el_filtro(
    logger_de_acceso: logging.Logger,
) -> None:
    for _ in range(3):
        with TestClient(create_app()):
            pass

    assert len(_del_filtro(logger_de_acceso)) == 1


def test_el_filtro_instalado_por_el_lifespan_recorta_la_query_de_pacientes(
    logger_de_acceso: logging.Logger,
) -> None:
    with TestClient(create_app()):
        registro = logging.LogRecord(
            name=LOGGER_ACCESO,
            level=logging.INFO,
            pathname=__file__,
            lineno=0,
            msg='%s - "%s %s HTTP/%s" %d',
            args=("127.0.0.1:1", "GET", "/pacientes?q=FIC-0101", "1.1", 200),
            exc_info=None,
        )

        assert logger_de_acceso.filter(registro) is not False

    assert "FIC-0101" not in registro.getMessage()


def test_instalar_dos_veces_a_mano_tampoco_duplica(logger_de_acceso: logging.Logger) -> None:
    instalar_filtro_log_acceso()
    instalar_filtro_log_acceso()

    assert len(_del_filtro(logger_de_acceso)) == 1
