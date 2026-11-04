"""Migración 009: CHECK que impide un recordatorio `pendiente` con 3 intentos (reversible)."""

from collections.abc import Iterator
from contextlib import contextmanager
from uuid import UUID

import pytest
from alembic import command
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from tests.conftest import alembic_config
from tests.integration.factories import crear_catalogo, crear_turno
from tests.integration.test_migrations import current_revision

CHECK = "ck_recordatorio_pendiente_intentos"
SQLSTATE_CHECK = "23514"


@contextmanager
def _sesion(url: str) -> Iterator[Session]:
    motor = create_engine(url)
    try:
        with Session(motor) as sesion:
            yield sesion
    finally:
        motor.dispose()


def _checks(url: str) -> dict[str, str]:
    with _sesion(url) as sesion:
        filas = sesion.execute(
            text(
                "SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint "
                "WHERE conrelid = 'recordatorio'::regclass AND contype = 'c'"
            )
        ).all()
    return {nombre: definicion for nombre, definicion in filas}


def _crear_turno(url: str) -> UUID:
    with _sesion(url) as sesion:
        turno = crear_turno(sesion, crear_catalogo(sesion))
        sesion.commit()
        return turno.id


def _insertar_pendiente_con_3_intentos(url: str, turno_id: UUID) -> None:
    with _sesion(url) as sesion:
        sesion.execute(
            text(
                "INSERT INTO recordatorio (turno_id, programado_para, estado, canal, intentos) "
                "VALUES (:turno_id, now(), 'pendiente', 'mock', 3)"
            ),
            {"turno_id": turno_id},
        )
        sesion.commit()


def _borrar_recordatorios(url: str) -> None:
    with _sesion(url) as sesion:
        sesion.execute(text("DELETE FROM recordatorio"))
        sesion.commit()


def test_upgrade_head_creates_the_pendiente_intentos_check(scratch_url: str) -> None:
    command.upgrade(alembic_config(scratch_url), "head")

    checks = _checks(scratch_url)

    assert current_revision(scratch_url) == "009"
    assert CHECK in checks
    assert "'pendiente'" in checks[CHECK]
    assert "intentos < 3" in checks[CHECK]


def test_head_rejects_a_pendiente_with_three_attempts(scratch_url: str) -> None:
    command.upgrade(alembic_config(scratch_url), "head")
    turno_id = _crear_turno(scratch_url)

    with pytest.raises(IntegrityError) as excinfo:
        _insertar_pendiente_con_3_intentos(scratch_url, turno_id)

    assert excinfo.value.orig.sqlstate == SQLSTATE_CHECK  # type: ignore[union-attr]
    assert excinfo.value.orig.diag.constraint_name == CHECK  # type: ignore[union-attr]


def test_downgrade_to_008_drops_the_check_and_the_database_accepts_the_row(
    scratch_url: str,
) -> None:
    config = alembic_config(scratch_url)
    command.upgrade(config, "head")
    turno_id = _crear_turno(scratch_url)

    command.downgrade(config, "008")

    assert current_revision(scratch_url) == "008"
    assert CHECK not in _checks(scratch_url)
    _insertar_pendiente_con_3_intentos(scratch_url, turno_id)


def test_reupgrade_on_a_database_without_that_data_restores_the_check(scratch_url: str) -> None:
    config = alembic_config(scratch_url)
    command.upgrade(config, "head")
    turno_id = _crear_turno(scratch_url)
    command.downgrade(config, "008")
    _insertar_pendiente_con_3_intentos(scratch_url, turno_id)
    _borrar_recordatorios(scratch_url)

    command.upgrade(config, "head")

    assert CHECK in _checks(scratch_url)
    with pytest.raises(IntegrityError) as excinfo:
        _insertar_pendiente_con_3_intentos(scratch_url, turno_id)
    assert excinfo.value.orig.diag.constraint_name == CHECK  # type: ignore[union-attr]
