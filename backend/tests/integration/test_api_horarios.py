"""API de franjas de atención: app real, PostgreSQL real, recepcionista autenticada."""

from datetime import time
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.infrastructure.db.models import HorarioAtencion, Profesional

NO_EXISTE_PROFESIONAL = {"detail": {"codigo": "recurso_inexistente", "recurso": "profesional"}}
NO_EXISTE_HORARIO = {"detail": {"codigo": "recurso_inexistente", "recurso": "horario"}}


@pytest.fixture
def profesional_a(db_session: Session) -> Profesional:
    profesional = Profesional(nombre="Ana", apellido="Ficticia")
    db_session.add(profesional)
    db_session.flush()
    return profesional


@pytest.fixture
def profesional_b(db_session: Session) -> Profesional:
    profesional = Profesional(nombre="Beto", apellido="Ficticio")
    db_session.add(profesional)
    db_session.flush()
    return profesional


def _franja(
    db_session: Session, profesional: Profesional, dia: int, inicio: time, fin: time
) -> HorarioAtencion:
    franja = HorarioAtencion(
        profesional_id=profesional.id, dia_semana=dia, hora_inicio=inicio, hora_fin=fin
    )
    db_session.add(franja)
    db_session.flush()
    return franja


def _en_base(db_session: Session, profesional: Profesional) -> list[tuple[int, time, time]]:
    consulta = (
        select(HorarioAtencion.dia_semana, HorarioAtencion.hora_inicio, HorarioAtencion.hora_fin)
        .where(HorarioAtencion.profesional_id == profesional.id)
        .order_by(HorarioAtencion.dia_semana, HorarioAtencion.hora_inicio)
    )
    return [tuple(fila) for fila in db_session.execute(consulta)]  # type: ignore[misc]


def _cuerpo(dia: int = 0, inicio: str = "09:00", fin: str = "13:00") -> dict[str, Any]:
    return {"dia_semana": dia, "hora_inicio": inicio, "hora_fin": fin}


def _url(profesional_id: UUID, horario_id: UUID | None = None) -> str:
    base = f"/profesionales/{profesional_id}/horarios"
    return base if horario_id is None else f"{base}/{horario_id}"


# --- Alta ---------------------------------------------------------------------------------------


def test_alta_de_la_franja_de_la_manana_responde_201_y_persiste(
    client: TestClient, db_session: Session, profesional_a: Profesional
) -> None:
    respuesta = client.post(_url(profesional_a.id), json=_cuerpo())

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["profesional_id"] == str(profesional_a.id)
    assert (cuerpo["dia_semana"], cuerpo["hora_inicio"], cuerpo["hora_fin"]) == (
        0,
        "09:00:00",
        "13:00:00",
    )
    assert UUID(cuerpo["id"])
    assert _en_base(db_session, profesional_a) == [(0, time(9, 0), time(13, 0))]


def test_alta_acepta_horas_con_segundos(client: TestClient, profesional_a: Profesional) -> None:
    respuesta = client.post(_url(profesional_a.id), json=_cuerpo(2, "14:30:00", "18:00:00"))

    assert respuesta.status_code == 201
    assert respuesta.json()["hora_inicio"] == "14:30:00"


def test_alta_de_manana_y_tarde_el_mismo_dia(
    client: TestClient, db_session: Session, profesional_a: Profesional
) -> None:
    _franja(db_session, profesional_a, 0, time(9, 0), time(13, 0))

    respuesta = client.post(_url(profesional_a.id), json=_cuerpo(0, "14:00", "18:00"))

    assert respuesta.status_code == 201
    assert len(_en_base(db_session, profesional_a)) == 2


def test_alta_sobre_profesional_inexistente_responde_404_sin_filas(
    client: TestClient, db_session: Session
) -> None:
    antes = db_session.scalar(select(func.count()).select_from(HorarioAtencion))

    respuesta = client.post(_url(uuid4()), json=_cuerpo())

    assert respuesta.status_code == 404
    assert respuesta.json() == NO_EXISTE_PROFESIONAL
    assert db_session.scalar(select(func.count()).select_from(HorarioAtencion)) == antes


def test_alta_para_un_profesional_desactivado_responde_201(
    client: TestClient, db_session: Session, profesional_a: Profesional
) -> None:
    profesional_a.activo = False
    db_session.flush()

    respuesta = client.post(_url(profesional_a.id), json=_cuerpo(1))

    assert respuesta.status_code == 201
    assert _en_base(db_session, profesional_a) == [(1, time(9, 0), time(13, 0))]


# --- Validación de la franja -------------------------------------------------------------------


