"""Hash y verificación de contraseñas (argon2id vía pwdlib)."""

from functools import cache, cached_property

from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError

# Valor fijo y no secreto: solo sirve para igualar el costo de verificar un usuario inexistente.
_VALOR_DUMMY = "contrasena-ficticia-anti-timing"


class Hasher:
    """Envoltorio de `PasswordHash` con el contrato que usa la aplicación."""

    def __init__(self, password_hash: PasswordHash) -> None:
        self._password_hash = password_hash

    def hash(self, password: str) -> str:
        return self._password_hash.hash(password)

    def verify_and_update(self, password: str, hash_guardado: str) -> tuple[bool, str | None]:
        """Devuelve `(valido, hash_nuevo)`; `hash_nuevo` solo si el hash guardado quedó viejo.

        Un hash de formato desconocido se trata como contraseña incorrecta, pero igual se paga
        una verificación (contra el dummy) para no responder más rápido que otros rechazos.
        """
        try:
            return self._password_hash.verify_and_update(password, hash_guardado)
        except UnknownHashError:
            self.verificar_dummy(password)
            return False, None

    @cached_property
    def hash_dummy(self) -> str:
        """Hash ficticio calculado con los parámetros de esta instancia (una sola vez)."""
        return self._password_hash.hash(_VALOR_DUMMY)

    def verificar_dummy(self, password: str) -> None:
        """Verifica contra el hash ficticio y descarta el resultado (mismo costo que uno real)."""
        self._password_hash.verify(password, self.hash_dummy)


@cache
def get_hasher() -> Hasher:
    return Hasher(PasswordHash.recommended())
