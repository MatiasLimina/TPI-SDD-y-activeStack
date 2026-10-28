from collections.abc import Iterator

import pytest
from alembic import command
from sqlalchemy import Engine, create_engine, text

from app.infrastructure.db import seed
from app.infrastructure.security.contrasenas import Hasher
from tests.conftest import alembic_config

CATALOGO = {"profesional": 2, "sillon": 2, "prestacion": 4, "paciente": 4}


def _contrasenas(
    recepcion: str | None = "clave-main-recepcion-ficticia",
    odonto_1: str | None = "clave-main-odontologo1-ficticia",
    odonto_2: str | None = "clave-main-odontologo2-ficticia",
) -> seed.SeedSettings:
    """Aislada del `.env` local y del entorno: solo valen los valores del test."""
    return seed.SeedSettings(
        _env_file=None,
        SEED_RECEPCIONISTA_PASSWORD=recepcion,
        SEED_ODONTOLOGO_1_PASSWORD=odonto_1,
        SEED_ODONTOLOGO_2_PASSWORD=odonto_2,
    )


@pytest.fixture
def scratch_engine(scratch_url: str, monkeypatch: pytest.MonkeyPatch) -> Iterator[Engine]:
    command.upgrade(alembic_config(scratch_url), "head")
    engine = create_engine(scratch_url)
    monkeypatch.setattr(seed, "get_engine", lambda: engine)
    yield engine
    engine.dispose()


def _conteos(engine: Engine) -> dict[str, int]:
    with engine.connect() as connection:
        return {
            tabla: connection.execute(text(f"SELECT count(*) FROM {tabla}")).scalar_one()
            for tabla in (*CATALOGO, "usuario")
        }


def test_main_run_twice_commits_catalog_and_users_without_error_or_duplicates(
    scratch_engine: Engine, hasher_test: Hasher
) -> None:
    seed.main(_contrasenas(), hasher_test)
    seed.main(_contrasenas(), hasher_test)

    assert _conteos(scratch_engine) == {**CATALOGO, "usuario": 3}


def test_main_without_password_variables_commits_catalog_and_no_users(
    scratch_engine: Engine, hasher_test: Hasher
) -> None:
    seed.main(_contrasenas(None, None, None), hasher_test)

    assert _conteos(scratch_engine) == {**CATALOGO, "usuario": 0}


def test_main_with_empty_second_dentist_password_skips_only_that_user(
    scratch_engine: Engine, hasher_test: Hasher
) -> None:
    seed.main(_contrasenas(odonto_2=""), hasher_test)

    assert _conteos(scratch_engine) == {**CATALOGO, "usuario": 2}
    with scratch_engine.connect() as connection:
        emails = connection.execute(text("SELECT email FROM usuario")).scalars().all()
    assert "bruno.inventado@example.com" not in emails


def test_main_by_default_reads_passwords_with_seed_settings_and_production_hasher(
    scratch_engine: Engine, hasher_test: Hasher, monkeypatch: pytest.MonkeyPatch
) -> None:
    solo_recepcion = _contrasenas(odonto_1=None, odonto_2=None)
    monkeypatch.setattr(seed, "SeedSettings", lambda: solo_recepcion)
    monkeypatch.setattr(seed, "get_hasher", lambda: hasher_test)

    seed.main()

    assert _conteos(scratch_engine) == {**CATALOGO, "usuario": 1}
