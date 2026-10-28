"""`AutenticarToken` y `usuario_actual` sobre una ruta de prueba, con PostgreSQL real."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import uuid4

import jwt
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.auth import requiere_rol, usuario_actual
from app.domain.usuarios import Rol, UsuarioAutenticado
from app.infrastructure.db.models import Usuario
from app.infrastructure.security.tokens import EmisorTokens
from tests.conftest import SECRETO_TEST

CUERPO_401 = {"detail": {"codigo": "no_autenticado", "mensaje": "No autenticado"}}
RUTA = "/_prueba/yo"


@pytest.fixture
def cliente(app_de_test: FastAPI) -> TestClient:
    @app_de_test.get(RUTA)
    def yo(
        usuario: Annotated[UsuarioAutenticado, Depends(usuario_actual)],
    ) -> dict[str, str | None]:
        return {
            "id": str(usuario.id),
            "rol": usuario.rol,
            "profesional_id": None
            if usuario.profesional_id is None
            else str(usuario.profesional_id),
        }

    return TestClient(app_de_test)


def _firmar(sub: object, *, exp: datetime | None = None, **extra: object) -> str:
    payload: dict[str, object] = {"sub": sub, **extra}
    if exp is not None:
        payload["exp"] = exp
    return jwt.encode(payload, SECRETO_TEST, algorithm="HS256")


def _ahora() -> datetime:
    return datetime.now(UTC)


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_token_valido_devuelve_el_usuario_con_rol_y_profesional_de_la_base(
    cliente: TestClient, odontologo: Usuario, token_de: Callable[[Usuario], str]
) -> None:
    respuesta = cliente.get(RUTA, headers=_bearer(token_de(odontologo)))

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "id": str(odontologo.id),
        "rol": "odontologo",
        "profesional_id": str(odontologo.profesional_id),
    }


def test_la_recepcionista_se_autentica_sin_profesional(
    cliente: TestClient, recepcionista: Usuario, token_de: Callable[[Usuario], str]
) -> None:
    respuesta = cliente.get(RUTA, headers=_bearer(token_de(recepcionista)))

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "id": str(recepcionista.id),
        "rol": "recepcionista",
        "profesional_id": None,
    }


def test_el_rol_y_el_profesional_salen_de_la_base_y_no_de_los_claims(
    cliente: TestClient, odontologo: Usuario, recepcionista: Usuario
) -> None:
    token = _firmar(
        str(odontologo.id),
        exp=_ahora() + timedelta(minutes=5),
        rol="recepcionista",
        profesional_id=str(uuid4()),
    )

    respuesta = cliente.get(RUTA, headers=_bearer(token))

    assert respuesta.status_code == 200
    assert respuesta.json()["rol"] == "odontologo"
    assert respuesta.json()["profesional_id"] == str(odontologo.profesional_id)


def test_un_token_que_vence_en_60_segundos_todavia_pasa(
    cliente: TestClient, recepcionista: Usuario
) -> None:
    token = _firmar(str(recepcionista.id), exp=_ahora() + timedelta(seconds=60))

    assert cliente.get(RUTA, headers=_bearer(token)).status_code == 200


def _sin_encabezado(_: Usuario, __: Session) -> dict[str, str]:
    return {}


def _esquema_basic(_: Usuario, __: Session) -> dict[str, str]:
    return {"Authorization": "Basic dXN1YXJpbzpjbGF2ZQ=="}


def _bearer_vacio(_: Usuario, __: Session) -> dict[str, str]:
    return {"Authorization": "Bearer "}


def _basura(_: Usuario, __: Session) -> dict[str, str]:
    return _bearer("no-es-un-jwt")


def _vencido_hace_una_hora(u: Usuario, __: Session) -> dict[str, str]:
    return _bearer(_firmar(str(u.id), exp=_ahora() - timedelta(hours=1)))


def _recien_vencido(u: Usuario, __: Session) -> dict[str, str]:
    return _bearer(_firmar(str(u.id), exp=_ahora() - timedelta(seconds=60)))


def _otra_clave(u: Usuario, __: Session) -> dict[str, str]:
    token = jwt.encode(
        {"sub": str(u.id), "exp": _ahora() + timedelta(minutes=5)},
        "otra-clave-ficticia-de-al-menos-32-bytes-xx",
        algorithm="HS256",
    )
    return _bearer(token)


def _alg_none(u: Usuario, __: Session) -> dict[str, str]:
    payload = {"sub": str(u.id), "exp": _ahora() + timedelta(minutes=5)}
    return _bearer(jwt.encode(payload, None, algorithm="none"))


def _sin_exp(u: Usuario, __: Session) -> dict[str, str]:
    return _bearer(_firmar(str(u.id)))


def _sin_sub(_: Usuario, __: Session) -> dict[str, str]:
    token = jwt.encode({"exp": _ahora() + timedelta(minutes=5)}, SECRETO_TEST, algorithm="HS256")
    return _bearer(token)


def _sub_no_uuid(_: Usuario, __: Session) -> dict[str, str]:
    return _bearer(_firmar("abc", exp=_ahora() + timedelta(minutes=5)))


def _sub_inexistente(_: Usuario, __: Session) -> dict[str, str]:
    return _bearer(_firmar(str(uuid4()), exp=_ahora() + timedelta(minutes=5)))


def _usuario_desactivado(u: Usuario, session: Session) -> dict[str, str]:
    token = EmisorTokens(SECRETO_TEST, 60).emitir(u)
    u.activo = False
    session.flush()
    return _bearer(token)


@pytest.mark.parametrize(
    "armar",
    [
        pytest.param(_sin_encabezado, id="sin-encabezado"),
        pytest.param(_esquema_basic, id="esquema-basic"),
        pytest.param(_bearer_vacio, id="bearer-vacio"),
        pytest.param(_basura, id="no-es-un-jwt"),
        pytest.param(_vencido_hace_una_hora, id="vencido-hace-una-hora"),
        pytest.param(_recien_vencido, id="recien-vencido-60s"),
        pytest.param(_otra_clave, id="firmado-con-otra-clave"),
        pytest.param(_alg_none, id="alg-none"),
        pytest.param(_sin_exp, id="sin-exp"),
        pytest.param(_sin_sub, id="sin-sub"),
        pytest.param(_sub_no_uuid, id="sub-no-uuid"),
        pytest.param(_sub_inexistente, id="sub-inexistente"),
        pytest.param(_usuario_desactivado, id="usuario-desactivado-tras-emitir"),
    ],
)
def test_todo_problema_de_token_responde_el_mismo_401(
    cliente: TestClient,
    db_session: Session,
    recepcionista: Usuario,
    armar: Callable[[Usuario, Session], dict[str, str]],
) -> None:
    encabezados = armar(recepcionista, db_session)

    respuesta = cliente.get(RUTA, headers=encabezados)

    assert respuesta.status_code == 401
    assert respuesta.json() == CUERPO_401
    assert respuesta.headers["WWW-Authenticate"] == "Bearer"


# --- 7.2 requiere_rol --------------------------------------------------------------------

CUERPO_403 = {"detail": {"codigo": "rol_insuficiente", "mensaje": "Rol insuficiente"}}


@pytest.fixture
def cliente_roles(app_de_test: FastAPI) -> TestClient:
    def _id(usuario: UsuarioAutenticado) -> dict[str, str]:
        return {"id": str(usuario.id)}

    @app_de_test.get("/_prueba/solo-recepcion")
    def solo_recepcion(
        usuario: Annotated[UsuarioAutenticado, Depends(requiere_rol(Rol.RECEPCIONISTA))],
    ) -> dict[str, str]:
        return _id(usuario)

    @app_de_test.get("/_prueba/ambos")
    def ambos(
        usuario: Annotated[
            UsuarioAutenticado, Depends(requiere_rol(Rol.RECEPCIONISTA, Rol.ODONTOLOGO))
        ],
    ) -> dict[str, str]:
        return _id(usuario)

    return TestClient(app_de_test)


def test_requiere_rol_deja_pasar_a_la_recepcionista(
    cliente_roles: TestClient, recepcionista: Usuario, token_de: Callable[[Usuario], str]
) -> None:
    respuesta = cliente_roles.get(
        "/_prueba/solo-recepcion", headers=_bearer(token_de(recepcionista))
    )

    assert respuesta.status_code == 200
    assert respuesta.json() == {"id": str(recepcionista.id)}


def test_requiere_rol_rechaza_al_odontologo_con_403(
    cliente_roles: TestClient, odontologo: Usuario, token_de: Callable[[Usuario], str]
) -> None:
    respuesta = cliente_roles.get("/_prueba/solo-recepcion", headers=_bearer(token_de(odontologo)))

    assert respuesta.status_code == 403
    assert respuesta.json() == CUERPO_403
    assert "WWW-Authenticate" not in respuesta.headers


def test_requiere_rol_usa_el_rol_de_la_base_y_no_el_del_token(
    cliente_roles: TestClient, odontologo: Usuario
) -> None:
    token = _firmar(str(odontologo.id), exp=_ahora() + timedelta(minutes=5), rol="recepcionista")

    respuesta = cliente_roles.get("/_prueba/solo-recepcion", headers=_bearer(token))

    assert respuesta.status_code == 403
    assert respuesta.json() == CUERPO_403


def test_requiere_rol_con_ambos_roles_deja_pasar_a_los_dos(
    cliente_roles: TestClient,
    recepcionista: Usuario,
    odontologo: Usuario,
    token_de: Callable[[Usuario], str],
) -> None:
    for usuario in (recepcionista, odontologo):
        respuesta = cliente_roles.get("/_prueba/ambos", headers=_bearer(token_de(usuario)))

        assert respuesta.status_code == 200
        assert respuesta.json() == {"id": str(usuario.id)}


def test_requiere_rol_sin_token_responde_401_y_no_403(cliente_roles: TestClient) -> None:
    respuesta = cliente_roles.get("/_prueba/solo-recepcion")

    assert respuesta.status_code == 401
    assert respuesta.json() == CUERPO_401
