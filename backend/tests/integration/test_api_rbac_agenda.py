"""GET /turnos con odontólogo y sin autenticación: app real, PostgreSQL real, tokens reales."""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

import jwt
import pytest
from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy.orm import Session

from app.infrastructure.db.models import Bloqueo, Turno, Usuario
from app.infrastructure.security.contrasenas import Hasher
from app.infrastructure.security.tokens import EmisorTokens
from tests.conftest import SECRETO_TEST
from tests.integration.factories import Catalogo, crear_catalogo

LOCAL = ZoneInfo("America/Argentina/Buenos_Aires")
CUERPO_401 = {"detail": {"codigo": "no_autenticado", "mensaje": "No autenticado"}}
MENSAJE_AJENO = "Solo podés consultar tu propia agenda"


def _l(dia: int, hora: int) -> datetime:
    return datetime(2026, 10, dia, hora, 0, tzinfo=LOCAL)


@pytest.fixture
def catalogo(db_session: Session) -> Catalogo:
    return crear_catalogo(db_session)


@pytest.fixture
def odontologo_de_a(
    db_session: Session, catalogo: Catalogo, hasher_test: Hasher, emisor_test: EmisorTokens
) -> dict[str, str]:
    """Encabezados de un odontólogo vinculado al profesional A del catálogo."""
    usuario = Usuario(
        email="odontologo.a@example.com",
        password_hash=hasher_test.hash("clave-ficticia-odontologo-a"),
        rol="odontologo",
        profesional_id=catalogo.profesionales[0].id,
    )
    db_session.add(usuario)
    db_session.flush()
    return {"Authorization": f"Bearer {emisor_test.emitir(usuario)}"}


def _turno(db_session: Session, c: Catalogo, hora: int, *, prof: int, sillon: int = 0) -> Turno:
    inicio = _l(8, hora)
    turno = Turno(
        profesional_id=c.profesionales[prof].id,
        sillon_id=c.sillones[sillon].id,
        paciente_id=c.pacientes[prof].id,
        prestacion_id=c.limpieza.id,
        inicio=inicio,
        fin=inicio + timedelta(minutes=45),
        duracion_min=45,
    )
    db_session.add(turno)
    db_session.flush()
    return turno


def _bloqueo(db_session: Session, c: Catalogo, autor: Usuario, prof: int) -> Bloqueo:
    bloqueo = Bloqueo(
        profesional_id=c.profesionales[prof].id,
        inicio=_l(8, 15),
        fin=_l(8, 16),
        motivo="Congreso",
        creado_por=autor.id,
    )
    db_session.add(bloqueo)
    db_session.flush()
    return bloqueo


def _pedir(client: TestClient, headers: dict[str, str], **extra: str | UUID) -> Response:
    params = {"desde": "2026-10-08", "hasta": "2026-10-08", **{k: str(v) for k, v in extra.items()}}
    return client.get("/turnos", params=params, headers=headers)


# --- 6.1 aislamiento del odontólogo -----------------------------------------------------------


def test_odontologo_sin_filtro_o_con_el_suyo_ve_solo_su_agenda(
    client: TestClient,
    db_session: Session,
    catalogo: Catalogo,
    recepcionista: Usuario,
    odontologo_de_a: dict[str, str],
) -> None:
    turno_a = _turno(db_session, catalogo, 10, prof=0)
    _turno(db_session, catalogo, 11, prof=1, sillon=1)
    bloqueo_a = _bloqueo(db_session, catalogo, recepcionista, 0)
    _bloqueo(db_session, catalogo, recepcionista, 1)

    sin_filtro = _pedir(client, odontologo_de_a)
    con_el_suyo = _pedir(client, odontologo_de_a, profesional_id=catalogo.profesionales[0].id)

    for respuesta in (sin_filtro, con_el_suyo):
        assert respuesta.status_code == 200
        cuerpo = respuesta.json()
        assert [t["id"] for t in cuerpo["turnos"]] == [str(turno_a.id)]
        assert [b["id"] for b in cuerpo["bloqueos"]] == [str(bloqueo_a.id)]


def test_odontologo_con_otro_profesional_o_uno_inexistente_recibe_403_identicos(
    client: TestClient,
    db_session: Session,
    catalogo: Catalogo,
    odontologo_de_a: dict[str, str],
) -> None:
    _turno(db_session, catalogo, 10, prof=1, sillon=1)

    de_b = _pedir(client, odontologo_de_a, profesional_id=catalogo.profesionales[1].id)
    inexistente = _pedir(client, odontologo_de_a, profesional_id=uuid4())

    for respuesta in (de_b, inexistente):
        assert respuesta.status_code == 403
        assert respuesta.json() == {
            "detail": {"codigo": "profesional_ajeno", "mensaje": MENSAJE_AJENO}
        }


