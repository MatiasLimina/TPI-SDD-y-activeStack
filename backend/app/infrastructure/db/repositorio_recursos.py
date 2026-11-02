"""Acceso a datos del catálogo (profesionales, sillones, prestaciones): un repositorio genérico."""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import InstrumentedAttribute, Session

from app.domain.recursos import RecursoDuplicadoError, TipoRecurso
from app.infrastructure.db.models import Prestacion, Profesional, Sillon
from app.infrastructure.db.models.mixins import CatalogoMixin

SQLSTATE_UNIQUE = "23505"


@dataclass(frozen=True)
class DefinicionRecurso[M: CatalogoMixin]:
    """Lo que distingue a un recurso de otro para el repositorio genérico."""

    modelo: type[M]
    tipo: TipoRecurso
    flag: str  # nombre del atributo de actividad: `activo` o `activa`
    orden: tuple[InstrumentedAttribute[object], ...]
    # El nombre de cada restricción UNIQUE (migración 002) es contrato: de él se deduce el campo
    unicas: dict[str, str]


DEFINICION_PROFESIONAL = DefinicionRecurso(
    modelo=Profesional,
    tipo=TipoRecurso.PROFESIONAL,
    flag="activo",
    orden=(Profesional.apellido, Profesional.nombre, Profesional.id),
    unicas={"uq_profesional_matricula": "matricula"},
)
DEFINICION_SILLON = DefinicionRecurso(
    modelo=Sillon,
    tipo=TipoRecurso.SILLON,
    flag="activo",
    orden=(Sillon.nombre, Sillon.id),
    unicas={"uq_sillon_nombre": "nombre"},
)
DEFINICION_PRESTACION = DefinicionRecurso(
    modelo=Prestacion,
    tipo=TipoRecurso.PRESTACION,
    flag="activa",
    orden=(Prestacion.nombre, Prestacion.id),
    unicas={"uq_prestacion_nombre": "nombre"},
)


class RepositorioRecursos[M: CatalogoMixin]:
    def __init__(self, session: Session, definicion: DefinicionRecurso[M]) -> None:
        self._session = session
        self._definicion = definicion

    def listar(self) -> list[M]:
        """Todos los recursos, activos e inactivos, en el orden fijo de la definición."""
        consulta = select(self._definicion.modelo).order_by(*self._definicion.orden)
        return list(self._session.scalars(consulta))

    def obtener(self, id: UUID) -> M | None:
        return self._session.get(self._definicion.modelo, id)

    def obtener_para_actualizar(self, id: UUID) -> M | None:
        """Lee la fila con `SELECT ... FOR UPDATE`, releyéndola si ya estaba en la sesión."""
        return self._session.get(
            self._definicion.modelo, id, with_for_update=True, populate_existing=True
        )

    def agregar(self, entidad: M) -> None:
        self._session.add(entidad)

    def guardar(self) -> None:
        """`flush` que traduce la violación de un UNIQUE conocido a `RecursoDuplicadoError`."""
        try:
            self._session.flush()
        except IntegrityError as error:
            campo = self._campo_duplicado(error)
            if campo is None:
                raise
            raise RecursoDuplicadoError(self._definicion.tipo, campo) from error

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()

    def _campo_duplicado(self, error: IntegrityError) -> str | None:
        if getattr(error.orig, "sqlstate", None) != SQLSTATE_UNIQUE:
            return None
        constraint = getattr(getattr(error.orig, "diag", None), "constraint_name", None)
        return self._definicion.unicas.get(constraint or "")
