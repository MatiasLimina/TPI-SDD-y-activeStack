from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
import redis

from app.domain.notificaciones import MensajeRecordatorio
from tests.fakes import (
    ColaEnMemoria,
    ColaQueFalla,
    ColaQueRechazaEncolado,
    EmisorQueFalla,
    EmisorQueFallaCon,
    EmisorQueRegistra,
    RelojManual,
)

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


def test_reloj_manual_returns_the_adjusted_instant() -> None:
    reloj = RelojManual(AHORA)
    assert reloj() == AHORA

    otro = AHORA + timedelta(days=1, minutes=7)
    reloj.ajustar(otro)

    assert reloj() == otro
    assert reloj.ahora == otro


def test_reloj_manual_avanzar_moves_forward_from_the_current_instant() -> None:
    reloj = RelojManual(AHORA)

    reloj.avanzar(timedelta(seconds=40))
    reloj.avanzar(timedelta(minutes=1))

    assert reloj() == AHORA + timedelta(seconds=100)


def test_emisor_que_registra_keeps_the_messages_in_order_and_counts_invocations() -> None:
    emisor = EmisorQueRegistra()
    otro = MensajeRecordatorio(UUID(int=3), UUID(int=4), "otro texto ficticio")

    emisor.enviar(MENSAJE)
    emisor.enviar(otro)

    assert emisor.enviados == [MENSAJE, otro]
    assert emisor.invocaciones == 2


def test_emisor_que_falla_is_an_emisor_que_registra() -> None:
    assert isinstance(EmisorQueFalla(fallas=0), EmisorQueRegistra)


def test_emisor_que_falla_con_fails_only_for_the_given_reminder_ids() -> None:
    emisor = EmisorQueFallaCon({UUID(int=1)})
    mala = MensajeRecordatorio(UUID(int=1), UUID(int=9), "texto ficticio")
    buena = MensajeRecordatorio(UUID(int=2), UUID(int=9), "texto ficticio")

    emisor.enviar(buena)
    with pytest.raises(RuntimeError):
        emisor.enviar(mala)
    emisor.enviar(buena)

    assert emisor.invocaciones == 3
    assert emisor.enviados == [buena, buena]


def test_cola_que_rechaza_encolado_rejects_only_the_given_ids_and_keeps_the_rest() -> None:
    cola = ColaQueRechazaEncolado(rechaza_ids={UUID(int=1)})

    with pytest.raises(redis.exceptions.ConnectionError):
        cola.encolar(UUID(int=1), AHORA)
    cola.encolar(UUID(int=2), AHORA)

    assert cola.elementos == {UUID(int=2): AHORA}
    assert cola.tomar_vencidos(AHORA, 10) == [UUID(int=2)]


def test_cola_que_rechaza_encolado_rejects_everything_from_the_trigger_id_on() -> None:
    cola = ColaQueRechazaEncolado(rechaza_todo_desde=UUID(int=2))

    cola.encolar(UUID(int=1), AHORA)
    with pytest.raises(redis.exceptions.ConnectionError):
        cola.encolar(UUID(int=2), AHORA)
    with pytest.raises(redis.exceptions.ConnectionError):
        cola.encolar(UUID(int=3), AHORA)

    assert cola.elementos == {UUID(int=1): AHORA}


def test_cola_que_rechaza_encolado_accepts_again_after_reabrir() -> None:
    cola = ColaQueRechazaEncolado(rechaza_todo_desde=UUID(int=2))
    with pytest.raises(redis.exceptions.ConnectionError):
        cola.encolar(UUID(int=2), AHORA)

    cola.reabrir()
    cola.encolar(UUID(int=3), AHORA)

    assert isinstance(cola, ColaEnMemoria)
    assert cola.elementos == {UUID(int=3): AHORA}
