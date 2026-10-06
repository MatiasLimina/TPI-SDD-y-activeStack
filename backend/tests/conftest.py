"""Fixtures compartidas. Los tests de persistencia usan PostgreSQL real (TEST_DATABASE_URL)."""

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from dotenv import dotenv_values
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.config import REPO_ROOT

BACKEND_DIR = Path(__file__).resolve().parents[1]
DB_HINT = "Levantá la base de test con: docker compose up -d db (y copiá .env.example a .env)."


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        if "integration" in item.path.parts:
            item.add_marker(pytest.mark.integration)


def get_test_database_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL") or dotenv_values(REPO_ROOT / ".env").get(
        "TEST_DATABASE_URL"
    )
    if not url:
        pytest.fail(f"TEST_DATABASE_URL no está definida. {DB_HINT}", pytrace=False)
    return url


def alembic_config(db_url: str) -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    config.attributes["db_url"] = db_url
    return config


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    url = get_test_database_url()
    test_engine = create_engine(url, connect_args={"connect_timeout": 5})
    try:
        with test_engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except OperationalError:
        test_engine.dispose()
        pytest.fail(f"No se pudo conectar a la base de test. {DB_HINT}", pytrace=False)
    command.upgrade(alembic_config(url), "head")
    yield test_engine
    test_engine.dispose()


@pytest.fixture
def db_session(engine: Engine) -> Iterator[Session]:
    """Sesion dentro de una transaccion externa que siempre se revierte."""
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()
