"""RBAC y `creado_por` en las rutas de turnos: app real, PostgreSQL real, tokens reales."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.turnos import get_reloj
from app.infrastructure.db.models import Turno, Usuario
from app.infrastructure.security.contrasenas import Hasher
from app.infrastructure.security.tokens import EmisorTokens
from tests.conftest import SECRETO_TEST
from tests.integration.factories import Catalogo, crear_catalogo

AHORA = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)  # 2026-10-07 09:00 hora local
INICIO_LOCAL = "2026-10-08T10:00:00-03:00"
INICIO = datetime(2026, 10, 8, 13, 0, tzinfo=UTC)
CUERPO_401 = {"detail": {"codigo": "no_autenticado", "mensaje": "No autenticado"}}
CUERPO_403 = {"detail": {"codigo": "rol_insuficiente", "mensaje": "Rol insuficiente"}}

Peticion = tuple[str, str, dict[str, Any]]
ArmarPeticion = Callable[[str], Peticion]


@pytest.fixture
def catalogo(db_session: Session) -> Catalogo:
    return crear_catalogo(db_session)


@pytest.fixture
def api(client: TestClient) -> TestClient:
    """Cliente autenticado como la recepcionista de test, con el reloj fijo."""
    client.app.dependency_overrides[get_reloj] = lambda: lambda: AHORA  # type: ignore[attr-defined]
    return client


@pytest.fixture
def anonimo(api: TestClient, cliente_anonimo: TestClient) -> TestClient:
    """Cliente sin `Authorization` (comparte la app y el reloj fijo de `api`)."""
    return cliente_anonimo


@pytest.fixture
def otra_recepcionista(db_session: Session, hasher_test: Hasher) -> Usuario:
    usuario = Usuario(
        email="recepcion2@example.com",
        password_hash=hasher_test.hash("clave-ficticia-recepcion-2"),
        rol="recepcionista",
    )
    db_session.add(usuario)
    db_session.flush()
    return usuario


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _de(usuario: Usuario, emisor: EmisorTokens) -> dict[str, str]:
    return _bearer(emisor.emitir(usuario))


def _firmado(usuario: Usuario, *, exp: datetime) -> dict[str, str]:
    token = jwt.encode({"sub": str(usuario.id), "exp": exp}, SECRETO_TEST, algorithm="HS256")
    return _bearer(token)


def _body(c: Catalogo, **cambios: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "profesional_id": str(c.profesionales[0].id),
        "paciente_id": str(c.pacientes[0].id),
        "prestacion_id": str(c.limpieza.id),
        "sillon_id": str(c.sillones[0].id),
        "inicio": INICIO_LOCAL,
    }
    body.update(cambios)
    return body


def _cantidad(session: Session) -> int:
    session.expire_all()
    return session.scalar(select(func.count()).select_from(Turno)) or 0


def _turno(session: Session, turno_id: str) -> Turno:
    session.expire_all()
    return session.execute(select(Turno).where(Turno.id == UUID(turno_id))).scalar_one()


def _crear(api: TestClient, c: Catalogo) -> str:
    respuesta = api.post("/turnos", json=_body(c))
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()["id"]


# --- 7.4 POST /turnos --------------------------------------------------------------------


def test_post_turnos_sin_token_responde_401_y_no_persiste(
    anonimo: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    respuesta = anonimo.post("/turnos", json=_body(catalogo))

    assert respuesta.status_code == 401
    assert respuesta.json() == CUERPO_401
    assert respuesta.headers["WWW-Authenticate"] == "Bearer"
    assert _cantidad(db_session) == 0


def test_post_turnos_de_un_odontologo_responde_403_y_no_persiste(
    anonimo: TestClient,
    db_session: Session,
    catalogo: Catalogo,
    odontologo: Usuario,
    emisor_test: EmisorTokens,
) -> None:
    respuesta = anonimo.post("/turnos", json=_body(catalogo), headers=_de(odontologo, emisor_test))

    assert respuesta.status_code == 403
    assert respuesta.json() == CUERPO_403
    assert _cantidad(db_session) == 0


def test_post_turnos_ignora_un_creado_por_del_body_y_usa_al_autenticado(
    api: TestClient,
    db_session: Session,
    catalogo: Catalogo,
    recepcionista: Usuario,
    otra_recepcionista: Usuario,
) -> None:
    respuesta = api.post("/turnos", json=_body(catalogo, creado_por=str(otra_recepcionista.id)))

    assert respuesta.status_code == 201
    assert respuesta.json()["creado_por"] == str(recepcionista.id)
    assert _turno(db_session, respuesta.json()["id"]).creado_por == recepcionista.id


def test_post_turnos_sin_token_y_con_body_incompleto_responde_401_y_no_422(
    anonimo: TestClient, db_session: Session
) -> None:
    respuesta = anonimo.post("/turnos", json={"profesional_id": "no-es-un-uuid"})

    assert respuesta.status_code == 401
    assert respuesta.json() == CUERPO_401
    assert _cantidad(db_session) == 0


def test_post_turnos_de_un_odontologo_con_body_incompleto_responde_403_y_no_422(
    anonimo: TestClient, odontologo: Usuario, emisor_test: EmisorTokens
) -> None:
    respuesta = anonimo.post("/turnos", json={}, headers=_de(odontologo, emisor_test))

    assert respuesta.status_code == 403


@pytest.mark.parametrize(
    "segundos", [-3600, -60], ids=["vencido-hace-una-hora", "recien-vencido-60s"]
)
def test_post_turnos_con_token_vencido_responde_401_y_no_persiste(
    anonimo: TestClient,
    db_session: Session,
    catalogo: Catalogo,
    recepcionista: Usuario,
    segundos: int,
) -> None:
    encabezados = _firmado(recepcionista, exp=datetime.now(UTC) + timedelta(seconds=segundos))

    respuesta = anonimo.post("/turnos", json=_body(catalogo), headers=encabezados)

    assert respuesta.status_code == 401
    assert respuesta.json() == CUERPO_401
    assert _cantidad(db_session) == 0


def test_post_turnos_con_usuario_desactivado_tras_emitir_el_token_responde_401(
    anonimo: TestClient,
    db_session: Session,
    catalogo: Catalogo,
    recepcionista: Usuario,
    emisor_test: EmisorTokens,
) -> None:
    encabezados = _de(recepcionista, emisor_test)
    recepcionista.activo = False
    db_session.flush()

    respuesta = anonimo.post("/turnos", json=_body(catalogo), headers=encabezados)

    assert respuesta.status_code == 401
    assert respuesta.json() == CUERPO_401
    assert _cantidad(db_session) == 0


def test_post_turnos_con_token_que_vence_en_60_segundos_responde_201(
    anonimo: TestClient, db_session: Session, catalogo: Catalogo, recepcionista: Usuario
) -> None:
    encabezados = _firmado(recepcionista, exp=datetime.now(UTC) + timedelta(seconds=60))

    respuesta = anonimo.post("/turnos", json=_body(catalogo), headers=encabezados)

    assert respuesta.status_code == 201
    assert respuesta.json()["creado_por"] == str(recepcionista.id)
    assert _turno(db_session, respuesta.json()["id"]).creado_por == recepcionista.id


# --- 7.5 cancelar y reprogramar ----------------------------------------------------------


def _cancelar(turno_id: str) -> Peticion:
    return "POST", f"/turnos/{turno_id}/cancelar", {"motivo": "Viaje"}


def _reprogramar(turno_id: str) -> Peticion:
    return "PATCH", f"/turnos/{turno_id}/reprogramar", {"inicio": "2026-10-08T15:00:00-03:00"}


PETICIONES = [pytest.param(_cancelar, id="cancelar"), pytest.param(_reprogramar, id="reprogramar")]


def _intacto(session: Session, turno_id: str, autor: Usuario) -> None:
    turno = _turno(session, turno_id)
    assert (turno.estado, turno.inicio, turno.creado_por) == ("programado", INICIO, autor.id)


@pytest.mark.parametrize("armar", PETICIONES)
def test_sin_token_responde_401_y_deja_el_turno_intacto(
    api: TestClient,
    anonimo: TestClient,
    db_session: Session,
    catalogo: Catalogo,
    recepcionista: Usuario,
    armar: ArmarPeticion,
) -> None:
    turno_id = _crear(api, catalogo)
    metodo, url, cuerpo = armar(turno_id)

    respuesta = anonimo.request(metodo, url, json=cuerpo)

    assert respuesta.status_code == 401
    assert respuesta.json() == CUERPO_401
    _intacto(db_session, turno_id, recepcionista)


@pytest.mark.parametrize("armar", PETICIONES)
def test_odontologo_responde_403_y_deja_el_turno_intacto(
    api: TestClient,
    anonimo: TestClient,
    db_session: Session,
    catalogo: Catalogo,
    recepcionista: Usuario,
    odontologo: Usuario,
    emisor_test: EmisorTokens,
    armar: ArmarPeticion,
) -> None:
    turno_id = _crear(api, catalogo)
    metodo, url, cuerpo = armar(turno_id)

    respuesta = anonimo.request(metodo, url, json=cuerpo, headers=_de(odontologo, emisor_test))

    assert respuesta.status_code == 403
    assert respuesta.json() == CUERPO_403
    _intacto(db_session, turno_id, recepcionista)


@pytest.mark.parametrize("armar", PETICIONES)
def test_odontologo_con_turno_inexistente_responde_403_y_no_404(
    anonimo: TestClient, odontologo: Usuario, emisor_test: EmisorTokens, armar: ArmarPeticion
) -> None:
    metodo, url, cuerpo = armar(str(uuid4()))

    respuesta = anonimo.request(metodo, url, json=cuerpo, headers=_de(odontologo, emisor_test))

    assert respuesta.status_code == 403


@pytest.mark.parametrize("armar", PETICIONES)
def test_sin_token_con_turno_inexistente_responde_401_y_no_404(
    anonimo: TestClient, armar: ArmarPeticion
) -> None:
    metodo, url, cuerpo = armar(str(uuid4()))

    assert anonimo.request(metodo, url, json=cuerpo).status_code == 401


def _motivo_largo(turno_id: str) -> Peticion:
    return "POST", f"/turnos/{turno_id}/cancelar", {"motivo": "x" * 300}


def _fecha_invalida(turno_id: str) -> Peticion:
    return "PATCH", f"/turnos/{turno_id}/reprogramar", {"inicio": "no-es-una-fecha"}


def _inicio_nulo(turno_id: str) -> Peticion:
    return "PATCH", f"/turnos/{turno_id}/reprogramar", {"inicio": None}


@pytest.mark.parametrize(
    "armar",
    [
        pytest.param(_motivo_largo, id="cancelar-motivo-largo"),
        pytest.param(_fecha_invalida, id="reprogramar-fecha-invalida"),
        pytest.param(_inicio_nulo, id="reprogramar-inicio-nulo"),
    ],
)
def test_odontologo_con_campos_mal_formados_responde_403_y_no_422(
    anonimo: TestClient, odontologo: Usuario, emisor_test: EmisorTokens, armar: ArmarPeticion
) -> None:
    metodo, url, cuerpo = armar(str(uuid4()))

    respuesta = anonimo.request(metodo, url, json=cuerpo, headers=_de(odontologo, emisor_test))

    assert respuesta.status_code == 403
    assert respuesta.json() == CUERPO_403


def test_turno_con_id_mal_formado_responde_403_al_odontologo_y_401_sin_token(
    anonimo: TestClient, odontologo: Usuario, emisor_test: EmisorTokens
) -> None:
    con_token = anonimo.post("/turnos/no-es-uuid/cancelar", headers=_de(odontologo, emisor_test))
    sin_token = anonimo.post("/turnos/no-es-uuid/cancelar")

    assert (con_token.status_code, sin_token.status_code) == (403, 401)


@pytest.mark.parametrize("armar", PETICIONES)
def test_otra_recepcionista_conserva_el_autor_del_turno(
    api: TestClient,
    anonimo: TestClient,
    db_session: Session,
    catalogo: Catalogo,
    recepcionista: Usuario,
    otra_recepcionista: Usuario,
    emisor_test: EmisorTokens,
    armar: ArmarPeticion,
) -> None:
    turno_id = _crear(api, catalogo)
    metodo, url, cuerpo = armar(turno_id)

    respuesta = anonimo.request(
        metodo, url, json=cuerpo, headers=_de(otra_recepcionista, emisor_test)
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["creado_por"] == str(recepcionista.id)
    assert _turno(db_session, turno_id).creado_por == recepcionista.id
