"""Caso de uso: reprogramar un turno (PATCH parcial sobre la misma fila)."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from uuid import UUID

from app.application.validacion_turno import (
    Reloj,
    SolicitudTurno,
    ValidadorTurno,
    validar_solicitud_turno,
)
from app.domain.time import to_utc
from app.domain.turnos import (
    TurnoInexistenteError,
    TurnoRegistrado,
    validar_campos_editables,
    validar_modificable,
)
from app.infrastructure.db.repositorio_turnos import RepositorioTurnos

ObservadorReprogramacion = Callable[[TurnoRegistrado, TurnoRegistrado], None]
"""Punto de extensión (anterior, nuevo): efecto lateral antes del commit, misma transacción."""


class Omitido(Enum):
    """Centinela de "campo no enviado", distinto de un `None` explícito."""

    OMITIDO = "omitido"


OMITIDO = Omitido.OMITIDO


@dataclass(frozen=True)
class SolicitudReprogramacion:
    """Cambios pedidos; cada campo editable puede venir omitido (se conserva el actual)."""

    inicio: datetime | Omitido = OMITIDO
    profesional_id: UUID | Omitido = OMITIDO
    sillon_id: UUID | None | Omitido = OMITIDO
    duracion_min: int | Omitido = OMITIDO
    campos_no_editables: tuple[str, ...] = ()


def aplicar_cambios(actual: TurnoRegistrado, solicitud: SolicitudReprogramacion) -> SolicitudTurno:
    """Fusiona los cambios sobre el turno actual. Paciente y prestación nunca cambian.

    `sillon_id=None` explícito queda `None` (lo resuelve la validación compartida); la
    duración omitida conserva la del turno, incluso si estaba ajustada.
    """
    return SolicitudTurno(
        profesional_id=_valor(solicitud.profesional_id, actual.profesional_id),
        paciente_id=actual.paciente_id,
        prestacion_id=actual.prestacion_id,
        sillon_id=_valor(solicitud.sillon_id, actual.sillon_id),
        inicio=_valor(solicitud.inicio, actual.inicio),
        duracion_min=_valor(solicitud.duracion_min, actual.duracion_min),
    )


def _valor[T](pedido: T | Omitido, actual: T) -> T:
    return actual if isinstance(pedido, Omitido) else pedido


class ReprogramarTurno:
    def __init__(
        self,
        repositorio: RepositorioTurnos,
        reloj: Reloj,
        validadores: Sequence[ValidadorTurno] = (),
        observadores: Sequence[ObservadorReprogramacion] = (),
    ) -> None:
        self._repositorio = repositorio
        self._reloj = reloj
        self._validadores = validadores
        self._observadores = observadores

    def ejecutar(self, turno_id: UUID, solicitud: SolicitudReprogramacion) -> TurnoRegistrado:
        validar_campos_editables(solicitud.campos_no_editables)
        turno = self._repositorio.obtener_para_actualizar(turno_id)
        if turno is None:
            raise TurnoInexistenteError(turno_id)
        try:
            ahora = to_utc(self._reloj())
            validar_modificable(turno.estado, turno.inicio, ahora)
            propuesto = validar_solicitud_turno(
                self._repositorio,
                aplicar_cambios(turno, solicitud),
                ahora=ahora,
                validadores=self._validadores,
                excluir_id=turno.id,
            )
            nuevo = self._repositorio.actualizar(turno.id, propuesto)
            for observador in self._observadores:
                observador(turno, nuevo)
        except Exception:
            self._repositorio.rollback()  # libera el bloqueo y deja el turno intacto
            raise
        self._repositorio.commit()
        return nuevo
