"""RN-AG-06 al reprogramar (PATCH /turnos/{id}/reprogramar), con reloj fijo inyectado."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.api.turnos import get_reloj
from app.infrastructure.db.models import Bloqueo, Profesional, Turno, Usuario
from tests.integration.factories import Catalogo, crear_catalogo
from tests.integration.helpers_recordatorios import recordatorios_de

AHORA = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)  # 2026-10-07 09:00 hora local
TURNO_EN_BLOQUEO = {
    "detail": {
        "codigo": "turno_en_bloqueo",
        "mensaje": "el turno se superpone con un bloqueo de agenda del profesional",
    }
}


@pytest.fixture
def catalogo(db_session: Session) -> Catalogo:
    return crear_catalogo(db_session)


@pytest.fixture
def api(client: TestClient) -> TestClient:
    client.app.dependency_overrides[get_reloj] = lambda: lambda: AHORA  # type: ignore[attr-defined]
    return client


def _local(dia: int, hora: int, minuto: int = 0) -> str:
    return f"2026-10-{dia:02d}T{hora:02d}:{minuto:02d}:00-03:00"


def _utc(dia: int, hora: int, minuto: int = 0) -> datetime:
    return datetime(2026, 10, dia, hora, minuto, tzinfo=UTC)


def _bloquear(
    db_session: Session, profesional: Profesional, autor: Usuario, inicio: str, fin: str
) -> None:
    db_session.add(
        Bloqueo(
            profesional_id=profesional.id,
            inicio=datetime.fromisoformat(inicio),
            fin=datetime.fromisoformat(fin),
            motivo="Congreso",
            creado_por=autor.id,
        )
    )
    db_session.flush()


def _crear(api: TestClient, c: Catalogo, inicio: str, **cambios: Any) -> str:
    body = {
        "profesional_id": str(c.profesionales[0].id),
        "paciente_id": str(c.pacientes[0].id),
        "prestacion_id": str(c.limpieza.id),
        "sillon_id": str(c.sillones[0].id),
        "inicio": inicio,
        **cambios,
    }
    respuesta = api.post("/turnos", json=body)
    assert respuesta.status_code == 201, respuesta.text
    return str(respuesta.json()["id"])


def _turno(session: Session, turno_id: str) -> Turno:
    session.expire_all()
    return session.execute(select(Turno).where(Turno.id == turno_id)).scalar_one()


def _intacto(
    session: Session, turno_id: str, profesional_id: UUID, inicio: datetime, fin: datetime
) -> None:
    turno = _turno(session, turno_id)
    assert (turno.profesional_id, turno.inicio, turno.fin, turno.estado) == (
        profesional_id,
        inicio,
        fin,
        "programado",
    )


def test_reprogramar_con_un_nuevo_inicio_dentro_de_un_bloqueo_responde_422_y_deja_el_turno(
    api: TestClient, db_session: Session, catalogo: Catalogo, recepcionista: Usuario
) -> None:
    a = catalogo.profesionales[0]
    _bloquear(db_session, a, recepcionista, _local(8, 10), _local(8, 12))
    turno_id = _crear(api, catalogo, _local(8, 15))

    respuesta = api.patch(f"/turnos/{turno_id}/reprogramar", json={"inicio": _local(8, 10, 30)})

    assert respuesta.status_code == 422
    assert respuesta.json() == TURNO_EN_BLOQUEO
    _intacto(db_session, turno_id, a.id, _utc(8, 18), _utc(8, 18, 45))  # 15:00-15:45 local


def test_reprogramar_hacia_un_profesional_con_un_bloqueo_en_ese_horario_responde_422(
    api: TestClient, db_session: Session, catalogo: Catalogo, recepcionista: Usuario
) -> None:
    a, b = catalogo.profesionales
    _bloquear(db_session, b, recepcionista, _local(8, 10), _local(8, 12))
    turno_id = _crear(api, catalogo, _local(8, 10, 30))

    respuesta = api.patch(f"/turnos/{turno_id}/reprogramar", json={"profesional_id": str(b.id)})

    assert respuesta.status_code == 422
    assert respuesta.json() == TURNO_EN_BLOQUEO
    _intacto(db_session, turno_id, a.id, _utc(8, 13, 30), _utc(8, 14, 15))


def test_ampliar_la_duracion_hacia_un_bloqueo_responde_422_y_deja_el_turno(
    api: TestClient, db_session: Session, catalogo: Catalogo, recepcionista: Usuario
) -> None:
    a = catalogo.profesionales[0]
    _bloquear(db_session, a, recepcionista, _local(8, 10), _local(8, 12))
    turno_id = _crear(api, catalogo, _local(8, 9, 15))  # 09:15-10:00

    respuesta = api.patch(f"/turnos/{turno_id}/reprogramar", json={"duracion_min": 60})

    assert respuesta.status_code == 422
    assert respuesta.json() == TURNO_EN_BLOQUEO
    _intacto(db_session, turno_id, a.id, _utc(8, 12, 15), _utc(8, 13))


def test_reprogramar_a_un_horario_que_termina_justo_al_empezar_el_bloqueo_responde_200(
    api: TestClient, db_session: Session, catalogo: Catalogo, recepcionista: Usuario
) -> None:
    a = catalogo.profesionales[0]
    _bloquear(db_session, a, recepcionista, _local(8, 10), _local(8, 12))
    turno_id = _crear(api, catalogo, _local(8, 15))

    respuesta = api.patch(f"/turnos/{turno_id}/reprogramar", json={"inicio": _local(8, 9, 15)})

    assert respuesta.status_code == 200
    assert respuesta.json()["inicio"] == "2026-10-08T09:15:00-03:00"
    assert respuesta.json()["fin"] == "2026-10-08T10:00:00-03:00"
    _intacto(db_session, turno_id, a.id, _utc(8, 12, 15), _utc(8, 13))


def test_reprogramacion_rechazada_por_un_bloqueo_conserva_el_recordatorio_y_la_auditoria(
    api: TestClient, db_session: Session, catalogo: Catalogo, recepcionista: Usuario
) -> None:
    a = catalogo.profesionales[0]
    _bloquear(db_session, a, recepcionista, _local(9, 10), _local(9, 12))
    turno_id = _crear(api, catalogo, _local(9, 15))
    recordatorios_antes = recordatorios_de(db_session, UUID(turno_id))
    auditoria_antes = db_session.execute(text("SELECT count(*) FROM turno_auditoria")).scalar_one()
    assert [r["estado"] for r in recordatorios_antes] == ["pendiente"]

    respuesta = api.patch(f"/turnos/{turno_id}/reprogramar", json={"inicio": _local(9, 10, 30)})

    assert respuesta.status_code == 422
    assert respuesta.json() == TURNO_EN_BLOQUEO
    assert recordatorios_de(db_session, UUID(turno_id)) == recordatorios_antes
    despues = db_session.execute(text("SELECT count(*) FROM turno_auditoria")).scalar_one()
    assert despues == auditoria_antes
