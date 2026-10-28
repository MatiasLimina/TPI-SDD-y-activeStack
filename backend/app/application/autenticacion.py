"""Caso de uso: iniciar sesión con email y contraseña (RN-AU-01, DD-24)."""

from uuid import UUID

from app.domain.usuarios import (
    CredencialesInvalidasError,
    NoAutenticadoError,
    Rol,
    UsuarioAutenticado,
    normalizar_email,
)
from app.infrastructure.db.repositorio_usuarios import RepositorioUsuarios
from app.infrastructure.security.contrasenas import Hasher
from app.infrastructure.security.tokens import EmisorTokens, TokenInvalidoError


class IniciarSesion:
    def __init__(
        self, repositorio: RepositorioUsuarios, hasher: Hasher, emisor: EmisorTokens
    ) -> None:
        self._repositorio = repositorio
        self._hasher = hasher
        self._emisor = emisor

    def ejecutar(self, email: str, password: str) -> str:
        """Devuelve el JWT; todo rechazo es `CredencialesInvalidasError` tras una verificación."""
        usuario = self._repositorio.por_email(normalizar_email(email))
        if usuario is None:
            self._hasher.verificar_dummy(password)
            raise CredencialesInvalidasError
        valido, hash_nuevo = self._hasher.verify_and_update(password, usuario.password_hash)
        if not valido or not usuario.activo:
            raise CredencialesInvalidasError
        if hash_nuevo is not None:
            self._repositorio.actualizar_hash(usuario.id, hash_nuevo)
            self._repositorio.commit()
        return self._emisor.emitir(usuario)


class AutenticarToken:
    """Resuelve el usuario de un request: valida el token y relee al usuario de la base."""

    def __init__(self, repositorio: RepositorioUsuarios, emisor: EmisorTokens) -> None:
        self._repositorio = repositorio
        self._emisor = emisor

    def ejecutar(self, token: str | None) -> UsuarioAutenticado:
        """Todo fallo es `NoAutenticadoError`; el claim `rol` es informativo y no se usa."""
        if token is None:
            raise NoAutenticadoError
        try:
            claims = self._emisor.decodificar(token)
        except TokenInvalidoError as error:
            raise NoAutenticadoError from error
        usuario = self._repositorio.por_id(UUID(claims.sub))
        if usuario is None or not usuario.activo:
            raise NoAutenticadoError
        return UsuarioAutenticado(
            id=usuario.id, rol=Rol(usuario.rol), profesional_id=usuario.profesional_id
        )
