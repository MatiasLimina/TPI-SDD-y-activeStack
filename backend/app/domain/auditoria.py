"""Auditoría de turnos: acciones y instantánea del turno. Puro, sin base de datos ni FastAPI."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from app.domain.time import to_utc
from app.domain.turnos import TurnoCreado, TurnoRegistrado

Instantanea = dict[str, str | int | None]
"""Valores del turno en un momento dado; mismas nueve claves antes y después (design D2)."""


class AccionAuditoria(StrEnum):
    CREAR = "crear"
    REPROGRAMAR = "reprogramar"
    CANCELAR = "cancelar"


@dataclass(frozen=True)
class RegistroAuditoria:
    """Registro de auditoría persistido (lectura)."""

    id: int
    turno_id: UUID
    usuario_id: UUID
    accion: AccionAuditoria
    valores_previos: Instantanea | None
    valores_nuevos: Instantanea
    ocurrido_en: datetime


def instantanea_turno(turno: TurnoCreado | TurnoRegistrado) -> Instantanea:
    """Instantánea completa y fija del turno: UUIDs como texto e instantes en UTC (RN-CU-04).

    No incluye datos personales del paciente (solo su id), ni el id del turno ni su autor:
    esos viven en el registro de auditoría.
    """
    motivo = turno.motivo_cancelacion if isinstance(turno, TurnoRegistrado) else None
    return {
        "profesional_id": str(turno.profesional_id),
        "paciente_id": str(turno.paciente_id),
        "prestacion_id": str(turno.prestacion_id),
        "sillon_id": None if turno.sillon_id is None else str(turno.sillon_id),
        "inicio": to_utc(turno.inicio).isoformat(),
        "fin": to_utc(turno.fin).isoformat(),
        "duracion_min": turno.duracion_min,
        "estado": turno.estado,
        "motivo_cancelacion": motivo,
    }
