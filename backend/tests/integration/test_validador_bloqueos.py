"""ValidadorBloqueos (RN-AG-06) con bloqueos reales en PostgreSQL."""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy.orm import Session

from app.application.bloqueos_agenda import ValidadorBloqueos
from app.domain.bloqueos import MENSAJE_TURNO_EN_BLOQUEO
from app.domain.turnos import TurnoInvalidoError, TurnoPropuesto
from app.infrastructure.db.models import Bloqueo, Profesional, Usuario
from app.infrastructure.db.repositorio_bloqueos import RepositorioBloqueos


@pytest.fixture
def profesionales(db_session: Session) -> list[Profesional]:
    lista = [Profesional(nombre=n, apellido="Ficticio") for n in ("Ana", "Beto")]
    db_session.add_all(lista)
    db_session.flush()
    return lista


@pytest.fixture
def validador(db_session: Session) -> ValidadorBloqueos:
    return ValidadorBloqueos(RepositorioBloqueos(db_session))


def _h(hora: int, minuto: int = 0) -> datetime:
    """Instante UTC del jueves 2026-10-08 (10:00 local es 13:00Z)."""
    return datetime(2026, 10, 8, hora, minuto, tzinfo=UTC)


def _bloquear(
    db_session: Session, profesional: Profesional, autor: Usuario, inicio: datetime, fin: datetime
) -> None:
    db_session.add(
        Bloqueo(
            profesional_id=profesional.id,
            inicio=inicio,
            fin=fin,
            motivo="Congreso",
            creado_por=autor.id,
        )
    )
    db_session.flush()


def _propuesto(profesional_id: UUID, inicio: datetime, minutos: int = 45) -> TurnoPropuesto:
    return TurnoPropuesto(
        profesional_id=profesional_id,
        paciente_id=uuid4(),
        prestacion_id=uuid4(),
        sillon_id=None,
        inicio=inicio,
        fin=inicio + timedelta(minutes=minutos),
        duracion_min=minutos,
    )


@pytest.mark.parametrize(
    ("fin_bloqueo", "inicio", "minutos"),
    [
        (_h(15), _h(13, 30), 45),  # bloqueo 10:00-12:00; turno 10:30-11:15 local: adentro
        (_h(15), _h(12, 30), 45),  # 09:30-10:15: empieza antes y termina adentro
        (_h(15), _h(14, 30), 45),  # 11:30-12:15: empieza adentro y termina después
        (_h(13, 15), _h(12, 45), 60),  # bloqueo 10:00-10:15; turno 09:45-10:45: lo contiene
    ],
    ids=["adentro", "empieza-antes", "termina-despues", "contiene"],
)
def test_turno_que_se_superpone_con_un_bloqueo_lanza_turno_en_bloqueo_con_el_mensaje_del_spec(
    db_session: Session,
    profesionales: list[Profesional],
    recepcionista: Usuario,
    validador: ValidadorBloqueos,
    fin_bloqueo: datetime,
    inicio: datetime,
    minutos: int,
) -> None:
    _bloquear(db_session, profesionales[0], recepcionista, _h(13), fin_bloqueo)

    with pytest.raises(TurnoInvalidoError) as excinfo:
        validador(_propuesto(profesionales[0].id, inicio, minutos))

    assert excinfo.value.codigo == "turno_en_bloqueo"
    assert excinfo.value.mensaje == MENSAJE_TURNO_EN_BLOQUEO
    assert (
        MENSAJE_TURNO_EN_BLOQUEO == "el turno se superpone con un bloqueo de agenda del profesional"
    )


@pytest.mark.parametrize(
    "inicio",
    [_h(12, 15), _h(15)],  # 09:15-10:00 y 12:00-12:45 local: contiguos al bloqueo
    ids=["contiguo-antes", "contiguo-despues"],
)
def test_turno_contiguo_a_un_bloqueo_no_lanza(
    db_session: Session,
    profesionales: list[Profesional],
    recepcionista: Usuario,
    validador: ValidadorBloqueos,
    inicio: datetime,
) -> None:
    _bloquear(db_session, profesionales[0], recepcionista, _h(13), _h(15))

    validador(_propuesto(profesionales[0].id, inicio))


def test_bloqueo_de_otro_profesional_no_lanza(
    db_session: Session,
    profesionales: list[Profesional],
    recepcionista: Usuario,
    validador: ValidadorBloqueos,
) -> None:
    _bloquear(db_session, profesionales[1], recepcionista, _h(13), _h(15))

    validador(_propuesto(profesionales[0].id, _h(13, 30)))


def test_profesional_sin_bloqueos_no_lanza(
    profesionales: list[Profesional], validador: ValidadorBloqueos
) -> None:
    validador(_propuesto(profesionales[0].id, _h(13, 30)))
