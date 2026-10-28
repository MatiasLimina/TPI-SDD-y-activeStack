"""Dependencias de autenticación de la API: hasher y emisor de tokens. Sin base de datos."""

from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Annotated
from uuid import uuid4

import jwt
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

from app.api.auth import get_emisor_tokens, get_hasher
from app.config import get_settings
from app.infrastructure.security.contrasenas import Hasher
from app.infrastructure.security.contrasenas import get_hasher as get_hasher_infra
from app.infrastructure.security.tokens import EmisorTokens

SECRETO = "secreto-ficticio-de-prueba-de-al-menos-32-bytes"
CONTRASENA = "clave-ficticia-de-prueba"


class _Usuario:
    id = uuid4()
    rol = "recepcionista"
    profesional_id = None


@pytest.fixture
def entorno(monkeypatch: pytest.MonkeyPatch) -> Iterator[pytest.MonkeyPatch]:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:pass@localhost:5432/turnos")
    monkeypatch.setenv("JWT_SECRET", SECRETO)
    get_settings.cache_clear()
    yield monkeypatch
    get_settings.cache_clear()


def _app_con_dependencias() -> FastAPI:
    app = FastAPI()

    @app.get("/hash")
    def hash_(hasher: Annotated[Hasher, Depends(get_hasher)]) -> dict[str, str]:
        return {"hash": hasher.hash(CONTRASENA)}

    @app.get("/token")
    def token(emisor: Annotated[EmisorTokens, Depends(get_emisor_tokens)]) -> dict[str, str]:
        return {"token": emisor.emitir(_Usuario())}

    return app


def test_get_hasher_devuelve_el_hasher_de_produccion_argon2id() -> None:
    hasher = get_hasher()

    assert hasher is get_hasher_infra()
    assert hasher.hash(CONTRASENA).startswith("$argon2id$")


def test_get_emisor_tokens_usa_secreto_y_minutos_de_settings(entorno: pytest.MonkeyPatch) -> None:
    entorno.setenv("JWT_EXPIRE_MINUTES", "15")

    emisor = get_emisor_tokens()

    assert isinstance(emisor, EmisorTokens)
    crudo = jwt.decode(emisor.emitir(_Usuario()), SECRETO, algorithms=["HS256"])
    restante = datetime.fromtimestamp(crudo["exp"], UTC) - datetime.now(UTC)
    assert 14 * 60 < restante.total_seconds() <= 15 * 60


def test_get_emisor_tokens_toma_los_minutos_por_defecto_de_settings(
    entorno: pytest.MonkeyPatch,
) -> None:
    entorno.delenv("JWT_EXPIRE_MINUTES", raising=False)

    crudo = jwt.decode(get_emisor_tokens().emitir(_Usuario()), SECRETO, algorithms=["HS256"])

    restante = datetime.fromtimestamp(crudo["exp"], UTC) - datetime.now(UTC)
    assert 59 * 60 < restante.total_seconds() <= 60 * 60


def test_get_hasher_se_puede_sobreescribir_con_dependency_overrides() -> None:
    barato = Hasher(PasswordHash((Argon2Hasher(time_cost=1, memory_cost=8, parallelism=1),)))
    app = _app_con_dependencias()
    app.dependency_overrides[get_hasher] = lambda: barato

    hash_ = TestClient(app).get("/hash").json()["hash"]

    assert hash_.startswith("$argon2id$")
    assert "m=8,t=1,p=1" in hash_
    assert barato.verify_and_update(CONTRASENA, hash_) == (True, None)


def test_get_emisor_tokens_se_puede_sobreescribir_con_dependency_overrides() -> None:
    otro_secreto = "otro-secreto-ficticio-de-prueba-de-al-menos-32-bytes"
    app = _app_con_dependencias()
    app.dependency_overrides[get_emisor_tokens] = lambda: EmisorTokens(otro_secreto, 5)

    token = TestClient(app).get("/token").json()["token"]

    crudo = jwt.decode(token, otro_secreto, algorithms=["HS256"])
    assert crudo["sub"] == str(_Usuario.id)
    with pytest.raises(jwt.InvalidSignatureError):
        jwt.decode(token, SECRETO, algorithms=["HS256"])
