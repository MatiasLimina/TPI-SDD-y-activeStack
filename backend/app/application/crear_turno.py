"""Caso de uso: crear un turno validando reglas de dominio y no superposición."""

from collections.abc import Callable, Sequence

from app.application.validacion_turno import (
    Reloj,
    SolicitudTurno,
    ValidadorTurno,
    validar_solicitud_turno,
)
from app.domain.time import to_utc
from app.domain.turnos import TurnoCreado
from app.infrastructure.db.repositorio_turnos import RepositorioTurnos

__all__ = ["CrearTurno", "ObservadorTurno", "Reloj", "SolicitudTurno", "ValidadorTurno"]

ObservadorTurno = Callable[[TurnoCreado], None]
"""Punto de extensión: efecto lateral dentro de la misma transacción, antes del commit."""


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
        propuesto = validar_solicitud_turno(
            self._repositorio,
            solicitud,
            ahora=to_utc(self._reloj()),
            validadores=self._validadores,
        )
        creado = self._repositorio.insertar(propuesto)
        try:
            for observador in self._observadores:
                observador(creado)
        except Exception:
            self._repositorio.rollback()
            raise
        self._repositorio.commit()
        return creado
