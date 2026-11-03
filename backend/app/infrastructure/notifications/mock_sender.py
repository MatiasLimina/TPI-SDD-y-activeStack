"""Adaptador de notificación simulado: registra el envío en memoria y en el log (D13)."""

import logging

from app.domain.notificaciones import MensajeRecordatorio, NotificationSender

logger = logging.getLogger(__name__)


class MockSender:
    """No contacta ningún servicio externo. El texto no contiene datos clínicos (RN-NO-04)."""

    def __init__(self) -> None:
        self.enviados: list[MensajeRecordatorio] = []

    def enviar(self, mensaje: MensajeRecordatorio) -> None:
        self.enviados.append(mensaje)
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
