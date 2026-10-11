"""Fixtures de concurrencia compartidas: motor con pool propio y catálogo commiteado."""

from collections.abc import Iterator

import pytest
from sqlalchemy import Engine, create_engine, delete
from sqlalchemy.orm import Session

from app.infrastructure.db.models import Paciente, Prestacion, Profesional, Sillon, Turno
from tests.conftest import get_test_database_url
from tests.integration.factories import Catalogo, crear_catalogo

POOL_CONCURRENTE = 12


@pytest.fixture
def motor_concurrente(engine: Engine) -> Iterator[Engine]:
    motor = create_engine(get_test_database_url(), pool_size=POOL_CONCURRENTE)
    yield motor
    motor.dispose()


@pytest.fixture
def catalogo_commiteado(motor_concurrente: Engine) -> Iterator[Catalogo]:
    """Catálogo ficticio único, commiteado en su propia conexión y borrado al final."""
    with Session(motor_concurrente) as sesion:
        catalogo = crear_catalogo(sesion)
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
        with Session(motor_concurrente) as sesion:
            sesion.execute(delete(Turno).where(Turno.profesional_id.in_(ids[Profesional])))
            for modelo in (Prestacion, Paciente, Sillon, Profesional):
                sesion.execute(delete(modelo).where(modelo.id.in_(ids[modelo])))
            sesion.commit()
