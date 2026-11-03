"""ValidadorHorario (RN-AG-05) con franjas reales en PostgreSQL."""

from datetime import UTC, datetime, time, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy.orm import Session

from app.application.horarios_atencion import ValidadorHorario
from app.domain.horarios import MENSAJE_FUERA_DE_HORARIO
from app.domain.turnos import TurnoInvalidoError, TurnoPropuesto
from app.infrastructure.db.models import HorarioAtencion, Profesional
from app.infrastructure.db.repositorio_horarios import RepositorioHorarios

JUEVES = 3


@pytest.fixture
def profesional(db_session: Session) -> Profesional:
    profesional = Profesional(nombre="Ana", apellido="Ficticia")
    db_session.add(profesional)
    db_session.flush()
    return profesional


@pytest.fixture
def validador(db_session: Session) -> ValidadorHorario:
    return ValidadorHorario(RepositorioHorarios(db_session))


def _franja(db_session: Session, p: Profesional, dia: int, inicio: time, fin: time) -> None:
    db_session.add(
        HorarioAtencion(profesional_id=p.id, dia_semana=dia, hora_inicio=inicio, hora_fin=fin)
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


def test_turno_dentro_de_la_franja_no_lanza(
    db_session: Session, profesional: Profesional, validador: ValidadorHorario
) -> None:
    _franja(db_session, profesional, JUEVES, time(9, 0), time(13, 0))

    validador(_propuesto(profesional.id, datetime(2026, 10, 8, 13, 0, tzinfo=UTC)))  # 10:00 local


@pytest.mark.parametrize(
    "inicio",
    [
        datetime(2026, 10, 8, 15, 30, tzinfo=UTC),  # 12:30-13:15 local: excede
        datetime(2026, 10, 8, 11, 30, tzinfo=UTC),  # 08:30 local: antes de abrir
        datetime(2026, 10, 10, 13, 0, tzinfo=UTC),  # sábado: sin franjas ese día
    ],
)
def test_turno_fuera_de_la_franja_lanza_fuera_de_horario_con_el_mensaje_del_spec(
    db_session: Session, profesional: Profesional, validador: ValidadorHorario, inicio: datetime
) -> None:
    _franja(db_session, profesional, JUEVES, time(9, 0), time(13, 0))

    with pytest.raises(TurnoInvalidoError) as excinfo:
        validador(_propuesto(profesional.id, inicio))

    assert excinfo.value.codigo == "fuera_de_horario"
    assert excinfo.value.mensaje == MENSAJE_FUERA_DE_HORARIO
    assert MENSAJE_FUERA_DE_HORARIO == "el turno no cabe en el horario de atención del profesional"


def test_profesional_sin_franjas_lanza_fuera_de_horario(
    profesional: Profesional, validador: ValidadorHorario
) -> None:
    with pytest.raises(TurnoInvalidoError) as excinfo:
        validador(_propuesto(profesional.id, datetime(2026, 10, 8, 13, 0, tzinfo=UTC)))

    assert excinfo.value.codigo == "fuera_de_horario"


def test_lee_las_franjas_del_dia_local_del_inicio_no_del_dia_utc(
    db_session: Session, profesional: Profesional, validador: ValidadorHorario
) -> None:
    # 2026-10-09T01:00Z es el jueves 22:00 local (viernes en UTC)
    _franja(db_session, profesional, JUEVES, time(21, 0), time(23, 0))
    inicio = datetime(2026, 10, 9, 1, 0, tzinfo=UTC)

    validador(_propuesto(profesional.id, inicio))

    # La franja del viernes (día UTC) no habilita el turno: se busca por día local
    otra = Profesional(nombre="Beto", apellido="Ficticio")
    db_session.add(otra)
    db_session.flush()
    _franja(db_session, otra, 4, time(0, 0), time(23, 55))
    with pytest.raises(TurnoInvalidoError):
        validador(_propuesto(otra.id, inicio))
