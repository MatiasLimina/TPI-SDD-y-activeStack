"""Reglas de dominio de turnos: puras, sin base de datos, FastAPI ni reloj propio."""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal, Self
from uuid import UUID

from app.domain.time import to_local

GRILLA_MIN = 5
DURACION_MAX_MIN = 480


Recurso = Literal["profesional", "sillon", "paciente"]
ORDEN_RECURSOS: tuple[Recurso, ...] = ("profesional", "sillon", "paciente")


class TurnoError(Exception):
    """Base de los errores de dominio de turnos."""


class TurnoInvalidoError(TurnoError):
    """Regla de dominio violada (se traduce a 422)."""

    def __init__(self, codigo: str, mensaje: str) -> None:
        super().__init__(mensaje)
        self.codigo = codigo
        self.mensaje = mensaje


@dataclass(frozen=True)
class Intervalo:
    """Intervalo semiabierto [inicio, fin) entre dos instantes con zona horaria."""

    inicio: datetime
    fin: datetime


class ReferenciaInvalidaError(TurnoError):
    """Una referencia del body no existe o está inactiva (se traduce a 422)."""

    def __init__(self, referencia: str, motivo: Literal["inexistente", "inactiva"]) -> None:
        super().__init__(f"{referencia} {motivo}")
        self.referencia = referencia
        self.motivo = motivo


class SolapamientoError(TurnoError):
    """Solape con otro turno activo (se traduce a 409). Recursos en orden fijo."""

    def __init__(self, recursos: Iterable[Recurso]) -> None:
        conjunto = set(recursos)
        self.recursos: tuple[Recurso, ...] = tuple(r for r in ORDEN_RECURSOS if r in conjunto)
        super().__init__(f"solapamiento en: {', '.join(self.recursos)}")


@dataclass(frozen=True)
class TurnoPropuesto:
    """Turno ya normalizado (UTC, duración efectiva, fin calculado) antes de persistirse."""

    profesional_id: UUID
    paciente_id: UUID
    prestacion_id: UUID
    sillon_id: UUID | None
    inicio: datetime
    fin: datetime
    duracion_min: int

    @property
    def intervalo(self) -> Intervalo:
        return Intervalo(self.inicio, self.fin)


@dataclass(frozen=True)
class TurnoCreado:
    """Turno persistido."""

    id: UUID
    profesional_id: UUID
    paciente_id: UUID
    prestacion_id: UUID
    sillon_id: UUID | None
    inicio: datetime
    fin: datetime
    duracion_min: int
    estado: str = "programado"
    creado_por: UUID | None = None

    @classmethod
    def desde_propuesto(cls, propuesto: TurnoPropuesto, *, id: UUID) -> Self:
        return cls(
            id=id,
            profesional_id=propuesto.profesional_id,
            paciente_id=propuesto.paciente_id,
            prestacion_id=propuesto.prestacion_id,
            sillon_id=propuesto.sillon_id,
            inicio=propuesto.inicio,
            fin=propuesto.fin,
            duracion_min=propuesto.duracion_min,
        )


def solapan(a: Intervalo, b: Intervalo) -> bool:
    """Dos intervalos semiabiertos se solapan solo si a.inicio < b.fin y b.inicio < a.fin."""
    return a.inicio < b.fin and b.inicio < a.fin


def duracion_efectiva(duracion_prestacion: int, duracion_informada: int | None) -> int:
    """La duración informada reemplaza a la de la prestación (RN-AG-04)."""
    return duracion_prestacion if duracion_informada is None else duracion_informada


def calcular_fin(inicio: datetime, duracion_min: int) -> datetime:
    return inicio + timedelta(minutes=duracion_min)


def validar_duracion_y_grilla(inicio: datetime, duracion_min: int) -> None:
    """Duración en (0, 480] múltiplo de 5 e inicio alineado a 5 min en hora local (DD-15)."""
    if duracion_min <= 0 or duracion_min % GRILLA_MIN != 0 or duracion_min > DURACION_MAX_MIN:
        raise TurnoInvalidoError(
            "duracion_invalida",
            f"la duración debe ser múltiplo de {GRILLA_MIN} entre {GRILLA_MIN} "
            f"y {DURACION_MAX_MIN} minutos",
        )
    local = to_local(inicio)
    if local.minute % GRILLA_MIN != 0 or local.second != 0 or local.microsecond != 0:
        raise TurnoInvalidoError(
            "inicio_no_alineado",
            f"el inicio debe estar alineado a {GRILLA_MIN} minutos (hora local)",
        )


def validar_inicio_futuro(inicio: datetime, ahora: datetime) -> None:
    """El inicio no puede ser anterior al instante actual (RN-AG-12)."""
    if inicio < ahora:
        raise TurnoInvalidoError("inicio_en_pasado", "el inicio no puede estar en el pasado")


def validar_sillon(*, requiere_sillon: bool, sillon_informado: bool) -> None:
    """Coherencia entre la prestación y el sillón (RN-AG-10, DD-21)."""
    if requiere_sillon and not sillon_informado:
        raise TurnoInvalidoError("sillon_requerido", "la prestación requiere un sillón")
    if not requiere_sillon and sillon_informado:
        raise TurnoInvalidoError(
            "sillon_no_corresponde", "la prestación no requiere sillón y se informó uno"
        )
