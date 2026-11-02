"""Reglas de dominio del catálogo (profesionales, sillones, prestaciones), sin base ni HTTP."""

from collections.abc import Iterable
from enum import StrEnum

from app.domain.grilla import MENSAJE_DURACION_INVALIDA, duracion_en_grilla


class TipoRecurso(StrEnum):
    PROFESIONAL = "profesional"
    SILLON = "sillon"
    PRESTACION = "prestacion"


class RecursoError(Exception):
    """Base de los errores de dominio del catálogo."""


class RecursoInvalidoError(RecursoError):
    """Regla de dominio violada (se traduce a 422)."""

    def __init__(self, codigo: str, mensaje: str) -> None:
        super().__init__(mensaje)
        self.codigo = codigo
        self.mensaje = mensaje


class RecursoInexistenteError(RecursoError):
    """El recurso del path no existe (se traduce a 404)."""

    def __init__(self, tipo: TipoRecurso) -> None:
        super().__init__(f"{tipo.value} inexistente")
        self.tipo = tipo


class RecursoDuplicadoError(RecursoError):
    """Nombre o matrícula ya usado por otro recurso (se traduce a 409)."""

    def __init__(self, tipo: TipoRecurso, campo: str) -> None:
        super().__init__(f"{tipo.value} duplicado en {campo}")
        self.tipo = tipo
        self.campo = campo


class EstadoNoEditableError(RecursoError):
    """El body intentó fijar el estado de actividad: solo cambia con /desactivar (422)."""

    def __init__(self, campos: Iterable[str]) -> None:
        self.campos: tuple[str, ...] = tuple(campos)
        self.mensaje = "El estado de actividad no se edita: para dar de baja usá /desactivar"
        super().__init__(self.mensaje)


def validar_duracion_prestacion(duracion_min: int) -> None:
    """La duración de una prestación cumple la misma regla que la de un turno (DD-15)."""
    if not duracion_en_grilla(duracion_min):
        raise RecursoInvalidoError("duracion_invalida", MENSAJE_DURACION_INVALIDA)


def normalizar_matricula(valor: str | None) -> str | None:
    """Matrícula sin espacios extremos; vacía equivale a no tener (DD-26)."""
    if valor is None:
        return None
    return valor.strip() or None
