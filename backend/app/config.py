"""Configuracion de la aplicacion, leida solo de variables de entorno (RN-CU-03)."""

from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.domain.time import DEFAULT_TIMEZONE

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    DATABASE_URL: str
    JWT_SECRET: str
    REDIS_URL: str = "redis://localhost:6379/0"
    JWT_EXPIRE_MINUTES: int = Field(default=60, gt=0)
    APP_TIMEZONE: str = DEFAULT_TIMEZONE
    NOTIFICATION_ADAPTER: str = "mock"
    CORS_ORIGINS: str = "http://localhost:5173"

    @field_validator("APP_TIMEZONE")
    @classmethod
    def _validate_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError(f"APP_TIMEZONE invalida: {value!r}") from exc
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
