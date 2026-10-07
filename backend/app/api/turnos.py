"""POST /turnos y traducción de errores de dominio a HTTP (422 / 409)."""

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, FastAPI, Request, status
from fastapi.responses import JSONResponse
from pydantic import AwareDatetime, BaseModel
from sqlalchemy.orm import Session

from app.application.crear_turno import CrearTurno, Reloj, SolicitudTurno
from app.domain.time import to_local
from app.domain.turnos import (
    ReferenciaInvalidaError,
    SolapamientoError,
    TurnoCreado,
    TurnoInvalidoError,
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


def get_reloj() -> Reloj:
    """Dependencia del reloj; los tests la sobreescriben con un reloj fijo."""
    return lambda: datetime.now(UTC)


def get_crear_turno(
    session: Annotated[Session, Depends(get_session)],
    reloj: Annotated[Reloj, Depends(get_reloj)],
) -> CrearTurno:
    return CrearTurno(RepositorioTurnos(session), reloj)


@router.post("", status_code=status.HTTP_201_CREATED, response_model=TurnoOut)
def crear_turno(datos: TurnoIn, caso: Annotated[CrearTurno, Depends(get_crear_turno)]) -> TurnoOut:
    creado = caso.ejecutar(SolicitudTurno(**datos.model_dump()))
    return TurnoOut.desde_dominio(creado)


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
