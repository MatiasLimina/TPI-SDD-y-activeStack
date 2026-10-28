"""Autenticación de la API: dependencias de hasher y emisor de tokens (sin router todavía)."""

from app.config import get_settings
from app.infrastructure.security.contrasenas import Hasher
from app.infrastructure.security.contrasenas import get_hasher as _get_hasher_produccion
from app.infrastructure.security.tokens import EmisorTokens


def get_hasher() -> Hasher:
    """Dependencia del hasher; los tests la sobreescriben con uno de costo mínimo."""
    return _get_hasher_produccion()


def get_emisor_tokens() -> EmisorTokens:
    """Dependencia del emisor de tokens, configurado desde `Settings`."""
    settings = get_settings()
    return EmisorTokens(settings.JWT_SECRET, settings.JWT_EXPIRE_MINUTES)
