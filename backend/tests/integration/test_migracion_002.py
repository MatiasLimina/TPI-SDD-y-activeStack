import pytest
from alembic import command
from sqlalchemy import create_engine, inspect

from tests.conftest import alembic_config

TABLAS_ESPERADAS: dict[str, set[str]] = {
    "profesional": {
        "id",
        "nombre",
        "apellido",
        "matricula",
        "activo",
        "creado_en",
        "actualizado_en",
    },
    "sillon": {"id", "nombre", "activo", "creado_en", "actualizado_en"},
    "prestacion": {
        "id",
        "nombre",
        "duracion_min",
        "requiere_sillon",
        "activa",
        "creado_en",
        "actualizado_en",
    },
    "paciente": {
        "id",
        "nombre",
        "apellido",
        "documento",
        "telefono",
        "email",
        "activo",
        "creado_en",
        "actualizado_en",
    },
}


def _columnas(url: str, tabla: str) -> set[str] | None:
    scratch = create_engine(url)
    try:
        inspector = inspect(scratch)
        if not inspector.has_table(tabla):
            return None
        return {col["name"] for col in inspector.get_columns(tabla)}
    finally:
        scratch.dispose()


@pytest.mark.parametrize("tabla", sorted(TABLAS_ESPERADAS))
def test_upgrade_head_creates_catalog_table_with_expected_columns(
    scratch_url: str, tabla: str
) -> None:
    command.upgrade(alembic_config(scratch_url), "head")

    assert _columnas(scratch_url, tabla) == TABLAS_ESPERADAS[tabla]


def test_downgrade_to_001_drops_catalog_tables_and_reupgrade_restores_them(
    scratch_url: str,
) -> None:
    config = alembic_config(scratch_url)
    command.upgrade(config, "head")

    command.downgrade(config, "001")

    assert all(_columnas(scratch_url, tabla) is None for tabla in TABLAS_ESPERADAS)

    command.upgrade(config, "head")

    assert all(_columnas(scratch_url, tabla) is not None for tabla in TABLAS_ESPERADAS)
