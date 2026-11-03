"""Fixtures de concurrencia compartidas: motor con pool propio y catálogo commiteado."""

from collections.abc import Iterator

import pytest
from sqlalchemy import Engine, create_engine, delete, select
from sqlalchemy.orm import Session

from app.infrastructure.db.models import (
    Paciente,
    Prestacion,
    Profesional,
    Recordatorio,
    Sillon,
    Turno,
)
from tests.conftest import get_test_database_url
from tests.integration.factories import Catalogo, crear_catalogo

POOL_CONCURRENTE = 12


@pytest.fixture
def motor_concurrente(engine: Engine) -> Iterator[Engine]:
    motor = create_engine(get_test_database_url(), pool_size=POOL_CONCURRENTE)
    yield motor
    motor.dispose()


def _catalogo_commiteado(motor: Engine, *, con_horario: bool) -> Iterator[Catalogo]:
    """Catálogo ficticio único, commiteado en su propia conexión y borrado al final."""
    with Session(motor) as sesion:
        catalogo = crear_catalogo(sesion, con_horario=con_horario)
        sesion.commit()
        ids = {
            Profesional: [p.id for p in catalogo.profesionales],
            Sillon: [s.id for s in catalogo.sillones],
            Paciente: [p.id for p in catalogo.pacientes],
            Prestacion: [catalogo.limpieza.id, catalogo.consulta.id],
        }
    try:
        yield catalogo
    finally:
        with Session(motor) as sesion:
            # Los recordatorios van primero: su FK RESTRICT impide borrar los turnos
            turnos = select(Turno.id).where(Turno.profesional_id.in_(ids[Profesional]))
            sesion.execute(delete(Recordatorio).where(Recordatorio.turno_id.in_(turnos)))
            sesion.execute(delete(Turno).where(Turno.profesional_id.in_(ids[Profesional])))
            for modelo in (Prestacion, Paciente, Sillon, Profesional):
                sesion.execute(delete(modelo).where(modelo.id.in_(ids[modelo])))
            sesion.commit()


@pytest.fixture
def catalogo_commiteado(motor_concurrente: Engine) -> Iterator[Catalogo]:
    """Catálogo commiteado con horario amplio (las franjas se borran en cascada)."""
    yield from _catalogo_commiteado(motor_concurrente, con_horario=True)


@pytest.fixture
def catalogo_commiteado_sin_horario(motor_concurrente: Engine) -> Iterator[Catalogo]:
    """Catálogo commiteado sin franjas, para los tests que cargan las suyas."""
    yield from _catalogo_commiteado(motor_concurrente, con_horario=False)
