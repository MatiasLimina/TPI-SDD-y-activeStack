"""RN-AG-06 en POST /turnos: turno fuera de los bloqueos de agenda, con reloj fijo inyectado."""

from datetime import UTC, datetime, time
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.api.turnos import get_reloj
from app.infrastructure.db.models import Bloqueo, HorarioAtencion, Profesional, Turno, Usuario
from tests.fakes import ColaEnMemoria
from tests.integration.factories import Catalogo, crear_catalogo

AHORA = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)  # 2026-10-07 09:00 hora local
JUEVES = 3
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


def _bloquear(
    db_session: Session,
    profesional: Profesional,
    autor: Usuario,
    inicio: str,
    fin: str,
) -> Bloqueo:
    bloqueo = Bloqueo(
        profesional_id=profesional.id,
        inicio=datetime.fromisoformat(inicio),
        fin=datetime.fromisoformat(fin),
        motivo="Congreso",
        creado_por=autor.id,
    )
    db_session.add(bloqueo)
    db_session.flush()
    return bloqueo


def _local(dia: int, hora: int, minuto: int = 0) -> str:
    return f"2026-10-{dia:02d}T{hora:02d}:{minuto:02d}:00-03:00"


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


def _turnos(session: Session) -> int:
    session.expire_all()
    return session.scalar(select(func.count()).select_from(Turno)) or 0


def _contar(session: Session, tabla: str) -> int:
    return int(session.execute(text(f"SELECT count(*) FROM {tabla}")).scalar_one())


@pytest.fixture
def bloqueo_de_10_a_12(db_session: Session, catalogo: Catalogo, recepcionista: Usuario) -> Bloqueo:
    """Bloqueo del profesional A el jueves 2026-10-08 de 10:00 a 12:00 hora local."""
    return _bloquear(
        db_session, catalogo.profesionales[0], recepcionista, _local(8, 10), _local(8, 12)
    )


@pytest.mark.parametrize(
    "inicio",
    [
        _local(8, 10, 30),  # adentro
        _local(8, 9, 30),  # empieza antes y termina adentro (09:30-10:15)
        _local(8, 11, 30),  # empieza adentro y termina después (11:30-12:15)
    ],
    ids=["adentro", "empieza-antes", "termina-despues"],
)
def test_turno_que_se_superpone_con_un_bloqueo_responde_422_exacto_y_no_persiste(
    api: TestClient,
    db_session: Session,
    catalogo: Catalogo,
    bloqueo_de_10_a_12: Bloqueo,
    inicio: str,
) -> None:
    respuesta = api.post("/turnos", json=_body(catalogo, inicio))

    assert respuesta.status_code == 422
    assert respuesta.json() == TURNO_EN_BLOQUEO
    assert _turnos(db_session) == 0


def test_turno_que_contiene_a_un_bloqueo_corto_responde_422(
    api: TestClient, db_session: Session, catalogo: Catalogo, recepcionista: Usuario
) -> None:
    _bloquear(
        db_session, catalogo.profesionales[0], recepcionista, _local(8, 10), _local(8, 10, 15)
    )

    respuesta = api.post("/turnos", json=_body(catalogo, _local(8, 9, 45), duracion_min=60))

    assert respuesta.status_code == 422
    assert respuesta.json() == TURNO_EN_BLOQUEO
    assert _turnos(db_session) == 0


def test_turno_que_empieza_justo_al_terminar_el_bloqueo_es_valido(
    api: TestClient, bloqueo_de_10_a_12: Bloqueo, catalogo: Catalogo
) -> None:
    respuesta = api.post("/turnos", json=_body(catalogo, _local(8, 12)))

    assert respuesta.status_code == 201
    assert respuesta.json()["inicio"] == "2026-10-08T12:00:00-03:00"


def test_turno_que_termina_justo_al_empezar_el_bloqueo_es_valido(
    api: TestClient, bloqueo_de_10_a_12: Bloqueo, catalogo: Catalogo
) -> None:
    respuesta = api.post("/turnos", json=_body(catalogo, _local(8, 9, 15)))

    assert respuesta.status_code == 201
    assert respuesta.json()["fin"] == "2026-10-08T10:00:00-03:00"


def test_bloqueo_de_otro_profesional_no_afecta_al_turno(
    api: TestClient, db_session: Session, catalogo: Catalogo, recepcionista: Usuario
) -> None:
    _bloquear(db_session, catalogo.profesionales[1], recepcionista, _local(8, 10), _local(8, 12))

    respuesta = api.post("/turnos", json=_body(catalogo, _local(8, 10, 30)))

    assert respuesta.status_code == 201


