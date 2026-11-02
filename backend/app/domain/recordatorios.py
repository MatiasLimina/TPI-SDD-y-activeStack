"""Reglas puras de los recordatorios (RN-NO-01..05): sin base, Redis ni FastAPI."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from app.domain.time import to_utc

MAX_INTENTOS = 3
"""Intentos de envío en total: el primero más dos reintentos (D10, DD-19)."""

ESPERA_BASE_REINTENTO = timedelta(minutes=1)


class EstadoRecordatorio(StrEnum):
    PENDIENTE = "pendiente"
    ENVIADO = "enviado"
    FALLIDO = "fallido"
    CANCELADO = "cancelado"


@dataclass(frozen=True)
class RecordatorioRegistrado:
    """Estado persistido de un recordatorio (`programado_para` siempre en UTC)."""

    id: UUID
    turno_id: UUID
    programado_para: datetime
    estado: EstadoRecordatorio
    canal: str
    intentos: int


def calcular_programacion(
    inicio: datetime, ahora: datetime, anticipacion: timedelta
) -> datetime | None:
    """Instante UTC en que corresponde enviar el recordatorio, o `None` si ya no hay tiempo.

    Se programa solo si `inicio - anticipacion >= ahora`: con exactamente la anticipación
    configurada sí se programa (D3, DD-13).
    """
    programado = to_utc(inicio) - anticipacion
    if programado < to_utc(ahora):
        return None
    return programado


def espera_reintento(intentos_hechos: int) -> timedelta:
    """Espera antes del próximo intento: 1 min tras el 1.º y 2 min tras el 2.º (D9)."""
    return ESPERA_BASE_REINTENTO * 2 ** (intentos_hechos - 1)


class ColaRecordatorios(Protocol):
    """Cola de recordatorios con vencimiento; la base sigue siendo la fuente de verdad."""

    def encolar(self, recordatorio_id: UUID, vence: datetime) -> None:
        """Agrega el recordatorio o, si ya está, reemplaza su vencimiento."""
        ...

    def tomar_vencidos(self, ahora: datetime, limite: int) -> list[UUID]:
        """Quita de la cola y devuelve, por vencimiento, hasta `limite` ids vencidos."""
        ...
