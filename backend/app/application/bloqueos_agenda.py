"""Casos de uso de los bloqueos de agenda y su validador de turnos (RN-HB-02, RN-AG-06)."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.domain.bloqueos import (
    MENSAJE_BLOQUEO_AJENO,
    MENSAJE_TURNO_EN_BLOQUEO,
    BloqueoConTurnosError,
    resolver_profesional,
    validar_bloqueo,
)
from app.domain.horarios import ProfesionalAjenoError
from app.domain.recursos import RecursoInexistenteError, TipoRecurso
from app.domain.time import to_utc
from app.domain.turnos import Intervalo, ReferenciaInvalidaError, TurnoInvalidoError, TurnoPropuesto
from app.domain.usuarios import Rol, UsuarioAutenticado
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


class ConsultarBloqueos:
    def __init__(self, repositorio: RepositorioBloqueos) -> None:
        self._repositorio = repositorio

    def ejecutar(self, usuario: UsuarioAutenticado, profesional_id: UUID | None) -> list[Bloqueo]:
        """La recepcionista ve todos o los del filtro; el odontólogo, solo los de su profesional.

        Un filtro ajeno del odontólogo se rechaza antes de buscar nada (no revela existencia).
        """
        if usuario.rol == Rol.ODONTOLOGO:
            profesional_id = resolver_profesional(usuario, profesional_id)
        return self._repositorio.listar(profesional_id)


class BorrarBloqueo:
    def __init__(self, repositorio: RepositorioBloqueos) -> None:
        self._repositorio = repositorio

    def ejecutar(self, usuario: UsuarioAutenticado, bloqueo_id: UUID) -> None:
        """Borra el bloqueo; al odontólogo un id ajeno o inexistente le da el mismo 403 (D12)."""
        bloqueo = self._repositorio.obtener(bloqueo_id)
        if usuario.rol == Rol.ODONTOLOGO:
            if bloqueo is None or bloqueo.profesional_id != usuario.profesional_id:
                raise ProfesionalAjenoError(MENSAJE_BLOQUEO_AJENO)
        elif bloqueo is None:
            raise RecursoInexistenteError(TipoRecurso.BLOQUEO)
        self._repositorio.bloquear_profesional(bloqueo.profesional_id)
        self._repositorio.eliminar(bloqueo)
        self._repositorio.commit()


class ValidadorBloqueos:
    """RN-AG-06 como `ValidadorTurno`: el turno no puede pisar un bloqueo de su profesional.

    No expone el bloqueo (ni su id ni su motivo) en el error (D10). La consulta corre después de
    que `cargar_referencias` tomó `FOR SHARE` sobre el profesional destino, que es lo que la
    serializa con el alta de un bloqueo (D13).
    """

    def __init__(self, repositorio: RepositorioBloqueos) -> None:
        self._repositorio = repositorio

    def __call__(self, propuesto: TurnoPropuesto) -> None:
        if self._repositorio.bloqueos_en(propuesto.profesional_id, propuesto.intervalo):
            raise TurnoInvalidoError("turno_en_bloqueo", MENSAJE_TURNO_EN_BLOQUEO)
