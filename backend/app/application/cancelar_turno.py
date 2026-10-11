"""Caso de uso: cancelar un turno programado antes de su inicio."""

from collections.abc import Callable, Sequence
from uuid import UUID

from app.application.crear_turno import Reloj
from app.domain.time import to_utc
from app.domain.turnos import (
    TurnoInexistenteError,
    TurnoRegistrado,
    normalizar_motivo,
    validar_cancelable,
)
from app.infrastructure.db.repositorio_turnos import RepositorioTurnos

ObservadorCancelacion = Callable[[TurnoRegistrado], None]
"""Punto de extensión: efecto lateral dentro de la misma transacción, antes del commit."""


class CancelarTurno:
    def __init__(
        self,
        repositorio: RepositorioTurnos,
        reloj: Reloj,
        observadores: Sequence[ObservadorCancelacion] = (),
    ) -> None:
        self._repositorio = repositorio
        self._reloj = reloj
        self._observadores = observadores

    def ejecutar(self, turno_id: UUID, motivo: str | None) -> TurnoRegistrado:
        motivo_normalizado = normalizar_motivo(motivo)
        turno = self._repositorio.obtener_para_actualizar(turno_id)
        if turno is None:
            raise TurnoInexistenteError(turno_id)
        try:
            validar_cancelable(turno.estado, turno.inicio, to_utc(self._reloj()))
        except Exception:
            self._repositorio.rollback()  # libera el bloqueo de la fila
            raise

        cancelado = self._repositorio.marcar_cancelado(turno_id, motivo_normalizado)
        try:
            for observador in self._observadores:
                observador(cancelado)
        except Exception:
            self._repositorio.rollback()
            raise
        self._repositorio.commit()
        return cancelado
