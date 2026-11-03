"""Garantía de la franja en PostgreSQL: escritura directa, sin pasar por la aplicación."""

from datetime import time

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.infrastructure.db.models import HorarioAtencion, Profesional

SQLSTATE_CHECK = "23514"
SQLSTATE_EXCLUSION = "23P01"


@pytest.fixture
def profesionales(db_session: Session) -> list[Profesional]:
    lista = [Profesional(nombre=n, apellido="Ficticio") for n in ("Ana", "Beto")]
    db_session.add_all(lista)
    db_session.flush()
    return lista


def _franja(profesional: Profesional, dia: int, inicio: time, fin: time) -> HorarioAtencion:
    return HorarioAtencion(
        profesional_id=profesional.id, dia_semana=dia, hora_inicio=inicio, hora_fin=fin
    )


def _insertar_rechazada(db_session: Session, franja: HorarioAtencion) -> str:
    with pytest.raises(IntegrityError) as excinfo, db_session.begin_nested():
        db_session.add(franja)
        db_session.flush()
    return str(getattr(excinfo.value.orig, "sqlstate", ""))


@pytest.mark.parametrize(
    ("dia", "inicio", "fin"),
    [
        (0, time(9, 0), time(9, 0)),
        (7, time(9, 0), time(13, 0)),
        (-1, time(9, 0), time(13, 0)),
        (0, time(9, 7), time(13, 0)),
        (0, time(9, 0), time(13, 0, 30)),
        (0, time(13, 0), time(9, 0)),
    ],
)
def test_la_base_rechaza_franjas_invalidas(
    db_session: Session, profesionales: list[Profesional], dia: int, inicio: time, fin: time
) -> None:
    sqlstate = _insertar_rechazada(db_session, _franja(profesionales[0], dia, inicio, fin))

    assert sqlstate == SQLSTATE_CHECK


@pytest.mark.parametrize(
    ("inicio", "fin"),
    [(time(12, 55), time(14, 0)), (time(10, 0), time(11, 0)), (time(8, 0), time(9, 5))],
)
def test_la_base_rechaza_franjas_superpuestas_del_mismo_profesional_y_dia(
    db_session: Session, profesionales: list[Profesional], inicio: time, fin: time
) -> None:
    db_session.add(_franja(profesionales[0], 0, time(9, 0), time(13, 0)))
    db_session.flush()

    sqlstate = _insertar_rechazada(db_session, _franja(profesionales[0], 0, inicio, fin))

    assert sqlstate == SQLSTATE_EXCLUSION


def test_la_base_acepta_contigua_otro_dia_y_otro_profesional(
    db_session: Session, profesionales: list[Profesional]
) -> None:
    ana, beto = profesionales
    db_session.add(_franja(ana, 0, time(9, 0), time(13, 0)))
    db_session.flush()

    db_session.add_all(
        [
            _franja(ana, 0, time(13, 0), time(17, 0)),
            _franja(ana, 1, time(9, 0), time(13, 0)),
            _franja(beto, 0, time(9, 0), time(13, 0)),
        ]
    )
    db_session.flush()

    total = db_session.scalar(select(func.count()).select_from(HorarioAtencion))
    assert total == 4


def test_borrar_el_profesional_borra_sus_franjas(
    db_session: Session, profesionales: list[Profesional]
) -> None:
    ana, beto = profesionales
    db_session.add_all(
        [_franja(ana, 0, time(9, 0), time(13, 0)), _franja(beto, 0, time(9, 0), time(13, 0))]
    )
    db_session.flush()

    db_session.delete(ana)
    db_session.flush()

    quedan = db_session.scalars(select(HorarioAtencion.profesional_id)).all()
    assert quedan == [beto.id]
