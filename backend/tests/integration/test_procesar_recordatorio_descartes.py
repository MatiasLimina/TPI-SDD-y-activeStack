"""El worker no envía si el turno está cancelado o el recordatorio ya no está pendiente."""

import logging
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.domain.recordatorios import EstadoRecordatorio
from tests.fakes import ColaEnMemoria, EmisorQueRegistra, RelojManual
from tests.integration.factories import Catalogo, crear_catalogo
from tests.integration.helpers_recordatorios import (
    BUENOS_AIRES,
    PROGRAMADO_PARA,
    armar_worker,
    caso_cancelar,
    caso_crear,
    ciclo_a,
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
    reloj = RelojManual(PROGRAMADO_PARA)
    turno = crear_sin_programar(db_session, catalogo)
    recordatorio_id = insertar_recordatorio(db_session, turno.id)
    db_session.execute(
        text("UPDATE turno SET estado = 'cancelado' WHERE id = :id"), {"id": turno.id}
    )
    cola, sender = ColaEnMemoria(), EmisorQueRegistra()
    cola.encolar(recordatorio_id, PROGRAMADO_PARA)

    ciclo_a(armar_worker(db_session, cola, sender, reloj), reloj, PROGRAMADO_PARA)

    assert sender.enviados == []
    (fila,) = recordatorios_de(db_session, turno.id)
    assert (fila["estado"], fila["intentos"]) == ("cancelado", 0)


def test_recordatorio_cancelado_que_seguia_en_la_cola_no_se_envia(
    db_session: Session, catalogo: Catalogo
) -> None:
    reloj = RelojManual(PROGRAMADO_PARA)
    prog = programador(db_session, AHORA_LOCAL)
    turno = caso_crear(db_session, prog, AHORA_LOCAL).ejecutar(solicitud(catalogo))
    cola, sender = ColaEnMemoria(), EmisorQueRegistra()
    prog.publicar(cola)
    assert len(cola.elementos) == 1
    caso_cancelar(db_session, programador(db_session, AHORA_LOCAL), AHORA_LOCAL).ejecutar(
        turno.id, None
    )

    ciclo_a(armar_worker(db_session, cola, sender, reloj), reloj, PROGRAMADO_PARA)

    assert sender.enviados == []
    (fila,) = recordatorios_de(db_session, turno.id)
    assert (fila["estado"], fila["intentos"]) == ("cancelado", 0)
    assert cola.elementos == {}


def test_recordatorio_enviado_encolado_de_nuevo_no_se_envia_dos_veces(
    db_session: Session, catalogo: Catalogo
) -> None:
    reloj = RelojManual(PROGRAMADO_PARA)
    turno = crear_sin_programar(db_session, catalogo)
    recordatorio_id = insertar_recordatorio(db_session, turno.id)
    cola, sender = ColaEnMemoria(), EmisorQueRegistra()
    worker = armar_worker(db_session, cola, sender, reloj)
    cola.encolar(recordatorio_id, PROGRAMADO_PARA)
    ciclo_a(worker, reloj, PROGRAMADO_PARA)

    cola.encolar(recordatorio_id, PROGRAMADO_PARA)
    ciclo_a(worker, reloj, PROGRAMADO_PARA)

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
    reloj = RelojManual(PROGRAMADO_PARA)
    turno = crear_sin_programar(db_session, catalogo)
    recordatorio_id = insertar_recordatorio(db_session, turno.id, estado=estado, intentos=intentos)
    cola, sender = ColaEnMemoria(), EmisorQueRegistra()
    cola.encolar(recordatorio_id, PROGRAMADO_PARA)

    ciclo_a(armar_worker(db_session, cola, sender, reloj), reloj, PROGRAMADO_PARA)

    assert sender.enviados == []
    (fila,) = recordatorios_de(db_session, turno.id)
    assert (fila["estado"], fila["intentos"]) == (estado.value, intentos)


def test_id_inexistente_se_descarta_y_el_resto_del_ciclo_se_procesa(
    db_session: Session, catalogo: Catalogo
) -> None:
    reloj = RelojManual(PROGRAMADO_PARA)
    turno = crear_sin_programar(db_session, catalogo)
    recordatorio_id = insertar_recordatorio(db_session, turno.id)
    fantasma = uuid4()
    cola, sender = ColaEnMemoria(), EmisorQueRegistra()
    cola.encolar(fantasma, PROGRAMADO_PARA.replace(minute=0))
    cola.encolar(recordatorio_id, PROGRAMADO_PARA.replace(minute=1))

    procesados = ciclo_a(
        armar_worker(db_session, cola, sender, reloj), reloj, PROGRAMADO_PARA.replace(minute=5)
    )

    assert procesados == 2
    assert [m.recordatorio_id for m in sender.enviados] == [recordatorio_id]
    (fila,) = recordatorios_de(db_session, turno.id)
    assert fila["estado"] == "enviado"
    assert cola.elementos == {}


INICIO_UTC = datetime(2026, 10, 9, 13, 0, tzinfo=UTC)  # inicio del turno de INICIO_TURNO


def test_turno_que_empieza_en_el_momento_de_procesar_no_envia_y_queda_cancelado(
    db_session: Session, catalogo: Catalogo
) -> None:
    reloj = RelojManual(PROGRAMADO_PARA)
    turno = crear_sin_programar(db_session, catalogo)
    recordatorio_id = insertar_recordatorio(db_session, turno.id)
    cola, sender = ColaEnMemoria(), EmisorQueRegistra()
    cola.encolar(recordatorio_id, PROGRAMADO_PARA)

    ciclo_a(armar_worker(db_session, cola, sender, reloj), reloj, INICIO_UTC)

    assert sender.invocaciones == 0
    (fila,) = recordatorios_de(db_session, turno.id)
    assert (fila["estado"], fila["intentos"]) == ("cancelado", 0)
    assert cola.elementos == {}


def test_recordatorio_atrasado_que_llega_un_minuto_antes_del_inicio_se_envia(
    db_session: Session, catalogo: Catalogo
) -> None:
    reloj = RelojManual(PROGRAMADO_PARA)
    turno = crear_sin_programar(db_session, catalogo)
    recordatorio_id = insertar_recordatorio(db_session, turno.id)
    cola, sender = ColaEnMemoria(), EmisorQueRegistra()
    cola.encolar(recordatorio_id, PROGRAMADO_PARA)

    ciclo_a(armar_worker(db_session, cola, sender, reloj), reloj, INICIO_UTC - timedelta(minutes=1))

    assert [m.recordatorio_id for m in sender.enviados] == [recordatorio_id]
    (fila,) = recordatorios_de(db_session, turno.id)
    assert (fila["estado"], fila["intentos"]) == ("enviado", 1)


def test_recordatorio_reencolado_tras_una_caida_larga_no_se_envia_y_queda_cancelado(
    db_session: Session, catalogo: Catalogo
) -> None:
    reloj = RelojManual(PROGRAMADO_PARA)
    turno = crear_sin_programar(db_session, catalogo)
    insertar_recordatorio(db_session, turno.id)
    cola, sender = ColaEnMemoria(), EmisorQueRegistra()
    worker = armar_worker(db_session, cola, sender, reloj)
    worker.iniciar()

    ciclo_a(worker, reloj, INICIO_UTC + timedelta(hours=2))

    assert sender.invocaciones == 0
    (fila,) = recordatorios_de(db_session, turno.id)
    assert (fila["estado"], fila["intentos"]) == ("cancelado", 0)
    assert cola.elementos == {}


def test_reintento_pendiente_de_un_turno_iniciado_no_se_envia_y_conserva_sus_intentos(
    db_session: Session, catalogo: Catalogo
) -> None:
    reloj = RelojManual(PROGRAMADO_PARA)
    turno = crear_sin_programar(db_session, catalogo)
    reintento = PROGRAMADO_PARA + timedelta(minutes=1)
    recordatorio_id = insertar_recordatorio(
        db_session, turno.id, intentos=1, programado_para=reintento
    )
    cola, sender = ColaEnMemoria(), EmisorQueRegistra()
    cola.encolar(recordatorio_id, reintento)

    ciclo_a(armar_worker(db_session, cola, sender, reloj), reloj, INICIO_UTC + timedelta(minutes=5))

    assert sender.invocaciones == 0
    (fila,) = recordatorios_de(db_session, turno.id)
    assert (fila["estado"], fila["intentos"]) == ("cancelado", 1)
    assert cola.elementos == {}


def test_el_descarte_por_turno_iniciado_no_registra_datos_del_paciente(
    db_session: Session, catalogo: Catalogo, caplog: pytest.LogCaptureFixture
) -> None:
    reloj = RelojManual(PROGRAMADO_PARA)
    turno = crear_sin_programar(db_session, catalogo)
    recordatorio_id = insertar_recordatorio(db_session, turno.id)
    cola = ColaEnMemoria()
    cola.encolar(recordatorio_id, PROGRAMADO_PARA)

    with caplog.at_level(logging.INFO, logger="app.application.recordatorios"):
        ciclo_a(armar_worker(db_session, cola, EmisorQueRegistra(), reloj), reloj, INICIO_UTC)

    mensajes = [r.getMessage() for r in caplog.records if "iniciado" in r.getMessage()]
    assert len(mensajes) == 1
    assert str(recordatorio_id) in mensajes[0]
    assert str(catalogo.pacientes[0].id) not in mensajes[0]