def test_bloqueo_de_varios_dias_rechaza_un_turno_del_dia_del_medio(
    api: TestClient, db_session: Session, catalogo: Catalogo, recepcionista: Usuario
) -> None:
    _bloquear(db_session, catalogo.profesionales[0], recepcionista, _local(8, 0), _local(10, 0))

    respuesta = api.post("/turnos", json=_body(catalogo, _local(9, 15)))

    assert respuesta.status_code == 422
    assert respuesta.json() == TURNO_EN_BLOQUEO
    assert _turnos(db_session) == 0


def test_fuera_de_horario_se_informa_antes_que_el_bloqueo(
    api: TestClient, db_session: Session, recepcionista: Usuario
) -> None:
    sin_horario = crear_catalogo(db_session, con_horario=False)
    a = sin_horario.profesionales[0]
    db_session.add(
        HorarioAtencion(
            profesional_id=a.id, dia_semana=JUEVES, hora_inicio=time(9, 0), hora_fin=time(13, 0)
        )
    )
    _bloquear(db_session, a, recepcionista, _local(8, 12), _local(8, 14))

    respuesta = api.post("/turnos", json=_body(sin_horario, _local(8, 12, 30)))

    assert respuesta.status_code == 422
    assert respuesta.json()["detail"]["codigo"] == "fuera_de_horario"
    assert _turnos(db_session) == 0


def test_dentro_de_un_bloqueo_y_en_conflicto_responde_422_y_no_409(
    api: TestClient, db_session: Session, catalogo: Catalogo, recepcionista: Usuario
) -> None:
    assert api.post("/turnos", json=_body(catalogo, _local(8, 9, 30))).status_code == 201  # -10:15
    _bloquear(
        db_session, catalogo.profesionales[0], recepcionista, _local(8, 10, 15), _local(8, 12)
    )

    respuesta = api.post("/turnos", json=_body(catalogo, _local(8, 10)))  # 10:00-10:45

    assert respuesta.status_code == 422
    assert respuesta.json() == TURNO_EN_BLOQUEO
    assert _turnos(db_session) == 1


def test_las_validaciones_previas_se_informan_antes_que_el_bloqueo(
    api: TestClient, db_session: Session, catalogo: Catalogo, bloqueo_de_10_a_12: Bloqueo
) -> None:
    respuesta = api.post("/turnos", json=_body(catalogo, _local(8, 10, 30), duracion_min=42))

    assert respuesta.status_code == 422
    assert respuesta.json()["detail"]["codigo"] == "duracion_invalida"
    assert _turnos(db_session) == 0


def test_turno_rechazado_por_un_bloqueo_no_deja_recordatorio_auditoria_ni_cola(
    api: TestClient,
    db_session: Session,
    catalogo: Catalogo,
    recepcionista: Usuario,
    cola: ColaEnMemoria,
) -> None:
    _bloquear(db_session, catalogo.profesionales[0], recepcionista, _local(9, 10), _local(9, 12))

    respuesta = api.post("/turnos", json=_body(catalogo, _local(9, 10, 30)))

    assert respuesta.status_code == 422
    assert respuesta.json() == TURNO_EN_BLOQUEO
    assert _turnos(db_session) == 0
    assert _contar(db_session, "recordatorio") == 0
    assert _contar(db_session, "turno_auditoria") == 0
    assert cola.elementos == {}


# --- Bloqueos superpuestos y borrado: el bloqueo vigente sigue rechazando --------------------


def test_borrar_un_bloqueo_superpuesto_deja_vigente_al_otro(
    api: TestClient, db_session: Session, catalogo: Catalogo, recepcionista: Usuario
) -> None:
    a = catalogo.profesionales[0]
    _bloquear(db_session, a, recepcionista, _local(8, 9), _local(8, 18))
    chico = _bloquear(db_session, a, recepcionista, _local(8, 10), _local(8, 11))

    borrado = api.delete(f"/bloqueos/{chico.id}")
    alta = api.post("/turnos", json=_body(catalogo, _local(8, 10)))

    assert borrado.status_code == 204
    assert alta.status_code == 422
    assert alta.json() == TURNO_EN_BLOQUEO


def test_el_intervalo_liberado_por_un_borrado_admite_turnos(
    api: TestClient, catalogo: Catalogo, bloqueo_de_10_a_12: Bloqueo
) -> None:
    assert api.delete(f"/bloqueos/{bloqueo_de_10_a_12.id}").status_code == 204

    respuesta = api.post("/turnos", json=_body(catalogo, _local(8, 10, 30)))

    assert respuesta.status_code == 201
