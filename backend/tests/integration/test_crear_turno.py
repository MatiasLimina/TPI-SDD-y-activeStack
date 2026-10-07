"""Caso de uso CrearTurno contra PostgreSQL real, con reloj fijo inyectado."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.application.crear_turno import CrearTurno, SolicitudTurno
from app.domain.turnos import (
    Recurso,
    ReferenciaInvalidaError,
    SolapamientoError,
    TurnoCreado,
    TurnoInvalidoError,
    TurnoPropuesto,
)
from app.infrastructure.db.models import Turno
from app.infrastructure.db.repositorio_turnos import RepositorioTurnos
from tests.integration.factories import Catalogo, crear_catalogo

AHORA = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)  # 09:00 hora local
INICIO = datetime(2026, 10, 8, 13, 0, tzinfo=UTC)  # 10:00 hora local del día siguiente


@pytest.fixture
def catalogo(db_session: Session) -> Catalogo:
    return crear_catalogo(db_session)


@pytest.fixture
def caso_de_uso(db_session: Session) -> CrearTurno:
    return CrearTurno(RepositorioTurnos(db_session), reloj=lambda: AHORA)


def _solicitud(
    c: Catalogo,
    *,
    prof: int = 0,
    sillon: int | None = 0,
    pac: int = 0,
    desde: int = 0,
    duracion: int | None = None,
    inicio: datetime | None = None,
) -> SolicitudTurno:
    return SolicitudTurno(
        profesional_id=c.profesionales[prof].id,
        paciente_id=c.pacientes[pac].id,
        prestacion_id=c.limpieza.id,
        sillon_id=None if sillon is None else c.sillones[sillon].id,
        inicio=inicio or INICIO + timedelta(minutes=desde),
        duracion_min=duracion,
    )


def _cantidad_turnos(session: Session) -> int:
    return session.scalar(select(func.count()).select_from(Turno)) or 0


# --- 5.1 alta válida ---------------------------------------------------------------------


def test_alta_valida_usa_la_duracion_de_la_prestacion_y_calcula_el_fin(
    db_session: Session, caso_de_uso: CrearTurno, catalogo: Catalogo
) -> None:
    creado = caso_de_uso.ejecutar(_solicitud(catalogo))

    assert isinstance(creado, TurnoCreado)
    assert creado.estado == "programado"
    assert creado.creado_por is None
    assert creado.duracion_min == 45
    assert creado.fin == INICIO + timedelta(minutes=45)
    assert db_session.get(Turno, creado.id) is not None


def test_alta_con_duracion_ajustada_reemplaza_la_de_la_prestacion(
    caso_de_uso: CrearTurno, catalogo: Catalogo
) -> None:
    creado = caso_de_uso.ejecutar(_solicitud(catalogo, duracion=60))

    assert creado.duracion_min == 60
    assert creado.fin == INICIO + timedelta(minutes=60)


def test_alta_normaliza_el_inicio_a_utc(caso_de_uso: CrearTurno, catalogo: Catalogo) -> None:
    local = INICIO.astimezone(ZoneInfo("America/Argentina/Buenos_Aires"))

    creado = caso_de_uso.ejecutar(_solicitud(catalogo, inicio=local))

    assert creado.inicio == INICIO
    assert creado.inicio.utcoffset() == timedelta(0)


# --- 5.2 orden de validaciones -----------------------------------------------------------


def test_referencia_invalida_responde_antes_que_el_solape(
    caso_de_uso: CrearTurno, catalogo: Catalogo
) -> None:
    caso_de_uso.ejecutar(_solicitud(catalogo))
    solicitud = _solicitud(catalogo)
    inexistente = SolicitudTurno(**{**solicitud.__dict__, "sillon_id": uuid4()})

    with pytest.raises(ReferenciaInvalidaError):
        caso_de_uso.ejecutar(inexistente)


@pytest.mark.parametrize(
    ("variacion", "codigo"),
    [
        ({"duracion": 42}, "duracion_invalida"),
        ({"sillon": None}, "sillon_requerido"),
        ({"inicio": INICIO + timedelta(minutes=17)}, "inicio_no_alineado"),
    ],
)
def test_regla_de_dominio_responde_antes_que_el_solape(
    caso_de_uso: CrearTurno, catalogo: Catalogo, variacion: dict[str, object], codigo: str
) -> None:
    caso_de_uso.ejecutar(_solicitud(catalogo))  # ocupa el horario

    with pytest.raises(TurnoInvalidoError) as excinfo:
        caso_de_uso.ejecutar(_solicitud(catalogo, desde=15, **variacion))  # type: ignore[arg-type]

    assert excinfo.value.codigo == codigo


def test_inicio_en_pasado_se_evalua_con_el_reloj_inyectado(
    db_session: Session, catalogo: Catalogo
) -> None:
    tarde = CrearTurno(RepositorioTurnos(db_session), reloj=lambda: INICIO + timedelta(minutes=1))

    with pytest.raises(TurnoInvalidoError) as excinfo:
        tarde.ejecutar(_solicitud(catalogo))

    assert excinfo.value.codigo == "inicio_en_pasado"
    assert _cantidad_turnos(db_session) == 0


def test_inicio_igual_al_reloj_es_aceptado(db_session: Session, catalogo: Catalogo) -> None:
    justo = CrearTurno(RepositorioTurnos(db_session), reloj=lambda: INICIO)

    assert justo.ejecutar(_solicitud(catalogo)).inicio == INICIO


# --- 5.3 pre-chequeo ---------------------------------------------------------------------


def test_conflicto_total_lista_profesional_sillon_y_paciente(
    caso_de_uso: CrearTurno, catalogo: Catalogo
) -> None:
    caso_de_uso.ejecutar(_solicitud(catalogo))

    with pytest.raises(SolapamientoError) as excinfo:
        caso_de_uso.ejecutar(_solicitud(catalogo, desde=15))

    assert excinfo.value.recursos == ("profesional", "sillon", "paciente")


@pytest.mark.parametrize(
    ("variacion", "recurso"),
    [
        ({"sillon": 1, "pac": 1}, "profesional"),
        ({"prof": 1, "pac": 1}, "sillon"),
        ({"prof": 1, "sillon": 1}, "paciente"),
    ],
)
def test_conflicto_parcial_lista_un_solo_recurso(
    db_session: Session,
    caso_de_uso: CrearTurno,
    catalogo: Catalogo,
    variacion: dict[str, int],
    recurso: str,
) -> None:
    caso_de_uso.ejecutar(_solicitud(catalogo))

    with pytest.raises(SolapamientoError) as excinfo:
        caso_de_uso.ejecutar(_solicitud(catalogo, desde=15, **variacion))

    assert excinfo.value.recursos == (recurso,)
    assert _cantidad_turnos(db_session) == 1


# --- 5.4 puntos de extensión -------------------------------------------------------------


def test_validador_que_falla_corta_el_alta_sin_persistir(
    db_session: Session, catalogo: Catalogo
) -> None:
    def rechaza(propuesto: TurnoPropuesto) -> None:
        raise TurnoInvalidoError("fuera_de_horario", "fuera del horario de atención")

    caso = CrearTurno(RepositorioTurnos(db_session), lambda: AHORA, validadores=[rechaza])

    with pytest.raises(TurnoInvalidoError) as excinfo:
        caso.ejecutar(_solicitud(catalogo))

    assert excinfo.value.codigo == "fuera_de_horario"
    assert _cantidad_turnos(db_session) == 0


def test_validador_recibe_el_turno_propuesto_ya_normalizado(
    db_session: Session, catalogo: Catalogo
) -> None:
    vistos: list[TurnoPropuesto] = []
    caso = CrearTurno(RepositorioTurnos(db_session), lambda: AHORA, validadores=[vistos.append])

    caso.ejecutar(_solicitud(catalogo))

    assert len(vistos) == 1
    assert (vistos[0].inicio, vistos[0].fin) == (INICIO, INICIO + timedelta(minutes=45))
    assert vistos[0].duracion_min == 45


def test_observador_recibe_el_turno_creado_antes_del_commit(
    db_session: Session, catalogo: Catalogo
) -> None:
    eventos: list[str] = []
    recibidos: list[TurnoCreado] = []
    repositorio = RepositorioTurnos(db_session)
    commit_original = repositorio.commit

    def commit_registrado() -> None:
        eventos.append("commit")
        commit_original()

    repositorio.commit = commit_registrado  # type: ignore[method-assign]

    def observador(creado: TurnoCreado) -> None:
        eventos.append("observador")
        recibidos.append(creado)

    caso = CrearTurno(repositorio, lambda: AHORA, observadores=[observador])

    creado = caso.ejecutar(_solicitud(catalogo))

    assert recibidos == [creado]
    assert eventos == ["observador", "commit"]


def test_observador_que_falla_deshace_el_alta(db_session: Session, catalogo: Catalogo) -> None:
    def falla(creado: TurnoCreado) -> None:
        raise RuntimeError("auditoría caída")

    caso = CrearTurno(RepositorioTurnos(db_session), lambda: AHORA, observadores=[falla])

    with pytest.raises(RuntimeError):
        caso.ejecutar(_solicitud(catalogo))

    assert _cantidad_turnos(db_session) == 0


def test_con_listas_vacias_por_defecto_el_alta_funciona(
    caso_de_uso: CrearTurno, catalogo: Catalogo
) -> None:
    assert caso_de_uso.ejecutar(_solicitud(catalogo)).estado == "programado"


# --- 5.5 carrera que esquiva el pre-chequeo ----------------------------------------------


def test_carrera_que_esquiva_el_prechequeo_termina_en_solapamiento_de_sillon(
    db_session: Session, catalogo: Catalogo
) -> None:
    repositorio = RepositorioTurnos(db_session)
    caso = CrearTurno(repositorio, lambda: AHORA)
    caso.ejecutar(_solicitud(catalogo))
    # solo se sustituye la consulta del pre-chequeo; el INSERT y la exclusión son reales
    repositorio.buscar_conflictos = lambda *a, **k: set[Recurso]()  # type: ignore[method-assign]

    with pytest.raises(SolapamientoError) as excinfo:
        caso.ejecutar(_solicitud(catalogo, desde=15, prof=1, pac=1))

    assert excinfo.value.recursos == ("sillon",)
    assert _cantidad_turnos(db_session) == 1
