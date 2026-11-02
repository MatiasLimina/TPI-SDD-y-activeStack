"""Migración 006: CHECK de la grilla de 5 minutos y del máximo de 480 en prestacion.duracion_min."""

from alembic import command
from sqlalchemy import create_engine, text

from tests.conftest import alembic_config

MULTIPLO = "ck_prestacion_duracion_min_multiplo_5"
MAXIMA = "ck_prestacion_duracion_min_maxima"
POSITIVA = "ck_prestacion_duracion_min_positiva"


def _checks_de_prestacion(url: str) -> dict[str, str]:
    scratch = create_engine(url)
    try:
        with scratch.connect() as connection:
            filas = connection.execute(
                text(
                    "SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint "
                    "WHERE conrelid = 'prestacion'::regclass AND contype = 'c'"
                )
            ).all()
        return dict(filas)
    finally:
        scratch.dispose()


def test_upgrade_head_creates_both_duration_checks_and_keeps_the_positive_one(
    scratch_url: str,
) -> None:
    command.upgrade(alembic_config(scratch_url), "head")

    checks = _checks_de_prestacion(scratch_url)

    assert set(checks) == {POSITIVA, MULTIPLO, MAXIMA}
    assert "duracion_min > 0" in checks[POSITIVA]
    assert "mod(duracion_min, 5) = 0" in checks[MULTIPLO]
    assert "duracion_min <= 480" in checks[MAXIMA]


def test_downgrade_to_005_drops_the_new_checks_and_reupgrade_restores_them(
    scratch_url: str,
) -> None:
    config = alembic_config(scratch_url)
    command.upgrade(config, "head")

    command.downgrade(config, "005")

    assert set(_checks_de_prestacion(scratch_url)) == {POSITIVA}

    command.upgrade(config, "head")

    assert set(_checks_de_prestacion(scratch_url)) == {POSITIVA, MULTIPLO, MAXIMA}
