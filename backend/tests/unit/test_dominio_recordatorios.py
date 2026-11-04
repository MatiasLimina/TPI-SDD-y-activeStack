from datetime import UTC, datetime, timedelta, timezone

import pytest

from app.domain.recordatorios import (
    MAX_INTENTOS,
    EstadoRecordatorio,
    calcular_programacion,
    espera_reintento,
)

AHORA = datetime(2026, 10, 7, 13, 0, tzinfo=UTC)  # 10:00 hora local
ANTICIPACION = timedelta(hours=24)


def test_calcular_programacion_with_more_than_lead_returns_inicio_minus_lead() -> None:
    inicio = AHORA + timedelta(hours=49)

    assert calcular_programacion(inicio, AHORA, ANTICIPACION) == inicio - ANTICIPACION


def test_calcular_programacion_with_exactly_lead_returns_ahora() -> None:
    inicio = AHORA + timedelta(hours=24)

    assert calcular_programacion(inicio, AHORA, ANTICIPACION) == AHORA


def test_calcular_programacion_with_less_than_lead_returns_none() -> None:
    inicio = AHORA + timedelta(hours=23, minutes=59)

    assert calcular_programacion(inicio, AHORA, ANTICIPACION) is None


@pytest.mark.parametrize(
    ("horas_por_delante", "esperado_programa"),
    [(47, False), (48, True), (49, True)],
)
def test_calcular_programacion_with_48h_lead_boundaries(
    horas_por_delante: int, esperado_programa: bool
) -> None:
    inicio = AHORA + timedelta(hours=horas_por_delante)

    resultado = calcular_programacion(inicio, AHORA, timedelta(hours=48))

    assert (resultado is not None) is esperado_programa


def test_calcular_programacion_returns_utc_for_offset_inicio() -> None:
    inicio = datetime(2026, 10, 9, 10, 0, tzinfo=timezone(timedelta(hours=-3)))

    resultado = calcular_programacion(inicio, AHORA, ANTICIPACION)

    assert resultado == datetime(2026, 10, 8, 13, 0, tzinfo=UTC)
    assert resultado is not None
    assert resultado.utcoffset() == timedelta(0)


def test_estado_recordatorio_has_exactly_the_four_states() -> None:
    assert {e.value for e in EstadoRecordatorio} == {
        "pendiente",
        "enviado",
        "fallido",
        "cancelado",
    }


def test_estado_recordatorio_compares_as_string() -> None:
    assert EstadoRecordatorio.PENDIENTE == "pendiente"


def test_max_intentos_is_three() -> None:
    assert MAX_INTENTOS == 3


@pytest.mark.parametrize(("intentos", "minutos"), [(1, 1), (2, 2)])
def test_espera_reintento_doubles_each_attempt(intentos: int, minutos: int) -> None:
    assert espera_reintento(intentos) == timedelta(minutes=minutos)
