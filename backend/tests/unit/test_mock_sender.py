import logging
from uuid import UUID

import pytest

from app.domain.notificaciones import MensajeRecordatorio
from app.infrastructure.notifications.mock_sender import MockSender, crear_sender

MENSAJE = MensajeRecordatorio(
    UUID(int=10), UUID(int=20), "Recordatorio: tiene un turno el 09/10/2026 a las 10:00 en X."
)


def test_mock_sender_enviar_records_the_message() -> None:
    sender = MockSender()

    sender.enviar(MENSAJE)

    assert sender.enviados == [MENSAJE]


def test_mock_sender_enviar_accumulates_messages_in_order() -> None:
    sender = MockSender()
    otro = MensajeRecordatorio(UUID(int=11), UUID(int=21), "otro texto")

    sender.enviar(MENSAJE)
    sender.enviar(otro)

    assert sender.enviados == [MENSAJE, otro]


def test_mock_sender_enviar_logs_info_with_reminder_id_and_text(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO):
        MockSender().enviar(MENSAJE)

    (registro,) = [
        r for r in caplog.records if r.name == "app.infrastructure.notifications.mock_sender"
    ]
    assert registro.levelno == logging.INFO
    mensaje = registro.getMessage()
    assert "recordatorio enviado (mock)" in mensaje
    assert str(MENSAJE.recordatorio_id) in mensaje
    assert MENSAJE.texto in mensaje


def test_mock_sender_enviar_log_omits_patient_id(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO):
        MockSender().enviar(MENSAJE)

    mensajes = [
        r.getMessage()
        for r in caplog.records
        if r.name == "app.infrastructure.notifications.mock_sender"
    ]
    assert mensajes
    assert all(str(MENSAJE.paciente_id) not in m for m in mensajes)
    assert all("paciente_id" not in m for m in mensajes)


def test_crear_sender_mock_returns_a_mock_sender() -> None:
    assert isinstance(crear_sender("mock"), MockSender)


def test_crear_sender_unknown_adapter_is_rejected() -> None:
    with pytest.raises(ValueError, match="whatsapp"):
        crear_sender("whatsapp")
