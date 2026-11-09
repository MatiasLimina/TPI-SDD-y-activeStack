"""docker-compose.yml: el servicio `worker` de recordatorios y las variables de la API."""

from typing import Any

import pytest
import yaml

from app.config import REPO_ROOT

VARIABLES_DEL_WORKER = {
    "DATABASE_URL",
    "REDIS_URL",
    "APP_TIMEZONE",
    "NOTIFICATION_ADAPTER",
    "REMINDER_LEAD_HOURS",
    "CONSULTORIO_NOMBRE",
}


@pytest.fixture(scope="module")
def servicios() -> dict[str, Any]:
    compose = yaml.safe_load((REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    return dict(compose["services"])


def test_worker_service_uses_the_same_build_as_api(servicios: dict[str, Any]) -> None:
    assert "worker" in servicios
    assert servicios["worker"]["build"] == servicios["api"]["build"]


def test_worker_service_runs_the_reminder_process(servicios: dict[str, Any]) -> None:
    assert servicios["worker"]["command"] == ["python", "-m", "app.worker"]


def test_worker_service_receives_the_six_variables_and_no_jwt_secret(
    servicios: dict[str, Any],
) -> None:
    entorno = servicios["worker"]["environment"]

    assert set(entorno) == VARIABLES_DEL_WORKER
    assert "JWT_SECRET" not in entorno


def test_worker_service_points_to_the_compose_services(servicios: dict[str, Any]) -> None:
    entorno = servicios["worker"]["environment"]

    assert "@db:5432/" in entorno["DATABASE_URL"]
    assert entorno["REDIS_URL"] == "redis://redis:6379/0"


def test_worker_service_depends_on_healthy_db_and_redis(servicios: dict[str, Any]) -> None:
    depende = servicios["worker"]["depends_on"]

    assert depende["db"]["condition"] == "service_healthy"
    assert "redis" in depende


def test_api_service_waits_for_healthy_db_and_started_redis(servicios: dict[str, Any]) -> None:
    depende = servicios["api"]["depends_on"]

    assert depende["db"]["condition"] == "service_healthy"
    assert depende["redis"]["condition"] == "service_started"


def test_worker_service_restarts_unless_stopped(servicios: dict[str, Any]) -> None:
    assert servicios["worker"]["restart"] == "unless-stopped"


@pytest.mark.parametrize("variable", ["REMINDER_LEAD_HOURS", "CONSULTORIO_NOMBRE"])
def test_api_service_receives_reminder_variables_besides_the_previous_ones(
    servicios: dict[str, Any], variable: str
) -> None:
    entorno = servicios["api"]["environment"]

    assert variable in entorno
    assert {"DATABASE_URL", "JWT_SECRET", "NOTIFICATION_ADAPTER", "CORS_ORIGINS"} <= set(entorno)


def test_api_and_worker_share_the_same_reminder_settings(servicios: dict[str, Any]) -> None:
    api, worker = servicios["api"]["environment"], servicios["worker"]["environment"]

    for variable in ("REMINDER_LEAD_HOURS", "CONSULTORIO_NOMBRE", "NOTIFICATION_ADAPTER"):
        assert api[variable] == worker[variable]


def test_frontend_service_is_built_from_its_folder_and_published_on_5173(
    servicios: dict[str, Any],
) -> None:
    frontend = servicios["frontend"]

    assert frontend["build"] == "./frontend"
    assert "5173:5173" in frontend["ports"]


def test_frontend_service_starts_after_api(servicios: dict[str, Any]) -> None:
    depende = servicios["frontend"]["depends_on"]

    assert depende["api"]["condition"] == "service_started"


def test_frontend_service_api_url_is_reachable_from_the_browser(servicios: dict[str, Any]) -> None:
    api_url = servicios["frontend"]["environment"]["VITE_API_URL"]

    assert api_url == "${VITE_API_URL:-http://localhost:8000}"
    assert "//api" not in api_url


@pytest.mark.parametrize("secreto", ["JWT_SECRET", "DATABASE_URL", "REDIS_URL"])
def test_frontend_service_receives_no_backend_secret(
    servicios: dict[str, Any], secreto: str
) -> None:
    assert secreto not in servicios["frontend"]["environment"]


def test_frontend_service_declares_no_env_file(servicios: dict[str, Any]) -> None:
    assert "env_file" not in servicios["frontend"]


def test_frontend_dockerfile_uses_node_24_and_a_reproducible_install() -> None:
    dockerfile = (REPO_ROOT / "frontend" / "Dockerfile").read_text(encoding="utf-8")

    assert dockerfile.startswith("FROM node:24-slim")
    assert "npm ci" in dockerfile
    assert "0.0.0.0" in dockerfile


@pytest.mark.parametrize("carpeta", ["node_modules", "dist"])
def test_frontend_dockerignore_excludes_host_artifacts(carpeta: str) -> None:
    lineas = (REPO_ROOT / "frontend" / ".dockerignore").read_text(encoding="utf-8").splitlines()

    assert carpeta in {linea.strip().rstrip("/") for linea in lineas}
