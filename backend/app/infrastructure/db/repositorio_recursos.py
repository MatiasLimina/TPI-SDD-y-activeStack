"""Acceso a datos del catálogo (profesionales, sillones, prestaciones): un repositorio genérico."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
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
        self._nuevos: list[M] = []
        self._cambios: list[tuple[M, Mapping[str, Any]]] = []

    @property
    def tipo(self) -> TipoRecurso:
        return self._definicion.tipo

    @property
    def flag(self) -> str:
        """Nombre del atributo de actividad: `activo` o `activa`."""
        return self._definicion.flag

    def construir(self, **datos: Any) -> M:
        """Instancia el modelo del recurso con `datos` ya validados."""
        return self._definicion.modelo(**datos)

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
        """Deja el recurso para el próximo `guardar`; entra a la sesión dentro de su SAVEPOINT."""
        self._nuevos.append(entidad)

    def modificar(self, entidad: M, cambios: Mapping[str, Any]) -> None:
        """Deja `cambios` para el próximo `guardar`; se aplican dentro de su SAVEPOINT."""
        self._cambios.append((entidad, cambios))

    def guardar(self) -> None:
        """`flush` en un SAVEPOINT que traduce un UNIQUE conocido a `RecursoDuplicadoError`.

        El SAVEPOINT deja la sesión usable tras el rechazo: solo se revierte esta escritura.
        """
        nuevos, self._nuevos = self._nuevos, []
        cambios, self._cambios = self._cambios, []
        try:
            with self._session.begin_nested():
                self._session.add_all(nuevos)
                for entidad, valores in cambios:
                    for campo, valor in valores.items():
                        setattr(entidad, campo, valor)
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
