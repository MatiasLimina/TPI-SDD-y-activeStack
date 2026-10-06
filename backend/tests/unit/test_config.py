import pytest
from pydantic import ValidationError

from app.config import Settings, get_settings

ENV_VARS = [
    "DATABASE_URL",
    "REDIS_URL",
    "JWT_SECRET",
    "JWT_EXPIRE_MINUTES",
    "APP_TIMEZONE",
    "NOTIFICATION_ADAPTER",
    "CORS_ORIGINS",
]
DB_URL = "postgresql+psycopg://user:pass@localhost:5432/turnos"


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    get_settings.cache_clear()


def load() -> Settings:
    return Settings(_env_file=None)


@pytest.mark.parametrize(
    ("tz", "db_url"),
    [
        ("America/Argentina/Buenos_Aires", DB_URL),
        ("UTC", "postgresql+psycopg://other:other@db:5432/otra"),
    ],
)
def test_settings_values_come_from_environment(
    monkeypatch: pytest.MonkeyPatch, tz: str, db_url: str
) -> None:
    monkeypatch.setenv("DATABASE_URL", db_url)
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    monkeypatch.setenv("APP_TIMEZONE", tz)

    settings = load()

    assert settings.DATABASE_URL == db_url
    assert settings.APP_TIMEZONE == tz
    assert settings.JWT_SECRET == "test-secret"


def test_settings_defaults_for_non_sensitive_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", DB_URL)
    monkeypatch.setenv("JWT_SECRET", "test-secret")

    settings = load()

    assert settings.APP_TIMEZONE == "America/Argentina/Buenos_Aires"
    assert settings.JWT_EXPIRE_MINUTES == 60


@pytest.mark.parametrize("missing", ["DATABASE_URL", "JWT_SECRET"])
def test_settings_missing_required_variable_names_it(
    monkeypatch: pytest.MonkeyPatch, missing: str
) -> None:
    values = {"DATABASE_URL": DB_URL, "JWT_SECRET": "test-secret"}
    for name, value in values.items():
        if name != missing:
            monkeypatch.setenv(name, value)

    with pytest.raises(ValidationError, match=missing):
        load()


def test_settings_invalid_timezone_names_variable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", DB_URL)
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    monkeypatch.setenv("APP_TIMEZONE", "Mars/Olympus")

    with pytest.raises(ValidationError, match="APP_TIMEZONE"):
        load()


def test_get_settings_is_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", DB_URL)
    monkeypatch.setenv("JWT_SECRET", "test-secret")

    assert get_settings() is get_settings()
