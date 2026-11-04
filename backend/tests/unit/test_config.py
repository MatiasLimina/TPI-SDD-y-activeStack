import pytest
from pydantic import ValidationError

from app.config import ConfiguracionWorker, Settings, get_settings

ENV_VARS = [
    "DATABASE_URL",
    "REDIS_URL",
    "JWT_SECRET",
    "JWT_EXPIRE_MINUTES",
    "APP_TIMEZONE",
    "NOTIFICATION_ADAPTER",
    "CORS_ORIGINS",
    "REMINDER_LEAD_HOURS",
    "CONSULTORIO_NOMBRE",
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


@pytest.mark.parametrize("valor", ["0", "-5", "abc", "1.5", ""])
def test_settings_jwt_expire_minutes_invalid_names_variable(
    monkeypatch: pytest.MonkeyPatch, valor: str
) -> None:
    monkeypatch.setenv("DATABASE_URL", DB_URL)
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    monkeypatch.setenv("JWT_EXPIRE_MINUTES", valor)

    with pytest.raises(ValidationError, match="JWT_EXPIRE_MINUTES"):
        load()


@pytest.mark.parametrize("valor", [1, 15, 1440])
def test_settings_jwt_expire_minutes_accepts_positive_integers(
    monkeypatch: pytest.MonkeyPatch, valor: int
) -> None:
    monkeypatch.setenv("DATABASE_URL", DB_URL)
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    monkeypatch.setenv("JWT_EXPIRE_MINUTES", str(valor))

    assert load().JWT_EXPIRE_MINUTES == valor


def test_settings_reminder_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", DB_URL)
    monkeypatch.setenv("JWT_SECRET", "test-secret")

    settings = load()

    assert settings.REMINDER_LEAD_HOURS == 24
    assert settings.NOTIFICATION_ADAPTER == "mock"
    assert settings.CONSULTORIO_NOMBRE == "Consultorio odontológico"


@pytest.mark.parametrize(
    ("horas", "nombre"),
    [("48", "Consultorio Odontológico Ejemplo"), ("72", "Clínica Ficticia Norte")],
)
def test_settings_reminder_values_come_from_environment(
    monkeypatch: pytest.MonkeyPatch, horas: str, nombre: str
) -> None:
    monkeypatch.setenv("DATABASE_URL", DB_URL)
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    monkeypatch.setenv("REMINDER_LEAD_HOURS", horas)
    monkeypatch.setenv("CONSULTORIO_NOMBRE", nombre)

    settings = load()

    assert settings.REMINDER_LEAD_HOURS == int(horas)
    assert settings.CONSULTORIO_NOMBRE == nombre


@pytest.mark.parametrize("valor", ["0", "-24", "un-dia", "1.5", ""])
def test_settings_reminder_lead_hours_invalid_names_variable(
    monkeypatch: pytest.MonkeyPatch, valor: str
) -> None:
    monkeypatch.setenv("DATABASE_URL", DB_URL)
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    monkeypatch.setenv("REMINDER_LEAD_HOURS", valor)

    with pytest.raises(ValidationError, match="REMINDER_LEAD_HOURS"):
        load()


@pytest.mark.parametrize("valor", [1, 12, 168])
def test_settings_reminder_lead_hours_accepts_positive_integers(
    monkeypatch: pytest.MonkeyPatch, valor: int
) -> None:
    monkeypatch.setenv("DATABASE_URL", DB_URL)
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    monkeypatch.setenv("REMINDER_LEAD_HOURS", str(valor))

    assert load().REMINDER_LEAD_HOURS == valor


@pytest.mark.parametrize("valor", ["whatsapp", "sms", "MOCK"])
def test_settings_unknown_notification_adapter_names_variable(
    monkeypatch: pytest.MonkeyPatch, valor: str
) -> None:
    monkeypatch.setenv("DATABASE_URL", DB_URL)
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    monkeypatch.setenv("NOTIFICATION_ADAPTER", valor)

    with pytest.raises(ValidationError, match="NOTIFICATION_ADAPTER"):
        load()


@pytest.mark.parametrize("valor", ["", "   ", "	"])
def test_settings_blank_consultorio_nombre_names_variable(
    monkeypatch: pytest.MonkeyPatch, valor: str
) -> None:
    monkeypatch.setenv("DATABASE_URL", DB_URL)
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    monkeypatch.setenv("CONSULTORIO_NOMBRE", valor)

    with pytest.raises(ValidationError, match="CONSULTORIO_NOMBRE"):
        load()


WORKER_ENV = {
    "DATABASE_URL": DB_URL,
    "REDIS_URL": "redis://localhost:6379/0",
    "APP_TIMEZONE": "America/Argentina/Buenos_Aires",
    "NOTIFICATION_ADAPTER": "mock",
    "REMINDER_LEAD_HOURS": "24",
    "CONSULTORIO_NOMBRE": "Consultorio Odontológico Ejemplo",
}


def test_worker_config_loads_without_jwt_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    for nombre, valor in WORKER_ENV.items():
        monkeypatch.setenv(nombre, valor)

    config = ConfiguracionWorker(_env_file=None)

    assert config.DATABASE_URL == DB_URL
    assert config.REMINDER_LEAD_HOURS == 24
    assert config.CONSULTORIO_NOMBRE == "Consultorio Odontológico Ejemplo"
    assert not hasattr(config, "JWT_SECRET")


def test_settings_without_jwt_secret_still_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    for nombre, valor in WORKER_ENV.items():
        monkeypatch.setenv(nombre, valor)

    with pytest.raises(ValidationError, match="JWT_SECRET"):
        load()


def test_worker_config_requires_database_url() -> None:
    with pytest.raises(ValidationError, match="DATABASE_URL"):
        ConfiguracionWorker(_env_file=None)


def test_settings_extends_worker_config() -> None:
    assert issubclass(Settings, ConfiguracionWorker)
    assert set(ConfiguracionWorker.model_fields) <= set(Settings.model_fields)
