"""Adaptador de notificación simulado: registra el envío solo en el log (D13)."""

import logging

from app.domain.notificaciones import MensajeRecordatorio, NotificationSender

logger = logging.getLogger(__name__)


class MockSender:
    """No contacta ningún servicio externo y no guarda estado: el worker vive mucho tiempo.

    El texto no contiene datos clínicos (RN-NO-04). Los tests que necesitan inspeccionar lo
    enviado usan `tests.fakes.EmisorQueRegistra`.
    """

    def enviar(self, mensaje: MensajeRecordatorio) -> None:
        logger.info(
            "recordatorio enviado (mock): recordatorio_id=%s texto=%s",
            mensaje.recordatorio_id,
            mensaje.texto,
        )


def crear_sender(adaptador: str) -> NotificationSender:
    """Devuelve el adaptador configurado en `NOTIFICATION_ADAPTER` (hoy solo `mock`)."""
    if adaptador == "mock":
        return MockSender()
    raise ValueError(f"adaptador de notificación desconocido: {adaptador!r}")
