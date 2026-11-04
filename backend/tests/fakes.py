"""Dobles de los puertos externos para los tests (cola y emisor de recordatorios)."""

import threading
from collections.abc import Collection
from datetime import datetime, timedelta
from uuid import UUID

import redis

from app.domain.notificaciones import MensajeRecordatorio


class ColaEnMemoria:
    """Cola de recordatorios en memoria que cumple el mismo contrato que `ColaRedis`.

    Un cerrojo hace atómicas las operaciones, como en Redis: cada id sale a un solo consumidor.
    """

    def __init__(self) -> None:
        self.elementos: dict[UUID, datetime] = {}
        self._cerrojo = threading.Lock()

    def encolar(self, recordatorio_id: UUID, vence: datetime) -> None:
        with self._cerrojo:
            self.elementos[recordatorio_id] = vence

    def tomar_vencidos(self, ahora: datetime, limite: int) -> list[UUID]:
        with self._cerrojo:
            vencidos = sorted(
                (vence, recordatorio_id)
                for recordatorio_id, vence in self.elementos.items()
                if vence <= ahora
            )[:limite]
            for _, recordatorio_id in vencidos:
                del self.elementos[recordatorio_id]
        return [recordatorio_id for _, recordatorio_id in vencidos]


class ColaQueFalla:
    """Cola caída: toda operación lanza el error de conexión de redis-py."""

    def encolar(self, recordatorio_id: UUID, vence: datetime) -> None:
        raise redis.exceptions.ConnectionError("Redis no disponible (doble de test)")

    def tomar_vencidos(self, ahora: datetime, limite: int) -> list[UUID]:
        raise redis.exceptions.ConnectionError("Redis no disponible (doble de test)")


class ColaQueRechazaEncolado(ColaEnMemoria):
    """Cola en memoria cuyo encolado falla con el error de conexión de redis-py.

    Rechaza el encolado de los ids de `rechaza_ids` y, si se da `rechaza_todo_desde`, todo
    encolado desde el primer intento con ese id (inclusive). Los dos se pueden fijar después de
    sembrar `elementos`. `reabrir()` la deja disponible de nuevo.
    """

    def __init__(
        self,
        rechaza_ids: Collection[UUID] = (),
        rechaza_todo_desde: UUID | None = None,
    ) -> None:
        super().__init__()
        self.rechaza_ids = set(rechaza_ids)
        self.rechaza_todo_desde = rechaza_todo_desde
        self._cerrada = False

    def encolar(self, recordatorio_id: UUID, vence: datetime) -> None:
        if recordatorio_id == self.rechaza_todo_desde:
            self._cerrada = True
        if self._cerrada or recordatorio_id in self.rechaza_ids:
            raise redis.exceptions.ConnectionError(
                f"Redis no disponible al encolar {recordatorio_id} (doble de test)"
            )
        super().encolar(recordatorio_id, vence)

    def reabrir(self) -> None:
        self.rechaza_ids = set()
        self.rechaza_todo_desde = None
        self._cerrada = False


class RelojManual:
    """Reloj inyectable: invocable, con el instante fijado por el test."""

    def __init__(self, ahora: datetime) -> None:
        self.ahora = ahora

    def __call__(self) -> datetime:
        return self.ahora

    def ajustar(self, instante: datetime) -> None:
        self.ahora = instante

    def avanzar(self, delta: timedelta) -> None:
        self.ahora += delta


class EmisorQueRegistra:
    """Emisor que registra cada mensaje enviado y cuenta las invocaciones."""

    def __init__(self) -> None:
        self.invocaciones = 0
        self.enviados: list[MensajeRecordatorio] = []

    def enviar(self, mensaje: MensajeRecordatorio) -> None:
        self.invocaciones += 1
        self.enviados.append(mensaje)


class EmisorQueFallaCon(EmisorQueRegistra):
    """Emisor que falla solo con los recordatorios de `ids` y registra el resto."""

    def __init__(self, ids: Collection[UUID]) -> None:
        super().__init__()
        self._ids = set(ids)

    def enviar(self, mensaje: MensajeRecordatorio) -> None:
        if mensaje.recordatorio_id in self._ids:
            self.invocaciones += 1
            raise RuntimeError("fallo de envío (doble de test)")
        super().enviar(mensaje)


class EmisorQueFalla(EmisorQueRegistra):
    """Emisor que falla las primeras `fallas` invocaciones y después registra el envío."""

    def __init__(self, fallas: int) -> None:
        super().__init__()
        self._fallas = fallas

    def enviar(self, mensaje: MensajeRecordatorio) -> None:
        if self.invocaciones < self._fallas:
            self.invocaciones += 1
            raise RuntimeError("fallo de envío (doble de test)")
        super().enviar(mensaje)
