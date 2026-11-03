"""Arranque y bucle del worker con dependencias inyectadas (sin Redis ni base reales)."""

import threading
from datetime import UTC, datetime

import pytest

from app import worker
from app.application.recordatorios import WorkerRecordatorios
from app.config import ConfiguracionWorker

AHORA = datetime(2026, 10, 8, 13, 0, tzinfo=UTC)


class WorkerFalso:
    """Registra el orden de las llamadas y devuelve cuántos vencidos 'procesó' por ciclo."""

    def __init__(self, procesados_por_ciclo: list[int] | None = None) -> None:
        self.llamadas: list[tuple[str, datetime | None]] = []
        self._procesados = list(procesados_por_ciclo or [])

    def iniciar(self) -> int:
        self.llamadas.append(("iniciar", None))
        return 0

    def ciclo(self, ahora: datetime) -> int:
        self.llamadas.append(("ciclo", ahora))
        return self._procesados.pop(0) if self._procesados else 0


def test_correr_calls_iniciar_once_and_then_ciclo_with_the_injected_clock() -> None:
    falso = WorkerFalso()

    ciclos = worker.correr(
        falso, reloj=lambda: AHORA, detenido=threading.Event(), pausa_s=0, max_ciclos=1
    )

    assert ciclos == 1
    assert falso.llamadas == [("iniciar", None), ("ciclo", AHORA)]


@pytest.mark.parametrize("max_ciclos", [1, 3])
def test_correr_stops_after_max_ciclos(max_ciclos: int) -> None:
    falso = WorkerFalso()

    ciclos = worker.correr(
        falso, reloj=lambda: AHORA, detenido=threading.Event(), pausa_s=0, max_ciclos=max_ciclos
    )

    assert ciclos == max_ciclos
    assert [nombre for nombre, _ in falso.llamadas] == ["iniciar"] + ["ciclo"] * max_ciclos


def test_correr_with_stop_already_requested_does_not_run_any_cycle() -> None:
    falso = WorkerFalso()
    detenido = threading.Event()
    detenido.set()

    ciclos = worker.correr(falso, reloj=lambda: AHORA, detenido=detenido, pausa_s=0)

    assert ciclos == 0
    assert [nombre for nombre, _ in falso.llamadas] == ["iniciar"]


def test_correr_exits_cleanly_when_stop_is_requested_during_a_cycle() -> None:
    detenido = threading.Event()

    class PideDetenerse(WorkerFalso):
        def ciclo(self, ahora: datetime) -> int:
            detenido.set()
            return super().ciclo(ahora)

    falso = PideDetenerse()

    ciclos = worker.correr(falso, reloj=lambda: AHORA, detenido=detenido, pausa_s=60)

    assert ciclos == 1


def test_correr_does_not_pause_when_there_was_work() -> None:
    """Con trabajo pendiente encadena ciclos; con la cola vacía espera `pausa_s` o el stop."""
    esperas: list[float] = []

    class EventoEspiado(threading.Event):
        def wait(self, timeout: float | None = None) -> bool:
            esperas.append(-1.0 if timeout is None else timeout)
            return super().wait(0)

    espiado = EventoEspiado()
    falso = WorkerFalso([3, 0, 0])

    worker.correr(falso, reloj=lambda: AHORA, detenido=espiado, pausa_s=5, max_ciclos=3)

    assert esperas == [5]


def test_correr_propagates_unexpected_errors() -> None:
    class Roto(WorkerFalso):
        def ciclo(self, ahora: datetime) -> int:
            raise RuntimeError("error inesperado de la base")

    with pytest.raises(RuntimeError, match="base"):
        worker.correr(Roto(), reloj=lambda: AHORA, detenido=threading.Event(), pausa_s=0)


def test_construir_worker_wires_the_worker_without_connecting() -> None:
    config = ConfiguracionWorker(
        _env_file=None,
        DATABASE_URL="postgresql+psycopg://user:pass@localhost:5432/ficticia",
        REDIS_URL="redis://localhost:6379/9",
    )

    armado = worker.construir_worker(config)

    assert isinstance(armado.worker, WorkerRecordatorios)
    armado.cerrar()
