"""API de bloqueos de agenda (C-11): app real, PostgreSQL real, tokens reales."""

from collections.abc import Callable
from datetime import UTC, datetime, time
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.api.turnos import get_reloj
from app.infrastructure.db.models import Bloqueo, HorarioAtencion, Profesional, Usuario
from tests.integration.factories import Catalogo, crear_catalogo, dar_horario_amplio
from tests.integration.helpers_recordatorios import recordatorios_de

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


# --- Requisito: Profesional del bloqueo según el rol -----------------------------------------


def test_odontologo_sin_profesional_bloquea_su_propia_agenda(
    como: Callable[[Usuario], TestClient], db_session: Session, odontologo: Usuario
) -> None:
    respuesta = como(odontologo).post(
        "/bloqueos", json=_body(None, _jueves(10), _jueves(11), "Trámite")
    )

    assert respuesta.status_code == 201
    assert respuesta.json()["profesional_id"] == str(odontologo.profesional_id)
    assert respuesta.json()["creado_por"] == str(odontologo.id)
    assert [b.profesional_id for b in _bloqueos(db_session)] == [odontologo.profesional_id]


def test_odontologo_que_indica_su_propio_profesional_bloquea_su_agenda(
    como: Callable[[Usuario], TestClient], odontologo: Usuario
) -> None:
    propio = odontologo.profesional_id
    assert propio is not None

    respuesta = como(odontologo).post(
        "/bloqueos", json=_body(propio, _jueves(10), _jueves(11), "Trámite")
    )

    assert respuesta.status_code == 201
    assert respuesta.json()["profesional_id"] == str(propio)


def test_odontologo_no_bloquea_la_agenda_de_otro_exista_o_no(
    como: Callable[[Usuario], TestClient],
    db_session: Session,
    catalogo: Catalogo,
    odontologo: Usuario,
) -> None:
    b = catalogo.profesionales[1]
    api = como(odontologo)

    ajeno = api.post("/bloqueos", json=_body(b, _jueves(10), _jueves(11), "Trámite"))
    inexistente = api.post("/bloqueos", json=_body(uuid4(), _jueves(10), _jueves(11), "Trámite"))

    assert (ajeno.status_code, ajeno.json()) == (403, CUERPO_AJENO)
    assert (inexistente.status_code, inexistente.json()) == (403, CUERPO_AJENO)
    assert _bloqueos(db_session) == []


def test_profesional_ajeno_se_evalua_antes_que_el_bloqueo_invalido(
    como: Callable[[Usuario], TestClient],
    db_session: Session,
    catalogo: Catalogo,
    odontologo: Usuario,
) -> None:
    b = catalogo.profesionales[1]

    respuesta = como(odontologo).post(
        "/bloqueos", json=_body(b, _jueves(10), _jueves(10), "Trámite")
    )

    assert (respuesta.status_code, respuesta.json()) == (403, CUERPO_AJENO)
    assert _bloqueos(db_session) == []


def test_recepcionista_sin_profesional_recibe_422_profesional_requerido(
    api: TestClient, db_session: Session
) -> None:
    respuesta = api.post("/bloqueos", json=_body(None, _jueves(10), _jueves(11), "Trámite"))

    assert respuesta.status_code == 422
    assert respuesta.json() == {
        "detail": {
            "codigo": "profesional_requerido",
            "mensaje": "indicá el profesional del bloqueo",
        }
    }
    assert _bloqueos(db_session) == []


def test_profesional_inexistente_recibe_422_referencia_invalida(
    api: TestClient, db_session: Session
) -> None:
    respuesta = api.post("/bloqueos", json=_body(uuid4(), _jueves(10), _jueves(11), "Trámite"))

    assert respuesta.status_code == 422
    assert respuesta.json() == {
        "detail": {
            "codigo": "referencia_invalida",
            "referencia": "profesional",
            "motivo": "inexistente",
        }
    }
    assert _bloqueos(db_session) == []


# --- Requisito: Validación del bloqueo -------------------------------------------------------

BLOQUEO_INVALIDO = {
    "detail": {
        "codigo": "bloqueo_invalido",
        "mensaje": "el bloqueo debe tener fin posterior a inicio y un motivo no vacío",
    }
}


