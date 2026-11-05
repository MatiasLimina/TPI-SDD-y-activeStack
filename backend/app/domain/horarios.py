"""Horarios de atención (RN-AG-05, RN-HB-01): franjas semanales y la regla "cabe en una franja".

`dia_semana`: 0 = lunes … 6 = domingo (convención de `date.weekday()`). Las horas son de pared
en la zona local, sin zona horaria. Sin base de datos ni HTTP.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, time
from zoneinfo import ZoneInfo

from app.domain.grilla import GRILLA_MIN
from app.domain.recursos import RecursoInvalidoError
from app.domain.time import to_local

MENSAJE_FUERA_DE_HORARIO = "el turno no cabe en el horario de atención del profesional"
MENSAJE_PROFESIONAL_AJENO = "Solo podés consultar tu propio horario"
MENSAJE_FRANJA_INVALIDA = (
    "la franja debe tener dia_semana entre 0 y 6 y hora_fin posterior a hora_inicio, "
    f"con horas en múltiplos de {GRILLA_MIN} minutos y sin zona horaria"
)


class FranjaSuperpuestaError(Exception):
    """La franja se superpone con otra del mismo profesional y día (se traduce a 409)."""

    def __init__(self) -> None:
        super().__init__("franja superpuesta")


class ProfesionalAjenoError(Exception):
    """Un odontólogo operó sobre un recurso de otro profesional (se traduce a 403).

    El mensaje por defecto es el del horario; cada recurso (p. ej. los bloqueos) pasa el suyo.
    """

    def __init__(self, mensaje: str = MENSAJE_PROFESIONAL_AJENO) -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje


@dataclass(frozen=True)
class Franja:
    dia_semana: int
    hora_inicio: time
    hora_fin: time


def _hora_en_grilla(hora: time) -> bool:
    return (
        hora.tzinfo is None
        and hora.second == 0
        and hora.microsecond == 0
        and hora.minute % GRILLA_MIN == 0
    )


def validar_franja(franja: Franja) -> None:
    """Lanza `franja_invalida` si el día, el orden de las horas o la grilla no se cumplen."""
    valida = (
        0 <= franja.dia_semana <= 6
        and _hora_en_grilla(franja.hora_inicio)
        and _hora_en_grilla(franja.hora_fin)
        and franja.hora_fin > franja.hora_inicio
    )
    if not valida:
        raise RecursoInvalidoError("franja_invalida", MENSAJE_FRANJA_INVALIDA)


def se_superponen(a: Franja, b: Franja) -> bool:
    """Mismo día e intervalos semiabiertos `[inicio, fin)` que se pisan."""
    return (
        a.dia_semana == b.dia_semana and a.hora_inicio < b.hora_fin and b.hora_inicio < a.hora_fin
    )


def cabe_en_horario(
    inicio_utc: datetime, fin_utc: datetime, franjas: Iterable[Franja], tz: str
) -> bool:
    """El turno, en hora local, cabe completo en una única franja del día local de su inicio."""
    zona = ZoneInfo(tz)
    inicio = to_local(inicio_utc, tz)
    fin = to_local(fin_utc, tz)
    return any(
        franja.dia_semana == inicio.weekday()
        and datetime.combine(inicio.date(), franja.hora_inicio, zona) <= inicio
        and fin <= datetime.combine(inicio.date(), franja.hora_fin, zona)
        for franja in franjas
    )
