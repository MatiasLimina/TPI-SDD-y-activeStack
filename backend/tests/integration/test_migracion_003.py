from alembic import command
from sqlalchemy import create_engine, inspect, text

from tests.conftest import alembic_config

COLUMNAS_TURNO = {
    "id",
    "profesional_id",
    "paciente_id",
    "prestacion_id",
    "sillon_id",
    "inicio",
    "fin",
    "duracion_min",
    "estado",
    "motivo_cancelacion",
    "creado_por",
    "creado_en",
    "actualizado_en",
}
EXCLUSIONES = {
    "turno_sin_solape_profesional",
    "turno_sin_solape_sillon",
    "turno_sin_solape_paciente",
}


def _inspeccionar(url: str) -> dict[str, object]:
    scratch = create_engine(url)
    try:
        inspector = inspect(scratch)
        if not inspector.has_table("turno"):
            return {}
        with scratch.connect() as connection:
            exclusiones = {
                fila[0]
                for fila in connection.execute(
                    text("SELECT conname FROM pg_constraint WHERE contype = 'x'")
                )
            }
        return {
            "columnas": {c["name"] for c in inspector.get_columns("turno")},
            "fks": {
                fk["constrained_columns"][0]: (fk["referred_table"], fk["options"].get("ondelete"))
                for fk in inspector.get_foreign_keys("turno")
            },
            "checks": {c["name"] for c in inspector.get_check_constraints("turno")},
            "exclusiones": exclusiones,
            "indices": {i["name"] for i in inspector.get_indexes("turno")},
        }
    finally:
        scratch.dispose()


def test_upgrade_head_creates_turno_with_columns_fks_checks_and_exclusions(
    scratch_url: str,
) -> None:
    command.upgrade(alembic_config(scratch_url), "003")

    esquema = _inspeccionar(scratch_url)

    assert esquema["columnas"] == COLUMNAS_TURNO
    assert esquema["fks"] == {
        "profesional_id": ("profesional", "RESTRICT"),
        "paciente_id": ("paciente", "RESTRICT"),
        "prestacion_id": ("prestacion", "RESTRICT"),
        "sillon_id": ("sillon", "RESTRICT"),
    }
    assert esquema["checks"] == {"ck_turno_estado_valido", "ck_turno_fin_mayor"}
    assert esquema["exclusiones"] == EXCLUSIONES
    assert {"ix_turno_profesional_id_inicio", "ix_turno_sillon_id_inicio"} <= esquema["indices"]


def test_exclusion_de_sillon_ignora_turnos_sin_sillon(scratch_url: str) -> None:
    command.upgrade(alembic_config(scratch_url), "003")
    engine = create_engine(scratch_url)
    try:
        with engine.connect() as connection:
            definicion = connection.execute(
                text(
                    "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
                    "WHERE conname = 'turno_sin_solape_sillon'"
                )
            ).scalar_one()
    finally:
        engine.dispose()

    assert "sillon_id IS NOT NULL" in definicion
    assert "cancelado" in definicion


def test_downgrade_drops_turno_and_reupgrade_restores_it(scratch_url: str) -> None:
    config = alembic_config(scratch_url)
    command.upgrade(config, "003")

    command.downgrade(config, "002")

    assert _inspeccionar(scratch_url) == {}

    command.upgrade(config, "003")

    assert _inspeccionar(scratch_url)["columnas"] == COLUMNAS_TURNO
