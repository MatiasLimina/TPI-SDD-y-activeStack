"""Migración 005: tabla turno_auditoria, sus restricciones y los triggers append-only."""

from typing import Any

from alembic import command
from sqlalchemy import create_engine, inspect, text

from tests.conftest import alembic_config

COLUMNAS = {
    "id",
    "turno_id",
    "usuario_id",
    "accion",
    "valores_previos",
    "valores_nuevos",
    "ocurrido_en",
}
FUNCION = "turno_auditoria_inmutable"


def _inspeccionar(url: str) -> dict[str, Any]:
    scratch = create_engine(url)
    try:
        inspector = inspect(scratch)
        with scratch.connect() as connection:
            funcion = connection.execute(
                text("SELECT count(*) FROM pg_proc WHERE proname = :nombre"), {"nombre": FUNCION}
            ).scalar_one()
        if not inspector.has_table("turno_auditoria"):
            return {"tabla": False, "funcion": funcion}
        with scratch.connect() as connection:
            identidad = dict(
                connection.execute(
                    text(
                        "SELECT column_name, identity_generation FROM information_schema.columns "
                        "WHERE table_name = 'turno_auditoria' AND is_identity = 'YES'"
                    )
                ).all()
            )
            triggers = {
                nombre: definicion
                for nombre, definicion in connection.execute(
                    text(
                        "SELECT tgname, pg_get_triggerdef(oid) FROM pg_trigger "
                        "WHERE tgrelid = 'turno_auditoria'::regclass AND NOT tgisinternal"
                    )
                ).all()
            }
            definiciones = dict(
                connection.execute(
                    text(
                        "SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint "
                        "WHERE conrelid = 'turno_auditoria'::regclass"
                    )
                ).all()
            )
        return {
            "tabla": True,
            "funcion": funcion,
            "columnas": {c["name"]: c for c in inspector.get_columns("turno_auditoria")},
            "identidad": identidad,
            "checks": {c["name"] for c in inspector.get_check_constraints("turno_auditoria")},
            "definiciones": definiciones,
            "fks": {
                fk["constrained_columns"][0]: (fk["referred_table"], fk["options"].get("ondelete"))
                for fk in inspector.get_foreign_keys("turno_auditoria")
            },
            "pk": inspector.get_pk_constraint("turno_auditoria"),
            "indices": {
                i["name"]: i["column_names"] for i in inspector.get_indexes("turno_auditoria")
            },
            "triggers": triggers,
        }
    finally:
        scratch.dispose()


def test_upgrade_head_creates_turno_auditoria_with_expected_columns_and_types(
    scratch_url: str,
) -> None:
    command.upgrade(alembic_config(scratch_url), "head")

    esquema = _inspeccionar(scratch_url)

    columnas = esquema["columnas"]
    assert set(columnas) == COLUMNAS
    assert str(columnas["id"]["type"]) == "BIGINT"
    assert str(columnas["turno_id"]["type"]) == "UUID"
    assert str(columnas["usuario_id"]["type"]) == "UUID"
    assert str(columnas["accion"]["type"]) == "VARCHAR(20)"
    assert str(columnas["valores_previos"]["type"]) == "JSONB"
    assert str(columnas["valores_nuevos"]["type"]) == "JSONB"
    assert columnas["ocurrido_en"]["type"].timezone is True
    assert esquema["pk"]["name"] == "pk_turno_auditoria"
    assert esquema["pk"]["constrained_columns"] == ["id"]


def test_id_is_generated_always_identity_and_only_valores_previos_is_nullable(
    scratch_url: str,
) -> None:
    command.upgrade(alembic_config(scratch_url), "head")

    esquema = _inspeccionar(scratch_url)

    assert esquema["identidad"] == {"id": "ALWAYS"}
    assert {n for n, c in esquema["columnas"].items() if c["nullable"]} == {"valores_previos"}
    assert esquema["columnas"]["ocurrido_en"]["default"] is None


def test_checks_and_foreign_keys_encode_the_integrity_rules(scratch_url: str) -> None:
    command.upgrade(alembic_config(scratch_url), "head")

    esquema = _inspeccionar(scratch_url)

    assert esquema["checks"] == {
        "ck_turno_auditoria_accion_valida",
        "ck_turno_auditoria_previos_segun_accion",
    }
    accion = esquema["definiciones"]["ck_turno_auditoria_accion_valida"]
    assert all(valor in accion for valor in ("crear", "reprogramar", "cancelar"))
    coherencia = esquema["definiciones"]["ck_turno_auditoria_previos_segun_accion"]
    assert "valores_previos IS NULL" in coherencia
    assert esquema["fks"] == {
        "turno_id": ("turno", "RESTRICT"),
        "usuario_id": ("usuario", "RESTRICT"),
    }


def test_indexes_cover_the_ordered_query_and_the_user_foreign_key(scratch_url: str) -> None:
    command.upgrade(alembic_config(scratch_url), "head")

    indices = _inspeccionar(scratch_url)["indices"]

    assert indices["ix_turno_auditoria_turno_id"] == ["turno_id", "id"]
    assert indices["ix_turno_auditoria_usuario_id"] == ["usuario_id"]


def test_upgrade_head_installs_append_only_triggers_for_row_and_truncate(
    scratch_url: str,
) -> None:
    command.upgrade(alembic_config(scratch_url), "head")

    esquema = _inspeccionar(scratch_url)

    assert esquema["funcion"] == 1
    triggers = list(esquema["triggers"].values())
    assert len(triggers) == 2
    por_fila = [t for t in triggers if "FOR EACH ROW" in t]
    por_sentencia = [t for t in triggers if "FOR EACH STATEMENT" in t]
    assert len(por_fila) == 1
    # pg_get_triggerdef normaliza el orden de los eventos
    assert "BEFORE DELETE OR UPDATE" in por_fila[0]
    assert len(por_sentencia) == 1
    assert "BEFORE TRUNCATE" in por_sentencia[0]


def test_downgrade_to_004_drops_table_triggers_and_function_and_reupgrade_restores_them(
    scratch_url: str,
) -> None:
    config = alembic_config(scratch_url)
    command.upgrade(config, "head")

    command.downgrade(config, "004")

    sin_tabla = _inspeccionar(scratch_url)
    assert sin_tabla == {"tabla": False, "funcion": 0}

    command.upgrade(config, "head")

    restaurado = _inspeccionar(scratch_url)
    assert restaurado["tabla"] is True
    assert set(restaurado["columnas"]) == COLUMNAS
    assert restaurado["funcion"] == 1
    assert len(restaurado["triggers"]) == 2
