"""Configuracion de la aplicacion, leida solo de variables de entorno (RN-CU-03)."""

from functools import lru_cache
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.domain.time import DEFAULT_TIMEZONE

REPO_ROOT = Path(__file__).resolve().parents[2]


class ConfiguracionWorker(BaseSettings):
    """Variables que necesita el worker de recordatorios: no incluye `JWT_SECRET` (D14)."""

    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    DATABASE_URL: str
    REDIS_URL: str = "redis://localhost:6379/0"
    APP_TIMEZONE: str = DEFAULT_TIMEZONE
    NOTIFICATION_ADAPTER: Literal["mock"] = "mock"
    REMINDER_LEAD_HOURS: int = Field(default=24, gt=0)
    CONSULTORIO_NOMBRE: str = "Consultorio odontológico"

    @field_validator("APP_TIMEZONE")
    @classmethod
    def _validate_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError(f"APP_TIMEZONE invalida: {value!r}") from exc
        return value

    @field_validator("CONSULTORIO_NOMBRE")
    @classmethod
    def _validate_consultorio_nombre(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("CONSULTORIO_NOMBRE no puede estar vacio")
        return value


class Settings(ConfiguracionWorker):
    JWT_SECRET: str
    JWT_EXPIRE_MINUTES: int = Field(default=60, gt=0)
    CORS_ORIGINS: str = "http://localhost:5173"


@lru_cache
def get_settings() -> Settings:
    return Settings()
