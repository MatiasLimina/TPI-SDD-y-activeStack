from alembic import command
from sqlalchemy import create_engine, inspect, text

from tests.conftest import alembic_config

COLUMNAS_USUARIO = {
    "id",
    "email",
    "password_hash",
    "rol",
    "profesional_id",
    "activo",
    "creado_en",
    "actualizado_en",
}


def _inspeccionar(url: str) -> dict[str, object]:
    scratch = create_engine(url)
    try:
        inspector = inspect(scratch)
        fks_turno = {
            fk["constrained_columns"][0]: (fk["referred_table"], fk["options"].get("ondelete"))
            for fk in inspector.get_foreign_keys("turno")
        }
        indices_turno = {i["name"]: i for i in inspector.get_indexes("turno")}
        if not inspector.has_table("usuario"):
            return {"usuario": False, "fks_turno": fks_turno, "indices_turno": indices_turno}
        with scratch.connect() as connection:
            definiciones = dict(
                connection.execute(
                    text(
                        "SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint "
                        "WHERE conrelid = 'usuario'::regclass"
                    )
                ).all()
            )
            indice_parcial = connection.execute(
                text(
                    "SELECT indexdef FROM pg_indexes "
                    "WHERE tablename = 'usuario' AND indexname = 'uq_usuario_profesional_activo'"
                )
            ).scalar_one_or_none()
        columnas = {c["name"]: c for c in inspector.get_columns("usuario")}
        return {
            "usuario": True,
            "columnas": columnas,
            "checks": {c["name"] for c in inspector.get_check_constraints("usuario")},
            "uniques": {
                u["name"]: u["column_names"] for u in inspector.get_unique_constraints("usuario")
            },
            "indices": {i["name"] for i in inspector.get_indexes("usuario")},
            "definiciones": definiciones,
            "indice_parcial": indice_parcial,
            "fks": {
                fk["constrained_columns"][0]: (fk["referred_table"], fk["options"].get("ondelete"))
                for fk in inspector.get_foreign_keys("usuario")
            },
            "fks_turno": fks_turno,
            "indices_turno": indices_turno,
        }
    finally:
        scratch.dispose()


def test_upgrade_head_creates_usuario_with_columns_checks_unique_and_indexes(
    scratch_url: str,
) -> None:
    command.upgrade(alembic_config(scratch_url), "head")

    esquema = _inspeccionar(scratch_url)

    assert set(esquema["columnas"]) == COLUMNAS_USUARIO
    assert esquema["checks"] == {
        "ck_usuario_rol_valido",
        "ck_usuario_profesional_segun_rol",
        "ck_usuario_email_normalizado",
    }
    assert esquema["uniques"] == {"uq_usuario_email": ["email"]}
    assert {"ix_usuario_profesional_id", "uq_usuario_profesional_activo"} <= esquema["indices"]
    assert esquema["fks"] == {"profesional_id": ("profesional", "RESTRICT")}


def test_usuario_columns_have_expected_nullability_and_activo_defaults_to_true(
    scratch_url: str,
) -> None:
    command.upgrade(alembic_config(scratch_url), "head")

    columnas = _inspeccionar(scratch_url)["columnas"]

    assert {n for n, c in columnas.items() if c["nullable"]} == {"profesional_id"}
    assert "true" in str(columnas["activo"]["default"])


def test_unique_profesional_index_is_partial_on_activo(scratch_url: str) -> None:
    command.upgrade(alembic_config(scratch_url), "head")

    indice = _inspeccionar(scratch_url)["indice_parcial"]

    assert indice is not None
    assert "UNIQUE" in indice
    assert "(profesional_id)" in indice
    assert "WHERE activo" in indice


def test_check_definitions_encode_the_business_rules(scratch_url: str) -> None:
    command.upgrade(alembic_config(scratch_url), "head")

    definiciones = _inspeccionar(scratch_url)["definiciones"]

    assert "recepcionista" in definiciones["ck_usuario_rol_valido"]
    assert "odontologo" in definiciones["ck_usuario_rol_valido"]
    assert "profesional_id IS NOT NULL" in definiciones["ck_usuario_profesional_segun_rol"]
    assert "btrim" in definiciones["ck_usuario_email_normalizado"]
    assert "lower" in definiciones["ck_usuario_email_normalizado"]


def test_upgrade_head_adds_creado_por_fk_restrict_and_index_to_turno(scratch_url: str) -> None:
    command.upgrade(alembic_config(scratch_url), "head")

    esquema = _inspeccionar(scratch_url)

    assert esquema["fks_turno"]["creado_por"] == ("usuario", "RESTRICT")
    assert esquema["indices_turno"]["ix_turno_creado_por"]["column_names"] == ["creado_por"]


def test_downgrade_to_003_drops_usuario_and_turno_fk_and_reupgrade_restores_them(
    scratch_url: str,
) -> None:
    config = alembic_config(scratch_url)
    command.upgrade(config, "head")

    command.downgrade(config, "003")

    sin_usuario = _inspeccionar(scratch_url)
    assert sin_usuario["usuario"] is False
    assert "creado_por" not in sin_usuario["fks_turno"]
    assert "ix_turno_creado_por" not in sin_usuario["indices_turno"]

    command.upgrade(config, "head")

    restaurado = _inspeccionar(scratch_url)
    assert set(restaurado["columnas"]) == COLUMNAS_USUARIO
    assert restaurado["fks_turno"]["creado_por"] == ("usuario", "RESTRICT")
    assert "ix_turno_creado_por" in restaurado["indices_turno"]
