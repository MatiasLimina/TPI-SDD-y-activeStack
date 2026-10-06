from pathlib import Path

import pytest

from app.config import REPO_ROOT, Settings

ENV_EXAMPLE = REPO_ROOT / ".env.example"


def parse_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            values[key.strip()] = value.strip()
    return values


@pytest.mark.parametrize("field", sorted(Settings.model_fields))
def test_env_example_declares_every_settings_field(field: str) -> None:
    assert field in parse_env(ENV_EXAMPLE)


@pytest.mark.parametrize(
    "field",
    ["TEST_DATABASE_URL", "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB", "POSTGRES_PORT"],
)
def test_env_example_declares_infrastructure_variables(field: str) -> None:
    assert field in parse_env(ENV_EXAMPLE)


def test_env_example_jwt_secret_is_placeholder() -> None:
    assert parse_env(ENV_EXAMPLE)["JWT_SECRET"] == "change-me"
