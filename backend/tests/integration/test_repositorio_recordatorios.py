"""RepositorioRecordatorios contra PostgreSQL real."""

import uuid
from datetime import UTC, datetime, timedelta, timezone

import pytest
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.domain.recordatorios import EstadoRecordatorio
from app.infrastructure.db.models import Recordatorio, Turno
from app.infrastructure.db.repositorio_recordatorios import RepositorioRecordatorios
from tests.integration.factories import Catalogo, crear_catalogo, crear_turno

PROGRAMADO = datetime(2026, 10, 7, 13, 0, tzinfo=UTC)


@pytest.fixture
def catalogo(db_session: Session) -> Catalogo:
    return crear_catalogo(db_session)


@pytest.fixture
def turno(db_session: Session, catalogo: Catalogo) -> Turno:
    return crear_turno(db_session, catalogo)


@pytest.fixture
def repositorio(db_session: Session) -> RepositorioRecordatorios:
    return RepositorioRecordatorios(db_session)


def _leer(session: Session, recordatorio_id: uuid.UUID) -> Recordatorio:
    return session.execute(
        select(Recordatorio)
        .where(Recordatorio.id == recordatorio_id)
        .execution_options(populate_existing=True)
    ).scalar_one()


def test_crear_pendiente_persists_with_flush_and_returns_id(
    db_session: Session, repositorio: RepositorioRecordatorios, turno: Turno
) -> None:
    recordatorio_id = repositorio.crear_pendiente(turno.id, PROGRAMADO, "mock")

    # `connection()` no hace autoflush: la fila ya está en la base sin commit
    fila = (
        db_session.connection()
        .execute(
            text("SELECT turno_id, estado, canal, intentos FROM recordatorio WHERE id = :id"),
            {"id": recordatorio_id},
        )
        .one()
    )
    assert tuple(fila) == (turno.id, "pendiente", "mock", 0)
    assert len(db_session.new) == 0


def test_crear_pendiente_stores_programado_para_in_utc(
    db_session: Session, repositorio: RepositorioRecordatorios, turno: Turno
) -> None:
    local = datetime(2026, 10, 8, 10, 0, tzinfo=timezone(timedelta(hours=-3)))

    recordatorio_id = repositorio.crear_pendiente(turno.id, local, "mock")

    assert _leer(db_session, recordatorio_id).programado_para == datetime(
        2026, 10, 8, 13, 0, tzinfo=UTC
    )


def test_cancelar_pendiente_only_touches_the_pending_of_that_turno(
    db_session: Session, repositorio: RepositorioRecordatorios, catalogo: Catalogo, turno: Turno
) -> None:
    otro = crear_turno(db_session, catalogo, desplazamiento_min=120)
    pendiente = repositorio.crear_pendiente(turno.id, PROGRAMADO, "mock")
    pendiente_ajeno = repositorio.crear_pendiente(otro.id, PROGRAMADO, "mock")
    db_session.add_all(
        [
            Recordatorio(
                turno_id=turno.id,
                programado_para=PROGRAMADO,
                canal="mock",
                estado="enviado",
                intentos=1,
            ),
            Recordatorio(
                turno_id=turno.id,
                programado_para=PROGRAMADO,
                canal="mock",
                estado="fallido",
                intentos=3,
            ),
        ]
    )
    db_session.flush()

    repositorio.cancelar_pendiente(turno.id)

    assert _leer(db_session, pendiente).estado == "cancelado"
    assert _leer(db_session, pendiente_ajeno).estado == "pendiente"
    estados = db_session.execute(
        select(Recordatorio.estado).where(Recordatorio.turno_id == turno.id)
    ).scalars()
    assert sorted(estados) == ["cancelado", "enviado", "fallido"]


def test_cancelar_pendiente_keeps_programado_para_and_intentos(
    db_session: Session, repositorio: RepositorioRecordatorios, turno: Turno
) -> None:
    recordatorio_id = repositorio.crear_pendiente(turno.id, PROGRAMADO, "mock")

    repositorio.cancelar_pendiente(turno.id)

    cancelado = _leer(db_session, recordatorio_id)
    assert (cancelado.programado_para, cancelado.intentos) == (PROGRAMADO, 0)


def test_cancelar_pendiente_without_reminder_does_nothing(
    repositorio: RepositorioRecordatorios, turno: Turno
) -> None:
    assert repositorio.cancelar_pendiente(turno.id) is False


