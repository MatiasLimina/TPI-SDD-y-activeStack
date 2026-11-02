from datetime import UTC, datetime
from uuid import UUID

import pytest
import redis

from app.domain.notificaciones import MensajeRecordatorio
from tests.fakes import ColaQueFalla, EmisorQueFalla

MENSAJE = MensajeRecordatorio(UUID(int=1), UUID(int=2), "texto ficticio")
AHORA = datetime(2026, 10, 8, 13, 0, tzinfo=UTC)


def test_cola_que_falla_raises_connection_error_on_encolar() -> None:
    with pytest.raises(redis.exceptions.ConnectionError):
        ColaQueFalla().encolar(UUID(int=1), AHORA)


def test_cola_que_falla_raises_connection_error_on_tomar_vencidos() -> None:
    with pytest.raises(redis.exceptions.ConnectionError):
        ColaQueFalla().tomar_vencidos(AHORA, 10)


@pytest.mark.parametrize("fallas", [0, 1, 2])
def test_emisor_que_falla_fails_the_first_n_times_and_then_succeeds(fallas: int) -> None:
    emisor = EmisorQueFalla(fallas=fallas)

    for _ in range(fallas):
        with pytest.raises(RuntimeError):
            emisor.enviar(MENSAJE)
    emisor.enviar(MENSAJE)

    assert emisor.invocaciones == fallas + 1
    assert emisor.enviados == [MENSAJE]
