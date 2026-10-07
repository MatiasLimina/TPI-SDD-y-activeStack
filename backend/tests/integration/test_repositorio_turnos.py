from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import event, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.turnos import (
    Intervalo,
    Recurso,
    ReferenciaInvalidaError,
    SolapamientoError,
    TurnoPropuesto,
)
from app.infrastructure.db.models import Turno
from app.infrastructure.db.repositorio_turnos import RepositorioTurnos
from tests.integration.factories import Catalogo, crear_catalogo


@pytest.fixture
def catalogo(db_session: Session) -> Catalogo:
    return crear_catalogo(db_session)


# --- 4.1 carga de referencias ------------------------------------------------------------


def test_cargar_referencias_devuelve_las_entidades_por_id(
    db_session: Session, catalogo: Catalogo
) -> None:
    repo = RepositorioTurnos(db_session)

    refs = repo.cargar_referencias(
        profesional_id=catalogo.profesionales[0].id,
        paciente_id=catalogo.pacientes[0].id,
        prestacion_id=catalogo.limpieza.id,
        sillon_id=catalogo.sillones[0].id,
    )

    assert refs.profesional is catalogo.profesionales[0]
    assert refs.paciente is catalogo.pacientes[0]
    assert refs.prestacion is catalogo.limpieza
    assert refs.sillon is catalogo.sillones[0]


def test_cargar_referencias_sin_sillon_devuelve_none(
    db_session: Session, catalogo: Catalogo
) -> None:
    refs = RepositorioTurnos(db_session).cargar_referencias(
        profesional_id=catalogo.profesionales[0].id,
        paciente_id=catalogo.pacientes[0].id,
        prestacion_id=catalogo.consulta.id,
        sillon_id=None,
    )

    assert refs.sillon is None


@pytest.mark.parametrize("referencia", ["profesional", "paciente", "prestacion", "sillon"])
def test_referencia_inexistente_lanza_error_con_el_nombre_de_la_referencia(
    db_session: Session, catalogo: Catalogo, referencia: str
) -> None:
    ids = {
        "profesional": catalogo.profesionales[0].id,
        "paciente": catalogo.pacientes[0].id,
        "prestacion": catalogo.limpieza.id,
        "sillon": catalogo.sillones[0].id,
    }
    ids[referencia] = uuid4()

    with pytest.raises(ReferenciaInvalidaError) as excinfo:
        RepositorioTurnos(db_session).cargar_referencias(
            profesional_id=ids["profesional"],
            paciente_id=ids["paciente"],
            prestacion_id=ids["prestacion"],
            sillon_id=ids["sillon"],
        )

    assert (excinfo.value.referencia, excinfo.value.motivo) == (referencia, "inexistente")


@pytest.mark.parametrize(
    ("referencia", "desactivar"),
    [
        ("profesional", lambda c: setattr(c.profesionales[0], "activo", False)),
        ("paciente", lambda c: setattr(c.pacientes[0], "activo", False)),
        ("prestacion", lambda c: setattr(c.limpieza, "activa", False)),
        ("sillon", lambda c: setattr(c.sillones[0], "activo", False)),
    ],
)
def test_referencia_inactiva_lanza_error_inactiva(
    db_session: Session,
    catalogo: Catalogo,
    referencia: str,
    desactivar: Callable[[Catalogo], None],
) -> None:
    desactivar(catalogo)
    db_session.flush()

    with pytest.raises(ReferenciaInvalidaError) as excinfo:
        RepositorioTurnos(db_session).cargar_referencias(
            profesional_id=catalogo.profesionales[0].id,
            paciente_id=catalogo.pacientes[0].id,
            prestacion_id=catalogo.limpieza.id,
            sillon_id=catalogo.sillones[0].id,
        )

    assert (excinfo.value.referencia, excinfo.value.motivo) == (referencia, "inactiva")


# --- 4.2 pre-chequeo de conflictos -------------------------------------------------------

BASE = datetime(2026, 10, 8, 13, 0, tzinfo=UTC)  # 10:00 hora local


def _iv(desde: int, minutos: int) -> Intervalo:
    inicio = BASE + timedelta(minutes=desde)
    return Intervalo(inicio, inicio + timedelta(minutes=minutos))


def _existente(
    session: Session,
    c: Catalogo,
    *,
    prof: int = 0,
    sillon: int | None = 0,
    pac: int = 0,
    estado: str = "programado",
) -> None:
    iv = _iv(0, 45)
    session.add(
        Turno(
            profesional_id=c.profesionales[prof].id,
            sillon_id=None if sillon is None else c.sillones[sillon].id,
            paciente_id=c.pacientes[pac].id,
            prestacion_id=c.limpieza.id,
            inicio=iv.inicio,
            fin=iv.fin,
            duracion_min=45,
            estado=estado,
        )
    )
    session.flush()


def _conflictos(
    session: Session,
    c: Catalogo,
    intervalo: Intervalo,
    *,
    prof: int = 0,
    sillon: int | None = 0,
    pac: int = 0,
) -> set[Recurso]:
    return RepositorioTurnos(session).buscar_conflictos(
        intervalo,
        profesional_id=c.profesionales[prof].id,
        sillon_id=None if sillon is None else c.sillones[sillon].id,
        paciente_id=c.pacientes[pac].id,
    )


