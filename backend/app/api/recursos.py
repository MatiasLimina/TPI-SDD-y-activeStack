"""Rutas del catálogo: /profesionales, /sillones y /prestaciones (mismo contrato HTTP)."""

from typing import Annotated, Any, ClassVar, Self
from uuid import UUID

from fastapi import APIRouter, Depends, FastAPI, Request, status
from fastapi.responses import JSONResponse
from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    JsonValue,
    StringConstraints,
    model_validator,
)
from sqlalchemy.orm import Session

from app.api.auth import RecepcionistaAutenticada
from app.application.gestion_recursos import (
    CrearRecurso,
    DesactivarRecurso,
    EditarRecurso,
    Validador,
    validar_prestacion,
)
from app.domain.recursos import (
    EstadoNoEditableError,
    RecursoDuplicadoError,
    RecursoInexistenteError,
    RecursoInvalidoError,
    normalizar_matricula,
)
from app.infrastructure.db.models.mixins import CatalogoMixin
from app.infrastructure.db.repositorio_recursos import (
    DEFINICION_PRESTACION,
    DEFINICION_PROFESIONAL,
    DEFINICION_SILLON,
    DefinicionRecurso,
    RepositorioRecursos,
)
from app.infrastructure.db.session import get_session


def _texto(largo: int) -> Any:
    """Texto obligatorio: sin espacios extremos, no vacío y con el largo de su columna."""
    return Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=largo)]


Nombre100 = _texto(100)
Apellido100 = _texto(100)
Nombre50 = _texto(50)


def _matricula(valor: Any) -> Any:
    return normalizar_matricula(valor) if isinstance(valor, str) else valor


Matricula = Annotated[
    Annotated[str, StringConstraints(max_length=30)] | None, BeforeValidator(_matricula)
]


class _Entrada(BaseModel):
    """Base de los bodies de alta y edición."""

    # Nombre del campo de actividad; solo se detecta su presencia (no se puede editar)
    ESTADO: ClassVar[str]

    def datos(self) -> dict[str, Any]:
        """Los campos enviados, menos el estado de actividad."""
        return self.model_dump(include=self.model_fields_set - {self.ESTADO})

    def campos_estado(self) -> tuple[str, ...]:
        return (self.ESTADO,) if self.ESTADO in self.model_fields_set else ()


class ProfesionalIn(_Entrada):
    ESTADO: ClassVar[str] = "activo"

    nombre: Nombre100
    apellido: Apellido100
    matricula: Matricula = None
    activo: JsonValue = None


class SillonIn(_Entrada):
    ESTADO: ClassVar[str] = "activo"

    nombre: Nombre50
    activo: JsonValue = None


class PrestacionIn(_Entrada):
    ESTADO: ClassVar[str] = "activa"

    nombre: Nombre100
    # Sin restricciones de rango aquí: la regla de la grilla vive en el dominio (DD-15)
    duracion_min: int
    requiere_sillon: bool = True
    activa: JsonValue = None


class _Cambios(_Entrada):
    """Body de un PATCH: lo omitido se conserva; `null` solo vale donde el campo es opcional."""

    OBLIGATORIOS: ClassVar[tuple[str, ...]]

    @model_validator(mode="after")
    def _sin_nulos_en_campos_obligatorios(self) -> Self:
        for campo in self.OBLIGATORIOS:
            if campo in self.model_fields_set and getattr(self, campo) is None:
                raise ValueError(f"{campo} no admite null")
        return self


class ProfesionalCambios(_Cambios):
    ESTADO: ClassVar[str] = "activo"
    OBLIGATORIOS: ClassVar[tuple[str, ...]] = ("nombre", "apellido")

    nombre: Nombre100 | None = None
    apellido: Apellido100 | None = None
    matricula: Matricula = None
    activo: JsonValue = None


class SillonCambios(_Cambios):
    ESTADO: ClassVar[str] = "activo"
    OBLIGATORIOS: ClassVar[tuple[str, ...]] = ("nombre",)

    nombre: Nombre50 | None = None
    activo: JsonValue = None


class PrestacionCambios(_Cambios):
    ESTADO: ClassVar[str] = "activa"
    OBLIGATORIOS: ClassVar[tuple[str, ...]] = ("nombre", "duracion_min", "requiere_sillon")

    nombre: Nombre100 | None = None
    duracion_min: int | None = None
    requiere_sillon: bool | None = None
    activa: JsonValue = None


