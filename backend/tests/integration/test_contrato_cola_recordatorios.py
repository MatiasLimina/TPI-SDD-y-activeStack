"""Contrato de la cola de recordatorios: lo cumplen `ColaRedis` (Redis real) y `ColaEnMemoria`."""

import threading
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
import redis

from app.domain.recordatorios import ColaRecordatorios
from app.infrastructure.queue.cola_redis import ColaRedis
from tests.conftest import REDIS_HINT, get_test_redis_url
from tests.fakes import ColaEnMemoria

T0 = datetime(2026, 10, 8, 13, 0, tzinfo=UTC)
R1, R2, R3 = UUID(int=1), UUID(int=2), UUID(int=3)


@pytest.fixture
def cliente_redis() -> Iterator[redis.Redis]:
    cliente = redis.Redis.from_url(
        get_test_redis_url(),
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=2,
    )
    try:
        cliente.ping()
    except redis.exceptions.RedisError:
        pytest.fail(f"No se pudo conectar a Redis de test. {REDIS_HINT}", pytrace=False)
    yield cliente
    cliente.close()


@pytest.fixture(params=["redis", "memoria"])
def cola(request: pytest.FixtureRequest) -> Iterator[ColaRecordatorios]:
    if request.param == "memoria":
        yield ColaEnMemoria()
        return
    cliente: redis.Redis = request.getfixturevalue("cliente_redis")
    clave = f"test:recordatorios:{uuid4()}"
    try:
        yield ColaRedis(cliente, clave)
    finally:
        cliente.delete(clave)


def test_tomar_vencidos_delivers_only_due_items_in_order(cola: ColaRecordatorios) -> None:
    cola.encolar(R1, T0 + timedelta(minutes=5))
    cola.encolar(R2, T0)
    cola.encolar(R3, T0 + timedelta(hours=1))

    vencidos = cola.tomar_vencidos(T0 + timedelta(minutes=10), 10)

    assert vencidos == [R2, R1]
    assert cola.tomar_vencidos(T0 + timedelta(minutes=59), 10) == []
    assert cola.tomar_vencidos(T0 + timedelta(hours=1), 10) == [R3]


def test_tomar_vencidos_includes_item_due_exactly_now(cola: ColaRecordatorios) -> None:
    cola.encolar(R1, T0)

    assert cola.tomar_vencidos(T0, 10) == [R1]


def test_tomar_vencidos_on_empty_queue_returns_empty_list(cola: ColaRecordatorios) -> None:
    assert cola.tomar_vencidos(T0, 10) == []


def test_tomar_vencidos_delivers_a_due_item_only_once(cola: ColaRecordatorios) -> None:
    cola.encolar(R1, T0)

    primero = cola.tomar_vencidos(T0, 10)
    segundo = cola.tomar_vencidos(T0, 10)

    assert primero == [R1]
    assert segundo == []


def test_encolar_again_replaces_the_due_time_without_duplicating(cola: ColaRecordatorios) -> None:
    cola.encolar(R1, T0)

    cola.encolar(R1, T0 + timedelta(minutes=2))

    assert cola.tomar_vencidos(T0 + timedelta(minutes=1), 10) == []
    assert cola.tomar_vencidos(T0 + timedelta(minutes=2), 10) == [R1]
    assert cola.tomar_vencidos(T0 + timedelta(minutes=3), 10) == []


def test_encolar_again_can_bring_the_due_time_forward(cola: ColaRecordatorios) -> None:
    cola.encolar(R1, T0 + timedelta(hours=1))

    cola.encolar(R1, T0)

    assert cola.tomar_vencidos(T0, 10) == [R1]


@pytest.mark.parametrize(("limite", "esperados"), [(1, [R1]), (2, [R1, R2]), (10, [R1, R2, R3])])
def test_tomar_vencidos_limit_bounds_the_delivered_items(
    cola: ColaRecordatorios, limite: int, esperados: list[UUID]
) -> None:
    for posicion, recordatorio_id in enumerate((R1, R2, R3)):
        cola.encolar(recordatorio_id, T0 + timedelta(seconds=posicion))

    entregados = cola.tomar_vencidos(T0 + timedelta(minutes=1), limite)

    assert entregados == esperados
    restantes = cola.tomar_vencidos(T0 + timedelta(minutes=1), 10)
    assert restantes == [R1, R2, R3][limite:]


def test_consumidores_simultaneos_no_comparten_elementos(cola: ColaRecordatorios) -> None:
    """Dos hilos con una barrera piden lotes hasta vaciar la cola: entre ambos, los 50 una vez."""
    ids = [UUID(int=1000 + i) for i in range(50)]
    for i, recordatorio_id in enumerate(ids):
        cola.encolar(recordatorio_id, T0 + timedelta(seconds=i))
    recibidos: list[list[UUID]] = [[], []]
    errores: list[BaseException] = []
    barrera = threading.Barrier(2)

    def consumir(indice: int) -> None:
        try:
            barrera.wait(timeout=5)
            while lote := cola.tomar_vencidos(T0 + timedelta(hours=1), 3):
                recibidos[indice].extend(lote)
        except BaseException as error:  # noqa: BLE001 - se re-verifica en el hilo principal
            errores.append(error)

    hilos = [threading.Thread(target=consumir, args=(i,)) for i in range(2)]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join(timeout=10)

    assert errores == []
    assert set(recibidos[0]).isdisjoint(recibidos[1])
    assert sorted(recibidos[0] + recibidos[1]) == sorted(ids)
