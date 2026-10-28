import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import Engine

from app.infrastructure.db.base import Base
from app.infrastructure.db.models import (
    Paciente,
    Prestacion,
    Profesional,
    Sillon,
    Turno,
    Usuario,
)

TABLAS_CATALOGO = {"profesional", "sillon", "prestacion", "paciente"}
TABLAS = TABLAS_CATALOGO | {"turno", "usuario"}


def test_base_metadata_registers_catalog_turno_and_usuario_tables() -> None:
    assert TABLAS <= set(Base.metadata.tables)


@pytest.mark.parametrize(
    ("modelo", "tabla"),
    [
        (Profesional, "profesional"),
        (Sillon, "sillon"),
        (Prestacion, "prestacion"),
        (Paciente, "paciente"),
        (Turno, "turno"),
        (Usuario, "usuario"),
    ],
)
def test_model_maps_to_expected_table(modelo: type[Base], tabla: str) -> None:
    assert modelo.__tablename__ == tabla


def test_autogenerate_against_migrated_database_detects_no_differences(engine: Engine) -> None:
    with engine.connect() as connection:
        context = MigrationContext.configure(
            connection, opts={"compare_type": True, "compare_server_default": True}
        )

        diferencias = compare_metadata(context, Base.metadata)

    assert diferencias == []
