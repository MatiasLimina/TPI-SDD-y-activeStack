"""RN-AG-05 en POST /turnos: horario de atención del profesional, con reloj fijo inyectado."""

from datetime import UTC, datetime, time
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.turnos import get_reloj
from app.infrastructure.db.models import HorarioAtencion, Profesional, Turno
from tests.integration.factories import Catalogo, crear_catalogo

AHORA = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)  # 2026-10-07 09:00 hora local
JUEVES = 3
FUERA_DE_HORARIO = {
    "detail": {
        "codigo": "fuera_de_horario",
        "mensaje": "el turno no cabe en el horario de atención del profesional",
    }
}


@pytest.fixture
def catalogo(db_session: Session) -> Catalogo:
    return crear_catalogo(db_session, con_horario=False)


@pytest.fixture
def api(client: TestClient) -> TestClient:
    client.app.dependency_overrides[get_reloj] = lambda: lambda: AHORA  # type: ignore[attr-defined]
    return client


def _franja(db_session: Session, p: Profesional, dia: int, inicio: time, fin: time) -> None:
    db_session.add(
        HorarioAtencion(profesional_id=p.id, dia_semana=dia, hora_inicio=inicio, hora_fin=fin)
    )
    db_session.flush()


def _manana(db_session: Session, p: Profesional) -> None:
    _franja(db_session, p, JUEVES, time(9, 0), time(13, 0))


def _tarde(db_session: Session, p: Profesional) -> None:
    _franja(db_session, p, JUEVES, time(14, 0), time(18, 0))


def _body(c: Catalogo, inicio: str, **cambios: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "profesional_id": str(c.profesionales[0].id),
        "paciente_id": str(c.pacientes[0].id),
        "prestacion_id": str(c.limpieza.id),
        "sillon_id": str(c.sillones[0].id),
        "inicio": inicio,
    }
    body.update(cambios)
    return body


def _jueves(hora: int, minuto: int = 0) -> str:
    return f"2026-10-08T{hora:02d}:{minuto:02d}:00-03:00"


def _turnos(session: Session) -> int:
    return session.scalar(select(func.count()).select_from(Turno)) or 0


def test_turno_dentro_de_la_franja_responde_201_con_inicio_y_fin_locales(
    api: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    _manana(db_session, catalogo.profesionales[0])

    respuesta = api.post("/turnos", json=_body(catalogo, _jueves(10)))

    assert respuesta.status_code == 201
    assert respuesta.json()["inicio"] == "2026-10-08T10:00:00-03:00"
    assert respuesta.json()["fin"] == "2026-10-08T10:45:00-03:00"


def test_turno_que_abre_y_turno_que_cierra_la_franja_son_validos(
    api: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    _manana(db_session, catalogo.profesionales[0])

    abre = api.post("/turnos", json=_body(catalogo, _jueves(9)))
    cierra = api.post("/turnos", json=_body(catalogo, _jueves(12, 15)))

    assert (abre.status_code, cierra.status_code) == (201, 201)
    assert cierra.json()["fin"] == "2026-10-08T13:00:00-03:00"


@pytest.mark.parametrize(
    ("inicio", "extra"),
    [
        (_jueves(12, 30), {}),  # excede el fin de la franja
        (_jueves(8, 30), {}),  # empieza antes de abrir
        (_jueves(13, 15), {"duracion_min": 30}),  # hueco entre franjas
        (_jueves(12, 30), {"duracion_min": 120}),  # cruza dos franjas
        ("2026-10-10T10:00:00-03:00", {}),  # sábado, sin franjas
        ("2026-10-08T15:30:00Z", {}),  # 12:30 local: se evalúa en hora local, no en UTC
    ],
    ids=["excede", "antes", "hueco", "cruza-dos", "sabado", "hora-utc"],
)
def test_turno_fuera_de_las_franjas_responde_422_exacto_y_no_persiste(
    api: TestClient,
    db_session: Session,
    catalogo: Catalogo,
    inicio: str,
    extra: dict[str, Any],
) -> None:
    _manana(db_session, catalogo.profesionales[0])
    _tarde(db_session, catalogo.profesionales[0])

    respuesta = api.post("/turnos", json=_body(catalogo, inicio, **extra))

    assert respuesta.status_code == 422
    assert respuesta.json() == FUERA_DE_HORARIO
    assert _turnos(db_session) == 0


def test_turno_en_la_segunda_franja_del_dia_responde_201(
    api: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    _manana(db_session, catalogo.profesionales[0])
    _tarde(db_session, catalogo.profesionales[0])

    assert api.post("/turnos", json=_body(catalogo, _jueves(15))).status_code == 201


def test_turno_que_cruza_dos_franjas_contiguas_se_rechaza(
    api: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    profesional = catalogo.profesionales[0]
    _manana(db_session, profesional)
    _franja(db_session, profesional, JUEVES, time(13, 0), time(17, 0))

    respuesta = api.post("/turnos", json=_body(catalogo, _jueves(12, 30), duracion_min=60))

    assert respuesta.status_code == 422
    assert respuesta.json()["detail"]["codigo"] == "fuera_de_horario"
    assert _turnos(db_session) == 0


def test_profesional_sin_franjas_rechaza_todo_turno(
    api: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    respuesta = api.post("/turnos", json=_body(catalogo, _jueves(10)))

    assert respuesta.status_code == 422
    assert respuesta.json() == FUERA_DE_HORARIO
    assert _turnos(db_session) == 0


def test_la_franja_de_otro_profesional_no_habilita_el_turno(
    api: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    _manana(db_session, catalogo.profesionales[1])

    respuesta = api.post("/turnos", json=_body(catalogo, _jueves(10)))

    assert respuesta.status_code == 422
    assert respuesta.json()["detail"]["codigo"] == "fuera_de_horario"


def test_el_dia_de_la_semana_es_el_local_y_no_el_utc(
    api: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    _franja(db_session, catalogo.profesionales[0], JUEVES, time(21, 0), time(23, 0))

    respuesta = api.post("/turnos", json=_body(catalogo, "2026-10-09T01:00:00Z"))

    assert respuesta.status_code == 201
    assert respuesta.json()["inicio"] == "2026-10-08T22:00:00-03:00"


def test_fuera_de_horario_y_en_conflicto_responde_422_y_no_409(
    api: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    _manana(db_session, catalogo.profesionales[0])
    previo = api.post(
        "/turnos",
        json=_body(
            catalogo, _jueves(12, 15), duracion_min=45, paciente_id=str(catalogo.pacientes[1].id)
        ),
    )
    assert previo.status_code == 201

    respuesta = api.post("/turnos", json=_body(catalogo, _jueves(12, 30)))

    assert respuesta.status_code == 422
    assert respuesta.json()["detail"]["codigo"] == "fuera_de_horario"


def test_las_validaciones_previas_se_evaluan_antes_que_el_horario(
    api: TestClient, catalogo: Catalogo
) -> None:
    respuesta = api.post(
        "/turnos", json=_body(catalogo, "2026-10-10T10:00:00-03:00", duracion_min=42)
    )

    assert respuesta.status_code == 422
    assert respuesta.json()["detail"]["codigo"] == "duracion_invalida"
