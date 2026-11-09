"""Casos de uso propios de pacientes: consulta con permisos por rol.

Alta, edición y desactivación reutilizan los casos de uso genéricos de `gestion_recursos`.
"""

from uuid import UUID

from app.domain.pacientes import PacienteAjenoError, terminos_busqueda
from app.domain.recursos import RecursoInexistenteError, TipoRecurso
from app.domain.usuarios import Rol, UsuarioAutenticado
from app.infrastructure.db.models import Paciente
from app.infrastructure.db.repositorio_pacientes import RepositorioPacientes


class ConsultarPaciente:
    def __init__(self, repositorio: RepositorioPacientes) -> None:
        self._repositorio = repositorio

    def listar(self, q: str | None, limite: int, desplazamiento: int) -> list[Paciente]:
        """Búsqueda y listado (la ruta lo reserva a la recepcionista)."""
        return self._repositorio.buscar(terminos_busqueda(q), limite, desplazamiento)

    def detalle(self, usuario: UsuarioAutenticado, paciente_id: UUID) -> Paciente:
        """Un odontólogo solo lee a pacientes de sus turnos y se evalúa antes que la existencia.

        Así un id ajeno y uno inexistente dan el mismo `PacienteAjenoError` (DD-27 i, DD-31 d).
        """
        if usuario.rol == Rol.ODONTOLOGO:
            return self._de_sus_turnos(usuario, paciente_id)
        paciente = self._repositorio.obtener(paciente_id)
        if paciente is None:
            raise RecursoInexistenteError(TipoRecurso.PACIENTE)
        return paciente

    def _de_sus_turnos(self, usuario: UsuarioAutenticado, paciente_id: UUID) -> Paciente:
        if usuario.profesional_id is None:
            raise PacienteAjenoError
        if not self._repositorio.tiene_turno_de(paciente_id, usuario.profesional_id):
            raise PacienteAjenoError
        paciente = self._repositorio.obtener(paciente_id)
        if paciente is None:  # imposible por la FK RESTRICT; no se revela igual que un ajeno
            raise PacienteAjenoError
        return paciente