def test_odontologo_con_sillon_compartido_nunca_ve_turnos_ni_bloqueos_de_otro_profesional(
    client: TestClient,
    db_session: Session,
    catalogo: Catalogo,
    recepcionista: Usuario,
    odontologo_de_a: dict[str, str],
) -> None:
    turno_a = _turno(db_session, catalogo, 10, prof=0, sillon=0)
    _turno(db_session, catalogo, 11, prof=1, sillon=0)
    bloqueo_a = _bloqueo(db_session, catalogo, recepcionista, 0)
    _bloqueo(db_session, catalogo, recepcionista, 1)

    respuesta = _pedir(client, odontologo_de_a, sillon_id=catalogo.sillones[0].id)

    cuerpo = respuesta.json()
    assert [t["id"] for t in cuerpo["turnos"]] == [str(turno_a.id)]
    assert [b["id"] for b in cuerpo["bloqueos"]] == [str(bloqueo_a.id)]


def test_el_odontologo_no_ve_documento_telefono_ni_email_del_paciente(
    client: TestClient,
    db_session: Session,
    catalogo: Catalogo,
    odontologo_de_a: dict[str, str],
) -> None:
    paciente = catalogo.pacientes[0]
    paciente.email = "paula.ficticia@example.com"
    _turno(db_session, catalogo, 10, prof=0)

    respuesta = _pedir(client, odontologo_de_a)

    (turno,) = respuesta.json()["turnos"]
    assert set(turno["paciente"]) == {"id", "nombre", "apellido"}
    for dato in (paciente.documento, paciente.telefono, paciente.email):
        assert dato is not None
        assert dato not in respuesta.text


def test_profesional_ajeno_se_evalua_antes_que_el_rango_invalido(
    client: TestClient, catalogo: Catalogo, odontologo_de_a: dict[str, str]
) -> None:
    respuesta = client.get(
        "/turnos",
        params={
            "desde": "2026-10-09",
            "hasta": "2026-10-08",
            "profesional_id": str(catalogo.profesionales[1].id),
        },
        headers=odontologo_de_a,
    )

    assert respuesta.status_code == 403
    assert respuesta.json()["detail"]["codigo"] == "profesional_ajeno"


def test_odontologo_con_rango_invalido_propio_recibe_422(
    client: TestClient, odontologo_de_a: dict[str, str]
) -> None:
    respuesta = client.get(
        "/turnos", params={"desde": "2026-10-09", "hasta": "2026-10-08"}, headers=odontologo_de_a
    )

    assert respuesta.status_code == 422
    assert respuesta.json()["detail"]["codigo"] == "rango_invalido"


# --- 6.2 autenticación ------------------------------------------------------------------------


def test_sin_token_da_401_con_www_authenticate_y_sin_turnos(
    cliente_anonimo: TestClient, client: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    _turno(db_session, catalogo, 10, prof=0)

    respuesta = cliente_anonimo.get(
        "/turnos", params={"desde": "2026-10-08", "hasta": "2026-10-08"}
    )

    assert respuesta.status_code == 401
    assert respuesta.headers["WWW-Authenticate"] == "Bearer"
    assert respuesta.json() == CUERPO_401


def test_autenticacion_antes_que_los_parametros(cliente_anonimo: TestClient) -> None:
    respuesta = cliente_anonimo.get("/turnos", params={"desde": "no-es-fecha"})

    assert respuesta.status_code == 401


def test_token_vencido_da_401_no_autenticado(
    cliente_anonimo: TestClient, recepcionista: Usuario
) -> None:
    vencido = jwt.encode(
        {"sub": str(recepcionista.id), "exp": datetime.now(UTC) - timedelta(hours=1)},
        SECRETO_TEST,
        algorithm="HS256",
    )

    respuesta = cliente_anonimo.get(
        "/turnos",
        params={"desde": "2026-10-08", "hasta": "2026-10-08"},
        headers={"Authorization": f"Bearer {vencido}"},
    )

    assert respuesta.status_code == 401
    assert respuesta.headers["WWW-Authenticate"] == "Bearer"
    assert respuesta.json()["detail"]["codigo"] == "no_autenticado"