@pytest.mark.parametrize(
    "cuerpo",
    [
        _cuerpo(0, "09:00", "09:00"),
        _cuerpo(0, "22:00", "02:00"),
        _cuerpo(7),
        _cuerpo(-1),
        _cuerpo(0, "09:07", "13:00"),
        _cuerpo(0, "09:00", "13:00:30"),
        _cuerpo(0, "09:00-03:00", "13:00"),
    ],
    ids=["fin-igual", "fin-anterior", "dia-7", "dia-menos-1", "min-07", "seg-30", "con-zona"],
)
def test_alta_invalida_responde_422_franja_invalida_sin_persistir(
    client: TestClient, db_session: Session, profesional_a: Profesional, cuerpo: dict[str, Any]
) -> None:
    respuesta = client.post(_url(profesional_a.id), json=cuerpo)

    assert respuesta.status_code == 422
    assert respuesta.json()["detail"]["codigo"] == "franja_invalida"
    assert _en_base(db_session, profesional_a) == []


@pytest.mark.parametrize(
    "cuerpo",
    [
        {"dia_semana": 0, "hora_inicio": "09:00"},
        _cuerpo(0, "nueve", "13:00"),
        _cuerpo("lunes"),  # type: ignore[arg-type]
    ],
    ids=["sin-hora-fin", "hora-no-parseable", "dia-texto"],
)
def test_alta_con_campo_faltante_o_de_tipo_invalido_responde_422_de_fastapi(
    client: TestClient, db_session: Session, profesional_a: Profesional, cuerpo: dict[str, Any]
) -> None:
    respuesta = client.post(_url(profesional_a.id), json=cuerpo)

    assert respuesta.status_code == 422
    assert isinstance(respuesta.json()["detail"], list)
    assert _en_base(db_session, profesional_a) == []


# --- Superposición -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("inicio", "fin"), [("12:00", "15:00"), ("10:00", "11:00"), ("08:00", "09:05")]
)
def test_alta_superpuesta_o_contenida_responde_409(
    client: TestClient, db_session: Session, profesional_a: Profesional, inicio: str, fin: str
) -> None:
    _franja(db_session, profesional_a, 0, time(9, 0), time(13, 0))

    respuesta = client.post(_url(profesional_a.id), json=_cuerpo(0, inicio, fin))

    assert respuesta.status_code == 409
    assert respuesta.json() == {"detail": {"codigo": "franja_superpuesta"}}
    assert _en_base(db_session, profesional_a) == [(0, time(9, 0), time(13, 0))]


def test_alta_contigua_de_otro_dia_y_de_otro_profesional_responde_201(
    client: TestClient,
    db_session: Session,
    profesional_a: Profesional,
    profesional_b: Profesional,
) -> None:
    _franja(db_session, profesional_a, 0, time(9, 0), time(13, 0))

    contigua = client.post(_url(profesional_a.id), json=_cuerpo(0, "13:00", "17:00"))
    otro_dia = client.post(_url(profesional_a.id), json=_cuerpo(1))
    otro_prof = client.post(_url(profesional_b.id), json=_cuerpo(0))

    assert [contigua.status_code, otro_dia.status_code, otro_prof.status_code] == [201] * 3


# --- Consulta ----------------------------------------------------------------------------------


def test_listado_en_orden_por_dia_y_hora(
    client: TestClient, db_session: Session, profesional_a: Profesional
) -> None:
    _franja(db_session, profesional_a, 1, time(9, 0), time(13, 0))
    _franja(db_session, profesional_a, 0, time(14, 0), time(18, 0))
    _franja(db_session, profesional_a, 0, time(9, 0), time(13, 0))

    respuesta = client.get(_url(profesional_a.id))

    assert respuesta.status_code == 200
    assert [(f["dia_semana"], f["hora_inicio"], f["hora_fin"]) for f in respuesta.json()] == [
        (0, "09:00:00", "13:00:00"),
        (0, "14:00:00", "18:00:00"),
        (1, "09:00:00", "13:00:00"),
    ]


def test_listado_de_profesional_sin_franjas_es_lista_vacia(
    client: TestClient, profesional_a: Profesional
) -> None:
    respuesta = client.get(_url(profesional_a.id))

    assert respuesta.status_code == 200
    assert respuesta.json() == []


def test_listado_excluye_las_franjas_de_otro_profesional(
    client: TestClient,
    db_session: Session,
    profesional_a: Profesional,
    profesional_b: Profesional,
) -> None:
    propia = _franja(db_session, profesional_a, 0, time(9, 0), time(13, 0))
    _franja(db_session, profesional_b, 0, time(9, 0), time(13, 0))

    respuesta = client.get(_url(profesional_a.id))

    assert [f["id"] for f in respuesta.json()] == [str(propia.id)]


