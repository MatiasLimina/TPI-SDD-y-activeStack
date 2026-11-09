"""Acceso a datos de pacientes: repositorio del catálogo más búsqueda y turnos propios."""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import ColumnElement, String, exists, func, or_, select
from sqlalchemy.orm import Session

from app.domain.pacientes import CARACTERES_CON_ACENTO, CARACTERES_SIN_ACENTO
from app.domain.recursos import TipoRecurso
from app.infrastructure.db.models import Paciente, Turno
from app.infrastructure.db.repositorio_recursos import DefinicionRecurso, RepositorioRecursos

DEFINICION_PACIENTE = DefinicionRecurso(
    modelo=Paciente,
    tipo=TipoRecurso.PACIENTE,
    flag="activo",
    orden=(Paciente.apellido, Paciente.nombre, Paciente.id),
    unicas={"uq_paciente_documento": "documento"},
)


def _plegada(columna: ColumnElement[str]) -> ColumnElement[str]:
    """`lower(translate(col, ...))` con la tabla de `app.domain.pacientes` (DD-31 f).

    `translate` va primero y cubre también las mayúsculas acentuadas, así el resultado no depende
    del locale de la base.
    """
    plegada = func.translate(columna, CARACTERES_CON_ACENTO, CARACTERES_SIN_ACENTO, type_=String)
    return func.lower(plegada, type_=String)


class RepositorioPacientes(RepositorioRecursos[Paciente]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, DEFINICION_PACIENTE)

    def buscar(self, terminos: Sequence[str], limite: int, desplazamiento: int) -> list[Paciente]:
        """Pacientes activos e inactivos cuyo nombre, apellido o documento contiene cada término.

        `terminos` llega ya plegado (`terminos_busqueda`). AND entre términos, OR entre campos.
        `autoescape` toma `%`, `_` y la barra como texto. Orden fijo con `id` de desempate, y el
        recorte (`limite`, `desplazamiento`) se aplica después de filtrar y ordenar.
        """
        campos = [
            _plegada(Paciente.nombre),
            _plegada(Paciente.apellido),
            _plegada(Paciente.documento),
        ]
        consulta = select(Paciente)
        for termino in terminos:
            consulta = consulta.where(
                or_(*(campo.contains(termino, autoescape=True) for campo in campos))
            )
        consulta = (
            consulta.order_by(*DEFINICION_PACIENTE.orden).limit(limite).offset(desplazamiento)
        )
        return list(self._session.scalars(consulta))

    def tiene_turno_de(self, paciente_id: UUID, profesional_id: UUID) -> bool:
        """Hay al menos un turno del profesional con el paciente, en cualquier estado y fecha."""
        hay_turno = exists().where(
            Turno.paciente_id == paciente_id, Turno.profesional_id == profesional_id
        )
        return bool(self._session.scalar(select(hay_turno)))
