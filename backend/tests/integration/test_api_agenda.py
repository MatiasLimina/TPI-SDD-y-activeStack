"""GET /turnos (agenda por rango de días locales) de punta a punta con PostgreSQL real."""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.turnos import get_reloj
from app.infrastructure.db.models import Bloqueo, Turno, Usuario
from tests.integration.factories import Catalogo, crear_catalogo

LOCAL = ZoneInfo("America/Argentina/Buenos_Aires")
CLAVES_TURNO = {
    "id",
    "profesional_id",
    "paciente",
    "prestacion_id",
    "sillon_id",
    "inicio",
    "fin",
    "duracion_min",
    "estado",
    "creado_por",
    "motivo_cancelacion",
}
CLAVES_BLOQUEO = {"id", "profesional_id", "inicio", "fin", "motivo", "creado_por"}


@pytest.fixture
def catalogo(db_session: Session) -> Catalogo:
    return crear_catalogo(db_session)


def _l(dia: int, hora: int, minuto: int = 0, mes: int = 10) -> datetime:
    """Instante en hora local de Buenos Aires de 2026."""
    return datetime(2026, mes, dia, hora, minuto, tzinfo=LOCAL)


def _turno(
    db_session: Session,
    c: Catalogo,
    inicio: datetime,
    *,
    minutos: int = 45,
    prof: int = 0,
    sillon: int | None = 0,
    paciente: int = 0,
    estado: str = "programado",
    motivo: str | None = None,
) -> Turno:
    turno = Turno(
        profesional_id=c.profesionales[prof].id,
        sillon_id=None if sillon is None else c.sillones[sillon].id,
        paciente_id=c.pacientes[paciente].id,
        prestacion_id=c.limpieza.id,
        inicio=inicio,
        fin=inicio + timedelta(minutes=minutos),
        duracion_min=minutos,
        estado=estado,
        motivo_cancelacion=motivo,
    )
    db_session.add(turno)
    db_session.flush()
    return turno


def _bloqueo(
    db_session: Session,
    autor: Usuario,
    profesional_id: UUID,
    inicio: datetime,
    fin: datetime,
    motivo: str = "Congreso",
) -> Bloqueo:
    bloqueo = Bloqueo(
        profesional_id=profesional_id, inicio=inicio, fin=fin, motivo=motivo, creado_por=autor.id
    )
    db_session.add(bloqueo)
    db_session.flush()
    return bloqueo


def _agenda(client: TestClient, desde: str, hasta: str | None = None, **filtros: UUID | str) -> Any:
    params = {"desde": desde, "hasta": hasta or desde, **{k: str(v) for k, v in filtros.items()}}
    return client.get("/turnos", params=params)


def _ids(items: list[dict[str, Any]]) -> list[str]:
    return [i["id"] for i in items]


# --- 5.1 consulta por rango -------------------------------------------------------------------


def test_agenda_diaria_de_la_recepcionista_trae_solo_el_turno_y_el_bloqueo_del_dia(
    client: TestClient,
    db_session: Session,
    catalogo: Catalogo,
    recepcionista: Usuario,
) -> None:
    a, b = catalogo.profesionales
    turno = _turno(db_session, catalogo, _l(8, 10))
    _turno(db_session, catalogo, _l(9, 10))  # otro dia
    bloqueo = _bloqueo(db_session, recepcionista, b.id, _l(8, 15), _l(8, 16))
    _bloqueo(db_session, recepcionista, a.id, _l(10, 15), _l(10, 16))  # otro dia

    respuesta = _agenda(client, "2026-10-08")

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert set(cuerpo) == {"turnos", "bloqueos"}
    assert _ids(cuerpo["turnos"]) == [str(turno.id)]
    assert _ids(cuerpo["bloqueos"]) == [str(bloqueo.id)]


def test_dia_sin_turnos_ni_bloqueos_devuelve_dos_listas_vacias(
    client: TestClient, catalogo: Catalogo
) -> None:
    respuesta = _agenda(client, "2026-10-09")

    assert respuesta.status_code == 200
    assert respuesta.json() == {"turnos": [], "bloqueos": []}


