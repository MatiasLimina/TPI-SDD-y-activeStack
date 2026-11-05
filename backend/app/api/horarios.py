"""Rutas de los horarios de atención: /profesionales/{profesional_id}/horarios (RN-HB-01)."""

from datetime import time
from typing import Annotated, Any, Self
from uuid import UUID

from fastapi import APIRouter, Depends, FastAPI, Request, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.orm import Session

from app.api.auth import RecepcionistaAutenticada, UsuarioDeAmbosRoles
from app.application.horarios_atencion import (
    BorrarFranja,
    ConsultarHorarios,
    CrearFranja,
    EditarFranja,
)
from app.domain.horarios import (
    Franja,
    FranjaSuperpuestaError,
    ProfesionalAjenoError,
)
from app.infrastructure.db.models import HorarioAtencion
from app.infrastructure.db.repositorio_horarios import RepositorioHorarios
from app.infrastructure.db.session import get_session

router = APIRouter(prefix="/profesionales/{profesional_id}/horarios", tags=["horarios"])

DESCRIPCION_DIA = "Día de la semana: 0 = lunes … 6 = domingo."
DESCRIPCION_HORA = (
    "Hora local sin zona horaria, en múltiplos de 5 minutos (HH:MM o HH:MM:SS); "
    "la franja no cruza la medianoche."
)
NOTA_UNA_FRANJA = (
    "Un turno debe caber completo en una única franja: dos franjas contiguas "
    "(09:00-13:00 y 13:00-17:00) no se suman; para atención continua cargá una sola franja."
)


class FranjaIn(BaseModel):
    # Sin rangos aquí: la regla vive en el dominio (`franja_invalida`), una sola fuente
    dia_semana: int = Field(description=DESCRIPCION_DIA)
    hora_inicio: time = Field(description=DESCRIPCION_HORA)
    hora_fin: time = Field(description=DESCRIPCION_HORA)

    def a_franja(self) -> Franja:
        return Franja(self.dia_semana, self.hora_inicio, self.hora_fin)


class FranjaCambios(BaseModel):
    """PATCH parcial: lo omitido se conserva, `null` explícito es 422 y lo desconocido se ignora."""

    dia_semana: int | None = Field(default=None, description=DESCRIPCION_DIA)
    hora_inicio: time | None = Field(default=None, description=DESCRIPCION_HORA)
    hora_fin: time | None = Field(default=None, description=DESCRIPCION_HORA)

    @model_validator(mode="after")
    def _sin_nulos(self) -> Self:
        for campo in ("dia_semana", "hora_inicio", "hora_fin"):
            if campo in self.model_fields_set and getattr(self, campo) is None:
                raise ValueError(f"{campo} no admite null")
        return self

    def datos(self) -> dict[str, Any]:
        return self.model_dump(include=self.model_fields_set)


class FranjaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    profesional_id: UUID
    dia_semana: int = Field(description=DESCRIPCION_DIA)
    hora_inicio: time
    hora_fin: time


def get_consultar(session: Annotated[Session, Depends(get_session)]) -> ConsultarHorarios:
    return ConsultarHorarios(RepositorioHorarios(session))


def get_crear(
    session: Annotated[Session, Depends(get_session)], usuario: RecepcionistaAutenticada
) -> CrearFranja:
    return CrearFranja(RepositorioHorarios(session))


def get_editar(
    session: Annotated[Session, Depends(get_session)], usuario: RecepcionistaAutenticada
) -> EditarFranja:
    return EditarFranja(RepositorioHorarios(session))


def get_borrar(
    session: Annotated[Session, Depends(get_session)], usuario: RecepcionistaAutenticada
) -> BorrarFranja:
    return BorrarFranja(RepositorioHorarios(session))


@router.get("", response_model=list[FranjaOut])
def listar_franjas(
    usuario: UsuarioDeAmbosRoles,
    profesional_id: UUID,
    caso: Annotated[ConsultarHorarios, Depends(get_consultar)],
) -> list[HorarioAtencion]:
    return caso.ejecutar(usuario, profesional_id)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=FranjaOut,
    description=f"Crea una franja de atención. {NOTA_UNA_FRANJA}",
)
def crear_franja(
    usuario: RecepcionistaAutenticada,
    profesional_id: UUID,
    datos: FranjaIn,
    caso: Annotated[CrearFranja, Depends(get_crear)],
) -> HorarioAtencion:
    return caso.ejecutar(profesional_id, datos.a_franja())


@router.patch(
    "/{horario_id}",
    response_model=FranjaOut,
    description=f"Edita parcialmente una franja. {NOTA_UNA_FRANJA}",
)
def editar_franja(
    usuario: RecepcionistaAutenticada,
    profesional_id: UUID,
    horario_id: UUID,
    datos: FranjaCambios,
    caso: Annotated[EditarFranja, Depends(get_editar)],
) -> HorarioAtencion:
    return caso.ejecutar(profesional_id, horario_id, datos.datos())


@router.delete("/{horario_id}", status_code=status.HTTP_204_NO_CONTENT)
def borrar_franja(
    usuario: RecepcionistaAutenticada,
    profesional_id: UUID,
    horario_id: UUID,
    caso: Annotated[BorrarFranja, Depends(get_borrar)],
) -> Response:
    caso.ejecutar(profesional_id, horario_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def registrar_manejadores_horarios(app: FastAPI) -> None:
    @app.exception_handler(FranjaSuperpuestaError)
    def _franja_superpuesta(_: Request, __: FranjaSuperpuestaError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": {"codigo": "franja_superpuesta"}},
        )

    @app.exception_handler(ProfesionalAjenoError)
    def _profesional_ajeno(_: Request, error: ProfesionalAjenoError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": {"codigo": "profesional_ajeno", "mensaje": error.mensaje}},
        )
