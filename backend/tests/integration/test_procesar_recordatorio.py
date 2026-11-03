"""Procesamiento de recordatorios vencidos por el worker, con PostgreSQL real y cola en memoria."""

from datetime import datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from app.infrastructure.db.models import Paciente, Prestacion, Profesional, Sillon
from app.infrastructure.notifications.mock_sender import MockSender
from tests.fakes import ColaEnMemoria
from tests.integration.factories import Catalogo, crear_catalogo
from tests.integration.helpers_recordatorios import (
    BUENOS_AIRES,
    CONSULTORIO,
    PROGRAMADO_PARA,
    armar_worker,
    crear_sin_programar,
    insertar_recordatorio,
    recordatorios_de,
)

TEXTO_ESPERADO = (
    "Recordatorio: tiene un turno el 09/10/2026 a las 10:00 en Consultorio Odontológico Ejemplo."
)


@pytest.fixture
def catalogo(db_session: Session) -> Catalogo:
    return crear_catalogo(db_session)


def test_ciclo_con_recordatorio_vencido_lo_envia_una_vez_y_queda_enviado(
    db_session: Session, catalogo: Catalogo
) -> None:
    turno = crear_sin_programar(db_session, catalogo)
    recordatorio_id = insertar_recordatorio(db_session, turno.id)
    cola, sender = ColaEnMemoria(), MockSender()
    cola.encolar(recordatorio_id, PROGRAMADO_PARA)

    procesados = armar_worker(db_session, cola, sender).ciclo(PROGRAMADO_PARA)

    assert procesados == 1
    assert [m.recordatorio_id for m in sender.enviados] == [recordatorio_id]
    (fila,) = recordatorios_de(db_session, turno.id)
    assert (fila["estado"], fila["intentos"]) == ("enviado", 1)
    assert cola.elementos == {}


def test_ciclo_antes_del_vencimiento_no_envia_y_deja_pendiente(
    db_session: Session, catalogo: Catalogo
) -> None:
    turno = crear_sin_programar(db_session, catalogo)
    recordatorio_id = insertar_recordatorio(db_session, turno.id)
    cola, sender = ColaEnMemoria(), MockSender()
    cola.encolar(recordatorio_id, PROGRAMADO_PARA)

    procesados = armar_worker(db_session, cola, sender).ciclo(
        PROGRAMADO_PARA - timedelta(minutes=1)
    )

    assert procesados == 0
    assert sender.enviados == []
    (fila,) = recordatorios_de(db_session, turno.id)
    assert (fila["estado"], fila["intentos"]) == ("pendiente", 0)
    assert recordatorio_id in cola.elementos


def test_ciclo_procesa_varios_vencidos_y_deja_los_futuros(
    db_session: Session, catalogo: Catalogo
) -> None:
    primero = crear_sin_programar(db_session, catalogo)
    segundo = crear_sin_programar(
        db_session, catalogo, datetime(2026, 10, 9, 15, 0, tzinfo=BUENOS_AIRES), paciente=1
    )
    r1 = insertar_recordatorio(db_session, primero.id)
    r2 = insertar_recordatorio(
        db_session, segundo.id, programado_para=PROGRAMADO_PARA + timedelta(hours=5)
    )
    cola, sender = ColaEnMemoria(), MockSender()
    cola.encolar(r1, PROGRAMADO_PARA)
    cola.encolar(r2, PROGRAMADO_PARA + timedelta(hours=5))

    procesados = armar_worker(db_session, cola, sender).ciclo(PROGRAMADO_PARA + timedelta(hours=1))

    assert procesados == 1
    assert [m.recordatorio_id for m in sender.enviados] == [r1]
    assert set(cola.elementos) == {r2}


def test_el_mensaje_enviado_tiene_el_texto_exacto_y_va_dirigido_al_paciente(
    db_session: Session, catalogo: Catalogo
) -> None:
    turno = crear_sin_programar(db_session, catalogo)
    recordatorio_id = insertar_recordatorio(db_session, turno.id)
    cola, sender = ColaEnMemoria(), MockSender()
    cola.encolar(recordatorio_id, PROGRAMADO_PARA)

    armar_worker(db_session, cola, sender, consultorio=CONSULTORIO).ciclo(PROGRAMADO_PARA)

    (mensaje,) = sender.enviados
    assert mensaje.texto == TEXTO_ESPERADO
    assert mensaje.paciente_id == catalogo.pacientes[0].id


def test_el_mensaje_enviado_no_contiene_datos_clinicos_ni_personales(
    db_session: Session,
) -> None:
    profesional = Profesional(nombre="Ficticio", apellido="Pérez")
    paciente = Paciente(
        nombre="Ana", apellido="Prueba", documento="30111222", telefono="+54 11 5555-0003"
    )
    prestacion = Prestacion(nombre="Limpieza", duracion_min=45)
    sillon = Sillon(nombre="Sillón ficticio")
    db_session.add_all([profesional, paciente, prestacion, sillon])
    db_session.flush()
    catalogo = Catalogo([profesional], [sillon], [paciente], prestacion, prestacion)
    turno = crear_sin_programar(db_session, catalogo)
    recordatorio_id = insertar_recordatorio(db_session, turno.id)
    cola, sender = ColaEnMemoria(), MockSender()
    cola.encolar(recordatorio_id, PROGRAMADO_PARA)

    armar_worker(db_session, cola, sender).ciclo(PROGRAMADO_PARA)

    (mensaje,) = sender.enviados
    for prohibido in (
        "Limpieza",
        "Pérez",
        "Ana",
        "Prueba",
        "30111222",
        str(prestacion.id),
        str(profesional.id),
        str(sillon.id),
    ):
        assert prohibido not in mensaje.texto
    assert mensaje.texto == TEXTO_ESPERADO


def test_ciclo_sin_elementos_en_la_cola_no_hace_nada(db_session: Session) -> None:
    sender = MockSender()

    assert armar_worker(db_session, ColaEnMemoria(), sender).ciclo(PROGRAMADO_PARA) == 0
    assert sender.enviados == []
