"""Autenticación de las rutas de bloqueos: app real, PostgreSQL real, tokens reales."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.db.models import Bloqueo, Profesional, Usuario
from tests.conftest import SECRETO_TEST

CUERPO_401 = {"detail": {"codigo": "no_autenticado", "mensaje": "No autenticado"}}
INICIO = datetime(2026, 10, 8, 13, 0, tzinfo=UTC)  # 10:00 hora local


@pytest.fixture
def anonimo(client: TestClient, cliente_anonimo: TestClient) -> TestClient:
    return cliente_anonimo


@pytest.fixture
def b1(db_session: Session, recepcionista: Usuario) -> Bloqueo:
    """Bloqueo B1 del profesional A, el único de la base al empezar cada test."""
    profesional = Profesional(nombre="Ana", apellido="Ficticia")
    db_session.add(profesional)
    db_session.flush()
    bloqueo = Bloqueo(
        profesional_id=profesional.id,
        inicio=INICIO,
        fin=INICIO + timedelta(hours=2),
        motivo="Congreso",
        creado_por=recepcionista.id,
    )
    db_session.add(bloqueo)
    db_session.flush()
    return bloqueo


def _cuerpo_valido(b1: Bloqueo) -> dict[str, str]:
    return {
        "profesional_id": str(b1.profesional_id),
        "inicio": "2026-10-09T10:00:00-03:00",
        "fin": "2026-10-09T12:00:00-03:00",
        "motivo": "Trámite",
    }


def _ids(session: Session) -> list[UUID]:
    session.expire_all()
    return list(session.scalars(select(Bloqueo.id)))


def _sin_cambios(session: Session, b1: Bloqueo) -> None:
    assert _ids(session) == [b1.id]


def _token(usuario: Usuario, *, exp: datetime, secreto: str = SECRETO_TEST) -> dict[str, str]:
    token = jwt.encode({"sub": str(usuario.id), "exp": exp}, secreto, algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


def test_sin_token_las_tres_rutas_responden_401_y_b1_sigue_siendo_el_unico_bloqueo(
    anonimo: TestClient, db_session: Session, b1: Bloqueo
) -> None:
    respuestas = [
        anonimo.post("/bloqueos", json=_cuerpo_valido(b1)),
        anonimo.get("/bloqueos"),
        anonimo.delete(f"/bloqueos/{b1.id}"),
    ]

    for respuesta in respuestas:
        assert respuesta.status_code == 401
        assert respuesta.headers["WWW-Authenticate"] == "Bearer"
        assert respuesta.json() == CUERPO_401
    _sin_cambios(db_session, b1)


def test_la_autenticacion_se_evalua_antes_que_el_body_y_el_path(
    anonimo: TestClient, db_session: Session, b1: Bloqueo
) -> None:
    con_body_invalido = anonimo.post("/bloqueos", json={"fin": "no-es-fecha"})
    con_path_invalido = anonimo.delete("/bloqueos/no-es-un-id")
    con_query_invalida = anonimo.get("/bloqueos", params={"profesional_id": "no-es-un-id"})

    assert con_body_invalido.status_code == 401
    assert con_path_invalido.status_code == 401
    assert con_query_invalida.status_code == 401
    _sin_cambios(db_session, b1)


def test_token_vencido_o_con_firma_alterada_responde_401_y_no_persiste(
    anonimo: TestClient, db_session: Session, b1: Bloqueo, recepcionista: Usuario
) -> None:
    vencido = _token(recepcionista, exp=datetime.now(UTC) - timedelta(hours=1))
    alterado = _token(
        recepcionista,
        exp=datetime.now(UTC) + timedelta(hours=1),
        secreto="otro-secreto-ficticio-de-al-menos-32-bytes-para-firmar",
    )

    for encabezados in (vencido, alterado):
        respuesta = anonimo.post("/bloqueos", json=_cuerpo_valido(b1), headers=encabezados)

        assert respuesta.status_code == 401
        assert respuesta.headers["WWW-Authenticate"] == "Bearer"
        assert respuesta.json() == CUERPO_401
    _sin_cambios(db_session, b1)


def test_un_token_que_vence_en_60_segundos_todavia_vale(
    anonimo: TestClient, db_session: Session, b1: Bloqueo, recepcionista: Usuario
) -> None:
    encabezados = _token(recepcionista, exp=datetime.now(UTC) + timedelta(seconds=60))

    respuesta = anonimo.post("/bloqueos", json=_cuerpo_valido(b1), headers=encabezados)

    assert respuesta.status_code == 201
    assert len(_ids(db_session)) == 2
