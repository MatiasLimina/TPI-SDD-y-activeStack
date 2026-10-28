"""Reglas de dominio de usuarios: puras, sin base de datos ni FastAPI."""

import unicodedata
from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class Rol(StrEnum):
    RECEPCIONISTA = "recepcionista"
    ODONTOLOGO = "odontologo"


_ROLES_VALIDOS = frozenset(r.value for r in Rol)


@dataclass(frozen=True)
class UsuarioAutenticado:
    """Quien hace el request: rol y profesional salen siempre de la base, no del token."""

    id: UUID
    rol: Rol
    profesional_id: UUID | None


class NoAutenticadoError(Exception):
    """Falta el token o no vale (formato, firma, vencimiento) o su usuario no está activo."""


class RolInsuficienteError(Exception):
    """El usuario autenticado no tiene un rol permitido para la operación."""


class CredencialesInvalidasError(Exception):
    """Email desconocido, contraseña incorrecta o usuario inactivo (indistinguibles, DD-24)."""


class AltaUsuarioInvalidaError(Exception):
    """Un alta de usuario viola una regla de dominio (el CLI la traduce a código de salida 1)."""

    def __init__(self, codigo: str, mensaje: str) -> None:
        super().__init__(mensaje)
        self.codigo = codigo
        self.mensaje = mensaje


class UsuarioInexistenteError(Exception):
    """No hay un usuario con ese email (el CLI lo traduce a código de salida 1)."""


def normalizar_email(email: str) -> str:
    """Quita los espacios de los extremos y pasa a minúsculas (igual que el CHECK de la base)."""
    return email.strip().lower()


def _tiene_espacio_o_control(texto: str) -> bool:
    return any(c.isspace() or unicodedata.category(c) == "Cc" for c in texto)


def validar_forma_email(email: str) -> None:
    """Exige `algo@algo`: una sola arroba, sin espacios ni caracteres de control."""
    local, arroba, dominio = email.partition("@")
    if not arroba or not local or not dominio or "@" in dominio or _tiene_espacio_o_control(email):
        raise AltaUsuarioInvalidaError(
            "email_invalido", "El email debe tener la forma algo@algo, sin espacios."
        )


def validar_alta(rol: str, profesional_id: UUID | None) -> None:
    """Un odontólogo exige profesional; una recepcionista no admite ninguno."""
    if rol not in _ROLES_VALIDOS:
        raise AltaUsuarioInvalidaError("rol_invalido", f"Rol desconocido: {rol!r}.")
    if rol == Rol.ODONTOLOGO and profesional_id is None:
        raise AltaUsuarioInvalidaError(
            "profesional_requerido", "Un odontólogo necesita un profesional asociado."
        )
    if rol == Rol.RECEPCIONISTA and profesional_id is not None:
        raise AltaUsuarioInvalidaError(
            "profesional_no_permitido", "Una recepcionista no puede tener un profesional asociado."
        )
