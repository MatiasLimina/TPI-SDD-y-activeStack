"""Politica de tiempo (RN-CU-04): persistir en UTC, presentar en zona local."""

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

DEFAULT_TIMEZONE = "America/Argentina/Buenos_Aires"


class NaiveDatetimeError(ValueError):
    """Se recibio un datetime sin zona horaria."""


def _require_aware(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise NaiveDatetimeError("el datetime no tiene zona horaria (naive)")


def to_utc(value: datetime) -> datetime:
    """Convierte un datetime con zona al mismo instante en UTC."""
    _require_aware(value)
    return value.astimezone(UTC)


def to_local(value: datetime, tz: str = DEFAULT_TIMEZONE) -> datetime:
    """Convierte un datetime con zona a la zona de presentacion, conservando el instante."""
    _require_aware(value)
    return value.astimezone(ZoneInfo(tz))
