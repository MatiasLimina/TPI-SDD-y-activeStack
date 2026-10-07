"""Caso de uso: crear un turno validando reglas de dominio y no superposición."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.domain.time import to_utc
from app.domain.turnos import (
    SolapamientoError,
    TurnoCreado,
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
"""Punto de extensión: lanza un error de dominio para cortar el alta."""
ObservadorTurno = Callable[[TurnoCreado], None]
"""Punto de extensión: efecto lateral dentro de la misma transacción, antes del commit."""


@dataclass(frozen=True)
class SolicitudTurno:
    profesional_id: UUID
    paciente_id: UUID
    prestacion_id: UUID
    sillon_id: UUID | None
    inicio: datetime
    duracion_min: int | None = None


class CrearTurno:
    def __init__(
        self,
        repositorio: RepositorioTurnos,
        reloj: Reloj,
        validadores: Sequence[ValidadorTurno] = (),
        observadores: Sequence[ObservadorTurno] = (),
    ) -> None:
        self._repositorio = repositorio
        self._reloj = reloj
        self._validadores = validadores
        self._observadores = observadores

    def ejecutar(self, solicitud: SolicitudTurno) -> TurnoCreado:
        referencias = self._repositorio.cargar_referencias(
            profesional_id=solicitud.profesional_id,
            paciente_id=solicitud.paciente_id,
            prestacion_id=solicitud.prestacion_id,
            sillon_id=solicitud.sillon_id,
        )
        inicio = to_utc(solicitud.inicio)
        duracion = duracion_efectiva(referencias.prestacion.duracion_min, solicitud.duracion_min)
        validar_duracion_y_grilla(inicio, duracion)
        validar_inicio_futuro(inicio, to_utc(self._reloj()))
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
        for validador in self._validadores:
            validador(propuesto)

        conflictos = self._repositorio.buscar_conflictos(
            propuesto.intervalo,
            profesional_id=propuesto.profesional_id,
            sillon_id=propuesto.sillon_id,
            paciente_id=propuesto.paciente_id,
        )
        if conflictos:
            raise SolapamientoError(conflictos)

        creado = self._repositorio.insertar(propuesto)
        try:
            for observador in self._observadores:
                observador(creado)
        except Exception:
            self._repositorio.rollback()
            raise
        self._repositorio.commit()
        return creado
