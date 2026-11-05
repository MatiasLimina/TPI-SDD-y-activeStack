"""Casos de uso de los bloqueos de agenda y su validador de turnos (RN-HB-02, RN-AG-06)."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.domain.bloqueos import (
    BloqueoConTurnosError,
    resolver_profesional,
    validar_bloqueo,
)
from app.domain.time import to_utc
from app.domain.turnos import Intervalo, ReferenciaInvalidaError
from app.domain.usuarios import UsuarioAutenticado
from app.infrastructure.db.models import Bloqueo
from app.infrastructure.db.repositorio_bloqueos import RepositorioBloqueos


@dataclass(frozen=True)
class SolicitudBloqueo:
    profesional_id: UUID | None
    inicio: datetime
    fin: datetime
    motivo: str


class CrearBloqueo:
    def __init__(self, repositorio: RepositorioBloqueos) -> None:
        self._repositorio = repositorio

    def ejecutar(self, usuario: UsuarioAutenticado, solicitud: SolicitudBloqueo) -> Bloqueo:
        """Orden fijo: profesional según el rol, lock y existencia, forma, turnos activos.

        El lock `FOR NO KEY UPDATE` del profesional serializa este alta con el alta y la
        reprogramación de turnos de ese profesional (D13): la consulta de turnos que sigue ve
        todo lo confirmado antes de tomarlo, y quien llegue después espera al commit.
        """
        profesional_id = resolver_profesional(usuario, solicitud.profesional_id)
        if self._repositorio.bloquear_profesional(profesional_id) is None:
            raise ReferenciaInvalidaError("profesional", "inexistente")
        motivo = validar_bloqueo(solicitud.inicio, solicitud.fin, solicitud.motivo)
        inicio, fin = to_utc(solicitud.inicio), to_utc(solicitud.fin)
        turnos = self._repositorio.turnos_activos_en(profesional_id, Intervalo(inicio, fin))
        if turnos:
            raise BloqueoConTurnosError(turnos)
        bloqueo = Bloqueo(
            profesional_id=profesional_id,
            inicio=inicio,
            fin=fin,
            motivo=motivo,
            creado_por=usuario.id,
        )
        self._repositorio.agregar(bloqueo)
        self._repositorio.commit()
        return bloqueo
