from collections.abc import Iterator

import pytest
from app.main import create_app
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.infrastructure.db.session import get_session

UNREACHABLE_URL = "postgresql+psycopg://secret_user:secret_pass@127.0.0.1:1/secret_db"


@pytest.fixture
def degraded_client() -> Iterator[TestClient]:
    """App cuya sesion apunta a un puerto cerrado (PostgreSQL inexistente, sin mocks)."""
    unreachable = create_engine(UNREACHABLE_URL, connect_args={"connect_timeout": 1})

    def broken_session() -> Iterator[Session]:
        with Session(bind=unreachable) as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_session] = broken_session
    with TestClient(app) as test_client:
        yield test_client
    unreachable.dispose()


def test_health_database_up_returns_200_ok(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_health_requires_no_authentication(client: TestClient) -> None:
    response = client.get("/health", headers={})

    assert response.status_code == 200


def test_health_database_down_returns_503_degraded(degraded_client: TestClient) -> None:
    response = degraded_client.get("/health")

    assert response.status_code == 503
    assert response.json() == {"status": "degraded", "database": "unavailable"}


@pytest.mark.parametrize(
    "leaked", ["secret_user", "secret_pass", "secret_db", "127.0.0.1", "postgresql"]
)
def test_health_database_down_does_not_leak_connection_details(
    degraded_client: TestClient, leaked: str
) -> None:
    response = degraded_client.get("/health")

    assert leaked not in response.text


@pytest.mark.parametrize("path", ["/turnos", "/pacientes", "/"])
def test_unknown_route_returns_404(client: TestClient, path: str) -> None:
    assert client.get(path).status_code == 404
