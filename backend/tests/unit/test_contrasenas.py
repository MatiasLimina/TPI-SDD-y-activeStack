"""Hash de contraseñas (argon2id vía pwdlib). Sin base de datos. Datos ficticios."""

from argon2 import PasswordHasher, extract_parameters
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

from app.infrastructure.security.contrasenas import Hasher, get_hasher

CONTRASENA = "clave-ficticia-de-prueba"


class _PasswordHashEspia(PasswordHash):
    """Cuenta cuántas verificaciones se piden, sea por `verify` o por `verify_and_update`."""

    def __init__(self, hashers: tuple[Argon2Hasher, ...]) -> None:
        super().__init__(hashers)
        self.verificaciones = 0

    def verify(self, password: str | bytes, hash: str | bytes) -> bool:
        self.verificaciones += 1
        return super().verify(password, hash)

    def verify_and_update(
        self, password: str | bytes, hash: str | bytes
    ) -> tuple[bool, str | None]:
        self.verificaciones += 1
        return super().verify_and_update(password, hash)


def _hasher_barato() -> Hasher:
    return Hasher(PasswordHash((Argon2Hasher(time_cost=1, memory_cost=8, parallelism=1),)))


def test_el_hash_recomendado_es_argon2id_y_no_contiene_la_contrasena() -> None:
    hash_ = get_hasher().hash(CONTRASENA)

    assert hash_.startswith("$argon2id$")
    assert CONTRASENA not in hash_


def test_el_hash_generado_verifica_contra_su_contrasena() -> None:
    hasher = get_hasher()
    hash_ = hasher.hash(CONTRASENA)

    valido, hash_nuevo = hasher.verify_and_update(CONTRASENA, hash_)

    assert valido is True
    assert hash_nuevo is None


def test_dos_hashes_de_la_misma_contrasena_son_distintos() -> None:
    hasher = get_hasher()

    assert hasher.hash(CONTRASENA) != hasher.hash(CONTRASENA)


def test_get_hasher_devuelve_siempre_la_misma_instancia() -> None:
    assert get_hasher() is get_hasher()


def test_contrasena_incorrecta_devuelve_falso_y_sin_hash_nuevo() -> None:
    hasher = get_hasher()
    hash_ = hasher.hash(CONTRASENA)

    assert hasher.verify_and_update("otra-clave-ficticia", hash_) == (False, None)


def test_un_hash_con_parametros_distintos_se_reemplaza_por_uno_vigente() -> None:
    hash_barato = _hasher_barato().hash(CONTRASENA)
    recomendado = get_hasher()

    valido, hash_nuevo = recomendado.verify_and_update(CONTRASENA, hash_barato)

    assert valido is True
    assert hash_nuevo is not None
    assert hash_nuevo.startswith("$argon2id$")
    assert extract_parameters(hash_nuevo) != extract_parameters(hash_barato)
    assert PasswordHasher().check_needs_rehash(hash_nuevo) is False
    assert recomendado.verify_and_update(CONTRASENA, hash_nuevo) == (True, None)


def test_un_hash_con_parametros_distintos_y_contrasena_incorrecta_no_se_reemplaza() -> None:
    hash_barato = _hasher_barato().hash(CONTRASENA)

    assert get_hasher().verify_and_update("otra-clave-ficticia", hash_barato) == (False, None)


def test_un_hash_de_formato_desconocido_se_trata_como_invalido() -> None:
    hasher = get_hasher()

    for hash_raro in (
        "no-es-un-hash",
        "",
        "$2b$12$abcdefghijklmnopqrstuuABCDEFGHIJKLMNOPQRSTUVWXYZ0123",
    ):
        assert hasher.verify_and_update(CONTRASENA, hash_raro) == (False, None)


def test_el_dummy_se_calcula_con_los_parametros_de_la_propia_instancia() -> None:
    barato = _hasher_barato()
    recomendado = get_hasher()

    parametros_barato = extract_parameters(barato.hash_dummy)
    parametros_recomendado = extract_parameters(recomendado.hash_dummy)

    assert (parametros_barato.time_cost, parametros_barato.memory_cost) == (1, 8)
    assert parametros_barato.parallelism == 1
    assert parametros_recomendado == extract_parameters(PasswordHasher().hash("x"))
    assert parametros_barato != parametros_recomendado


def test_el_dummy_se_calcula_una_sola_vez_por_instancia() -> None:
    hasher = _hasher_barato()

    assert hasher.hash_dummy is hasher.hash_dummy


def test_verificar_dummy_ejecuta_una_verificacion_y_no_devuelve_nada() -> None:
    espia = _PasswordHashEspia((Argon2Hasher(time_cost=1, memory_cost=8, parallelism=1),))
    hasher = Hasher(espia)

    resultado = hasher.verificar_dummy(CONTRASENA)

    assert resultado is None
    assert espia.verificaciones == 1
    hasher.verificar_dummy("")
    assert espia.verificaciones == 2
