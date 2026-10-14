"""PATCH /turnos/{id}/reprogramar contra PostgreSQL real, con reloj fijo inyectado."""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.turnos import get_reloj
from app.infrastructure.db.models import Turno
from tests.integration.factories import Catalogo, crear_catalogo

AHORA = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)  # 2026-10-07 09:00 hora local
INICIO_LOCAL = "2026-10-08T10:00:00-03:00"
INICIO = datetime(2026, 10, 8, 13, 0, tzinfo=UTC)
LIMPIEZA = timedelta(minutes=45)


@pytest.fixture
def catalogo(db_session: Session) -> Catalogo:
    return crear_catalogo(db_session)


@pytest.fixture
def api(client: TestClient) -> TestClient:
    _fijar_reloj(client, AHORA)
    return client


def _fijar_reloj(client: TestClient, ahora: datetime) -> None:
    client.app.dependency_overrides[get_reloj] = lambda: lambda: ahora  # type: ignore[attr-defined]


def _local(inicio: datetime) -> str:
    """Instante UTC como texto con offset -03:00 (hora de Buenos Aires)."""
    return (inicio - timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M:%S-03:00")


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


def _crear(api: TestClient, c: Catalogo, **cambios: Any) -> str:
    respuesta = api.post("/turnos", json=_body(c, **cambios))
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()["id"]


def _patch(api: TestClient, turno_id: str, **cambios: Any) -> Any:
    return api.patch(f"/turnos/{turno_id}/reprogramar", json=cambios)


def _fila(session: Session, turno_id: str) -> tuple[datetime, datetime, int, str]:
    session.expire_all()
    return (
        session.execute(
            select(Turno.inicio, Turno.fin, Turno.duracion_min, Turno.estado).where(
                Turno.id == turno_id
            )
        )
        .one()
        ._tuple()
    )


def _intacto(session: Session, turno_id: str, duracion: int = 45) -> None:
    assert _fila(session, turno_id) == (
        INICIO,
        INICIO + timedelta(minutes=duracion),
        duracion,
        "programado",
    )


def _cantidad(session: Session) -> int:
    return session.scalar(select(func.count()).select_from(Turno)) or 0


# --- 7.1 reprogramación válida -------------------------------------------------------------


def test_reprogramar_a_un_hueco_libre_responde_200_con_el_mismo_id(
    api: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    turno_id = _crear(api, catalogo)
    nuevo = INICIO + timedelta(hours=5)

    respuesta = _patch(api, turno_id, inicio=_local(nuevo))

    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["id"] == turno_id
    assert cuerpo["estado"] == "programado"
    assert cuerpo["inicio"] == "2026-10-08T15:00:00-03:00"
    assert cuerpo["fin"] == "2026-10-08T15:45:00-03:00"
    assert cuerpo["motivo_cancelacion"] is None
    assert _fila(db_session, turno_id) == (nuevo, nuevo + LIMPIEZA, 45, "programado")
    assert _cantidad(db_session) == 1


def test_reprogramar_cambiando_profesional_y_sillon(
    api: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    turno_id = _crear(api, catalogo)

    respuesta = _patch(
        api,
        turno_id,
        profesional_id=str(catalogo.profesionales[1].id),
        sillon_id=str(catalogo.sillones[1].id),
    )

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["profesional_id"] == str(catalogo.profesionales[1].id)
    assert respuesta.json()["sillon_id"] == str(catalogo.sillones[1].id)
    _intacto(db_session, turno_id)  # el horario no cambió


# --- 7.2 parcialidad en el borde -----------------------------------------------------------


def test_solo_inicio_conserva_la_duracion_ajustada(api: TestClient, catalogo: Catalogo) -> None:
    turno_id = _crear(api, catalogo, duracion_min=60)

    respuesta = _patch(api, turno_id, inicio="2026-10-08T15:00:00-03:00")

    assert respuesta.status_code == 200
    assert respuesta.json()["duracion_min"] == 60
    assert respuesta.json()["fin"] == "2026-10-08T16:00:00-03:00"


def test_solo_duracion_conserva_el_inicio(api: TestClient, catalogo: Catalogo) -> None:
    turno_id = _crear(api, catalogo)

    respuesta = _patch(api, turno_id, duracion_min=90)

    assert respuesta.status_code == 200
    assert respuesta.json()["inicio"] == INICIO_LOCAL
    assert respuesta.json()["fin"] == "2026-10-08T11:30:00-03:00"


def test_volver_a_la_duracion_de_la_prestacion_informandola(
    api: TestClient, catalogo: Catalogo
) -> None:
    turno_id = _crear(api, catalogo, duracion_min=90)

    respuesta = _patch(api, turno_id, duracion_min=45)

    assert respuesta.status_code == 200
    assert respuesta.json()["duracion_min"] == 45


def test_body_vacio_responde_200_sin_cambios(
    api: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    turno_id = _crear(api, catalogo, duracion_min=60)

    respuesta = _patch(api, turno_id)

    assert respuesta.status_code == 200
    assert respuesta.json()["inicio"] == INICIO_LOCAL
    assert respuesta.json()["duracion_min"] == 60
    assert _cantidad(db_session) == 1


@pytest.mark.parametrize("campo", ["inicio", "profesional_id", "duracion_min"])
def test_nulo_explicito_en_campo_obligatorio_responde_422_y_deja_el_turno(
    api: TestClient, db_session: Session, catalogo: Catalogo, campo: str
) -> None:
    turno_id = _crear(api, catalogo)

    respuesta = _patch(api, turno_id, **{campo: None})

    assert respuesta.status_code == 422
    assert isinstance(respuesta.json()["detail"], list)  # formato nativo de Pydantic
    _intacto(db_session, turno_id)


def test_sillon_nulo_en_prestacion_que_requiere_sillon_responde_422_sillon_requerido(
    api: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    turno_id = _crear(api, catalogo)

    respuesta = _patch(api, turno_id, sillon_id=None)

    assert respuesta.status_code == 422
    assert respuesta.json()["detail"]["codigo"] == "sillon_requerido"
    _intacto(db_session, turno_id)


def test_sillon_en_prestacion_sin_sillon_responde_422_sillon_no_corresponde(
    api: TestClient, catalogo: Catalogo
) -> None:
    turno_id = _crear(api, catalogo, prestacion_id=str(catalogo.consulta.id), sillon_id=None)

    respuesta = _patch(api, turno_id, sillon_id=str(catalogo.sillones[0].id))

    assert respuesta.status_code == 422
    assert respuesta.json()["detail"]["codigo"] == "sillon_no_corresponde"


# --- 7.3 campos no editables ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("campos", "esperados"),
    [
        (["paciente_id"], ["paciente_id"]),
        (["prestacion_id"], ["prestacion_id"]),
        (["prestacion_id", "paciente_id"], ["paciente_id", "prestacion_id"]),
    ],
)
def test_paciente_o_prestacion_responden_422_campo_no_editable(
    api: TestClient,
    db_session: Session,
    catalogo: Catalogo,
    campos: list[str],
    esperados: list[str],
) -> None:
    turno_id = _crear(api, catalogo)
    cuerpo = {
        "paciente_id": str(uuid4()),
        "prestacion_id": str(catalogo.consulta.id),
    }

    respuesta = _patch(api, turno_id, **{c: cuerpo[c] for c in campos})

    assert respuesta.status_code == 422
    detalle = respuesta.json()["detail"]
    assert detalle["codigo"] == "campo_no_editable"
    assert detalle["campos"] == esperados
    assert detalle["mensaje"]
    _intacto(db_session, turno_id)


def test_el_mismo_paciente_actual_tambien_se_rechaza(api: TestClient, catalogo: Catalogo) -> None:
    turno_id = _crear(api, catalogo)

    respuesta = _patch(api, turno_id, paciente_id=str(catalogo.pacientes[0].id))

    assert respuesta.status_code == 422
    assert respuesta.json()["detail"]["campos"] == ["paciente_id"]


def test_prestacion_sobre_un_turno_cancelado_responde_422_no_409(
    api: TestClient, catalogo: Catalogo
) -> None:
    turno_id = _crear(api, catalogo)
    assert api.post(f"/turnos/{turno_id}/cancelar").status_code == 200

    respuesta = _patch(api, turno_id, prestacion_id=str(catalogo.consulta.id))

    assert respuesta.status_code == 422
    assert respuesta.json()["detail"]["codigo"] == "campo_no_editable"


def test_un_campo_desconocido_se_ignora(api: TestClient, catalogo: Catalogo) -> None:
    turno_id = _crear(api, catalogo)

    respuesta = _patch(api, turno_id, observaciones="trae radiografías")

    assert respuesta.status_code == 200


# --- 7.4 misma validación que el alta ------------------------------------------------------


@pytest.mark.parametrize(
    ("cambios", "codigo"),
    [
        ({"duracion_min": 42}, "duracion_invalida"),
        ({"inicio": "2026-10-08T15:07:00-03:00"}, "inicio_no_alineado"),
        ({"inicio": "2026-10-07T08:00:00-03:00"}, "inicio_en_pasado"),
    ],
    ids=["duracion-42", "inicio-15-07", "inicio-pasado"],
)
def test_validacion_de_dominio_responde_422_y_deja_el_original(
    api: TestClient,
    db_session: Session,
    catalogo: Catalogo,
    cambios: dict[str, Any],
    codigo: str,
) -> None:
    turno_id = _crear(api, catalogo)

    respuesta = _patch(api, turno_id, **cambios)

    assert respuesta.status_code == 422
    assert respuesta.json()["detail"]["codigo"] == codigo
    _intacto(db_session, turno_id)


def test_inicio_sin_zona_responde_422(
    api: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    turno_id = _crear(api, catalogo)

    respuesta = _patch(api, turno_id, inicio="2026-10-08T15:00:00")

    assert respuesta.status_code == 422
    _intacto(db_session, turno_id)


def test_profesional_inactivo_responde_422_referencia_profesional(
    api: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    turno_id = _crear(api, catalogo)
    catalogo.profesionales[1].activo = False
    db_session.flush()

    respuesta = _patch(api, turno_id, profesional_id=str(catalogo.profesionales[1].id))

    assert respuesta.status_code == 422
    detalle = respuesta.json()["detail"]
    assert (detalle["codigo"], detalle["referencia"]) == ("referencia_invalida", "profesional")
    _intacto(db_session, turno_id)


def test_sillon_inexistente_responde_422_referencia_sillon_no_404(
    api: TestClient, catalogo: Catalogo
) -> None:
    turno_id = _crear(api, catalogo)

    respuesta = _patch(api, turno_id, sillon_id=str(uuid4()))

    assert respuesta.status_code == 422
    assert respuesta.json()["detail"]["referencia"] == "sillon"


def test_invalido_y_en_conflicto_responde_422_no_409(api: TestClient, catalogo: Catalogo) -> None:
    turno_id = _crear(api, catalogo, inicio="2026-10-08T14:00:00-03:00")
    _crear(api, catalogo)  # ocupa 10:00

    respuesta = _patch(api, turno_id, inicio=INICIO_LOCAL, duracion_min=42)

    assert respuesta.status_code == 422


# --- 7.5 solape ----------------------------------------------------------------------------


def test_hueco_ocupado_responde_409_solapamiento_profesional_y_deja_el_original(
    api: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    turno_id = _crear(
        api, catalogo, inicio="2026-10-08T14:00:00-03:00", sillon_id=str(catalogo.sillones[1].id)
    )
    _crear(api, catalogo, paciente_id=str(catalogo.pacientes[1].id))

    respuesta = _patch(api, turno_id, inicio=INICIO_LOCAL)

    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == {"codigo": "solapamiento", "recursos": ["profesional"]}
    assert _fila(db_session, turno_id)[0] == INICIO + timedelta(hours=4)


def test_los_tres_recursos_en_conflicto_se_listan_en_orden(
    api: TestClient, catalogo: Catalogo
) -> None:
    turno_id = _crear(api, catalogo, inicio="2026-10-08T14:00:00-03:00")
    _crear(api, catalogo)

    respuesta = _patch(api, turno_id, inicio=INICIO_LOCAL)

    assert respuesta.status_code == 409
    assert respuesta.json()["detail"]["recursos"] == ["profesional", "sillon", "paciente"]


def test_solaparse_consigo_mismo_es_valido(api: TestClient, catalogo: Catalogo) -> None:
    turno_id = _crear(api, catalogo)

    respuesta = _patch(api, turno_id, inicio="2026-10-08T10:15:00-03:00")

    assert respuesta.status_code == 200
    assert respuesta.json()["fin"] == "2026-10-08T11:00:00-03:00"


def test_extender_la_duracion_sobre_el_propio_intervalo_es_valido(
    api: TestClient, catalogo: Catalogo
) -> None:
    turno_id = _crear(api, catalogo)

    assert _patch(api, turno_id, duracion_min=90).status_code == 200


def test_mismo_paciente_con_otro_turno_responde_409_paciente(
    api: TestClient, catalogo: Catalogo
) -> None:
    turno_id = _crear(api, catalogo, inicio="2026-10-08T14:00:00-03:00")
    _crear(
        api,
        catalogo,
        profesional_id=str(catalogo.profesionales[1].id),
        sillon_id=str(catalogo.sillones[1].id),
    )

    respuesta = _patch(api, turno_id, inicio=INICIO_LOCAL)

    assert respuesta.status_code == 409
    assert respuesta.json()["detail"]["recursos"] == ["paciente"]


def test_horario_contiguo_a_otro_turno_es_valido(api: TestClient, catalogo: Catalogo) -> None:
    turno_id = _crear(api, catalogo, inicio="2026-10-08T14:00:00-03:00")
    _crear(api, catalogo)

    assert _patch(api, turno_id, inicio="2026-10-08T10:45:00-03:00").status_code == 200


def test_destino_con_turno_cancelado_es_valido(api: TestClient, catalogo: Catalogo) -> None:
    turno_id = _crear(api, catalogo, inicio="2026-10-08T14:00:00-03:00")
    ocupante = _crear(api, catalogo)
    assert api.post(f"/turnos/{ocupante}/cancelar").status_code == 200

    assert _patch(api, turno_id, inicio=INICIO_LOCAL).status_code == 200


# --- 7.6 no modificable e inexistente ------------------------------------------------------


def test_un_minuto_antes_del_inicio_responde_200(api: TestClient, catalogo: Catalogo) -> None:
    turno_id = _crear(api, catalogo)
    _fijar_reloj(api, INICIO - timedelta(minutes=1))

    assert _patch(api, turno_id, inicio="2026-10-08T15:00:00-03:00").status_code == 200


@pytest.mark.parametrize(
    "ahora",
    [INICIO, INICIO + timedelta(minutes=20), INICIO + timedelta(days=1)],
    ids=["limite-exacto", "en-curso", "dia-posterior"],
)
def test_turno_iniciado_o_pasado_responde_409_ya_iniciado_y_no_cambia(
    api: TestClient, db_session: Session, catalogo: Catalogo, ahora: datetime
) -> None:
    turno_id = _crear(api, catalogo)
    _fijar_reloj(api, ahora)

    respuesta = _patch(api, turno_id, inicio=_local(ahora + timedelta(days=2)))

    assert respuesta.status_code == 409
    assert respuesta.json()["detail"]["codigo"] == "turno_ya_iniciado"
    _intacto(db_session, turno_id)


@pytest.mark.parametrize(
    ("ahora", "cambios"),
    [
        (AHORA, {"inicio": "2026-10-08T15:00:00-03:00"}),
        (INICIO + timedelta(days=1), {"inicio": "2026-10-10T15:00:00-03:00"}),
        (AHORA, {"duracion_min": 42}),
    ],
    ids=["futuro", "cancelado-y-pasado", "duracion-invalida"],
)
def test_turno_cancelado_responde_409_ya_cancelado_y_sigue_cancelado(
    api: TestClient,
    db_session: Session,
    catalogo: Catalogo,
    ahora: datetime,
    cambios: dict[str, Any],
) -> None:
    turno_id = _crear(api, catalogo)
    assert api.post(f"/turnos/{turno_id}/cancelar").status_code == 200
    _fijar_reloj(api, ahora)

    respuesta = _patch(api, turno_id, **cambios)

    assert respuesta.status_code == 409
    assert respuesta.json()["detail"]["codigo"] == "turno_ya_cancelado"
    assert _fila(db_session, turno_id) == (INICIO, INICIO + LIMPIEZA, 45, "cancelado")


def test_turno_inexistente_responde_404(api: TestClient) -> None:
    respuesta = _patch(api, str(uuid4()), inicio=INICIO_LOCAL)

    assert respuesta.status_code == 404
    assert respuesta.json()["detail"]["codigo"] == "turno_inexistente"


def test_id_con_formato_invalido_responde_422(api: TestClient) -> None:
    assert _patch(api, "no-es-un-uuid", inicio=INICIO_LOCAL).status_code == 422
