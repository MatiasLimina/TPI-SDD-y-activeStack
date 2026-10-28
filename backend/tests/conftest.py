"""Fixtures compartidas. Los tests de persistencia usan PostgreSQL real (TEST_DATABASE_URL)."""

import os
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from dotenv import dotenv_values
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.api.auth import get_emisor_tokens, get_hasher
from app.config import REPO_ROOT
from app.infrastructure.db.models import Profesional, Usuario
from app.infrastructure.db.session import get_session
from app.infrastructure.security.contrasenas import Hasher
from app.infrastructure.security.tokens import EmisorTokens
from app.main import create_app

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


SECRETO_TEST = "secreto-ficticio-solo-para-tests-de-al-menos-32-bytes"
CONTRASENA_RECEPCIONISTA = "clave-ficticia-recepcion"


@pytest.fixture(scope="session")
def hasher_test() -> Hasher:
    """Argon2id con parámetros mínimos: el mismo código de producción, con costo bajo."""
    return Hasher(PasswordHash((Argon2Hasher(time_cost=1, memory_cost=8, parallelism=1),)))


@pytest.fixture(scope="session")
def emisor_test() -> EmisorTokens:
    return EmisorTokens(SECRETO_TEST, 60)


@pytest.fixture
def recepcionista(db_session: Session, hasher_test: Hasher) -> Usuario:
    """Usuario ficticio real, creado en la sesión de test con el modelo de producción."""
    usuario = Usuario(
        email="recepcion@example.com",
        password_hash=hasher_test.hash(CONTRASENA_RECEPCIONISTA),
        rol="recepcionista",
    )
    db_session.add(usuario)
    db_session.flush()
    return usuario


@pytest.fixture
def odontologo(db_session: Session, hasher_test: Hasher) -> Usuario:
    """Odontólogo ficticio con su propio profesional, creado en la sesión de test."""
    profesional = Profesional(nombre="Olga", apellido="Ficticia")
    db_session.add(profesional)
    db_session.flush()
    usuario = Usuario(
        email="odontologa@example.com",
        password_hash=hasher_test.hash("clave-ficticia-odontologa"),
        rol="odontologo",
        profesional_id=profesional.id,
    )
    db_session.add(usuario)
    db_session.flush()
    return usuario


@pytest.fixture
def token_de(emisor_test: EmisorTokens) -> Callable[[Usuario], str]:
    return emisor_test.emitir


@pytest.fixture
def app_de_test(db_session: Session, hasher_test: Hasher, emisor_test: EmisorTokens) -> FastAPI:
    """App con sesión, hasher y emisor de test; la comparten los dos clientes."""
    app = create_app()
    app.dependency_overrides[get_session] = lambda: db_session
    app.dependency_overrides[get_hasher] = lambda: hasher_test
    app.dependency_overrides[get_emisor_tokens] = lambda: emisor_test
    return app


@pytest.fixture
def cliente_anonimo(app_de_test: FastAPI) -> Iterator[TestClient]:
    """Cliente HTTP sin encabezado `Authorization`."""
    with TestClient(app_de_test) as test_client:
        yield test_client


@pytest.fixture
def client(
    app_de_test: FastAPI, recepcionista: Usuario, token_de: Callable[[Usuario], str]
) -> Iterator[TestClient]:
    """Cliente HTTP autenticado por defecto como la recepcionista de test.

    Es un TestClient propio: si un test pide `client` y `cliente_anonimo`,
    el anónimo no debe heredar el encabezado de este.
    """
    encabezados = {"Authorization": f"Bearer {token_de(recepcionista)}"}
    with TestClient(app_de_test, headers=encabezados) as test_client:
        yield test_client


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
