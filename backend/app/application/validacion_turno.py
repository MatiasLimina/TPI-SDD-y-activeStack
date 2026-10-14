"""Validación compartida del alta y la reprogramación de turnos (RN-AG-08)."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.domain.time import to_utc
from app.domain.turnos import (
    SolapamientoError,
    TurnoPropuesto,
    calcular_fin,
    duracion_efectiva,
    validar_duracion_y_grilla,
    validar_inicio_futuro,
    validar_sillon,
)
from app.infrastructure.db.repositorio_turnos import RepositorioTurnos

Reloj = Callable[[], datetime]
"""Devuelve el instante actual con zona horaria (UTC)."""
ValidadorTurno = Callable[[TurnoPropuesto], None]
"""Punto de extensión: lanza un error de dominio para cortar el alta o la reprogramación."""


@dataclass(frozen=True)
class SolicitudTurno:
    profesional_id: UUID
    paciente_id: UUID
    prestacion_id: UUID
    sillon_id: UUID | None
    inicio: datetime
    duracion_min: int | None = None


def validar_solicitud_turno(
    repositorio: RepositorioTurnos,
    solicitud: SolicitudTurno,
    *,
    ahora: datetime,
    validadores: Sequence[ValidadorTurno] = (),
    excluir_id: UUID | None = None,
) -> TurnoPropuesto:
    """Valida la solicitud y devuelve el turno normalizado listo para persistir.

    Orden fijo: referencias, duración y grilla, inicio futuro, sillón, validadores inyectados
    y pre-chequeo de solape (`excluir_id` deja afuera al propio turno al reprogramar).
    """
    referencias = repositorio.cargar_referencias(
        profesional_id=solicitud.profesional_id,
        paciente_id=solicitud.paciente_id,
        prestacion_id=solicitud.prestacion_id,
        sillon_id=solicitud.sillon_id,
    )
    inicio = to_utc(solicitud.inicio)
    duracion = duracion_efectiva(referencias.prestacion.duracion_min, solicitud.duracion_min)
    validar_duracion_y_grilla(inicio, duracion)
    validar_inicio_futuro(inicio, ahora)
    validar_sillon(
        requiere_sillon=referencias.prestacion.requiere_sillon,
        sillon_informado=solicitud.sillon_id is not None,
    )
    propuesto = TurnoPropuesto(
        profesional_id=solicitud.profesional_id,
        paciente_id=solicitud.paciente_id,
        prestacion_id=solicitud.prestacion_id,
        sillon_id=solicitud.sillon_id,
        inicio=inicio,
        fin=calcular_fin(inicio, duracion),
        duracion_min=duracion,
    )
    for validador in validadores:
        validador(propuesto)

    conflictos = repositorio.buscar_conflictos(
        propuesto.intervalo,
        profesional_id=propuesto.profesional_id,
        sillon_id=propuesto.sillon_id,
        paciente_id=propuesto.paciente_id,
        excluir_id=excluir_id,
    )
    if conflictos:
        raise SolapamientoError(conflictos)
    return propuesto
