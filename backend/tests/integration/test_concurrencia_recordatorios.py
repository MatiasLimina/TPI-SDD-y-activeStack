"""Concurrencia: dos workers procesan el mismo recordatorio, cada uno en su conexión."""

import threading
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.application.crear_turno import CrearTurno, SolicitudTurno
from app.application.recordatorios import ProcesarRecordatorio, ResultadoProcesamiento
from app.domain.notificaciones import MensajeRecordatorio
from app.infrastructure.db.repositorio_turnos import RepositorioTurnos
from app.infrastructure.notifications.mock_sender import MockSender
from tests.fakes import ColaEnMemoria, RelojManual
from tests.integration.factories import Catalogo
from tests.integration.helpers_recordatorios import CONSULTORIO, PROGRAMADO_PARA, ZONA

AHORA = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)
INICIO = datetime(2026, 10, 9, 13, 0, tzinfo=UTC)
HILOS = 2
ESPERA_MAX_S = 0.3


class SenderQueEsperaAlOtro(MockSender):
    """Retiene el primer envío hasta que otro hilo también llegue a enviar (o venza el plazo).

    Con el bloqueo correcto el segundo hilo espera en la base y nunca llega: el plazo vence y
    el envío único se confirma. Sin bloqueo, ambos llegan y se registran dos envíos.
    """

    def __init__(self) -> None:
        super().__init__()
        self._llegaron = threading.Event()
        self._cantidad = 0
        self._cerrojo = threading.Lock()

    def enviar(self, mensaje: MensajeRecordatorio) -> None:
        with self._cerrojo:
            self._cantidad += 1
            if self._cantidad >= HILOS:
                self._llegaron.set()
        self._llegaron.wait(timeout=ESPERA_MAX_S)
        super().enviar(mensaje)


def _recordatorio_commiteado(motor: Engine, catalogo: Catalogo) -> UUID:
    with Session(motor) as sesion:
        turno = CrearTurno(RepositorioTurnos(sesion), reloj=lambda: AHORA).ejecutar(
            SolicitudTurno(
                profesional_id=catalogo.profesionales[0].id,
                paciente_id=catalogo.pacientes[0].id,
                prestacion_id=catalogo.limpieza.id,
                sillon_id=catalogo.sillones[0].id,
                inicio=INICIO,
            )
        )
        recordatorio_id = sesion.execute(
            text(
                "INSERT INTO recordatorio (turno_id, programado_para, estado, canal, intentos) "
                "VALUES (:turno_id, :programado_para, 'pendiente', 'mock', 0) RETURNING id"
            ),
            {"turno_id": turno.id, "programado_para": PROGRAMADO_PARA},
        ).scalar_one()
        sesion.commit()
        return recordatorio_id  # type: ignore[no-any-return]


def test_procesamiento_simultaneo_del_mismo_recordatorio_envia_exactamente_una_vez(
    motor_concurrente: Engine, catalogo_commiteado: Catalogo
) -> None:
    recordatorio_id = _recordatorio_commiteado(motor_concurrente, catalogo_commiteado)
    fabrica = sessionmaker(bind=motor_concurrente, expire_on_commit=False)
    sender = SenderQueEsperaAlOtro()
    procesador = ProcesarRecordatorio(
        fabrica, ColaEnMemoria(), sender, CONSULTORIO, ZONA, RelojManual(PROGRAMADO_PARA)
    )
    barrera = threading.Barrier(HILOS)
    resultados: list[Any] = [None] * HILOS

    def trabajar(indice: int) -> None:
        barrera.wait(timeout=10)
        try:
            resultados[indice] = procesador.procesar(recordatorio_id)
        except Exception as error:  # se inspecciona en el hilo principal
            resultados[indice] = error

    hilos = [threading.Thread(target=trabajar, args=(i,)) for i in range(HILOS)]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join(timeout=30)

    assert sorted(resultados, key=str) == [
        ResultadoProcesamiento.DESCARTADO,
        ResultadoProcesamiento.ENVIADO,
    ]
    assert [m.recordatorio_id for m in sender.enviados] == [recordatorio_id]
    with Session(motor_concurrente) as sesion:
        estado, intentos = sesion.execute(
            text("SELECT estado, intentos FROM recordatorio WHERE id = :id"),
            {"id": recordatorio_id},
        ).one()
    assert (estado, intentos) == ("enviado", 1)