def test_listado_de_profesional_desactivado_sigue_disponible(
    client: TestClient, db_session: Session, profesional_a: Profesional
) -> None:
    _franja(db_session, profesional_a, 0, time(9, 0), time(13, 0))
    profesional_a.activo = False
    db_session.flush()

    assert len(client.get(_url(profesional_a.id)).json()) == 1


def test_listado_de_profesional_inexistente_es_404_y_de_id_mal_formado_es_422(
    client: TestClient,
) -> None:
    inexistente = client.get(_url(uuid4()))
    mal_formado = client.get("/profesionales/no-es-un-id/horarios")

    assert inexistente.status_code == 404
    assert inexistente.json() == NO_EXISTE_PROFESIONAL
    assert mal_formado.status_code == 422


# --- Edición -----------------------------------------------------------------------------------


def test_editar_extiende_el_fin_y_persiste(
    client: TestClient, db_session: Session, profesional_a: Profesional
) -> None:
    franja = _franja(db_session, profesional_a, 0, time(9, 0), time(13, 0))

    respuesta = client.patch(_url(profesional_a.id, franja.id), json={"hora_fin": "14:00"})

    assert respuesta.status_code == 200
    assert (respuesta.json()["hora_inicio"], respuesta.json()["hora_fin"]) == (
        "09:00:00",
        "14:00:00",
    )
    assert _en_base(db_session, profesional_a) == [(0, time(9, 0), time(14, 0))]


def test_achicar_la_propia_franja_no_choca_consigo_misma(
    client: TestClient, db_session: Session, profesional_a: Profesional
) -> None:
    franja = _franja(db_session, profesional_a, 0, time(9, 0), time(13, 0))

    respuesta = client.patch(_url(profesional_a.id, franja.id), json={"hora_inicio": "10:00"})

    assert respuesta.status_code == 200
    assert (respuesta.json()["hora_inicio"], respuesta.json()["hora_fin"]) == (
        "10:00:00",
        "13:00:00",
    )


def test_editar_con_resultado_invalido_responde_422_y_conserva_la_franja(
    client: TestClient, db_session: Session, profesional_a: Profesional
) -> None:
    franja = _franja(db_session, profesional_a, 0, time(9, 0), time(13, 0))

    respuesta = client.patch(_url(profesional_a.id, franja.id), json={"hora_fin": "08:00"})

    assert respuesta.status_code == 422
    assert respuesta.json()["detail"]["codigo"] == "franja_invalida"
    assert _en_base(db_session, profesional_a) == [(0, time(9, 0), time(13, 0))]


def test_editar_que_se_superpone_con_otra_franja_responde_409_y_no_cambia_nada(
    client: TestClient, db_session: Session, profesional_a: Profesional
) -> None:
    primera = _franja(db_session, profesional_a, 0, time(9, 0), time(13, 0))
    _franja(db_session, profesional_a, 0, time(14, 0), time(18, 0))

    respuesta = client.patch(_url(profesional_a.id, primera.id), json={"hora_fin": "15:00"})

    assert respuesta.status_code == 409
    assert respuesta.json() == {"detail": {"codigo": "franja_superpuesta"}}
    assert _en_base(db_session, profesional_a) == [
        (0, time(9, 0), time(13, 0)),
        (0, time(14, 0), time(18, 0)),
    ]


def test_mover_una_franja_a_un_dia_donde_se_superpone_responde_409(
    client: TestClient, db_session: Session, profesional_a: Profesional
) -> None:
    lunes = _franja(db_session, profesional_a, 0, time(9, 0), time(13, 0))
    _franja(db_session, profesional_a, 1, time(10, 0), time(12, 0))

    respuesta = client.patch(_url(profesional_a.id, lunes.id), json={"dia_semana": 1})

    assert respuesta.status_code == 409
    assert _en_base(db_session, profesional_a) == [
        (0, time(9, 0), time(13, 0)),
        (1, time(10, 0), time(12, 0)),
    ]


def test_mover_una_franja_a_un_dia_libre_responde_200(
    client: TestClient, db_session: Session, profesional_a: Profesional
) -> None:
    lunes = _franja(db_session, profesional_a, 0, time(9, 0), time(13, 0))
    _franja(db_session, profesional_a, 1, time(10, 0), time(12, 0))

    respuesta = client.patch(_url(profesional_a.id, lunes.id), json={"dia_semana": 2})

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert (cuerpo["dia_semana"], cuerpo["hora_inicio"], cuerpo["hora_fin"]) == (
        2,
        "09:00:00",
        "13:00:00",
    )
    assert _en_base(db_session, profesional_a) == [
        (1, time(10, 0), time(12, 0)),
        (2, time(9, 0), time(13, 0)),
    ]


