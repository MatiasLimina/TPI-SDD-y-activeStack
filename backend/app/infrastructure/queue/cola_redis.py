"""Cola de recordatorios sobre un sorted set de Redis (D7): miembro = id, score = vencimiento."""

from datetime import datetime
from uuid import UUID

import redis

CLAVE_POR_DEFECTO = "recordatorios:programados"


class ColaRedis:
    """Implementa `ColaRecordatorios`. La base sigue siendo la fuente de verdad del estado."""

    def __init__(self, cliente: redis.Redis, clave: str = CLAVE_POR_DEFECTO) -> None:
        self._cliente = cliente
        self._clave = clave

    def encolar(self, recordatorio_id: UUID, vence: datetime) -> None:
        """`ZADD` es idempotente por miembro: volver a encolar reemplaza el vencimiento."""
        self._cliente.zadd(self._clave, {str(recordatorio_id): vence.timestamp()})

    def tomar_vencidos(self, ahora: datetime, limite: int) -> list[UUID]:
        """Entrega por vencimiento hasta `limite` ids vencidos, cada uno a un solo consumidor.

        Un id solo se devuelve si el `ZREM` lo quitó (devolvió 1): con varios workers, el que
        pierde la carrera no lo recibe. No hace falta Lua ni `WATCH`.
        """
        candidatos = self._cliente.zrangebyscore(
            self._clave, "-inf", ahora.timestamp(), start=0, num=limite
        )
        return [UUID(miembro) for miembro in candidatos if self._cliente.zrem(self._clave, miembro)]
