"""Bloqueos de agenda (RN-HB-02, RN-HB-03, RN-AG-06): reglas puras, sin base ni HTTP."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.domain.horarios import ProfesionalAjenoError
from app.domain.usuarios import Rol, UsuarioAutenticado

MENSAJE_BLOQUEO_INVALIDO = "el bloqueo debe tener fin posterior a inicio y un motivo no vacío"
MENSAJE_PROFESIONAL_REQUERIDO = "indicá el profesional del bloqueo"
MENSAJE_BLOQUEO_CON_TURNOS = (
    "hay turnos activos en el intervalo: reprogramalos o cancelalos antes de bloquear"
)
MENSAJE_TURNO_EN_BLOQUEO = "el turno se superpone con un bloqueo de agenda del profesional"
MENSAJE_BLOQUEO_AJENO = "Solo podés operar sobre tus propios bloqueos"


class BloqueoInvalidoError(Exception):
    """El bloqueo tiene `fin <= inicio` o un motivo vacío (se traduce a 422)."""

    def __init__(self, mensaje: str = MENSAJE_BLOQUEO_INVALIDO) -> None:
        super().__init__(mensaje)
        self.codigo = "bloqueo_invalido"
        self.mensaje = mensaje


class ProfesionalRequeridoError(Exception):
    """La recepcionista no indicó el profesional del bloqueo (se traduce a 422)."""

    def __init__(self, mensaje: str = MENSAJE_PROFESIONAL_REQUERIDO) -> None:
        super().__init__(mensaje)
        self.codigo = "profesional_requerido"
        self.mensaje = mensaje


@dataclass(frozen=True)
class TurnoAfectado:
    """Turno activo que impide un bloqueo; sin datos del paciente ni de la prestación (D9)."""

    id: UUID
    inicio: datetime
    fin: datetime


class BloqueoConTurnosError(Exception):
    """El intervalo del bloqueo pisa turnos activos del profesional (se traduce a 409)."""

    def __init__(self, turnos: Sequence[TurnoAfectado]) -> None:
        super().__init__(MENSAJE_BLOQUEO_CON_TURNOS)
        self.codigo = "bloqueo_con_turnos"
        self.mensaje = MENSAJE_BLOQUEO_CON_TURNOS
        self.turnos: tuple[TurnoAfectado, ...] = tuple(turnos)


def validar_bloqueo(inicio: datetime, fin: datetime, motivo: str) -> str:
    """Devuelve el motivo sin espacios extremos o lanza `BloqueoInvalidoError` (D7).

    El largo máximo lo valida el schema de la API; acá solo el intervalo y el motivo no vacío.
    """
    normalizado = motivo.strip()
    if fin <= inicio or not normalizado:
        raise BloqueoInvalidoError
    return normalizado


def resolver_profesional(usuario: UsuarioAutenticado, profesional_id: UUID | None) -> UUID:
    """Profesional del bloqueo según el rol (D1, Flujo 5).

    El odontólogo opera siempre sobre el suyo: lo omite o lo informa igual; otro (exista o no)
    es `ProfesionalAjenoError`, antes de mirar la base. La recepcionista debe informarlo.
    """
    if usuario.rol == Rol.ODONTOLOGO:
        if profesional_id is not None and profesional_id != usuario.profesional_id:
            raise ProfesionalAjenoError(MENSAJE_BLOQUEO_AJENO)
        assert usuario.profesional_id is not None  # lo garantiza el CHECK de `usuario`
        return usuario.profesional_id
    if profesional_id is None:
        raise ProfesionalRequeridoError
    return profesional_id