class _Salida(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ProfesionalOut(_Salida):
    id: UUID
    nombre: str
    apellido: str
    matricula: str | None
    activo: bool


class SillonOut(_Salida):
    id: UUID
    nombre: str
    activo: bool


class PrestacionOut(_Salida):
    id: UUID
    nombre: str
    duracion_min: int
    requiere_sillon: bool
    activa: bool


def _router[M: CatalogoMixin](
    *,
    prefijo: str,
    definicion: DefinicionRecurso[M],
    entrada: type[_Entrada],
    cambios: type[_Cambios],
    salida: type[_Salida],
    validar: Validador | None = None,
) -> APIRouter:
    router = APIRouter(prefix=prefijo, tags=[prefijo.removeprefix("/")])

    def get_crear(
        session: Annotated[Session, Depends(get_session)], usuario: RecepcionistaAutenticada
    ) -> CrearRecurso[M]:
        return CrearRecurso(RepositorioRecursos(session, definicion), validar)

    def get_editar(
        session: Annotated[Session, Depends(get_session)], usuario: RecepcionistaAutenticada
    ) -> EditarRecurso[M]:
        return EditarRecurso(RepositorioRecursos(session, definicion), validar)

    def get_desactivar(
        session: Annotated[Session, Depends(get_session)], usuario: RecepcionistaAutenticada
    ) -> DesactivarRecurso[M]:
        return DesactivarRecurso(RepositorioRecursos(session, definicion))

    @router.post("", status_code=status.HTTP_201_CREATED, response_model=salida)
    def crear(
        usuario: RecepcionistaAutenticada,
        datos: entrada,  # type: ignore[valid-type]
        caso: Annotated[CrearRecurso[M], Depends(get_crear)],
    ) -> M:
        return caso.ejecutar(datos.datos(), campos_estado=datos.campos_estado())

    @router.patch("/{recurso_id}", response_model=salida)
    def editar(
        usuario: RecepcionistaAutenticada,
        recurso_id: UUID,
        datos: cambios,  # type: ignore[valid-type]
        caso: Annotated[EditarRecurso[M], Depends(get_editar)],
    ) -> M:
        return caso.ejecutar(recurso_id, datos.datos(), campos_estado=datos.campos_estado())

    @router.post("/{recurso_id}/desactivar", response_model=salida)
    def desactivar(
        usuario: RecepcionistaAutenticada,
        recurso_id: UUID,
        caso: Annotated[DesactivarRecurso[M], Depends(get_desactivar)],
    ) -> M:
        return caso.ejecutar(recurso_id)

    return router


profesionales_router = _router(
    prefijo="/profesionales",
    definicion=DEFINICION_PROFESIONAL,
    entrada=ProfesionalIn,
    cambios=ProfesionalCambios,
    salida=ProfesionalOut,
)
sillones_router = _router(
    prefijo="/sillones",
    definicion=DEFINICION_SILLON,
    entrada=SillonIn,
    cambios=SillonCambios,
    salida=SillonOut,
)
prestaciones_router = _router(
    prefijo="/prestaciones",
    definicion=DEFINICION_PRESTACION,
    entrada=PrestacionIn,
    cambios=PrestacionCambios,
    salida=PrestacionOut,
    validar=validar_prestacion,
)


def registrar_manejadores_recursos(app: FastAPI) -> None:
    @app.exception_handler(RecursoInvalidoError)
    def _recurso_invalido(_: Request, error: RecursoInvalidoError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={"detail": {"codigo": error.codigo, "mensaje": error.mensaje}},
        )

    @app.exception_handler(EstadoNoEditableError)
    def _estado_no_editable(_: Request, error: EstadoNoEditableError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={
                "detail": {
                    "codigo": "campo_no_editable",
                    "campos": list(error.campos),
                    "mensaje": error.mensaje,
                }
            },
        )

    @app.exception_handler(RecursoDuplicadoError)
    def _recurso_duplicado(_: Request, error: RecursoDuplicadoError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": {"codigo": "recurso_duplicado", "campo": error.campo}},
        )

    @app.exception_handler(RecursoInexistenteError)
    def _recurso_inexistente(_: Request, error: RecursoInexistenteError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": {"codigo": "recurso_inexistente", "recurso": error.tipo.value}},
        )
