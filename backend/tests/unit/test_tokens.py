"""Emisión y decodificación de JWT (PyJWT, HS256). Sin base de datos. Datos ficticios."""

import ast
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import jwt
import pytest

from app.infrastructure.security.tokens import EmisorTokens, TokenInvalidoError

SECRETO = "secreto-ficticio-de-prueba-0123456789-abcdef-ampliado-a-64-bytes-o-mas-xyz"  # >= 64 B
OTRO_SECRETO = "otro-secreto-ficticio-de-prueba-9876543210-fedcba-ampliado-a-64-bytes-o-mas"
TOLERANCIA = timedelta(seconds=5)


@dataclass(frozen=True)
class _Usuario:
    id: UUID
    rol: str
    profesional_id: UUID | None


def _recepcionista() -> _Usuario:
    return _Usuario(id=uuid4(), rol="recepcionista", profesional_id=None)


def _odontologo() -> _Usuario:
    return _Usuario(id=uuid4(), rol="odontologo", profesional_id=uuid4())


def _firmar(payload: dict[str, object], secreto: str = SECRETO, algoritmo: str = "HS256") -> str:
    return jwt.encode(payload, secreto, algorithm=algoritmo)


def _payload_valido(**cambios: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "sub": str(uuid4()),
        "rol": "recepcionista",
        "profesional_id": None,
        "exp": datetime.now(UTC) + timedelta(minutes=30),
    }
    payload.update(cambios)
    return {clave: valor for clave, valor in payload.items() if valor is not _AUSENTE}


_AUSENTE = object()


# --- 2.2 emisión -----------------------------------------------------------------------------


@pytest.mark.parametrize("minutos", [60, 15])
def test_emitir_y_decodificar_devuelve_los_claims_y_un_exp_acotado(minutos: int) -> None:
    emisor = EmisorTokens(SECRETO, minutos)
    usuario = _recepcionista()

    t0 = datetime.now(UTC)
    token = emisor.emitir(usuario)
    t1 = datetime.now(UTC)
    claims = emisor.decodificar(token)

    assert claims.sub == str(usuario.id)
    assert claims.rol == "recepcionista"
    assert claims.profesional_id is None
    assert t0 + timedelta(minutes=minutos) - TOLERANCIA <= claims.exp
    assert claims.exp <= t1 + timedelta(minutes=minutos) + TOLERANCIA
    assert claims.exp.tzinfo is not None
    assert claims.exp.utcoffset() == timedelta(0)


def test_el_token_de_un_odontologo_lleva_su_profesional_id() -> None:
    emisor = EmisorTokens(SECRETO, 60)
    usuario = _odontologo()

    claims = emisor.decodificar(emisor.emitir(usuario))

    assert claims.sub == str(usuario.id)
    assert claims.rol == "odontologo"
    assert claims.profesional_id == str(usuario.profesional_id)


def test_el_token_emitido_es_un_jwt_hs256_con_sub_de_texto() -> None:
    emisor = EmisorTokens(SECRETO, 60)
    usuario = _odontologo()

    token = emisor.emitir(usuario)

    assert jwt.get_unverified_header(token)["alg"] == "HS256"
    crudo = jwt.decode(token, SECRETO, algorithms=["HS256"])
    assert crudo["sub"] == str(usuario.id)
    assert isinstance(crudo["exp"], int)


def test_un_token_emitido_con_otro_secreto_no_lo_acepta_el_emisor() -> None:
    token = EmisorTokens(OTRO_SECRETO, 60).emitir(_recepcionista())

    with pytest.raises(TokenInvalidoError):
        EmisorTokens(SECRETO, 60).decodificar(token)


# --- 2.3 decodificación estricta ---------------------------------------------------------------


def _token_hs512() -> str:
    return _firmar(_payload_valido(), algoritmo="HS512")


def _token_alg_none() -> str:
    return jwt.encode(_payload_valido(), None, algorithm="none")


@pytest.mark.parametrize(
    "token",
    [
        pytest.param(
            _firmar(_payload_valido(exp=datetime.now(UTC) - timedelta(hours=1))),
            id="vencido-hace-una-hora",
        ),
        pytest.param(
            _firmar(_payload_valido(exp=datetime.now(UTC) - timedelta(seconds=60))),
            id="vencido-hace-60-segundos",
        ),
        pytest.param(_firmar(_payload_valido(), secreto=OTRO_SECRETO), id="otra-clave"),
        pytest.param(_token_alg_none(), id="alg-none"),
        pytest.param(_token_hs512(), id="hs512"),
        pytest.param(_firmar(_payload_valido(exp=_AUSENTE)), id="sin-exp"),
        pytest.param(_firmar(_payload_valido(sub=_AUSENTE)), id="sin-sub"),
        pytest.param(_firmar(_payload_valido(sub="abc")), id="sub-no-uuid"),
        pytest.param(_firmar(_payload_valido(sub=str(uuid4()).upper() + "x")), id="sub-casi-uuid"),
        pytest.param("no-es-un-jwt", id="texto-cualquiera"),
        pytest.param("", id="vacio"),
        pytest.param("a.b.c", id="tres-partes-invalidas"),
    ],
)
def test_decodificar_rechaza_los_tokens_invalidos(token: str) -> None:
    with pytest.raises(TokenInvalidoError):
        EmisorTokens(SECRETO, 60).decodificar(token)


def test_decodificar_acepta_un_token_firmado_a_mano_que_vence_en_60_segundos() -> None:
    sub = uuid4()
    token = _firmar(_payload_valido(sub=str(sub), exp=datetime.now(UTC) + timedelta(seconds=60)))

    claims = EmisorTokens(SECRETO, 60).decodificar(token)

    assert claims.sub == str(sub)


def test_decodificar_acepta_un_token_sin_los_claims_informativos() -> None:
    sub = uuid4()
    token = _firmar(_payload_valido(sub=str(sub), rol=_AUSENTE, profesional_id=_AUSENTE))

    claims = EmisorTokens(SECRETO, 60).decodificar(token)

    assert claims.sub == str(sub)
    assert claims.rol is None
    assert claims.profesional_id is None


# --- 2.3 el módulo no depende del framework ni de la base ---------------------------------


def _modulos_importados(modulo: str) -> set[str]:
    ruta = Path(__file__).parents[2] / "app" / "infrastructure" / "security" / f"{modulo}.py"
    importados: set[str] = set()
    for nodo in ast.walk(ast.parse(ruta.read_text("utf-8"))):
        if isinstance(nodo, ast.Import):
            importados.update(alias.name.split(".")[0] for alias in nodo.names)
        elif isinstance(nodo, ast.ImportFrom) and nodo.module and nodo.level == 0:
            importados.add(nodo.module.split(".")[0])
    return importados


@pytest.mark.parametrize(("modulo", "libreria"), [("tokens", "jwt"), ("contrasenas", "pwdlib")])
def test_los_modulos_de_seguridad_no_importan_fastapi_ni_sqlalchemy(
    modulo: str, libreria: str
) -> None:
    importados = _modulos_importados(modulo)

    assert libreria in importados  # el parseo detecta imports reales
    assert importados.isdisjoint({"fastapi", "sqlalchemy", "starlette"})
