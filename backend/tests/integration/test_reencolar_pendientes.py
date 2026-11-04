"""Re-encolado de los pendientes al iniciar el worker (D11), con PostgreSQL real."""

from datetime import UTC, datetime
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.turnos import get_cola_recordatorios, get_reloj
from app.domain.recordatorios import EstadoRecordatorio
from app.infrastructure.notifications.mock_sender import MockSender
from tests.fakes import ColaEnMemoria, ColaQueFalla, RelojManual
from tests.integration.factories import Catalogo, crear_catalogo
from tests.integration.helpers_recordatorios import (
    BUENOS_AIRES,
    PROGRAMADO_PARA,
    armar_worker,
    ciclo_a,
    crear_sin_programar,
    insertar_recordatorio,
    recordatorios_de,
)

DIA_2 = datetime(2026, 10, 9, 13, 0, tzinfo=UTC)


@pytest.fixture
def catalogo(db_session: Session) -> Catalogo:
    return crear_catalogo(db_session)


def _sembrar_recordatorios(session: Session, catalogo: Catalogo) -> tuple[UUID, UUID]:
    """Dos pendientes (turnos distintos) más un cancelado, un enviado y un fallido."""
    turno_a = crear_sin_programar(
        session, catalogo, datetime(2026, 10, 9, 10, 0, tzinfo=BUENOS_AIRES)
    )
    turno_b = crear_sin_programar(
        session, catalogo, datetime(2026, 10, 10, 10, 0, tzinfo=BUENOS_AIRES)
    )
    turno_c = crear_sin_programar(
        session, catalogo, datetime(2026, 10, 11, 10, 0, tzinfo=BUENOS_AIRES)
    )
    primero = insertar_recordatorio(session, turno_a.id)
    segundo = insertar_recordatorio(session, turno_b.id, programado_para=DIA_2)
    insertar_recordatorio(session, turno_c.id, estado=EstadoRecordatorio.CANCELADO)
    insertar_recordatorio(session, turno_c.id, estado=EstadoRecordatorio.ENVIADO, intentos=1)
    insertar_recordatorio(session, turno_c.id, estado=EstadoRecordatorio.FALLIDO, intentos=3)
    return primero, segundo


def test_iniciar_encola_exactamente_los_pendientes_con_su_programado_para(
    db_session: Session, catalogo: Catalogo
) -> None:
    reloj = RelojManual(PROGRAMADO_PARA)
    primero, segundo = _sembrar_recordatorios(db_session, catalogo)
    cola = ColaEnMemoria()

    encolados = armar_worker(db_session, cola, MockSender(), reloj).iniciar()

    assert encolados == 2
    assert cola.elementos == {primero: PROGRAMADO_PARA, segundo: DIA_2}


def test_iniciar_sin_pendientes_deja_la_cola_vacia(db_session: Session, catalogo: Catalogo) -> None:
    reloj = RelojManual(PROGRAMADO_PARA)
    turno = crear_sin_programar(db_session, catalogo)
    insertar_recordatorio(db_session, turno.id, estado=EstadoRecordatorio.CANCELADO)
    cola = ColaEnMemoria()

    assert armar_worker(db_session, cola, MockSender(), reloj).iniciar() == 0
    assert cola.elementos == {}


def test_iniciar_dos_veces_deja_un_solo_elemento_y_un_unico_envio_al_vencer(
    db_session: Session, catalogo: Catalogo
) -> None:
    reloj = RelojManual(PROGRAMADO_PARA)
    turno = crear_sin_programar(db_session, catalogo)
    recordatorio_id = insertar_recordatorio(db_session, turno.id)
    cola, sender = ColaEnMemoria(), MockSender()
    worker = armar_worker(db_session, cola, sender, reloj)

    worker.iniciar()
    worker.iniciar()

    assert cola.elementos == {recordatorio_id: PROGRAMADO_PARA}
    ciclo_a(worker, reloj, PROGRAMADO_PARA)
    ciclo_a(worker, reloj, PROGRAMADO_PARA)
    assert [m.recordatorio_id for m in sender.enviados] == [recordatorio_id]


def test_iniciar_encola_un_pendiente_con_intentos_con_su_programado_para(
    db_session: Session, catalogo: Catalogo
) -> None:
    reloj = RelojManual(PROGRAMADO_PARA)
    turno = crear_sin_programar(db_session, catalogo)
    recordatorio_id = insertar_recordatorio(db_session, turno.id, intentos=2)
    cola = ColaEnMemoria()

    armar_worker(db_session, cola, MockSender(), reloj).iniciar()

    assert cola.elementos == {recordatorio_id: PROGRAMADO_PARA}


def test_alta_con_la_cola_caida_se_envia_despues_de_reiniciar_el_worker(
    client: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    reloj = RelojManual(PROGRAMADO_PARA)
    app = client.app
    app.dependency_overrides[get_reloj] = lambda: lambda: datetime(2026, 10, 7, 12, 0, tzinfo=UTC)  # type: ignore[attr-defined]
    app.dependency_overrides[get_cola_recordatorios] = ColaQueFalla  # type: ignore[attr-defined]
    respuesta = client.post(
        "/turnos",
        json={
            "profesional_id": str(catalogo.profesionales[0].id),
            "paciente_id": str(catalogo.pacientes[0].id),
            "prestacion_id": str(catalogo.limpieza.id),
            "sillon_id": str(catalogo.sillones[0].id),
            "inicio": "2026-10-09T10:00:00-03:00",
        },
    )
    assert respuesta.status_code == 201
    turno_id = UUID(respuesta.json()["id"])
    cola_nueva, sender = ColaEnMemoria(), MockSender()
    assert cola_nueva.elementos == {}

    worker = armar_worker(db_session, cola_nueva, sender, reloj)
    worker.iniciar()
    ciclo_a(worker, reloj, PROGRAMADO_PARA)

    (fila,) = recordatorios_de(db_session, turno_id)
    assert (fila["estado"], fila["intentos"]) == ("enviado", 1)
    assert len(sender.enviados) == 1
