"""Proceso del worker de recordatorios: `python -m app.worker`.

Usa `ConfiguracionWorker` (sin `JWT_SECRET`) y su propio engine. Es crash-only (D11): un error
inesperado termina el proceso con código distinto de 0 y Compose lo reinicia; al iniciar, el
worker re-encola los pendientes de la base.
"""

import logging
import signal
import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from types import FrameType
from typing import Protocol

import redis
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import sessionmaker

from app.application.recordatorios import (
    ProcesarRecordatorio,
    ReencolarPendientes,
    WorkerRecordatorios,
)
from app.config import ConfiguracionWorker
from app.infrastructure.notifications.mock_sender import crear_sender
from app.infrastructure.queue.cola_redis import ColaRedis, crear_cliente_redis

logger = logging.getLogger(__name__)

PAUSA_S = 5.0
"""Espera entre ciclos cuando la cola no tenía vencidos."""


class _Ciclable(Protocol):
    def iniciar(self) -> int: ...

    def ciclo(self) -> int: ...


@dataclass
class WorkerArmado:
    worker: WorkerRecordatorios
    motor: Engine
    cliente: redis.Redis

    def cerrar(self) -> None:
        self.cliente.close()
        self.motor.dispose()


def _ahora_utc() -> datetime:
    return datetime.now(UTC)


def construir_worker(
    config: ConfiguracionWorker, reloj: Callable[[], datetime] = _ahora_utc
) -> WorkerArmado:
    """Arma el worker con sus dependencias reales; no abre conexiones hasta usarlas.

    El mismo `reloj` va al worker y al procesador: una sola fuente de tiempo.
    """
    motor = create_engine(config.DATABASE_URL, pool_pre_ping=True, hide_parameters=True)
    cliente = crear_cliente_redis(config.REDIS_URL)
    cola = ColaRedis(cliente)
    sesiones = sessionmaker(bind=motor, expire_on_commit=False)
    procesador = ProcesarRecordatorio(
        sesiones,
        cola,
        crear_sender(config.NOTIFICATION_ADAPTER),
        config.CONSULTORIO_NOMBRE,
        config.APP_TIMEZONE,
        reloj,
    )
    worker = WorkerRecordatorios(cola, procesador, ReencolarPendientes(sesiones, cola), reloj)
    return WorkerArmado(worker, motor, cliente)


def correr(
    worker: _Ciclable,
    *,
    detenido: threading.Event,
    pausa_s: float = PAUSA_S,
    max_ciclos: int | None = None,
) -> int:
    """Re-encola al iniciar y repite `ciclo()` hasta que `detenido` se active.

    Con la cola sin vencidos espera `pausa_s` (interrumpible por `detenido`). `max_ciclos`
    acota la cantidad de ciclos (para los tests). Devuelve los ciclos ejecutados.
    """
    worker.iniciar()
    ciclos = 0
    while not detenido.is_set():
        procesados = worker.ciclo()
        ciclos += 1
        if max_ciclos is not None and ciclos >= max_ciclos:
            break
        if procesados == 0:
            detenido.wait(pausa_s)
    return ciclos


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    armado = construir_worker(ConfiguracionWorker())
    detenido = threading.Event()

    def pedir_detencion(signum: int, _frame: FrameType | None) -> None:
        logger.info("señal %s recibida: el worker se detiene", signum)
        detenido.set()

    signal.signal(signal.SIGTERM, pedir_detencion)
    signal.signal(signal.SIGINT, pedir_detencion)
    try:
        correr(armado.worker, detenido=detenido)
    finally:
        armado.cerrar()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
