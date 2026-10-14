"""POST /turnos, POST /turnos/{id}/cancelar y traducción de errores de dominio a HTTP."""

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, FastAPI, Request, status
from fastapi.responses import JSONResponse
from pydantic import AwareDatetime, BaseModel, Field
from sqlalchemy.orm import Session

from app.application.cancelar_turno import CancelarTurno
from app.application.crear_turno import CrearTurno, Reloj, SolicitudTurno
from app.domain.time import to_local
from app.domain.turnos import (
    ReferenciaInvalidaError,
    SolapamientoError,
    TurnoCreado,
    TurnoInexistenteError,
    TurnoInvalidoError,
    TurnoNoModificableError,
    TurnoRegistrado,
)
from app.infrastructure.db.repositorio_turnos import RepositorioTurnos
from app.infrastructure.db.session import get_session

router = APIRouter(prefix="/turnos", tags=["turnos"])


class TurnoIn(BaseModel):
    profesional_id: UUID
    paciente_id: UUID
    prestacion_id: UUID
    sillon_id: UUID | None = None
    inicio: AwareDatetime
    # Sin restricciones aquí: el rango lo valida el dominio (una sola fuente de la regla)
    duracion_min: int | None = None


class TurnoOut(BaseModel):
    id: UUID
    profesional_id: UUID
    paciente_id: UUID
    prestacion_id: UUID
    sillon_id: UUID | None
    inicio: datetime
    fin: datetime
    duracion_min: int
    estado: str
    creado_por: UUID | None
    motivo_cancelacion: str | None = None

    @classmethod
    def desde_dominio(cls, turno: TurnoCreado) -> "TurnoOut":
        return cls(
            id=turno.id,
            profesional_id=turno.profesional_id,
            paciente_id=turno.paciente_id,
            prestacion_id=turno.prestacion_id,
            sillon_id=turno.sillon_id,
            inicio=to_local(turno.inicio),
            fin=to_local(turno.fin),
            duracion_min=turno.duracion_min,
            estado=turno.estado,
            creado_por=turno.creado_por,
        )

    @classmethod
    def desde_registrado(cls, turno: TurnoRegistrado) -> "TurnoOut":
        return cls(
            id=turno.id,
            profesional_id=turno.profesional_id,
            paciente_id=turno.paciente_id,
            prestacion_id=turno.prestacion_id,
            sillon_id=turno.sillon_id,
            inicio=to_local(turno.inicio),
            fin=to_local(turno.fin),
            duracion_min=turno.duracion_min,
            estado=turno.estado,
            creado_por=turno.creado_por,
            motivo_cancelacion=turno.motivo_cancelacion,
        )


class CancelacionIn(BaseModel):
    # El largo coincide con la columna varchar(255); el strip lo hace el dominio
    motivo: str | None = Field(default=None, max_length=255)


def get_reloj() -> Reloj:
    """Dependencia del reloj; los tests la sobreescriben con un reloj fijo."""
    return lambda: datetime.now(UTC)


def get_crear_turno(
    session: Annotated[Session, Depends(get_session)],
    reloj: Annotated[Reloj, Depends(get_reloj)],
) -> CrearTurno:
    return CrearTurno(RepositorioTurnos(session), reloj)


def get_cancelar_turno(
    session: Annotated[Session, Depends(get_session)],
    reloj: Annotated[Reloj, Depends(get_reloj)],
) -> CancelarTurno:
    return CancelarTurno(RepositorioTurnos(session), reloj)


@router.post("", status_code=status.HTTP_201_CREATED, response_model=TurnoOut)
def crear_turno(datos: TurnoIn, caso: Annotated[CrearTurno, Depends(get_crear_turno)]) -> TurnoOut:
    creado = caso.ejecutar(SolicitudTurno(**datos.model_dump()))
    return TurnoOut.desde_dominio(creado)


@router.post("/{turno_id}/cancelar", response_model=TurnoOut)
def cancelar_turno(
    turno_id: UUID,
    caso: Annotated[CancelarTurno, Depends(get_cancelar_turno)],
    datos: CancelacionIn | None = None,
) -> TurnoOut:
    cancelado = caso.ejecutar(turno_id, None if datos is None else datos.motivo)
    return TurnoOut.desde_registrado(cancelado)


def registrar_manejadores(app: FastAPI) -> None:
    @app.exception_handler(TurnoInvalidoError)
    def _turno_invalido(_: Request, error: TurnoInvalidoError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={"detail": {"codigo": error.codigo, "mensaje": error.mensaje}},
        )

    @app.exception_handler(ReferenciaInvalidaError)
    def _referencia_invalida(_: Request, error: ReferenciaInvalidaError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={
                "detail": {
                    "codigo": "referencia_invalida",
                    "referencia": error.referencia,
                    "motivo": error.motivo,
                }
            },
        )

    @app.exception_handler(SolapamientoError)
    def _solapamiento(_: Request, error: SolapamientoError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": {"codigo": "solapamiento", "recursos": list(error.recursos)}},
        )

    @app.exception_handler(TurnoInexistenteError)
    def _turno_inexistente(_: Request, error: TurnoInexistenteError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": {"codigo": "turno_inexistente", "mensaje": str(error)}},
        )

    @app.exception_handler(TurnoNoModificableError)
    def _turno_no_modificable(_: Request, error: TurnoNoModificableError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": {"codigo": error.codigo, "mensaje": error.mensaje}},
        )
