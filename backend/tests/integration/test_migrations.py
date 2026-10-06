from collections.abc import Iterator

import pytest
from alembic import command
from alembic.runtime.migration import MigrationContext
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import make_url

from tests.conftest import alembic_config

SCRATCH_DB = "turnos_migrations_scratch"


@pytest.fixture
def scratch_url(engine: Engine) -> Iterator[str]:
    """Base vacia y descartable, para no interferir con la base de test compartida."""
    admin = engine.execution_options(isolation_level="AUTOCOMMIT")
    with admin.connect() as connection:
        connection.execute(text(f"DROP DATABASE IF EXISTS {SCRATCH_DB}"))
        connection.execute(text(f"CREATE DATABASE {SCRATCH_DB}"))
    url = make_url(engine.url.render_as_string(hide_password=False)).set(database=SCRATCH_DB)
    yield url.render_as_string(hide_password=False)
    with admin.connect() as connection:
        connection.execute(text(f"DROP DATABASE IF EXISTS {SCRATCH_DB}"))


def current_revision(url: str) -> str | None:
    scratch = create_engine(url)
    try:
        with scratch.connect() as connection:
            return MigrationContext.configure(connection).get_current_revision()
    finally:
        scratch.dispose()


def has_btree_gist(url: str) -> bool:
    scratch = create_engine(url)
    try:
        with scratch.connect() as connection:
            return (
                connection.execute(
                    text("SELECT count(*) FROM pg_extension WHERE extname = 'btree_gist'")
                ).scalar_one()
                == 1
            )
    finally:
        scratch.dispose()


def test_upgrade_on_empty_database_reaches_revision_001(scratch_url: str) -> None:
    command.upgrade(alembic_config(scratch_url), "head")

    assert current_revision(scratch_url) == "001"
    assert has_btree_gist(scratch_url)


def test_upgrade_twice_is_idempotent(scratch_url: str) -> None:
    config = alembic_config(scratch_url)
    command.upgrade(config, "head")

    command.upgrade(config, "head")

    assert current_revision(scratch_url) == "001"
    assert has_btree_gist(scratch_url)


def test_downgrade_to_base_removes_btree_gist_and_reupgrade_restores_it(
    scratch_url: str,
) -> None:
    config = alembic_config(scratch_url)
    command.upgrade(config, "head")

    command.downgrade(config, "base")

    assert current_revision(scratch_url) is None
    assert not has_btree_gist(scratch_url)

    command.upgrade(config, "head")

    assert current_revision(scratch_url) == "001"
    assert has_btree_gist(scratch_url)