@pytest.mark.parametrize(
    ("variacion", "esperado"),
    [
        ({"sillon": 1, "pac": 1}, {"profesional"}),
        ({"prof": 1, "pac": 1}, {"sillon"}),
        ({"prof": 1, "sillon": 1}, {"paciente"}),
        ({}, {"profesional", "sillon", "paciente"}),
        ({"prof": 1, "sillon": 1, "pac": 1}, set()),
    ],
)
def test_buscar_conflictos_devuelve_los_recursos_compartidos(
    db_session: Session, catalogo: Catalogo, variacion: dict[str, int], esperado: set[str]
) -> None:
    _existente(db_session, catalogo)

    assert _conflictos(db_session, catalogo, _iv(15, 45), **variacion) == esperado


def test_buscar_conflictos_ignora_turnos_contiguos(db_session: Session, catalogo: Catalogo) -> None:
    _existente(db_session, catalogo)

    assert _conflictos(db_session, catalogo, _iv(45, 30)) == set()


def test_buscar_conflictos_ignora_turnos_cancelados(
    db_session: Session, catalogo: Catalogo
) -> None:
    _existente(db_session, catalogo, estado="cancelado")

    assert _conflictos(db_session, catalogo, _iv(15, 45)) == set()


def test_buscar_conflictos_sin_sillon_no_consulta_por_sillon(
    db_session: Session, catalogo: Catalogo
) -> None:
    _existente(db_session, catalogo, sillon=None)  # existente sin sillón, mismo profesional

    assert _conflictos(db_session, catalogo, _iv(15, 30), prof=1, sillon=None, pac=1) == set()
    assert _conflictos(db_session, catalogo, _iv(15, 30), sillon=None, pac=1) == {"profesional"}


def test_buscar_conflictos_ejecuta_una_sola_consulta(
    db_session: Session, catalogo: Catalogo
) -> None:
    _existente(db_session, catalogo)
    sentencias: list[str] = []
    conexion = db_session.get_bind()
    escuchar = lambda conn, cursor, statement, *a: sentencias.append(statement)  # noqa: E731
    event.listen(conexion, "before_cursor_execute", escuchar)
    try:
        _conflictos(db_session, catalogo, _iv(15, 45))
    finally:
        event.remove(conexion, "before_cursor_execute", escuchar)

    assert len(sentencias) == 1


# --- 4.3 insertar y traducción de 23P01 ---------------------------------------------------


def _propuesto(
    c: Catalogo,
    *,
    prof: int = 0,
    sillon: int | None = 0,
    pac: int = 0,
    desde: int = 0,
    minutos: int = 45,
) -> TurnoPropuesto:
    iv = _iv(desde, minutos)
    return TurnoPropuesto(
        profesional_id=c.profesionales[prof].id,
        paciente_id=c.pacientes[pac].id,
        prestacion_id=c.limpieza.id,
        sillon_id=None if sillon is None else c.sillones[sillon].id,
        inicio=iv.inicio,
        fin=iv.fin,
        duracion_min=minutos,
    )


def test_insertar_persiste_en_utc_y_devuelve_turno_creado(
    db_session: Session, catalogo: Catalogo
) -> None:
    propuesto = _propuesto(catalogo)

    creado = RepositorioTurnos(db_session).insertar(propuesto)

    fila = db_session.get(Turno, creado.id)
    assert fila is not None
    assert fila.inicio == propuesto.inicio
    assert fila.inicio.utcoffset() == timedelta(0)
    assert (creado.estado, creado.creado_por) == ("programado", None)
    assert creado.fin == propuesto.fin


@pytest.mark.parametrize(
    ("variacion", "recurso"),
    [
        ({"sillon": 1, "pac": 1}, "profesional"),
        ({"prof": 1, "pac": 1}, "sillon"),
        ({"prof": 1, "sillon": 1}, "paciente"),
    ],
)
def test_insertar_traduce_la_exclusion_al_recurso_en_conflicto(
    db_session: Session, catalogo: Catalogo, variacion: dict[str, int], recurso: str
) -> None:
    repo = RepositorioTurnos(db_session)
    repo.insertar(_propuesto(catalogo))

    with pytest.raises(SolapamientoError) as excinfo:
        repo.insertar(_propuesto(catalogo, desde=15, minutos=30, **variacion))

    assert excinfo.value.recursos == (recurso,)
    cantidad = db_session.scalar(select(func.count()).select_from(Turno))
    assert cantidad == 1


def test_insertar_relanza_otras_violaciones_de_integridad(
    db_session: Session, catalogo: Catalogo
) -> None:
    propuesto = _propuesto(catalogo)
    invalido = TurnoPropuesto(**{**propuesto.__dict__, "fin": propuesto.inicio})

    with pytest.raises(IntegrityError):
        RepositorioTurnos(db_session).insertar(invalido)
