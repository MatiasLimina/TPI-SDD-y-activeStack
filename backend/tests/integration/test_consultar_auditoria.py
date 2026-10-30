"""Caso de uso ConsultarAuditoriaTurno contra PostgreSQL real."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.application.auditoria_turnos import ConsultarAuditoriaTurno
from app.domain.auditoria import AccionAuditoria
from app.domain.turnos import TurnoInexistenteError
from app.infrastructure.db.models import Turno, Usuario
from app.infrastructure.db.repositorio_auditoria import RepositorioAuditoria
from app.infrastructure.db.repositorio_turnos import RepositorioTurnos
from tests.integration.factories import Catalogo, crear_catalogo, crear_turno

OCURRIDO_EN = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)
NUEVOS = {"estado": "programado"}


@pytest.fixture
def catalogo(db_session: Session) -> Catalogo:
    return crear_catalogo(db_session)


@pytest.fixture
def turno(db_session: Session, catalogo: Catalogo) -> Turno:
    return crear_turno(db_session, catalogo)


def _caso(session: Session) -> ConsultarAuditoriaTurno:
    return ConsultarAuditoriaTurno(RepositorioTurnos(session), RepositorioAuditoria(session))


def test_ejecutar_devuelve_los_registros_del_turno_en_orden_de_insercion(
    db_session: Session, turno: Turno, recepcionista: Usuario
) -> None:
    repo = RepositorioAuditoria(db_session)
    previos = {"estado": "programado"}
    repo.registrar(turno.id, recepcionista.id, AccionAuditoria.CREAR, None, NUEVOS, OCURRIDO_EN)
    repo.registrar(
        turno.id,
        recepcionista.id,
        AccionAuditoria.CANCELAR,
        previos,
        {"estado": "cancelado"},
        OCURRIDO_EN,
    )

    registros = _caso(db_session).ejecutar(turno.id)

    assert [r.accion for r in registros] == ["crear", "cancelar"]
    assert registros[1].valores_previos == previos
    assert all(r.turno_id == turno.id for r in registros)


def test_ejecutar_solo_devuelve_los_registros_del_turno_pedido(
    db_session: Session, catalogo: Catalogo, turno: Turno, recepcionista: Usuario
) -> None:
    otro = crear_turno(db_session, catalogo, desplazamiento_min=120)
    repo = RepositorioAuditoria(db_session)
    repo.registrar(turno.id, recepcionista.id, AccionAuditoria.CREAR, None, NUEVOS, OCURRIDO_EN)
    repo.registrar(otro.id, recepcionista.id, AccionAuditoria.CREAR, None, NUEVOS, OCURRIDO_EN)

    assert len(_caso(db_session).ejecutar(turno.id)) == 1
    assert _caso(db_session).ejecutar(otro.id)[0].turno_id == otro.id


def test_ejecutar_con_turno_existente_sin_registros_devuelve_lista_vacia(
    db_session: Session, turno: Turno
) -> None:
    assert _caso(db_session).ejecutar(turno.id) == []


def test_ejecutar_con_turno_inexistente_lanza_turno_inexistente_error(
    db_session: Session, turno: Turno
) -> None:
    desconocido = uuid4()

    with pytest.raises(TurnoInexistenteError) as excinfo:
        _caso(db_session).ejecutar(desconocido)

    assert excinfo.value.turno_id == desconocido
