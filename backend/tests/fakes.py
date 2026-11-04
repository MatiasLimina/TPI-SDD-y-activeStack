"""Dobles de los puertos externos para los tests (cola y emisor de recordatorios)."""

from datetime import datetime, timedelta
from uuid import UUID

import redis

from app.domain.notificaciones import MensajeRecordatorio


class ColaEnMemoria:
    """Cola de recordatorios en memoria que cumple el mismo contrato que `ColaRedis`."""

    def __init__(self) -> None:
        self.elementos: dict[UUID, datetime] = {}

    def encolar(self, recordatorio_id: UUID, vence: datetime) -> None:
        self.elementos[recordatorio_id] = vence

    def tomar_vencidos(self, ahora: datetime, limite: int) -> list[UUID]:
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
