"""D12: el bloqueo del profesional choca con FOR SHARE y deja pasar FOR KEY SHARE."""

import pytest
from psycopg.errors import LockNotAvailable
from sqlalchemy import Engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.infrastructure.db.repositorio_horarios import RepositorioHorarios
from tests.integration.factories import Catalogo


def _bloquear_en_otra_conexion(motor: Engine, modo: str, profesional_id: object) -> None:
    with motor.connect() as conexion:
        conexion.execute(
            text(f"SELECT id FROM profesional WHERE id = :id {modo} NOWAIT"),
            {"id": profesional_id},
        )


def test_bloquear_profesional_choca_con_for_share_de_otra_conexion(
    motor_concurrente: Engine, catalogo_commiteado: Catalogo
) -> None:
    profesional = catalogo_commiteado.profesionales[0]
    with Session(motor_concurrente) as sesion:
        assert RepositorioHorarios(sesion).bloquear_profesional(profesional.id) is not None

        # FOR SHARE es lo que toma `cargar_referencias` al crear o reprogramar un turno
        with pytest.raises(OperationalError) as excinfo:
            _bloquear_en_otra_conexion(motor_concurrente, "FOR SHARE", profesional.id)

        assert isinstance(excinfo.value.orig, LockNotAvailable)


def test_bloquear_profesional_no_bloquea_for_key_share_de_las_fks_de_turno(
    motor_concurrente: Engine, catalogo_commiteado: Catalogo
) -> None:
    profesional = catalogo_commiteado.profesionales[0]
    with Session(motor_concurrente) as sesion:
        RepositorioHorarios(sesion).bloquear_profesional(profesional.id)

        _bloquear_en_otra_conexion(motor_concurrente, "FOR KEY SHARE", profesional.id)


def test_sin_bloquear_for_share_no_espera(
    motor_concurrente: Engine, catalogo_commiteado: Catalogo
) -> None:
    """Control: sin el bloqueo previo, el mismo FOR SHARE NOWAIT pasa."""
    _bloquear_en_otra_conexion(
        motor_concurrente, "FOR SHARE", catalogo_commiteado.profesionales[0].id
    )