@pytest.mark.parametrize(
    "params",
    [
        {"desde": "2026-10-08"},
        {"hasta": "2026-10-08"},
        {},
        {"desde": "08/10/2026", "hasta": "2026-10-08"},
        {"desde": "2026-10-08", "hasta": "2026-02-30"},
    ],
)
def test_fecha_faltante_mal_formada_o_inexistente_da_422(
    client: TestClient, params: dict[str, str]
) -> None:
    assert client.get("/turnos", params=params).status_code == 422


def test_las_rutas_de_escritura_siguen_exigiendo_recepcionista(
    client: TestClient, cliente_anonimo: TestClient
) -> None:
    assert cliente_anonimo.post("/turnos", json={}).status_code == 401
    assert cliente_anonimo.get("/turnos").status_code == 401


# --- 5.2 rango de hasta una semana ------------------------------------------------------------


def test_agenda_semanal_incluye_lunes_y_domingo_y_deja_afuera_el_lunes_siguiente(
    client: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    lunes = _turno(db_session, catalogo, _l(5, 9))
    domingo = _turno(db_session, catalogo, _l(11, 18))
    _turno(db_session, catalogo, _l(12, 9))

    respuesta = _agenda(client, "2026-10-05", "2026-10-11")

    assert respuesta.status_code == 200
    assert _ids(respuesta.json()["turnos"]) == [str(lunes.id), str(domingo.id)]


@pytest.mark.parametrize(
    ("desde", "hasta"),
    [
        ("2026-10-09", "2026-10-08"),
        ("2026-10-05", "2026-10-12"),
        ("9999-12-25", "9999-12-31"),  # el fin del intervalo [) no se puede representar
    ],
)
def test_rango_invalido_da_422_rango_invalido(client: TestClient, desde: str, hasta: str) -> None:
    respuesta = _agenda(client, desde, hasta)

    assert respuesta.status_code == 422
    detalle = respuesta.json()["detail"]
    assert detalle["codigo"] == "rango_invalido"
    assert detalle["mensaje"]


# --- 5.3 zona horaria y superposición ---------------------------------------------------------


def test_turno_de_la_noche_local_pertenece_al_dia_local_aunque_en_utc_sea_del_siguiente(
    client: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    turno = _turno(db_session, catalogo, _l(8, 22, 30), minutos=30)
    assert turno.inicio.astimezone(UTC) == datetime(2026, 10, 9, 1, 30, tzinfo=UTC)

    dia_8 = _agenda(client, "2026-10-08").json()["turnos"]
    dia_9 = _agenda(client, "2026-10-09").json()["turnos"]

    assert _ids(dia_8) == [str(turno.id)]
    assert dia_9 == []


def test_turno_de_la_madrugada_local_no_es_del_dia_anterior(
    client: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    turno = _turno(db_session, catalogo, _l(9, 0), minutos=30)
    assert turno.inicio.astimezone(UTC) == datetime(2026, 10, 9, 3, 0, tzinfo=UTC)

    assert _agenda(client, "2026-10-08").json()["turnos"] == []
    assert _ids(_agenda(client, "2026-10-09").json()["turnos"]) == [str(turno.id)]


def test_bloqueo_con_fecha_utc_del_dia_pedido_pero_de_la_noche_local_anterior_no_entra(
    client: TestClient, db_session: Session, catalogo: Catalogo, recepcionista: Usuario
) -> None:
    _bloqueo(
        db_session,
        recepcionista,
        catalogo.profesionales[0].id,
        datetime(2026, 10, 9, 2, 0, tzinfo=UTC),
        datetime(2026, 10, 9, 2, 59, tzinfo=UTC),
    )

    assert _agenda(client, "2026-10-09").json()["bloqueos"] == []
    assert len(_agenda(client, "2026-10-08").json()["bloqueos"]) == 1


def test_bloqueo_de_varios_dias_aparece_en_una_vista_diaria_con_su_intervalo_real(
    client: TestClient, db_session: Session, catalogo: Catalogo, recepcionista: Usuario
) -> None:
    bloqueo = _bloqueo(db_session, recepcionista, catalogo.profesionales[0].id, _l(5, 8), _l(9, 20))

    (visto,) = _agenda(client, "2026-10-07").json()["bloqueos"]

    assert visto["id"] == str(bloqueo.id)
    assert visto["inicio"] == "2026-10-05T08:00:00-03:00"
    assert visto["fin"] == "2026-10-09T20:00:00-03:00"


def test_bloqueos_contiguos_a_los_bordes_del_dia_no_entran(
    client: TestClient, db_session: Session, catalogo: Catalogo, recepcionista: Usuario
) -> None:
    a = catalogo.profesionales[0].id
    _bloqueo(db_session, recepcionista, a, _l(7, 20), _l(8, 0))  # termina al empezar
    _bloqueo(db_session, recepcionista, a, _l(9, 0), _l(9, 8))  # empieza al terminar

    assert _agenda(client, "2026-10-08").json()["bloqueos"] == []


def test_bloqueo_que_cruza_la_medianoche_al_inicio_del_dia_entra(
    client: TestClient, db_session: Session, catalogo: Catalogo, recepcionista: Usuario
) -> None:
    bloqueo = _bloqueo(db_session, recepcionista, catalogo.profesionales[0].id, _l(7, 22), _l(8, 1))

    assert _ids(_agenda(client, "2026-10-08").json()["bloqueos"]) == [str(bloqueo.id)]


def test_turno_que_cruza_la_medianoche_local_aparece_completo_en_ambos_dias(
    client: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    turno = _turno(db_session, catalogo, _l(7, 23, 30), minutos=60)

    for dia in ("2026-10-07", "2026-10-08"):
        (visto,) = _agenda(client, dia).json()["turnos"]
        assert visto["id"] == str(turno.id)
        assert visto["inicio"] == "2026-10-07T23:30:00-03:00"
        assert visto["fin"] == "2026-10-08T00:30:00-03:00"


# --- 5.4 filtros ------------------------------------------------------------------------------


def _dos_profesionales(
    db_session: Session, c: Catalogo, autor: Usuario
) -> tuple[Turno, Turno, Bloqueo, Bloqueo]:
    a, b = c.profesionales
    turno_a = _turno(db_session, c, _l(8, 10))
    turno_b = _turno(db_session, c, _l(8, 10), prof=1, sillon=1, paciente=1)
    bloqueo_a = _bloqueo(db_session, autor, a.id, _l(8, 15), _l(8, 16))
    bloqueo_b = _bloqueo(db_session, autor, b.id, _l(8, 15), _l(8, 16))
    return turno_a, turno_b, bloqueo_a, bloqueo_b


def test_la_recepcionista_filtra_por_profesional_y_sin_filtro_ve_a_todos(
    client: TestClient, db_session: Session, catalogo: Catalogo, recepcionista: Usuario
) -> None:
    turno_a, turno_b, bloqueo_a, bloqueo_b = _dos_profesionales(db_session, catalogo, recepcionista)

    de_a = _agenda(client, "2026-10-08", profesional_id=catalogo.profesionales[0].id).json()
    todos = _agenda(client, "2026-10-08").json()

    assert _ids(de_a["turnos"]) == [str(turno_a.id)]
    assert _ids(de_a["bloqueos"]) == [str(bloqueo_a.id)]
    assert set(_ids(todos["turnos"])) == {str(turno_a.id), str(turno_b.id)}
    assert set(_ids(todos["bloqueos"])) == {str(bloqueo_a.id), str(bloqueo_b.id)}


def test_profesional_inexistente_da_200_con_listas_vacias_y_mal_formado_da_422(
    client: TestClient, db_session: Session, catalogo: Catalogo, recepcionista: Usuario
) -> None:
    _dos_profesionales(db_session, catalogo, recepcionista)

    inexistente = _agenda(client, "2026-10-08", profesional_id=uuid4())
    mal_formado = _agenda(client, "2026-10-08", profesional_id="no-es-un-id")

    assert inexistente.status_code == 200
    assert inexistente.json() == {"turnos": [], "bloqueos": []}
    assert mal_formado.status_code == 422


def test_un_profesional_desactivado_conserva_su_agenda(
    client: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    a = catalogo.profesionales[0]
    turno = _turno(db_session, catalogo, _l(8, 10))
    a.activo = False
    db_session.flush()

    respuesta = _agenda(client, "2026-10-08", profesional_id=a.id)

    assert respuesta.status_code == 200
    assert _ids(respuesta.json()["turnos"]) == [str(turno.id)]


def test_filtro_por_sillon_no_alcanza_a_los_bloqueos_y_excluye_turnos_sin_sillon(
    client: TestClient, db_session: Session, catalogo: Catalogo, recepcionista: Usuario
) -> None:
    a, _ = catalogo.profesionales
    s1, _ = catalogo.sillones
    a_s1 = _turno(db_session, catalogo, _l(8, 10))
    b_s1 = _turno(db_session, catalogo, _l(8, 11), prof=1, sillon=0, paciente=1)
    _turno(db_session, catalogo, _l(8, 12), sillon=1)
    _turno(db_session, catalogo, _l(8, 13), sillon=None)
    bloqueo = _bloqueo(db_session, recepcionista, a.id, _l(8, 15), _l(8, 16))

    cuerpo = _agenda(client, "2026-10-08", sillon_id=s1.id).json()

    assert _ids(cuerpo["turnos"]) == [str(a_s1.id), str(b_s1.id)]
    assert _ids(cuerpo["bloqueos"]) == [str(bloqueo.id)]


def test_filtros_combinados_se_aplican_a_la_vez(
    client: TestClient, db_session: Session, catalogo: Catalogo, recepcionista: Usuario
) -> None:
    a, b = catalogo.profesionales
    a_s1 = _turno(db_session, catalogo, _l(8, 10))
    _turno(db_session, catalogo, _l(8, 11), prof=1, sillon=0, paciente=1)
    _turno(db_session, catalogo, _l(8, 12), sillon=1)
    bloqueo_a = _bloqueo(db_session, recepcionista, a.id, _l(8, 15), _l(8, 16))
    _bloqueo(db_session, recepcionista, b.id, _l(8, 15), _l(8, 16))

    cuerpo = _agenda(
        client, "2026-10-08", profesional_id=a.id, sillon_id=catalogo.sillones[0].id
    ).json()

    assert _ids(cuerpo["turnos"]) == [str(a_s1.id)]
    assert _ids(cuerpo["bloqueos"]) == [str(bloqueo_a.id)]


def test_sillon_inexistente_da_turnos_vacia_y_mal_formado_da_422(
    client: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    _turno(db_session, catalogo, _l(8, 10))

    inexistente = _agenda(client, "2026-10-08", sillon_id=uuid4())
    mal_formado = _agenda(client, "2026-10-08", sillon_id="no-es-un-id")

    assert inexistente.status_code == 200
    assert inexistente.json()["turnos"] == []
    assert mal_formado.status_code == 422


# --- 5.5 estados, fecha y forma de cada elemento ----------------------------------------------


def test_cancelado_y_programado_en_el_mismo_horario_aparecen_los_dos_con_su_estado(
    client: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    _turno(db_session, catalogo, _l(8, 10), estado="cancelado", motivo="Viaje")
    _turno(db_session, catalogo, _l(8, 10))

    turnos = _agenda(client, "2026-10-08").json()["turnos"]

    assert sorted((t["estado"], t["motivo_cancelacion"]) for t in turnos) == [
        ("cancelado", "Viaje"),
        ("programado", None),
    ]


def test_agenda_de_un_dia_pasado_respecto_del_reloj(
    client: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    client.app.dependency_overrides[get_reloj] = lambda: lambda: _l(8, 9)  # type: ignore[attr-defined]
    turno = _turno(db_session, catalogo, _l(6, 10))

    respuesta = _agenda(client, "2026-10-06")

    assert respuesta.status_code == 200
    assert _ids(respuesta.json()["turnos"]) == [str(turno.id)]


def test_campos_y_hora_local_del_turno_y_del_bloqueo(
    client: TestClient, db_session: Session, catalogo: Catalogo, recepcionista: Usuario
) -> None:
    turno = _turno(db_session, catalogo, _l(8, 10))
    turno.creado_por = recepcionista.id
    bloqueo = _bloqueo(
        db_session, recepcionista, catalogo.profesionales[0].id, _l(8, 15), _l(8, 16)
    )
    db_session.flush()
    paciente = catalogo.pacientes[0]

    cuerpo = _agenda(client, "2026-10-08").json()

    (visto,) = cuerpo["turnos"]
    assert set(visto) == CLAVES_TURNO
    assert visto["inicio"] == "2026-10-08T10:00:00-03:00"
    assert visto["fin"] == "2026-10-08T10:45:00-03:00"
    assert visto["duracion_min"] == 45
    assert visto["motivo_cancelacion"] is None
    assert visto["creado_por"] == str(recepcionista.id)
    assert visto["profesional_id"] == str(turno.profesional_id)
    assert visto["prestacion_id"] == str(catalogo.limpieza.id)
    assert visto["sillon_id"] == str(catalogo.sillones[0].id)
    assert visto["paciente"] == {
        "id": str(paciente.id),
        "nombre": paciente.nombre,
        "apellido": paciente.apellido,
    }
    (visto_b,) = cuerpo["bloqueos"]
    assert set(visto_b) == CLAVES_BLOQUEO
    assert visto_b["id"] == str(bloqueo.id)
    assert visto_b["inicio"] == "2026-10-08T15:00:00-03:00"
    assert visto_b["fin"] == "2026-10-08T16:00:00-03:00"
    assert visto_b["motivo"] == "Congreso"
    assert visto_b["creado_por"] == str(recepcionista.id)


def test_la_respuesta_no_trae_documento_telefono_ni_email_del_paciente(
    client: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    paciente = catalogo.pacientes[0]
    paciente.email = "carla.imaginaria@example.com"
    _turno(db_session, catalogo, _l(8, 10))

    respuesta = _agenda(client, "2026-10-08")

    assert set(respuesta.json()["turnos"][0]["paciente"]) == {"id", "nombre", "apellido"}
    for dato in (paciente.documento, paciente.telefono, paciente.email):
        assert dato is not None
        assert dato not in respuesta.text


def test_turno_sin_sillon_y_paciente_desactivado_se_muestran(
    client: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    paciente = catalogo.pacientes[0]
    _turno(db_session, catalogo, _l(8, 10), sillon=None)
    paciente.activo = False
    db_session.flush()

    (visto,) = _agenda(client, "2026-10-08").json()["turnos"]

    assert visto["sillon_id"] is None
    assert visto["paciente"] == {
        "id": str(paciente.id),
        "nombre": paciente.nombre,
        "apellido": paciente.apellido,
    }


def test_bloqueos_superpuestos_del_mismo_profesional_no_se_fusionan(
    client: TestClient, db_session: Session, catalogo: Catalogo, recepcionista: Usuario
) -> None:
    a = catalogo.profesionales[0].id
    uno = _bloqueo(db_session, recepcionista, a, _l(8, 10), _l(8, 12))
    dos = _bloqueo(db_session, recepcionista, a, _l(8, 11), _l(8, 13))

    bloqueos = _agenda(client, "2026-10-08").json()["bloqueos"]

    assert _ids(bloqueos) == [str(uno.id), str(dos.id)]


# --- 5.6 orden --------------------------------------------------------------------------------


def test_turnos_ordenados_por_inicio_entre_profesionales(
    client: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    a_11 = _turno(db_session, catalogo, _l(8, 11))
    b_09 = _turno(db_session, catalogo, _l(8, 9), prof=1, sillon=1, paciente=1)
    a_10 = _turno(db_session, catalogo, _l(8, 10))

    turnos = _agenda(client, "2026-10-08").json()["turnos"]

    assert _ids(turnos) == [str(b_09.id), str(a_10.id), str(a_11.id)]


def test_mismo_inicio_se_ordena_por_id_ascendente(
    client: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    a = _turno(db_session, catalogo, _l(8, 10))
    b = _turno(db_session, catalogo, _l(8, 10), prof=1, sillon=1, paciente=1)

    turnos = _agenda(client, "2026-10-08").json()["turnos"]

    assert _ids(turnos) == sorted([str(a.id), str(b.id)])


# --- 5.7 OpenAPI ------------------------------------------------------------------------------


def test_openapi_expone_get_y_post_en_turnos_y_documenta_los_parametros(
    client: TestClient,
) -> None:
    openapi = client.get("/openapi.json").json()

    operaciones = openapi["paths"]["/turnos"]
    assert set(operaciones) == {"get", "post"}
    parametros = {p["name"]: p for p in operaciones["get"]["parameters"]}
    assert set(parametros) == {"desde", "hasta", "profesional_id", "sillon_id"}
    assert all(p.get("description") for p in parametros.values())
    assert parametros["desde"]["required"] and parametros["hasta"]["required"]
    assert "YYYY-MM-DD" in parametros["desde"]["description"]
    assert "YYYY-MM-DD" in parametros["hasta"]["description"]
    assert "odontólogo" in parametros["profesional_id"]["description"]
