"""Migración 008: tabla recordatorio, sus restricciones e índices."""

from typing import Any

from alembic import command
from sqlalchemy import create_engine, inspect, text

from tests.conftest import alembic_config

COLUMNAS = {
    "id",
    "turno_id",
    "programado_para",
    "estado",
    "canal",
    "intentos",
    "creado_en",
    "actualizado_en",
}
CHECKS = {
    "ck_recordatorio_estado_valido",
    "ck_recordatorio_canal_valido",
    "ck_recordatorio_intentos_rango",
    "ck_recordatorio_intentos_segun_estado",
}


def _inspeccionar(url: str) -> dict[str, Any]:
    scratch = create_engine(url)
    try:
        inspector = inspect(scratch)
        if not inspector.has_table("recordatorio"):
            return {"tabla": False}
        with scratch.connect() as connection:
            definiciones = dict(
                connection.execute(
                    text(
                        "SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint "
                        "WHERE conrelid = 'recordatorio'::regclass"
                    )
                ).all()
            )
            indices = dict(
                connection.execute(
                    text(
                        "SELECT indexname, indexdef FROM pg_indexes "
                        "WHERE tablename = 'recordatorio'"
                    )
                ).all()
            )
        return {
            "tabla": True,
            "columnas": {c["name"]: c for c in inspector.get_columns("recordatorio")},
            "checks": {c["name"] for c in inspector.get_check_constraints("recordatorio")},
            "definiciones": definiciones,
            "fks": {
                fk["constrained_columns"][0]: (fk["referred_table"], fk["options"].get("ondelete"))
                for fk in inspector.get_foreign_keys("recordatorio")
            },
            "pk": inspector.get_pk_constraint("recordatorio"),
            "indices": indices,
        }
    finally:
        scratch.dispose()


def test_upgrade_head_creates_recordatorio_with_expected_columns_types_and_defaults(
    scratch_url: str,
) -> None:
    command.upgrade(alembic_config(scratch_url), "head")

    columnas = _inspeccionar(scratch_url)["columnas"]

    assert set(columnas) == COLUMNAS
    assert str(columnas["id"]["type"]) == "UUID"
    assert "gen_random_uuid()" in columnas["id"]["default"]
    assert str(columnas["turno_id"]["type"]) == "UUID"
    assert columnas["programado_para"]["type"].timezone is True
    assert str(columnas["estado"]["type"]) == "VARCHAR(20)"
    assert "'pendiente'" in columnas["estado"]["default"]
    assert str(columnas["canal"]["type"]) == "VARCHAR(20)"
    assert str(columnas["intentos"]["type"]) == "INTEGER"
    assert columnas["intentos"]["default"] == "0"
    assert columnas["creado_en"]["type"].timezone is True
    assert columnas["actualizado_en"]["type"].timezone is True


def test_upgrade_head_recordatorio_columns_are_not_null_and_programado_para_has_no_default(
    scratch_url: str,
) -> None:
    command.upgrade(alembic_config(scratch_url), "head")

    columnas = _inspeccionar(scratch_url)["columnas"]

    for nombre in ("turno_id", "programado_para", "estado", "canal", "intentos"):
        assert columnas[nombre]["nullable"] is False, nombre
    assert columnas["programado_para"]["default"] is None
    assert columnas["canal"]["default"] is None
    assert columnas["turno_id"]["default"] is None


def test_upgrade_head_creates_recordatorio_check_constraints(scratch_url: str) -> None:
    command.upgrade(alembic_config(scratch_url), "008")

    esquema = _inspeccionar(scratch_url)

    assert esquema["checks"] == CHECKS
    definiciones = esquema["definiciones"]
    for estado in ("pendiente", "enviado", "fallido", "cancelado"):
        assert f"'{estado}'" in definiciones["ck_recordatorio_estado_valido"]
    assert "'mock'" in definiciones["ck_recordatorio_canal_valido"]
    assert "intentos >= 0" in definiciones["ck_recordatorio_intentos_rango"]
    assert "intentos <= 3" in definiciones["ck_recordatorio_intentos_rango"]
    segun_estado = definiciones["ck_recordatorio_intentos_segun_estado"]
    assert "'fallido'" in segun_estado
    assert "'enviado'" in segun_estado


def test_upgrade_head_creates_pk_and_restrict_foreign_key_to_turno(scratch_url: str) -> None:
    command.upgrade(alembic_config(scratch_url), "head")

    esquema = _inspeccionar(scratch_url)

    assert esquema["pk"]["constrained_columns"] == ["id"]
    assert esquema["fks"] == {"turno_id": ("turno", "RESTRICT")}


def test_upgrade_head_creates_unique_partial_index_one_pending_per_turno(
    scratch_url: str,
) -> None:
    command.upgrade(alembic_config(scratch_url), "head")

    definicion = _inspeccionar(scratch_url)["indices"]["ux_recordatorio_turno_pendiente"]

    assert "CREATE UNIQUE INDEX" in definicion
    assert "(turno_id)" in definicion
    assert "estado)::text = 'pendiente'" in definicion


def test_upgrade_head_creates_fk_index_and_partial_programado_para_index(
    scratch_url: str,
) -> None:
    command.upgrade(alembic_config(scratch_url), "head")

    indices = _inspeccionar(scratch_url)["indices"]

    assert set(indices) == {
        "pk_recordatorio",
        "ux_recordatorio_turno_pendiente",
        "ix_recordatorio_turno_id",
        "ix_recordatorio_pendiente_programado_para",
    }
    assert "(turno_id)" in indices["ix_recordatorio_turno_id"]
    assert "UNIQUE" not in indices["ix_recordatorio_turno_id"]
    parcial = indices["ix_recordatorio_pendiente_programado_para"]
    assert "(programado_para)" in parcial
    assert "estado)::text = 'pendiente'" in parcial
    assert "UNIQUE" not in parcial


def test_downgrade_to_007_drops_table_and_reupgrade_restores_it(scratch_url: str) -> None:
    config = alembic_config(scratch_url)
    command.upgrade(config, "008")

    command.downgrade(config, "007")

    assert _inspeccionar(scratch_url) == {"tabla": False}

    command.upgrade(config, "008")

    restaurado = _inspeccionar(scratch_url)
    assert restaurado["tabla"] is True
    assert set(restaurado["columnas"]) == COLUMNAS
    assert restaurado["checks"] == CHECKS
    assert "ux_recordatorio_turno_pendiente" in restaurado["indices"]