@pytest.mark.parametrize(
    ("inicio", "fin", "motivo"),
    [
        (_jueves(10), _jueves(10), "Congreso"),
        (_jueves(12), _jueves(10), "Congreso"),
        (_jueves(10), _jueves(12), ""),
        (_jueves(10), _jueves(12), "   "),
    ],
    ids=["fin-igual", "fin-anterior", "motivo-vacio", "motivo-en-blanco"],
)
def test_bloqueo_con_intervalo_o_motivo_invalido_recibe_422_bloqueo_invalido(
    api: TestClient, db_session: Session, catalogo: Catalogo, inicio: str, fin: str, motivo: str
) -> None:
    a = catalogo.profesionales[0]

    respuesta = api.post("/bloqueos", json=_body(a, inicio, fin, motivo))

    assert (respuesta.status_code, respuesta.json()) == (422, BLOQUEO_INVALIDO)
    assert _bloqueos(db_session) == []


def test_motivo_con_espacios_en_los_extremos_se_guarda_recortado(
    api: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    a = catalogo.profesionales[0]

    respuesta = api.post("/bloqueos", json=_body(a, _jueves(10), _jueves(11), "  Congreso  "))

    assert respuesta.status_code == 201
    assert respuesta.json()["motivo"] == "Congreso"
    assert [b.motivo for b in _bloqueos(db_session)] == ["Congreso"]


def test_motivo_de_255_letras_se_acepta_solo_y_rodeado_de_espacios(
    api: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    a = catalogo.profesionales[0]
    letras = "ñ" * 255

    solo = api.post("/bloqueos", json=_body(a, _jueves(10), _jueves(11), letras))
    con_espacios = api.post("/bloqueos", json=_body(a, _jueves(11), _jueves(12), f"  {letras}  "))

    assert (solo.status_code, con_espacios.status_code) == (201, 201)
    assert solo.json()["motivo"] == letras
    assert con_espacios.json()["motivo"] == letras
    assert [b.motivo for b in _bloqueos(db_session)] == [letras, letras]


@pytest.mark.parametrize(
    "cuerpo",
    [
        {"inicio": "2026-10-08T10:00:00-03:00", "fin": "2026-10-08T11:00:00-03:00"},
        {"inicio": "2026-10-08T10:00:00-03:00", "motivo": "Congreso"},
        {
            "inicio": "2026-10-08T10:00:00-03:00",
            "fin": "2026-10-08T11:00:00-03:00",
            "motivo": "x" * 256,
        },
        {"inicio": "2026-10-08T10:00:00", "fin": "2026-10-08T11:00:00-03:00", "motivo": "Congreso"},
    ],
    ids=["sin-motivo", "sin-fin", "motivo-de-256", "inicio-sin-zona"],
)
def test_campos_faltantes_o_fuera_de_forma_reciben_422_sin_persistir(
    api: TestClient, db_session: Session, catalogo: Catalogo, cuerpo: dict[str, str]
) -> None:
    respuesta = api.post(
        "/bloqueos", json={"profesional_id": str(catalogo.profesionales[0].id), **cuerpo}
    )

    assert respuesta.status_code == 422
    assert _bloqueos(db_session) == []


def test_profesional_requerido_se_evalua_antes_que_el_bloqueo_invalido(
    api: TestClient, db_session: Session
) -> None:
    respuesta = api.post("/bloqueos", json=_body(None, _jueves(10), _jueves(10), "Congreso"))

    assert respuesta.status_code == 422
    assert respuesta.json()["detail"]["codigo"] == "profesional_requerido"
    assert _bloqueos(db_session) == []


def test_profesional_inexistente_se_evalua_antes_que_el_bloqueo_invalido(
    api: TestClient, db_session: Session
) -> None:
    respuesta = api.post("/bloqueos", json=_body(uuid4(), _jueves(10), _jueves(12), "   "))

    assert respuesta.status_code == 422
    assert respuesta.json()["detail"]["codigo"] == "referencia_invalida"
    assert _bloqueos(db_session) == []


# --- Requisito: Bloqueo sobre turnos activos rechazado ---------------------------------------


def _turno_por_api(
    api: TestClient,
    catalogo: Catalogo,
    inicio: str,
    *,
    profesional: Profesional | UUID | None = None,
    paciente: int = 0,
    **extra: Any,
) -> str:
    """Crea un turno de limpieza (45 min, sillón 1) por `POST /turnos`; devuelve su id."""
    elegido = catalogo.profesionales[0] if profesional is None else profesional
    cuerpo: dict[str, Any] = {
        "profesional_id": str(elegido if isinstance(elegido, UUID) else elegido.id),
        "paciente_id": str(catalogo.pacientes[paciente].id),
        "prestacion_id": str(catalogo.limpieza.id),
        "sillon_id": str(catalogo.sillones[paciente].id),
        "inicio": inicio,
        **extra,
    }
    respuesta = api.post("/turnos", json=cuerpo)
    assert respuesta.status_code == 201, respuesta.text
    return str(respuesta.json()["id"])


def _local(dia: int, hora: int, minuto: int = 0) -> str:
    return f"2026-10-{dia:02d}T{hora:02d}:{minuto:02d}:00-03:00"


MENSAJE_CON_TURNOS = (
    "hay turnos activos en el intervalo: reprogramalos o cancelalos antes de bloquear"
)


def _conflicto(*turnos: tuple[str, str, str]) -> dict[str, Any]:
    return {
        "detail": {
            "codigo": "bloqueo_con_turnos",
            "mensaje": MENSAJE_CON_TURNOS,
            "turnos": [{"id": i, "inicio": ini, "fin": fin} for i, ini, fin in turnos],
        }
    }


def test_bloqueo_sobre_un_turno_activo_recibe_409_con_el_turno_y_no_persiste(
    api: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    a = catalogo.profesionales[0]
    t1 = _turno_por_api(api, catalogo, _local(8, 10, 30))

    respuesta = api.post("/bloqueos", json=_body(a, _local(8, 10), _local(8, 12), "Congreso"))

    assert respuesta.status_code == 409
    assert respuesta.json() == _conflicto(
        (t1, "2026-10-08T10:30:00-03:00", "2026-10-08T11:15:00-03:00")
    )
    assert _bloqueos(db_session) == []


def test_varios_turnos_afectados_se_listan_por_inicio_sin_el_cancelado(
    api: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    a = catalogo.profesionales[0]
    t2 = _turno_por_api(api, catalogo, _local(8, 11))
    t1 = _turno_por_api(api, catalogo, _local(8, 9, 30))
    cancelado = _turno_por_api(
        api,
        catalogo,
        _local(8, 10, 30),
        prestacion_id=str(catalogo.consulta.id),
        sillon_id=None,
        duracion_min=15,
    )
    assert api.post(f"/turnos/{cancelado}/cancelar").status_code == 200

    respuesta = api.post("/bloqueos", json=_body(a, _local(8, 10), _local(8, 12), "Congreso"))

    assert respuesta.status_code == 409
    assert respuesta.json() == _conflicto(
        (t1, "2026-10-08T09:30:00-03:00", "2026-10-08T10:15:00-03:00"),
        (t2, "2026-10-08T11:00:00-03:00", "2026-10-08T11:45:00-03:00"),
    )
    assert _bloqueos(db_session) == []


@pytest.mark.parametrize(
    "hora_turno", [(9, 15), (12, 0)], ids=["termina-al-empezar", "empieza-al-terminar"]
)
def test_turno_contiguo_al_bloqueo_no_lo_impide(
    api: TestClient, db_session: Session, catalogo: Catalogo, hora_turno: tuple[int, int]
) -> None:
    a = catalogo.profesionales[0]
    _turno_por_api(api, catalogo, _local(8, *hora_turno))

    respuesta = api.post("/bloqueos", json=_body(a, _local(8, 10), _local(8, 12), "Congreso"))

    assert respuesta.status_code == 201
    assert len(_bloqueos(db_session)) == 1


def test_turno_cancelado_en_el_intervalo_no_impide_el_bloqueo(
    api: TestClient, catalogo: Catalogo
) -> None:
    a = catalogo.profesionales[0]
    cancelado = _turno_por_api(api, catalogo, _local(8, 10, 30))
    assert api.post(f"/turnos/{cancelado}/cancelar").status_code == 200

    respuesta = api.post("/bloqueos", json=_body(a, _local(8, 10), _local(8, 12), "Congreso"))

    assert respuesta.status_code == 201


def test_turno_de_otro_profesional_en_el_intervalo_no_impide_el_bloqueo(
    api: TestClient, catalogo: Catalogo
) -> None:
    a, b = catalogo.profesionales
    _turno_por_api(api, catalogo, _local(8, 10, 30), profesional=b, paciente=1)

    respuesta = api.post("/bloqueos", json=_body(a, _local(8, 10), _local(8, 12), "Congreso"))

    assert respuesta.status_code == 201


def test_odontologo_con_un_turno_propio_en_el_intervalo_recibe_409(
    api: TestClient,
    como: Callable[[Usuario], TestClient],
    db_session: Session,
    catalogo: Catalogo,
    odontologo: Usuario,
) -> None:
    propio = db_session.get(Profesional, odontologo.profesional_id)
    assert propio is not None
    dar_horario_amplio(db_session, propio)
    t1 = _turno_por_api(api, catalogo, _local(8, 10, 30), profesional=propio)

    respuesta = como(odontologo).post(
        "/bloqueos", json=_body(None, _local(8, 10), _local(8, 12), "Congreso")
    )

    assert respuesta.status_code == 409
    assert respuesta.json() == _conflicto(
        (t1, "2026-10-08T10:30:00-03:00", "2026-10-08T11:15:00-03:00")
    )
    assert _bloqueos(db_session) == []


def _contar(session: Session, tabla: str) -> int:
    return int(session.execute(text(f"SELECT count(*) FROM {tabla}")).scalar_one())


def _fila_de_turno(session: Session, turno_id: str) -> tuple[Any, ...]:
    session.expire_all()
    fila = session.execute(
        text("SELECT estado, inicio, fin, actualizado_en FROM turno WHERE id = :id"),
        {"id": turno_id},
    ).one()
    return tuple(fila)


def test_el_rechazo_no_toca_el_turno_ni_su_recordatorio_ni_la_auditoria(
    api: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    a = catalogo.profesionales[0]
    t1 = _turno_por_api(api, catalogo, _local(9, 10, 30))
    turno_antes = _fila_de_turno(db_session, t1)
    recordatorios_antes = recordatorios_de(db_session, UUID(t1))
    auditoria_antes = _contar(db_session, "turno_auditoria")
    assert [r["estado"] for r in recordatorios_antes] == ["pendiente"]

    respuesta = api.post("/bloqueos", json=_body(a, _local(9, 10), _local(9, 12), "Congreso"))

    assert respuesta.status_code == 409
    assert _bloqueos(db_session) == []
    assert _fila_de_turno(db_session, t1) == turno_antes
    assert recordatorios_de(db_session, UUID(t1)) == recordatorios_antes
    assert _contar(db_session, "turno_auditoria") == auditoria_antes


def test_cancelar_el_turno_y_repetir_el_bloqueo_rechazado_lo_acepta(
    api: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    a = catalogo.profesionales[0]
    t1 = _turno_por_api(api, catalogo, _local(8, 10, 30))
    cuerpo = _body(a, _local(8, 10), _local(8, 12), "Congreso")
    assert api.post("/bloqueos", json=cuerpo).status_code == 409
    assert _bloqueos(db_session) == []

    assert api.post(f"/turnos/{t1}/cancelar").status_code == 200
    respuesta = api.post("/bloqueos", json=cuerpo)

    assert respuesta.status_code == 201
    assert len(_bloqueos(db_session)) == 1


def test_bloqueo_retroactivo_sobre_un_turno_pasado_recibe_409(
    api: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    a = catalogo.profesionales[0]
    ahora = [datetime(2026, 10, 5, 12, 0, tzinfo=UTC)]  # 2026-10-05 09:00 hora local
    api.app.dependency_overrides[get_reloj] = lambda: lambda: ahora[0]  # type: ignore[attr-defined]
    t1 = _turno_por_api(api, catalogo, _local(6, 10, 30))
    ahora[0] = AHORA  # 2026-10-07 09:00 hora local

    respuesta = api.post("/bloqueos", json=_body(a, _local(6, 10), _local(6, 12), "Congreso"))

    assert respuesta.status_code == 409
    assert respuesta.json() == _conflicto(
        (t1, "2026-10-06T10:30:00-03:00", "2026-10-06T11:15:00-03:00")
    )
    assert _bloqueos(db_session) == []


# --- Requisito: Bloqueos superpuestos del mismo profesional ----------------------------------


def _bloquear(
    api: TestClient, profesional: Profesional | UUID | None, inicio: str, fin: str, motivo: str
) -> dict[str, Any]:
    respuesta = api.post("/bloqueos", json=_body(profesional, inicio, fin, motivo))
    assert respuesta.status_code == 201, respuesta.text
    return dict(respuesta.json())


def test_un_bloqueo_dentro_de_otro_del_mismo_profesional_se_acepta_y_quedan_los_dos(
    api: TestClient,
    como: Callable[[Usuario], TestClient],
    db_session: Session,
    odontologo: Usuario,
) -> None:
    propio = odontologo.profesional_id
    assert propio is not None
    _bloquear(api, propio, _local(8, 9), _local(8, 18), "Congreso")

    respuesta = como(odontologo).post(
        "/bloqueos", json=_body(None, _local(8, 10), _local(8, 11), "Trámite")
    )

    assert respuesta.status_code == 201
    assert [(b.motivo, b.profesional_id) for b in _bloqueos(db_session)] == [
        ("Congreso", propio),
        ("Trámite", propio),
    ]


# --- Requisito: Consulta de bloqueos ---------------------------------------------------------


def test_recepcionista_lista_todos_los_bloqueos_ordenados_por_inicio(
    api: TestClient, catalogo: Catalogo
) -> None:
    a, b = catalogo.profesionales
    de_a = _bloquear(api, a, _local(9, 10), _local(9, 11), "Curso")
    de_b = _bloquear(api, b, _local(8, 15), _local(8, 16), "Trámite")

    respuesta = api.get("/bloqueos")

    assert respuesta.status_code == 200
    assert respuesta.json() == [de_b, de_a]


def test_recepcionista_filtra_los_bloqueos_por_profesional(
    api: TestClient, catalogo: Catalogo
) -> None:
    a, b = catalogo.profesionales
    de_a = _bloquear(api, a, _local(9, 10), _local(9, 11), "Curso")
    _bloquear(api, b, _local(8, 15), _local(8, 16), "Trámite")

    respuesta = api.get("/bloqueos", params={"profesional_id": str(a.id)})

    assert respuesta.status_code == 200
    assert respuesta.json() == [de_a]


def test_la_consulta_incluye_los_bloqueos_pasados_primero(
    api: TestClient, catalogo: Catalogo
) -> None:
    a = catalogo.profesionales[0]
    del_8 = _bloquear(api, a, _local(8, 10), _local(8, 11), "Curso")
    del_6 = _bloquear(api, a, _local(6, 10), _local(6, 11), "Trámite")

    respuesta = api.get("/bloqueos", params={"profesional_id": str(a.id)})

    assert respuesta.json() == [del_6, del_8]


def test_el_filtro_por_un_profesional_inexistente_da_lista_vacia(
    api: TestClient, catalogo: Catalogo
) -> None:
    _bloquear(api, catalogo.profesionales[0], _local(8, 10), _local(8, 11), "Curso")

    respuesta = api.get("/bloqueos", params={"profesional_id": str(uuid4())})

    assert (respuesta.status_code, respuesta.json()) == (200, [])


def test_odontologo_ve_solo_los_bloqueos_de_su_profesional_con_y_sin_filtro(
    api: TestClient,
    como: Callable[[Usuario], TestClient],
    catalogo: Catalogo,
    odontologo: Usuario,
) -> None:
    propio = odontologo.profesional_id
    assert propio is not None
    de_a = _bloquear(api, propio, _local(8, 10), _local(8, 11), "Curso")
    _bloquear(api, catalogo.profesionales[1], _local(8, 10), _local(8, 11), "Trámite")
    cliente = como(odontologo)

    sin_filtro = cliente.get("/bloqueos")
    con_el_suyo = cliente.get("/bloqueos", params={"profesional_id": str(propio)})

    assert (sin_filtro.status_code, sin_filtro.json()) == (200, [de_a])
    assert (con_el_suyo.status_code, con_el_suyo.json()) == (200, [de_a])


def test_odontologo_que_filtra_por_otro_profesional_recibe_403(
    como: Callable[[Usuario], TestClient], catalogo: Catalogo, odontologo: Usuario
) -> None:
    respuesta = como(odontologo).get(
        "/bloqueos", params={"profesional_id": str(catalogo.profesionales[1].id)}
    )

    assert (respuesta.status_code, respuesta.json()) == (403, CUERPO_AJENO)


def test_filtro_mal_formado_recibe_422(api: TestClient) -> None:
    assert api.get("/bloqueos", params={"profesional_id": "no-es-un-id"}).status_code == 422


# --- Requisito: Borrado de un bloqueo --------------------------------------------------------


def test_recepcionista_borra_un_bloqueo_y_deja_de_listarse(
    api: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    a = catalogo.profesionales[0]
    bloqueo = _bloquear(api, a, _local(8, 10), _local(8, 12), "Congreso")

    respuesta = api.delete(f"/bloqueos/{bloqueo['id']}")

    assert (respuesta.status_code, respuesta.content) == (204, b"")
    assert api.get("/bloqueos").json() == []
    assert _bloqueos(db_session) == []


def test_odontologo_borra_un_bloqueo_de_su_agenda_creado_por_la_recepcion(
    api: TestClient,
    como: Callable[[Usuario], TestClient],
    db_session: Session,
    odontologo: Usuario,
) -> None:
    bloqueo = _bloquear(api, odontologo.profesional_id, _local(8, 10), _local(8, 12), "Congreso")

    respuesta = como(odontologo).delete(f"/bloqueos/{bloqueo['id']}")

    assert (respuesta.status_code, respuesta.content) == (204, b"")
    assert _bloqueos(db_session) == []


def test_odontologo_no_borra_un_bloqueo_de_otro_profesional(
    api: TestClient,
    como: Callable[[Usuario], TestClient],
    db_session: Session,
    catalogo: Catalogo,
    odontologo: Usuario,
) -> None:
    de_b = _bloquear(api, catalogo.profesionales[1], _local(8, 10), _local(8, 12), "Congreso")

    respuesta = como(odontologo).delete(f"/bloqueos/{de_b['id']}")

    assert (respuesta.status_code, respuesta.json()) == (403, CUERPO_AJENO)
    assert [str(b.id) for b in _bloqueos(db_session)] == [de_b["id"]]


def test_odontologo_con_un_bloqueo_inexistente_recibe_403_y_no_404(
    api: TestClient,
    como: Callable[[Usuario], TestClient],
    db_session: Session,
    odontologo: Usuario,
) -> None:
    propio = _bloquear(api, odontologo.profesional_id, _local(8, 10), _local(8, 12), "Congreso")

    respuesta = como(odontologo).delete(f"/bloqueos/{uuid4()}")

    assert (respuesta.status_code, respuesta.json()) == (403, CUERPO_AJENO)
    assert [str(b.id) for b in _bloqueos(db_session)] == [propio["id"]]


def test_recepcionista_con_un_bloqueo_inexistente_recibe_404(api: TestClient) -> None:
    respuesta = api.delete(f"/bloqueos/{uuid4()}")

    assert respuesta.status_code == 404
    assert respuesta.json() == {"detail": {"codigo": "recurso_inexistente", "recurso": "bloqueo"}}


def test_borrar_con_un_identificador_mal_formado_recibe_422(api: TestClient) -> None:
    assert api.delete("/bloqueos/no-es-un-id").status_code == 422
