"""Casos de uso de los horarios de atención (franjas por profesional) y su validador de turnos."""

from collections.abc import Mapping
from typing import Any
from uuid import UUID

from app.domain.horarios import (
    MENSAJE_FUERA_DE_HORARIO,
    Franja,
    FranjaSuperpuestaError,
    ProfesionalAjenoError,
    cabe_en_horario,
    validar_franja,
)
from app.domain.recursos import RecursoInexistenteError, TipoRecurso
from app.domain.time import DEFAULT_TIMEZONE, to_local
from app.domain.turnos import TurnoInvalidoError, TurnoPropuesto
from app.domain.usuarios import Rol, UsuarioAutenticado
from app.infrastructure.db.models import HorarioAtencion
from app.infrastructure.db.repositorio_horarios import RepositorioHorarios


def _franja(horario: HorarioAtencion) -> Franja:
    return Franja(horario.dia_semana, horario.hora_inicio, horario.hora_fin)


class ConsultarHorarios:
    def __init__(self, repositorio: RepositorioHorarios) -> None:
        self._repositorio = repositorio

    def ejecutar(self, usuario: UsuarioAutenticado, profesional_id: UUID) -> list[HorarioAtencion]:
        """Un odontólogo solo lee el horario propio: se evalúa antes de buscar al profesional."""
        if usuario.rol == Rol.ODONTOLOGO and usuario.profesional_id != profesional_id:
            raise ProfesionalAjenoError
        if self._repositorio.obtener_profesional(profesional_id) is None:
            raise RecursoInexistenteError(TipoRecurso.PROFESIONAL)
        return self._repositorio.listar(profesional_id)


class CrearFranja:
    def __init__(self, repositorio: RepositorioHorarios) -> None:
        self._repositorio = repositorio

    def ejecutar(self, profesional_id: UUID, franja: Franja) -> HorarioAtencion:
        if self._repositorio.bloquear_profesional(profesional_id) is None:
            raise RecursoInexistenteError(TipoRecurso.PROFESIONAL)
        validar_franja(franja)
        if self._repositorio.superpuestas(profesional_id, franja, None):
            raise FranjaSuperpuestaError
        horario = HorarioAtencion(
            profesional_id=profesional_id,
            dia_semana=franja.dia_semana,
            hora_inicio=franja.hora_inicio,
            hora_fin=franja.hora_fin,
        )
        self._repositorio.agregar(horario)
        self._repositorio.guardar()
        self._repositorio.commit()
        return horario


class EditarFranja:
    def __init__(self, repositorio: RepositorioHorarios) -> None:
        self._repositorio = repositorio

    def ejecutar(
        self, profesional_id: UUID, horario_id: UUID, cambios: Mapping[str, Any]
    ) -> HorarioAtencion:
        """Aplica solo los `cambios` enviados; valida y compara la franja resultante."""
        if self._repositorio.bloquear_profesional(profesional_id) is None:
            raise RecursoInexistenteError(TipoRecurso.PROFESIONAL)
        horario = self._repositorio.obtener(profesional_id, horario_id)
        if horario is None:
            raise RecursoInexistenteError(TipoRecurso.HORARIO)
        actual = _franja(horario)
        resultante = Franja(
            dia_semana=cambios.get("dia_semana", actual.dia_semana),
            hora_inicio=cambios.get("hora_inicio", actual.hora_inicio),
            hora_fin=cambios.get("hora_fin", actual.hora_fin),
        )
        validar_franja(resultante)
        if self._repositorio.superpuestas(profesional_id, resultante, horario.id):
            raise FranjaSuperpuestaError
        self._repositorio.modificar(horario, cambios)
        self._repositorio.guardar()
        self._repositorio.commit()
        return horario


class BorrarFranja:
    def __init__(self, repositorio: RepositorioHorarios) -> None:
        self._repositorio = repositorio

    def ejecutar(self, profesional_id: UUID, horario_id: UUID) -> None:
        if self._repositorio.bloquear_profesional(profesional_id) is None:
            raise RecursoInexistenteError(TipoRecurso.PROFESIONAL)
        horario = self._repositorio.obtener(profesional_id, horario_id)
        if horario is None:
            raise RecursoInexistenteError(TipoRecurso.HORARIO)
        self._repositorio.eliminar(horario)
        self._repositorio.commit()


class ValidadorHorario:
    """RN-AG-05 como `ValidadorTurno`: el turno debe caber en una franja del día local."""

    def __init__(self, repositorio: RepositorioHorarios, tz: str = DEFAULT_TIMEZONE) -> None:
        self._repositorio = repositorio
        self._tz = tz

    def __call__(self, propuesto: TurnoPropuesto) -> None:
        dia = to_local(propuesto.inicio, self._tz).weekday()
        franjas = self._repositorio.franjas_del_dia(propuesto.profesional_id, dia)
        if not cabe_en_horario(propuesto.inicio, propuesto.fin, franjas, self._tz):
            raise TurnoInvalidoError("fuera_de_horario", MENSAJE_FUERA_DE_HORARIO)
