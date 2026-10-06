import pytest
from alembic import command
from sqlalchemy import create_engine, text

from app.infrastructure.db import seed
from tests.conftest import alembic_config


def test_main_run_twice_commits_catalog_without_error_or_duplicates(
    scratch_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    command.upgrade(alembic_config(scratch_url), "head")
    scratch_engine = create_engine(scratch_url)
    monkeypatch.setattr(seed, "get_engine", lambda: scratch_engine)

    seed.main()
    seed.main()

    try:
        with scratch_engine.connect() as connection:
            conteos = {
                tabla: connection.execute(text(f"SELECT count(*) FROM {tabla}")).scalar_one()
                for tabla in ("profesional", "sillon", "prestacion", "paciente")
            }
    finally:
        scratch_engine.dispose()
    assert conteos == {"profesional": 2, "sillon": 2, "prestacion": 4, "paciente": 4}
