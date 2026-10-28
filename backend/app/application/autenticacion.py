"""Caso de uso: iniciar sesión con email y contraseña (RN-AU-01, DD-24)."""

from app.domain.usuarios import CredencialesInvalidasError, normalizar_email
from app.infrastructure.db.repositorio_usuarios import RepositorioUsuarios
from app.infrastructure.security.contrasenas import Hasher
from app.infrastructure.security.tokens import EmisorTokens


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
