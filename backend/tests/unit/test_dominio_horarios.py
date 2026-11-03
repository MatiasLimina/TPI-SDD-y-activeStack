"""Reglas de dominio de los horarios de atención (RN-AG-05, RN-HB-01), sin base de datos."""

import ast
from datetime import UTC, datetime, time, timedelta, timezone
from pathlib import Path

import pytest

from app.domain import horarios
from app.domain.horarios import Franja, cabe_en_horario, se_superponen, validar_franja
from app.domain.recursos import RecursoInvalidoError
from app.domain.time import DEFAULT_TIMEZONE


def _franja(dia: int, inicio: time, fin: time) -> Franja:
    return Franja(dia_semana=dia, hora_inicio=inicio, hora_fin=fin)


@pytest.mark.parametrize(
    "franja",
    [
        _franja(0, time(9, 0), time(13, 0)),
        _franja(6, time(0, 0), time(23, 55)),
    ],
)
def test_validar_franja_acepta_franjas_validas(franja: Franja) -> None:
    validar_franja(franja)


@pytest.mark.parametrize(
    "franja",
    [
        _franja(0, time(9, 0), time(9, 0)),
        _franja(0, time(22, 0), time(2, 0)),
        _franja(7, time(9, 0), time(13, 0)),
        _franja(-1, time(9, 0), time(13, 0)),
        _franja(0, time(9, 7), time(13, 0)),
        _franja(0, time(9, 0), time(13, 0, 30)),
        _franja(0, time(9, 0, 0, 5), time(13, 0)),
        _franja(0, time(9, 0, tzinfo=timezone(timedelta(hours=-3))), time(13, 0)),
    ],
)
def test_validar_franja_rechaza_con_codigo_franja_invalida(franja: Franja) -> None:
    with pytest.raises(RecursoInvalidoError) as excinfo:
        validar_franja(franja)

    assert excinfo.value.codigo == "franja_invalida"


def test_el_dominio_de_horarios_no_importa_sqlalchemy_ni_fastapi() -> None:
    arbol = ast.parse(Path(horarios.__file__).read_text(encoding="utf-8"))
    importados = {
        (nodo.module or "") if isinstance(nodo, ast.ImportFrom) else alias.name
        for nodo in ast.walk(arbol)
        if isinstance(nodo, ast.Import | ast.ImportFrom)
        for alias in (nodo.names if isinstance(nodo, ast.Import) else [None])
    }

    assert not any(m.split(".")[0] in {"sqlalchemy", "fastapi"} for m in importados)


@pytest.mark.parametrize(
    ("otra", "esperado"),
    [
        (_franja(0, time(12, 0), time(15, 0)), True),
        (_franja(0, time(10, 0), time(11, 0)), True),
        (_franja(0, time(13, 0), time(17, 0)), False),
        (_franja(0, time(7, 0), time(9, 0)), False),
        (_franja(1, time(9, 0), time(13, 0)), False),
    ],
)
def test_se_superponen_usa_intervalos_semiabiertos_y_el_mismo_dia(
    otra: Franja, esperado: bool
) -> None:
    base = _franja(0, time(9, 0), time(13, 0))

    assert se_superponen(base, otra) is esperado
    assert se_superponen(otra, base) is esperado


def _utc(dia: int, hora: int, minuto: int = 0) -> datetime:
    return datetime(2026, 10, dia, hora, minuto, tzinfo=UTC)


JUEVES = 3
MANANA = _franja(JUEVES, time(9, 0), time(13, 0))
TARDE = _franja(JUEVES, time(14, 0), time(18, 0))


@pytest.mark.parametrize(
    ("inicio", "minutos", "franjas", "esperado"),
    [
        # 10:00 local = 13:00Z
        (_utc(8, 13), 45, [MANANA], True),
        (_utc(8, 12), 45, [MANANA], True),  # abre justo
        (_utc(8, 15, 15), 45, [MANANA], True),  # 12:15-13:00, cierra justo
        (_utc(8, 15, 30), 45, [MANANA], False),  # 12:30-13:15 excede
        (_utc(8, 11, 30), 45, [MANANA], False),  # 08:30-09:15 antes
        (_utc(8, 18), 45, [MANANA, TARDE], True),  # 15:00 segunda franja
        (_utc(8, 16, 15), 30, [MANANA, TARDE], False),  # 13:15 hueco
        (_utc(8, 15, 30), 120, [MANANA, TARDE], False),  # 12:30-14:30 cruza
        (_utc(8, 15, 30), 60, [MANANA, _franja(JUEVES, time(13, 0), time(17, 0))], False),
        (_utc(10, 13), 45, [MANANA], False),  # sábado
        (_utc(8, 13), 45, [], False),
        (_utc(8, 15, 30), 45, [MANANA, TARDE], False),  # 15:30Z es 12:30 local, no UTC
        (_utc(9, 1), 45, [_franja(JUEVES, time(21, 0), time(23, 0))], True),  # jueves 22:00 local
        (_utc(9, 2, 30), 45, [_franja(JUEVES, time(0, 0), time(23, 55))], False),  # 23:30-00:15
    ],
)
def test_cabe_en_horario_evalua_en_hora_local_y_en_una_unica_franja(
    inicio: datetime, minutos: int, franjas: list[Franja], esperado: bool
) -> None:
    fin = inicio + timedelta(minutes=minutos)

    assert cabe_en_horario(inicio, fin, franjas, DEFAULT_TIMEZONE) is esperado