def test_editar_con_nulo_explicito_es_422_y_con_campo_desconocido_se_ignora(
    client: TestClient, db_session: Session, profesional_a: Profesional
) -> None:
    franja = _franja(db_session, profesional_a, 0, time(9, 0), time(13, 0))

    nulo = client.patch(_url(profesional_a.id, franja.id), json={"hora_inicio": None})
    desconocido = client.patch(_url(profesional_a.id, franja.id), json={"color": "azul"})

    assert nulo.status_code == 422
    assert desconocido.status_code == 200
    assert "color" not in desconocido.json()
    assert _en_base(db_session, profesional_a) == [(0, time(9, 0), time(13, 0))]


def test_editar_la_franja_de_otro_profesional_responde_404_horario(
    client: TestClient,
    db_session: Session,
    profesional_a: Profesional,
    profesional_b: Profesional,
) -> None:
    ajena = _franja(db_session, profesional_b, 0, time(9, 0), time(13, 0))

    respuesta = client.patch(_url(profesional_a.id, ajena.id), json={"hora_fin": "14:00"})

    assert respuesta.status_code == 404
    assert respuesta.json() == NO_EXISTE_HORARIO
    assert _en_base(db_session, profesional_b) == [(0, time(9, 0), time(13, 0))]


def test_editar_franja_o_profesional_inexistente_responde_404_distinguiendo_el_recurso(
    client: TestClient, db_session: Session, profesional_a: Profesional
) -> None:
    franja = _franja(db_session, profesional_a, 0, time(9, 0), time(13, 0))

    sin_franja = client.patch(_url(profesional_a.id, uuid4()), json={"hora_fin": "14:00"})
    sin_profesional = client.patch(_url(uuid4(), franja.id), json={"hora_fin": "14:00"})

    assert sin_franja.json() == NO_EXISTE_HORARIO
    assert sin_profesional.json() == NO_EXISTE_PROFESIONAL
    assert (sin_franja.status_code, sin_profesional.status_code) == (404, 404)
    assert _en_base(db_session, profesional_a) == [(0, time(9, 0), time(13, 0))]


def test_editar_con_body_invalido_sobre_path_inexistente_responde_422_no_404(
    client: TestClient,
) -> None:
    respuesta = client.patch(_url(uuid4(), uuid4()), json={"hora_inicio": None})

    assert respuesta.status_code == 422


# --- Borrado -----------------------------------------------------------------------------------


def test_borrar_responde_204_sin_cuerpo_y_el_listado_ya_no_la_incluye(
    client: TestClient, db_session: Session, profesional_a: Profesional
) -> None:
    _franja(db_session, profesional_a, 0, time(9, 0), time(13, 0))
    tarde = _franja(db_session, profesional_a, 0, time(14, 0), time(18, 0))

    respuesta = client.delete(_url(profesional_a.id, tarde.id))

    assert respuesta.status_code == 204
    assert respuesta.content == b""
    restantes = client.get(_url(profesional_a.id)).json()
    assert [(f["hora_inicio"], f["hora_fin"]) for f in restantes] == [("09:00:00", "13:00:00")]


def test_borrar_franja_inexistente_responde_404_horario(
    client: TestClient, profesional_a: Profesional
) -> None:
    respuesta = client.delete(_url(profesional_a.id, uuid4()))

    assert respuesta.status_code == 404
    assert respuesta.json() == NO_EXISTE_HORARIO


def test_borrar_sobre_profesional_inexistente_responde_404_profesional_y_conserva_la_franja(
    client: TestClient, db_session: Session, profesional_a: Profesional
) -> None:
    franja = _franja(db_session, profesional_a, 0, time(9, 0), time(13, 0))

    respuesta = client.delete(_url(uuid4(), franja.id))

    assert respuesta.status_code == 404
    assert respuesta.json() == NO_EXISTE_PROFESIONAL
    assert _en_base(db_session, profesional_a) == [(0, time(9, 0), time(13, 0))]


def test_borrar_la_franja_de_otro_profesional_responde_404_y_no_la_borra(
    client: TestClient,
    db_session: Session,
    profesional_a: Profesional,
    profesional_b: Profesional,
) -> None:
    ajena = _franja(db_session, profesional_b, 0, time(9, 0), time(13, 0))

    respuesta = client.delete(_url(profesional_a.id, ajena.id))

    assert respuesta.status_code == 404
    assert respuesta.json() == NO_EXISTE_HORARIO
    assert _en_base(db_session, profesional_b) == [(0, time(9, 0), time(13, 0))]
