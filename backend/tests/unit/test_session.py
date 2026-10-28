"""El engine de producción no debe filtrar parámetros SQL (p. ej. hashes) en mensajes de error."""

from collections.abc import Iterator
from types import SimpleNamespace

import pytest

from app.infrastructure.db import session as modulo_session


@pytest.fixture
def engine_de_produccion(monkeypatch: pytest.MonkeyPatch) -> Iterator[object]:
    monkeypatch.setattr(
        modulo_session,
        "get_settings",
        lambda: SimpleNamespace(DATABASE_URL="postgresql+psycopg://u:p@localhost:1/ficticia"),
    )
    modulo_session.get_engine.cache_clear()
    try:
        yield modulo_session.get_engine()
    finally:
        modulo_session.dispose_engine()
        modulo_session.get_engine.cache_clear()


def test_engine_de_produccion_oculta_los_parametros_de_las_sentencias(
    engine_de_produccion: modulo_session.Engine,
) -> None:
    assert engine_de_produccion.hide_parameters is True
