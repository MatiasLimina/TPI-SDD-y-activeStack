"""Cola de recordatorios sobre un sorted set de Redis (D7): miembro = id, score = vencimiento."""

from datetime import datetime
from uuid import UUID

import redis

CLAVE_POR_DEFECTO = "recordatorios:programados"


_TOMAR_VENCIDOS = """
local ids = redis.call('ZRANGEBYSCORE', KEYS[1], '-inf', ARGV[1], 'LIMIT', 0, ARGV[2])
if #ids > 0 then redis.call('ZREM', KEYS[1], unpack(ids)) end
return ids
"""
"""Lee y quita los vencidos en un solo viaje. Redis ejecuta el script de forma atómica."""


class ColaRedis:
    """Implementa `ColaRecordatorios`. La base sigue siendo la fuente de verdad del estado.

    `tomar_vencidos` usa un script Lua (`_TOMAR_VENCIDOS`): un `ZRANGEBYSCORE` y un `ZREM` de
    los ids leídos, atómicos, en un solo viaje (`EVALSHA`, con caída automática a `EVAL`).
    """

    def __init__(self, cliente: redis.Redis, clave: str = CLAVE_POR_DEFECTO) -> None:
        self._cliente = cliente
        self._clave = clave
        self._tomar_vencidos = cliente.register_script(_TOMAR_VENCIDOS)

    def encolar(self, recordatorio_id: UUID, vence: datetime) -> None:
        """`ZADD` es idempotente por miembro: volver a encolar reemplaza el vencimiento."""
        self._cliente.zadd(self._clave, {str(recordatorio_id): vence.timestamp()})

    def tomar_vencidos(self, ahora: datetime, limite: int) -> list[UUID]:
        """Entrega por vencimiento hasta `limite` ids vencidos, cada uno a un solo consumidor.

        El script los lee y los quita de forma atómica: con varios workers, cada id llega a uno.
        `limite` es chico (100 por ciclo), lejos del tope de argumentos de `unpack`.
        """
        miembros = self._tomar_vencidos(keys=[self._clave], args=[ahora.timestamp(), limite])
        return [UUID(miembro) for miembro in miembros]


def crear_cliente_redis(url: str) -> redis.Redis:
    """Cliente con timeouts cortos: acotan la espera de la API cuando Redis está caído."""
    return redis.Redis.from_url(
        url, decode_responses=True, socket_connect_timeout=2, socket_timeout=2
    )
