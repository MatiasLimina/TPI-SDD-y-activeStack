"""Contenido y puerto de las notificaciones de recordatorio (RN-NO-04): dominio puro."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.domain.time import to_local


@dataclass(frozen=True)
class MensajeRecordatorio:
    """Mensaje al paciente: sin campos para prestación, profesional ni datos personales."""

    recordatorio_id: UUID
    paciente_id: UUID
    texto: str


def armar_mensaje(
    recordatorio_id: UUID,
    paciente_id: UUID,
    inicio: datetime,
    consultorio: str,
    zona: str,
) -> MensajeRecordatorio:
    """Arma el texto fijo con la fecha y la hora locales del inicio y el consultorio (D12)."""
    local = to_local(inicio, zona)
    texto = (
        f"Recordatorio: tiene un turno el {local:%d/%m/%Y} a las {local:%H:%M} en {consultorio}."
    )
    return MensajeRecordatorio(recordatorio_id, paciente_id, texto)


class NotificationSender(Protocol):
    """Puerto de envío. Lanza una excepción si el envío falla.

    Un adaptador real debería usar `recordatorio_id` como clave de idempotencia: la entrega
    es "al menos una vez" (si el worker cae entre enviar y confirmar, se envía de nuevo).
    """

    def enviar(self, mensaje: MensajeRecordatorio) -> None: ...
