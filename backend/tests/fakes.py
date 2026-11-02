"""Dobles de los puertos externos para los tests (cola y emisor de recordatorios)."""

from datetime import datetime
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


class EmisorQueFalla:
    """Emisor que falla las primeras `fallas` invocaciones y después registra el envío."""

    def __init__(self, fallas: int) -> None:
        self._fallas = fallas
        self.invocaciones = 0
        self.enviados: list[MensajeRecordatorio] = []

    def enviar(self, mensaje: MensajeRecordatorio) -> None:
        self.invocaciones += 1
        if self.invocaciones <= self._fallas:
            raise RuntimeError("fallo de envío (doble de test)")
        self.enviados.append(mensaje)
