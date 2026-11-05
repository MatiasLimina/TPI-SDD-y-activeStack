"""API de bloqueos de agenda (C-11): app real, PostgreSQL real, tokens reales."""

from collections.abc import Callable
from datetime import UTC, datetime, time
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.turnos import get_reloj
from app.infrastructure.db.models import Bloqueo, HorarioAtencion, Profesional, Usuario
from tests.integration.factories import Catalogo, crear_catalogo

AHORA = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)  # 2026-10-07 09:00 hora local
MENSAJE_AJENO = "Solo podés operar sobre tus propios bloqueos"
CUERPO_AJENO = {"detail": {"codigo": "profesional_ajeno", "mensaje": MENSAJE_AJENO}}


@pytest.fixture
def catalogo(db_session: Session) -> Catalogo:
    return crear_catalogo(db_session)


@pytest.fixture
def api(client: TestClient) -> TestClient:
    """Cliente de la recepcionista con el reloj fijo en 2026-10-07 09:00 hora local."""
    client.app.dependency_overrides[get_reloj] = lambda: lambda: AHORA  # type: ignore[attr-defined]
    return client


@pytest.fixture
def como(app_de_test: Any, token_de: Callable[[Usuario], str]) -> Callable[[Usuario], TestClient]:
    """Cliente autenticado como el usuario indicado, con el mismo reloj fijo."""
    app_de_test.dependency_overrides[get_reloj] = lambda: lambda: AHORA

    def construir(usuario: Usuario) -> TestClient:
        return TestClient(app_de_test, headers={"Authorization": f"Bearer {token_de(usuario)}"})

    return construir


def _bloqueos(session: Session) -> list[Bloqueo]:
    session.expire_all()
    return list(session.scalars(select(Bloqueo).order_by(Bloqueo.inicio, Bloqueo.id)))


def _body(
    profesional: Profesional | UUID | None, inicio: str, fin: str, motivo: str
) -> dict[str, Any]:
    body: dict[str, Any] = {"inicio": inicio, "fin": fin, "motivo": motivo}
    if profesional is not None:
        body["profesional_id"] = str(
            profesional if isinstance(profesional, UUID) else profesional.id
        )
    return body


def _jueves(hora: int, minuto: int = 0) -> str:
    return f"2026-10-08T{hora:02d}:{minuto:02d}:00-03:00"


# --- Requisito: Alta de un bloqueo de agenda -------------------------------------------------


def test_recepcionista_bloquea_una_franja_y_la_respuesta_y_la_base_coinciden_con_el_spec(
    api: TestClient, db_session: Session, catalogo: Catalogo, recepcionista: Usuario
) -> None:
    a = catalogo.profesionales[0]

    respuesta = api.post("/bloqueos", json=_body(a, _jueves(10), _jueves(12), "Congreso"))

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo == {
        "id": cuerpo["id"],
        "profesional_id": str(a.id),
        "inicio": "2026-10-08T10:00:00-03:00",
        "fin": "2026-10-08T12:00:00-03:00",
        "motivo": "Congreso",
        "creado_por": str(recepcionista.id),
    }
    [guardado] = _bloqueos(db_session)
    assert str(guardado.id) == cuerpo["id"]
    assert guardado.inicio == datetime(2026, 10, 8, 13, 0, tzinfo=UTC)
    assert guardado.fin == datetime(2026, 10, 8, 15, 0, tzinfo=UTC)
    assert guardado.creado_por == recepcionista.id


def test_instantes_informados_en_utc_se_responden_en_hora_local(
    api: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    a = catalogo.profesionales[0]

    respuesta = api.post(
        "/bloqueos", json=_body(a, "2026-10-08T13:00:00Z", "2026-10-08T15:00:00Z", "Congreso")
    )

    assert respuesta.status_code == 201
    assert respuesta.json()["inicio"] == "2026-10-08T10:00:00-03:00"
    assert respuesta.json()["fin"] == "2026-10-08T12:00:00-03:00"


def test_bloqueo_de_varios_dias_se_guarda_en_utc(
    api: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    a = catalogo.profesionales[0]

    respuesta = api.post(
        "/bloqueos",
        json=_body(a, "2026-10-12T00:00:00-03:00", "2026-10-17T00:00:00-03:00", "Vacaciones"),
    )

    assert respuesta.status_code == 201
    assert respuesta.json()["inicio"] == "2026-10-12T00:00:00-03:00"
    assert respuesta.json()["fin"] == "2026-10-17T00:00:00-03:00"
    [guardado] = _bloqueos(db_session)
    assert guardado.inicio == datetime(2026, 10, 12, 3, 0, tzinfo=UTC)
    assert guardado.fin == datetime(2026, 10, 17, 3, 0, tzinfo=UTC)


def test_bloqueo_fuera_del_horario_de_atencion_se_acepta(
    api: TestClient, db_session: Session, catalogo_sin_horario: Catalogo
) -> None:
    a = catalogo_sin_horario.profesionales[0]
    db_session.add_all(
        HorarioAtencion(
            profesional_id=a.id, dia_semana=dia, hora_inicio=time(9, 0), hora_fin=time(13, 0)
        )
        for dia in range(5)  # lunes a viernes
    )
    db_session.flush()

    respuesta = api.post(
        "/bloqueos",
        json=_body(a, "2026-10-10T10:00:00-03:00", "2026-10-10T11:00:00-03:00", "Curso"),
    )  # sábado

    assert respuesta.status_code == 201


def test_bloqueo_en_el_pasado_se_acepta(
    api: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    a = catalogo.profesionales[0]

    respuesta = api.post(
        "/bloqueos",
        json=_body(a, "2026-10-06T10:00:00-03:00", "2026-10-06T11:00:00-03:00", "Curso"),
    )

    assert respuesta.status_code == 201
    assert len(_bloqueos(db_session)) == 1


def test_bloqueo_de_un_profesional_desactivado_se_acepta(
    api: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    b = catalogo.profesionales[1]
    b.activo = False
    db_session.flush()

    respuesta = api.post("/bloqueos", json=_body(b, _jueves(10), _jueves(11), "Trámite"))

    assert respuesta.status_code == 201
    assert respuesta.json()["profesional_id"] == str(b.id)


def test_bloqueo_fuera_de_la_grilla_de_5_minutos_se_acepta_tal_cual(
    api: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    a = catalogo.profesionales[0]

    respuesta = api.post("/bloqueos", json=_body(a, _jueves(10, 3), _jueves(10, 7), "Trámite"))

    assert respuesta.status_code == 201
    assert respuesta.json()["inicio"] == "2026-10-08T10:03:00-03:00"
    assert respuesta.json()["fin"] == "2026-10-08T10:07:00-03:00"


@pytest.fixture
def catalogo_sin_horario(db_session: Session) -> Catalogo:
    return crear_catalogo(db_session, con_horario=False)
