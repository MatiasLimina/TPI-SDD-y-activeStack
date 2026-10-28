from alembic import command
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine, text

from tests.conftest import alembic_config


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


def test_upgrade_on_empty_database_reaches_head_revision(scratch_url: str) -> None:
    command.upgrade(alembic_config(scratch_url), "head")

    assert current_revision(scratch_url) == "004"
    assert has_btree_gist(scratch_url)


def test_upgrade_twice_is_idempotent(scratch_url: str) -> None:
    config = alembic_config(scratch_url)
    command.upgrade(config, "head")

    command.upgrade(config, "head")

    assert current_revision(scratch_url) == "004"
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

    assert current_revision(scratch_url) == "004"
    assert has_btree_gist(scratch_url)
