from sqlalchemy import text
from sqlalchemy.orm import Session


def test_db_session_select_one_returns_one(db_session: Session) -> None:
    assert db_session.execute(text("SELECT 1")).scalar_one() == 1


def test_db_session_server_is_postgresql(db_session: Session) -> None:
    version = db_session.execute(text("SELECT version()")).scalar_one()

    assert "PostgreSQL" in version


def test_btree_gist_extension_is_installed_after_migrating(db_session: Session) -> None:
    rows = db_session.execute(
        text("SELECT extname FROM pg_extension WHERE extname = 'btree_gist'")
    ).all()

    assert len(rows) == 1


def test_isolation_writes_in_first_test_are_visible_inside_it(db_session: Session) -> None:
    db_session.execute(text("CREATE TABLE scratch_isolation (id int)"))
    db_session.execute(text("INSERT INTO scratch_isolation VALUES (1)"))

    count = db_session.execute(text("SELECT count(*) FROM scratch_isolation")).scalar_one()

    assert count == 1


def test_isolation_writes_from_previous_test_are_not_visible(db_session: Session) -> None:
    exists = db_session.execute(text("SELECT to_regclass('scratch_isolation')")).scalar_one()

    assert exists is None
