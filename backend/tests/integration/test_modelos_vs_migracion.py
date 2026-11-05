import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import CheckConstraint, Engine, inspect

from app.infrastructure.db.base import Base
from app.infrastructure.db.models import (
    Bloqueo,
    Paciente,
    Prestacion,
    Profesional,
    Recordatorio,
    Sillon,
    Turno,
    TurnoAuditoria,
    Usuario,
)

TABLAS_CATALOGO = {"profesional", "sillon", "prestacion", "paciente"}
TABLAS = TABLAS_CATALOGO | {"turno", "usuario", "turno_auditoria", "recordatorio", "bloqueo"}


def test_base_metadata_registers_catalog_turno_usuario_auditoria_and_recordatorio_tables() -> None:
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
        (TurnoAuditoria, "turno_auditoria"),
        (Recordatorio, "recordatorio"),
        (Bloqueo, "bloqueo"),
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


def test_recordatorio_model_declares_the_same_checks_as_the_migrated_database(
    engine: Engine,
) -> None:
    """Alembic no compara los CHECK en el autogenerate: se comparan por nombre y definición."""
    en_el_modelo = {
        c.name: str(c.sqltext)
        for c in Recordatorio.__table__.constraints
        if isinstance(c, CheckConstraint)
    }

    en_la_base = {
        c["name"]: c["sqltext"] for c in inspect(engine).get_check_constraints("recordatorio")
    }

    assert set(en_el_modelo) == set(en_la_base)
    assert "ck_recordatorio_pendiente_intentos" in en_el_modelo
    assert "intentos < 3" in en_el_modelo["ck_recordatorio_pendiente_intentos"]
