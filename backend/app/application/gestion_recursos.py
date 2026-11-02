"""Casos de uso del catálogo: un mismo flujo para profesionales, sillones y prestaciones."""

from collections.abc import Callable, Mapping, Sequence
from typing import Any
from uuid import UUID

from app.domain.recursos import (
    EstadoNoEditableError,
    RecursoInexistenteError,
    validar_duracion_prestacion,
)
from app.infrastructure.db.models.mixins import CatalogoMixin
from app.infrastructure.db.repositorio_recursos import RepositorioRecursos

Validador = Callable[[Mapping[str, Any]], None]
"""Regla propia de un recurso sobre los datos ya normalizados (hoy, la duración de prestación)."""


def validar_prestacion(datos: Mapping[str, Any]) -> None:
    """Solo la prestación tiene una regla propia: su duración cumple la grilla (DD-15)."""
    if "duracion_min" in datos:
        validar_duracion_prestacion(datos["duracion_min"])


class CrearRecurso[M: CatalogoMixin]:
    def __init__(
        self, repositorio: RepositorioRecursos[M], validar: Validador | None = None
    ) -> None:
        self._repositorio = repositorio
        self._validar = validar

    def ejecutar(self, datos: Mapping[str, Any], *, campos_estado: Sequence[str] = ()) -> M:
        if campos_estado:
            raise EstadoNoEditableError(campos_estado)
        if self._validar is not None:
            self._validar(datos)
        entidad = self._repositorio.construir(**datos)
        self._repositorio.agregar(entidad)
        self._repositorio.guardar()
        self._repositorio.commit()
        return entidad


class EditarRecurso[M: CatalogoMixin]:
    def __init__(
        self, repositorio: RepositorioRecursos[M], validar: Validador | None = None
    ) -> None:
        self._repositorio = repositorio
        self._validar = validar

    def ejecutar(
        self, id: UUID, cambios: Mapping[str, Any], *, campos_estado: Sequence[str] = ()
    ) -> M:
        """Aplica solo los `cambios` enviados. Valida antes de leer la base (orden de design §2)."""
        if campos_estado:
            raise EstadoNoEditableError(campos_estado)
        if self._validar is not None:
            self._validar(cambios)
        entidad = self._repositorio.obtener_para_actualizar(id)
        if entidad is None:
            raise RecursoInexistenteError(self._repositorio.tipo)
        self._repositorio.modificar(entidad, cambios)
        self._repositorio.guardar()
        self._repositorio.commit()
        return entidad


class DesactivarRecurso[M: CatalogoMixin]:
    def __init__(self, repositorio: RepositorioRecursos[M]) -> None:
        self._repositorio = repositorio

    def ejecutar(self, id: UUID) -> M:
        """Baja lógica e idempotente: si ya estaba inactivo no se escribe nada (D5)."""
        entidad = self._repositorio.obtener_para_actualizar(id)
        if entidad is None:
            raise RecursoInexistenteError(self._repositorio.tipo)
        flag = self._repositorio.flag
        if getattr(entidad, flag):
            self._repositorio.modificar(entidad, {flag: False})
            self._repositorio.guardar()
        self._repositorio.commit()
        return entidad
