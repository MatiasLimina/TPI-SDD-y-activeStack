"""Dobles de los puertos externos para los tests (cola y emisor de recordatorios)."""

from datetime import datetime
from uuid import UUID


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
