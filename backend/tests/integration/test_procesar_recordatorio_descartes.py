"""El worker no envía si el turno está cancelado o el recordatorio ya no está pendiente."""

from datetime import datetime
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.domain.recordatorios import EstadoRecordatorio
from app.infrastructure.notifications.mock_sender import MockSender
from tests.fakes import ColaEnMemoria
from tests.integration.factories import Catalogo, crear_catalogo
from tests.integration.helpers_recordatorios import (
    BUENOS_AIRES,
    PROGRAMADO_PARA,
    armar_worker,
    caso_cancelar,
    caso_crear,
    crear_sin_programar,
    insertar_recordatorio,
    programador,
    recordatorios_de,
    solicitud,
)

AHORA_LOCAL = datetime(2026, 10, 7, 9, 0, tzinfo=BUENOS_AIRES)


@pytest.fixture
def catalogo(db_session: Session) -> Catalogo:
    return crear_catalogo(db_session)


def test_turno_cancelado_con_recordatorio_pendiente_no_envia_y_queda_cancelado(
    db_session: Session, catalogo: Catalogo
) -> None:
    turno = crear_sin_programar(db_session, catalogo)
    recordatorio_id = insertar_recordatorio(db_session, turno.id)
    db_session.execute(
        text("UPDATE turno SET estado = 'cancelado' WHERE id = :id"), {"id": turno.id}
    )
    cola, sender = ColaEnMemoria(), MockSender()
    cola.encolar(recordatorio_id, PROGRAMADO_PARA)

    armar_worker(db_session, cola, sender).ciclo(PROGRAMADO_PARA)

    assert sender.enviados == []
    (fila,) = recordatorios_de(db_session, turno.id)
    assert (fila["estado"], fila["intentos"]) == ("cancelado", 0)


def test_recordatorio_cancelado_que_seguia_en_la_cola_no_se_envia(
    db_session: Session, catalogo: Catalogo
) -> None:
    prog = programador(db_session, AHORA_LOCAL)
    turno = caso_crear(db_session, prog, AHORA_LOCAL).ejecutar(solicitud(catalogo))
    cola, sender = ColaEnMemoria(), MockSender()
    prog.publicar(cola)
    assert len(cola.elementos) == 1
    caso_cancelar(db_session, programador(db_session, AHORA_LOCAL), AHORA_LOCAL).ejecutar(
        turno.id, None
    )

    armar_worker(db_session, cola, sender).ciclo(PROGRAMADO_PARA)

    assert sender.enviados == []
    (fila,) = recordatorios_de(db_session, turno.id)
    assert (fila["estado"], fila["intentos"]) == ("cancelado", 0)
    assert cola.elementos == {}


def test_recordatorio_enviado_encolado_de_nuevo_no_se_envia_dos_veces(
    db_session: Session, catalogo: Catalogo
) -> None:
    turno = crear_sin_programar(db_session, catalogo)
    recordatorio_id = insertar_recordatorio(db_session, turno.id)
    cola, sender = ColaEnMemoria(), MockSender()
    worker = armar_worker(db_session, cola, sender)
    cola.encolar(recordatorio_id, PROGRAMADO_PARA)
    worker.ciclo(PROGRAMADO_PARA)

    cola.encolar(recordatorio_id, PROGRAMADO_PARA)
    worker.ciclo(PROGRAMADO_PARA)

    assert len(sender.enviados) == 1
    (fila,) = recordatorios_de(db_session, turno.id)
    assert (fila["estado"], fila["intentos"]) == ("enviado", 1)
    assert cola.elementos == {}


@pytest.mark.parametrize(
    ("estado", "intentos"),
    [(EstadoRecordatorio.CANCELADO, 0), (EstadoRecordatorio.FALLIDO, 3)],
)
def test_recordatorio_cancelado_o_fallido_encolado_no_se_envia_y_no_cambia(
    db_session: Session, catalogo: Catalogo, estado: EstadoRecordatorio, intentos: int
) -> None:
    turno = crear_sin_programar(db_session, catalogo)
    recordatorio_id = insertar_recordatorio(db_session, turno.id, estado=estado, intentos=intentos)
    cola, sender = ColaEnMemoria(), MockSender()
    cola.encolar(recordatorio_id, PROGRAMADO_PARA)

    armar_worker(db_session, cola, sender).ciclo(PROGRAMADO_PARA)

    assert sender.enviados == []
    (fila,) = recordatorios_de(db_session, turno.id)
    assert (fila["estado"], fila["intentos"]) == (estado.value, intentos)


def test_id_inexistente_se_descarta_y_el_resto_del_ciclo_se_procesa(
    db_session: Session, catalogo: Catalogo
) -> None:
    turno = crear_sin_programar(db_session, catalogo)
    recordatorio_id = insertar_recordatorio(db_session, turno.id)
    fantasma = uuid4()
    cola, sender = ColaEnMemoria(), MockSender()
    cola.encolar(fantasma, PROGRAMADO_PARA.replace(minute=0))
    cola.encolar(recordatorio_id, PROGRAMADO_PARA.replace(minute=1))

    procesados = armar_worker(db_session, cola, sender).ciclo(PROGRAMADO_PARA.replace(minute=5))

    assert procesados == 2
    assert [m.recordatorio_id for m in sender.enviados] == [recordatorio_id]
    (fila,) = recordatorios_de(db_session, turno.id)
    assert fila["estado"] == "enviado"
    assert cola.elementos == {}
