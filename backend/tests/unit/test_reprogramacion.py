"""Fusión pura de los cambios de una reprogramación sobre el turno actual."""

import ast
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from app.application.reprogramar_turno import OMITIDO, SolicitudReprogramacion, aplicar_cambios
from app.application.validacion_turno import SolicitudTurno
from app.domain.turnos import TurnoRegistrado

INICIO = datetime(2026, 10, 8, 13, 0, tzinfo=UTC)


def _actual(*, duracion: int = 60, sillon: UUID | None = None) -> TurnoRegistrado:
    return TurnoRegistrado(
        id=uuid4(),
        profesional_id=uuid4(),
        paciente_id=uuid4(),
        prestacion_id=uuid4(),
        sillon_id=uuid4() if sillon is None else sillon,
        inicio=INICIO,
        fin=INICIO + timedelta(minutes=duracion),
        duracion_min=duracion,
        estado="programado",
        motivo_cancelacion=None,
    )


def test_aplicar_cambios_sin_cambios_reproduce_el_turno_actual_con_su_duracion_ajustada() -> None:
    actual = _actual(duracion=60)  # prestación de 45 con duración ajustada a 60

    resultado = aplicar_cambios(actual, SolicitudReprogramacion())

    assert resultado == SolicitudTurno(
        profesional_id=actual.profesional_id,
        paciente_id=actual.paciente_id,
        prestacion_id=actual.prestacion_id,
        sillon_id=actual.sillon_id,
        inicio=actual.inicio,
        duracion_min=60,
    )


def test_aplicar_cambios_con_otra_duracion_ajustada_la_conserva() -> None:
    actual = _actual(duracion=90)

    assert aplicar_cambios(actual, SolicitudReprogramacion()).duracion_min == 90


def test_aplicar_cambios_solo_inicio_conserva_el_resto() -> None:
    actual = _actual()
    nuevo = INICIO + timedelta(days=1)

    resultado = aplicar_cambios(actual, SolicitudReprogramacion(inicio=nuevo))

    assert resultado.inicio == nuevo
    assert resultado.duracion_min == actual.duracion_min
    assert resultado.profesional_id == actual.profesional_id
    assert resultado.sillon_id == actual.sillon_id


def test_aplicar_cambios_solo_duracion_conserva_el_inicio() -> None:
    actual = _actual(duracion=45)

    resultado = aplicar_cambios(actual, SolicitudReprogramacion(duracion_min=90))

    assert resultado.duracion_min == 90
    assert resultado.inicio == actual.inicio


def test_aplicar_cambios_solo_profesional_conserva_el_resto() -> None:
    actual = _actual()
    otro = uuid4()

    resultado = aplicar_cambios(actual, SolicitudReprogramacion(profesional_id=otro))

    assert resultado.profesional_id == otro
    assert resultado.sillon_id == actual.sillon_id
    assert resultado.inicio == actual.inicio


def test_aplicar_cambios_con_sillon_informado_lo_reemplaza() -> None:
    actual = _actual()
    otro = uuid4()

    assert aplicar_cambios(actual, SolicitudReprogramacion(sillon_id=otro)).sillon_id == otro


def test_aplicar_cambios_con_sillon_nulo_explicito_queda_sin_sillon() -> None:
    actual = _actual()

    resultado = aplicar_cambios(actual, SolicitudReprogramacion(sillon_id=None))

    assert resultado.sillon_id is None


def test_aplicar_cambios_sillon_omitido_se_distingue_de_nulo() -> None:
    actual = _actual()

    omitido = aplicar_cambios(actual, SolicitudReprogramacion(sillon_id=OMITIDO))
    nulo = aplicar_cambios(actual, SolicitudReprogramacion(sillon_id=None))

    assert omitido.sillon_id == actual.sillon_id
    assert nulo.sillon_id is None


def test_aplicar_cambios_paciente_y_prestacion_salen_siempre_del_turno_actual() -> None:
    actual = _actual()
    solicitud = SolicitudReprogramacion(
        inicio=INICIO + timedelta(hours=1),
        profesional_id=uuid4(),
        sillon_id=uuid4(),
        duracion_min=30,
        campos_no_editables=("paciente_id", "prestacion_id"),
    )

    resultado = aplicar_cambios(actual, solicitud)

    assert resultado.paciente_id == actual.paciente_id
    assert resultado.prestacion_id == actual.prestacion_id


def _modulos_importados(modulo: str) -> set[str]:
    ruta = Path(__file__).parents[2] / "app" / "application" / f"{modulo}.py"
    importados: set[str] = set()
    for nodo in ast.walk(ast.parse(ruta.read_text("utf-8"))):
        if isinstance(nodo, ast.Import):
            importados.update(alias.name.split(".")[0] for alias in nodo.names)
        elif isinstance(nodo, ast.ImportFrom) and nodo.module and nodo.level == 0:
            importados.add(nodo.module.split(".")[0])
    return importados


@pytest.mark.parametrize("modulo", ["reprogramar_turno", "validacion_turno"])
def test_la_capa_de_aplicacion_no_importa_sqlalchemy_ni_fastapi_directamente(modulo: str) -> None:
    importados = _modulos_importados(modulo)

    assert "app" in importados  # el parseo detecta imports reales
    assert importados.isdisjoint({"sqlalchemy", "fastapi"})
