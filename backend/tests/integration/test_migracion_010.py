"""Migración 010: tabla `bloqueo` con sus CHECKs, FKs e índice (reversible)."""

from collections.abc import Iterator
from contextlib import contextmanager

from alembic import command
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from tests.conftest import alembic_config
from tests.integration.test_migrations import current_revision


@contextmanager
def _sesion(url: str) -> Iterator[Session]:
    motor = create_engine(url)
    try:
        with Session(motor) as sesion:
            yield sesion
    finally:
        motor.dispose()


def _consultar(url: str, sql: str) -> list[tuple[object, ...]]:
    with _sesion(url) as sesion:
        return [tuple(fila) for fila in sesion.execute(text(sql)).all()]


def _existe_tabla(url: str) -> bool:
    return _consultar(url, "SELECT to_regclass('public.bloqueo') IS NOT NULL") == [(True,)]


def _checks(url: str) -> dict[str, str]:
    filas = _consultar(
        url,
        "SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint "
        "WHERE conrelid = 'bloqueo'::regclass AND contype = 'c'",
    )
    return {str(nombre): str(definicion) for nombre, definicion in filas}


def _fks(url: str) -> dict[str, str]:
    filas = _consultar(
        url,
        "SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint "
        "WHERE conrelid = 'bloqueo'::regclass AND contype = 'f'",
    )
    return {str(nombre): str(definicion) for nombre, definicion in filas}


def _columnas(url: str) -> dict[str, tuple[str, str]]:
    filas = _consultar(
        url,
        "SELECT column_name, data_type, is_nullable FROM information_schema.columns "
        "WHERE table_name = 'bloqueo'",
    )
    return {str(c): (str(tipo), str(nulo)) for c, tipo, nulo in filas}


def _indices(url: str) -> dict[str, str]:
    filas = _consultar(
        url, "SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'bloqueo'"
    )
    return {str(nombre): str(definicion) for nombre, definicion in filas}


def test_upgrade_head_crea_la_tabla_bloqueo_con_checks_fks_e_indice(scratch_url: str) -> None:
    command.upgrade(alembic_config(scratch_url), "head")

    assert current_revision(scratch_url) == "010"
    assert _existe_tabla(scratch_url)
    checks = _checks(scratch_url)
    assert set(checks) == {"ck_bloqueo_fin_mayor", "ck_bloqueo_motivo_no_vacio"}
    assert "fin > inicio" in checks["ck_bloqueo_fin_mayor"]
    assert "btrim" in checks["ck_bloqueo_motivo_no_vacio"]
    indices = _indices(scratch_url)
    assert "(profesional_id, inicio)" in indices["ix_bloqueo_profesional_id_inicio"]


def test_upgrade_head_declara_instantes_timestamptz_y_motivo_y_autor_obligatorios(
    scratch_url: str,
) -> None:
    command.upgrade(alembic_config(scratch_url), "head")

    columnas = _columnas(scratch_url)

    assert columnas["inicio"] == ("timestamp with time zone", "NO")
    assert columnas["fin"] == ("timestamp with time zone", "NO")
    assert columnas["motivo"] == ("character varying", "NO")
    assert columnas["creado_por"] == ("uuid", "NO")
    assert columnas["profesional_id"] == ("uuid", "NO")


def test_upgrade_head_declara_cascade_al_profesional_y_restrict_al_autor(scratch_url: str) -> None:
    command.upgrade(alembic_config(scratch_url), "head")

    fks = _fks(scratch_url)

    assert (
        "REFERENCES profesional(id) ON DELETE CASCADE"
        in fks["fk_bloqueo_profesional_id_profesional"]
    )
    assert "REFERENCES usuario(id) ON DELETE RESTRICT" in fks["fk_bloqueo_creado_por_usuario"]


def test_downgrade_a_009_elimina_la_tabla_y_el_reupgrade_la_restaura(scratch_url: str) -> None:
    config = alembic_config(scratch_url)
    command.upgrade(config, "head")

    command.downgrade(config, "009")

    assert current_revision(scratch_url) == "009"
    assert not _existe_tabla(scratch_url)

    command.upgrade(config, "head")

    assert current_revision(scratch_url) == "010"
    assert _existe_tabla(scratch_url)
    assert set(_checks(scratch_url)) == {"ck_bloqueo_fin_mayor", "ck_bloqueo_motivo_no_vacio"}
