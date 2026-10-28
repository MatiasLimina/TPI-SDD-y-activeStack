"""Emisión y decodificación de tokens JWT (HS256)."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol
from uuid import UUID

import jwt

ALGORITMO = "HS256"


class TokenInvalidoError(Exception):
    """El token no es válido (firma, algoritmo, vencimiento, claims o formato)."""


class UsuarioEmisible(Protocol):
    """Lo mínimo que `EmisorTokens` necesita de un usuario para emitir su token."""

    @property
    def id(self) -> UUID: ...

    @property
    def rol(self) -> str: ...

    @property
    def profesional_id(self) -> UUID | None: ...


@dataclass(frozen=True)
class ClaimsToken:
    sub: str
    rol: str | None
    profesional_id: str | None
    exp: datetime


class EmisorTokens:
    def __init__(self, secreto: str, minutos: int) -> None:
        self._secreto = secreto
        self._minutos = minutos

    def emitir(self, usuario: UsuarioEmisible) -> str:
        payload = {
            "sub": str(usuario.id),
            "rol": str(usuario.rol),
            "profesional_id": None
            if usuario.profesional_id is None
            else str(usuario.profesional_id),
            "exp": datetime.now(UTC) + timedelta(minutes=self._minutos),
        }
        return jwt.encode(payload, self._secreto, algorithm=ALGORITMO)

    def decodificar(self, token: str) -> ClaimsToken:
        """Valida firma, algoritmo, vencimiento y claims; todo fallo es `TokenInvalidoError`."""
        try:
            crudo = jwt.decode(
                token,
                self._secreto,
                algorithms=[ALGORITMO],
                options={"require": ["exp", "sub"]},
            )
            sub = crudo["sub"]
            UUID(sub)
        except (jwt.PyJWTError, ValueError, TypeError, AttributeError) as error:
            raise TokenInvalidoError("Token inválido") from error
        return ClaimsToken(
            sub=sub,
            rol=crudo.get("rol"),
            profesional_id=crudo.get("profesional_id"),
            exp=datetime.fromtimestamp(crudo["exp"], UTC),
        )