def test_listar_pendientes_returns_only_pending_ordered_with_utc_instants(
    db_session: Session, repositorio: RepositorioRecordatorios, catalogo: Catalogo, turno: Turno
) -> None:
    otro = crear_turno(db_session, catalogo, desplazamiento_min=120)
    tardio = repositorio.crear_pendiente(otro.id, PROGRAMADO + timedelta(days=1), "mock")
    temprano = repositorio.crear_pendiente(turno.id, PROGRAMADO, "mock")
    db_session.add(
        Recordatorio(
            turno_id=turno.id, programado_para=PROGRAMADO, canal="mock", estado="cancelado"
        )
    )
    db_session.flush()

    pendientes = repositorio.listar_pendientes()

    assert [(p.id, p.programado_para) for p in pendientes] == [
        (temprano, PROGRAMADO),
        (tardio, PROGRAMADO + timedelta(days=1)),
    ]
    assert all(p.programado_para.utcoffset() == timedelta(0) for p in pendientes)
    assert all(p.estado is EstadoRecordatorio.PENDIENTE for p in pendientes)


def test_listar_pendientes_without_pending_returns_empty(
    repositorio: RepositorioRecordatorios,
) -> None:
    assert repositorio.listar_pendientes() == []


def test_bloquear_para_envio_returns_reminder_and_turno_data(
    db_session: Session, repositorio: RepositorioRecordatorios, catalogo: Catalogo, turno: Turno
) -> None:
    recordatorio_id = repositorio.crear_pendiente(turno.id, PROGRAMADO, "mock")

    para_envio = repositorio.bloquear_para_envio(recordatorio_id)

    assert para_envio is not None
    assert para_envio.recordatorio.id == recordatorio_id
    assert para_envio.recordatorio.estado is EstadoRecordatorio.PENDIENTE
    assert para_envio.recordatorio.intentos == 0
    assert para_envio.recordatorio.programado_para == PROGRAMADO
    assert para_envio.turno_estado == "programado"
    assert para_envio.paciente_id == catalogo.pacientes[0].id
    assert para_envio.inicio == turno.inicio


def test_bloquear_para_envio_reports_cancelled_turno_state(
    db_session: Session, repositorio: RepositorioRecordatorios, turno: Turno
) -> None:
    recordatorio_id = repositorio.crear_pendiente(turno.id, PROGRAMADO, "mock")
    db_session.execute(
        text("UPDATE turno SET estado = 'cancelado' WHERE id = :id"), {"id": turno.id}
    )

    para_envio = repositorio.bloquear_para_envio(recordatorio_id)

    assert para_envio is not None
    assert para_envio.turno_estado == "cancelado"


def test_bloquear_para_envio_returns_none_for_unknown_id(
    repositorio: RepositorioRecordatorios,
) -> None:
    assert repositorio.bloquear_para_envio(uuid.uuid4()) is None


@pytest.mark.parametrize("intentos_previos", [0, 1, 2])
def test_marcar_enviado_adds_one_attempt_and_sets_enviado(
    db_session: Session,
    repositorio: RepositorioRecordatorios,
    turno: Turno,
    intentos_previos: int,
) -> None:
    recordatorio_id = repositorio.crear_pendiente(turno.id, PROGRAMADO, "mock")
    db_session.execute(
        text("UPDATE recordatorio SET intentos = :n WHERE id = :id"),
        {"n": intentos_previos, "id": recordatorio_id},
    )

    repositorio.marcar_enviado(recordatorio_id)

    enviado = _leer(db_session, recordatorio_id)
    assert (enviado.estado, enviado.intentos) == ("enviado", intentos_previos + 1)


def test_registrar_fallo_adds_attempts_and_becomes_fallido_on_the_third(
    db_session: Session, repositorio: RepositorioRecordatorios, turno: Turno
) -> None:
    recordatorio_id = repositorio.crear_pendiente(turno.id, PROGRAMADO, "mock")

    primero = repositorio.registrar_fallo(recordatorio_id)
    segundo = repositorio.registrar_fallo(recordatorio_id)
    tercero = repositorio.registrar_fallo(recordatorio_id)

    assert [(r.estado, r.intentos) for r in (primero, segundo, tercero)] == [
        (EstadoRecordatorio.PENDIENTE, 1),
        (EstadoRecordatorio.PENDIENTE, 2),
        (EstadoRecordatorio.FALLIDO, 3),
    ]
    persistido = _leer(db_session, recordatorio_id)
    assert (persistido.estado, persistido.intentos) == ("fallido", 3)


def test_marcar_cancelado_sets_cancelado_without_adding_attempts(
    db_session: Session, repositorio: RepositorioRecordatorios, turno: Turno
) -> None:
    recordatorio_id = repositorio.crear_pendiente(turno.id, PROGRAMADO, "mock")
    repositorio.registrar_fallo(recordatorio_id)

    repositorio.marcar_cancelado(recordatorio_id)

    cancelado = _leer(db_session, recordatorio_id)
    assert (cancelado.estado, cancelado.intentos) == ("cancelado", 1)
