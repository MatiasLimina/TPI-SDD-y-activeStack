"""Un error a mitad de lote devuelve a la cola lo tomado y no procesado (crash-only)."""

import logging
from datetime import UTC, datetime
from uuid import UUID

import pytest
import redis
from sqlalchemy import text
from sqlalchemy.orm import Session

from tests.fakes import ColaQueRechazaEncolado, EmisorQueFallaCon, RelojManual
from tests.integration.factories import Catalogo, crear_catalogo
from tests.integration.helpers_recordatorios import (
    armar_worker,
    ciclo_a,
    crear_sin_programar,
    insertar_recordatorio,
)

AHORA = datetime(2026, 10, 8, 13, 5, tzinfo=UTC)
VENCE_R1 = datetime(2026, 10, 8, 13, 0, tzinfo=UTC)
VENCE_R2 = datetime(2026, 10, 8, 13, 1, tzinfo=UTC)
VENCE_R3 = datetime(2026, 10, 8, 13, 2, tzinfo=UTC)
REINTENTO_R2 = datetime(2026, 10, 8, 13, 6, tzinfo=UTC)
# Un solo paciente y un solo profesional: los tres turnos van uno tras otro, sin solaparse
INICIOS = [datetime(2026, 10, 9, hora, 0, tzinfo=UTC) for hora in (13, 14, 15)]


@pytest.fixture
def catalogo(db_session: Session) -> Catalogo:
    return crear_catalogo(db_session)


def _tres_recordatorios(
    session: Session, catalogo: Catalogo, cola: ColaQueRechazaEncolado
) -> tuple[UUID, UUID, UUID]:
    """R1, R2 y R3 pendientes de turnos programados, ya en la cola (sin pasar por `encolar`)."""
    ids: list[UUID] = []
    for inicio, vence in zip(INICIOS, (VENCE_R1, VENCE_R2, VENCE_R3), strict=True):
        turno = crear_sin_programar(session, catalogo, inicio)
        recordatorio_id = insertar_recordatorio(session, turno.id, programado_para=vence)
        cola.elementos[recordatorio_id] = vence
        ids.append(recordatorio_id)
    return ids[0], ids[1], ids[2]


def _estado(session: Session, recordatorio_id: UUID) -> tuple[str, int, datetime]:
    fila = session.execute(
        text("SELECT estado, intentos, programado_para FROM recordatorio WHERE id = :id"),
        {"id": recordatorio_id},
    ).one()
    return fila.estado, fila.intentos, fila.programado_para


def test_error_a_mitad_de_lote_devuelve_a_la_cola_lo_no_procesado_y_relanza(
    db_session: Session, catalogo: Catalogo
) -> None:
    reloj = RelojManual(AHORA)
    cola = ColaQueRechazaEncolado()
    r1, r2, r3 = _tres_recordatorios(db_session, catalogo, cola)
    cola.rechaza_ids = {r2}
    worker = armar_worker(db_session, cola, EmisorQueFallaCon({r2}), reloj)

    with pytest.raises(redis.exceptions.ConnectionError) as excinfo:
        ciclo_a(worker, reloj, AHORA)

    assert str(r2) in str(excinfo.value)
    assert _estado(db_session, r1)[:2] == ("enviado", 1)
    assert _estado(db_session, r2) == ("pendiente", 1, REINTENTO_R2)
    assert _estado(db_session, r3) == ("pendiente", 0, VENCE_R3)
    assert cola.elementos == {r3: AHORA}


def test_si_la_devolucion_tambien_falla_se_propaga_el_error_original_y_se_advierte(
    db_session: Session, catalogo: Catalogo, caplog: pytest.LogCaptureFixture
) -> None:
    reloj = RelojManual(AHORA)
    cola = ColaQueRechazaEncolado()
    r1, r2, r3 = _tres_recordatorios(db_session, catalogo, cola)
    cola.rechaza_todo_desde = r2
    worker = armar_worker(db_session, cola, EmisorQueFallaCon({r2}), reloj)

    with caplog.at_level(logging.WARNING, logger="app.application.recordatorios"):
        with pytest.raises(redis.exceptions.ConnectionError) as excinfo:
            ciclo_a(worker, reloj, AHORA)

    assert str(r2) in str(excinfo.value)
    assert str(r3) not in str(excinfo.value)
    advertencias = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert any("devol" in mensaje for mensaje in advertencias)
    assert all(str(catalogo.pacientes[0].id) not in mensaje for mensaje in advertencias)
    assert _estado(db_session, r3) == ("pendiente", 0, VENCE_R3)
    assert cola.elementos == {}

    cola.reabrir()
    armar_worker(db_session, cola, EmisorQueFallaCon(set()), reloj).iniciar()

    assert cola.elementos == {r2: REINTENTO_R2, r3: VENCE_R3}
    assert r1 not in cola.elementos
