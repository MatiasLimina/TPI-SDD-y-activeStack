"""RN-AG-05 al reprogramar (PATCH /turnos/{id}/reprogramar) y cambios de horario sobre turnos."""

from datetime import UTC, datetime, time
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.turnos import get_reloj
from app.infrastructure.db.models import HorarioAtencion, Profesional, Turno
from tests.integration.factories import Catalogo, crear_catalogo

AHORA = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)  # 2026-10-07 09:00 hora local
JUEVES = 3


@pytest.fixture
def catalogo(db_session: Session) -> Catalogo:
    return crear_catalogo(db_session, con_horario=False)


@pytest.fixture
def api(client: TestClient) -> TestClient:
    client.app.dependency_overrides[get_reloj] = lambda: lambda: AHORA  # type: ignore[attr-defined]
    return client


def _franja(
    db_session: Session, p: Profesional, inicio: time = time(9, 0), fin: time = time(13, 0)
) -> HorarioAtencion:
    franja = HorarioAtencion(
        profesional_id=p.id, dia_semana=JUEVES, hora_inicio=inicio, hora_fin=fin
    )
    db_session.add(franja)
    db_session.flush()
    return franja


def _jueves(hora: int, minuto: int = 0) -> str:
    return f"2026-10-08T{hora:02d}:{minuto:02d}:00-03:00"


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


def _intacto(session: Session, turno_id: str, inicio: datetime, fin: datetime) -> None:
    turno = _turno(session, turno_id)
    assert (turno.inicio, turno.fin, turno.estado) == (inicio, fin, "programado")


def _utc(hora: int, minuto: int = 0) -> datetime:
    return datetime(2026, 10, 8, hora, minuto, tzinfo=UTC)


def test_reprogramar_a_un_inicio_fuera_del_horario_responde_422_y_el_turno_queda_intacto(
    api: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    _franja(db_session, catalogo.profesionales[0])
    turno_id = _crear(api, catalogo, _jueves(10))

    respuesta = api.patch(f"/turnos/{turno_id}/reprogramar", json={"inicio": _jueves(12, 30)})

    assert respuesta.status_code == 422
    assert respuesta.json()["detail"]["codigo"] == "fuera_de_horario"
    _intacto(db_session, turno_id, _utc(13), _utc(13, 45))


def test_reprogramar_a_un_profesional_sin_franja_ese_dia_responde_422(
    api: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    _franja(db_session, catalogo.profesionales[0])
    turno_id = _crear(api, catalogo, _jueves(10))

    respuesta = api.patch(
        f"/turnos/{turno_id}/reprogramar",
        json={"profesional_id": str(catalogo.profesionales[1].id)},
    )

    assert respuesta.status_code == 422
    assert respuesta.json()["detail"]["codigo"] == "fuera_de_horario"
    assert _turno(db_session, turno_id).profesional_id == catalogo.profesionales[0].id


def test_turno_que_quedo_fuera_de_horario_no_se_reprograma_solo_para_cambiar_el_sillon(
    api: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    profesional = catalogo.profesionales[0]
    franja = _franja(db_session, profesional, time(9, 0), time(14, 0))
    turno_id = _crear(api, catalogo, _jueves(12, 30))
    editada = api.patch(
        f"/profesionales/{profesional.id}/horarios/{franja.id}", json={"hora_fin": "12:00"}
    )
    assert editada.status_code == 200

    respuesta = api.patch(
        f"/turnos/{turno_id}/reprogramar", json={"sillon_id": str(catalogo.sillones[1].id)}
    )

    assert respuesta.status_code == 422
    assert respuesta.json()["detail"]["codigo"] == "fuera_de_horario"
    assert _turno(db_session, turno_id).sillon_id == catalogo.sillones[0].id
    _intacto(db_session, turno_id, _utc(15, 30), _utc(16, 15))


def test_ampliar_la_duracion_mas_alla_de_la_franja_responde_422(
    api: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    _franja(db_session, catalogo.profesionales[0])
    turno_id = _crear(api, catalogo, _jueves(12, 15))

    respuesta = api.patch(f"/turnos/{turno_id}/reprogramar", json={"duracion_min": 60})

    assert respuesta.status_code == 422
    assert respuesta.json()["detail"]["codigo"] == "fuera_de_horario"
    _intacto(db_session, turno_id, _utc(15, 15), _utc(16, 0))


def test_reprogramar_que_termina_justo_al_cierre_de_la_franja_responde_200(
    api: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    _franja(db_session, catalogo.profesionales[0])
    turno_id = _crear(api, catalogo, _jueves(10))

    respuesta = api.patch(f"/turnos/{turno_id}/reprogramar", json={"inicio": _jueves(12, 15)})

    assert respuesta.status_code == 200
    assert respuesta.json()["inicio"] == "2026-10-08T12:15:00-03:00"
    assert respuesta.json()["fin"] == "2026-10-08T13:00:00-03:00"
    _intacto(db_session, turno_id, _utc(15, 15), _utc(16, 0))


def test_borrar_la_franja_de_un_turno_futuro_no_lo_modifica(
    api: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    profesional = catalogo.profesionales[0]
    franja = _franja(db_session, profesional)
    turno_id = _crear(api, catalogo, _jueves(10))

    respuesta = api.delete(f"/profesionales/{profesional.id}/horarios/{franja.id}")

    assert respuesta.status_code == 204
    _intacto(db_session, turno_id, _utc(13), _utc(13, 45))


def test_cancelar_un_turno_que_quedo_fuera_de_horario_responde_200_cancelado(
    api: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    profesional = catalogo.profesionales[0]
    franja = _franja(db_session, profesional, time(9, 0), time(14, 0))
    turno_id = _crear(api, catalogo, _jueves(12, 30))
    api.patch(f"/profesionales/{profesional.id}/horarios/{franja.id}", json={"hora_fin": "12:00"})

    respuesta = api.post(f"/turnos/{turno_id}/cancelar")

    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "cancelado"
