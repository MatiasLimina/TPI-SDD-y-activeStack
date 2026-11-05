"""Rutas de los bloqueos de agenda: /bloqueos (RN-HB-02, RN-HB-03, US-003)."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, FastAPI, Request, status
from fastapi.responses import JSONResponse
from pydantic import AwareDatetime, BaseModel, Field, StringConstraints
from sqlalchemy.orm import Session

from app.api.auth import UsuarioDeAmbosRoles
from app.application.bloqueos_agenda import CrearBloqueo, SolicitudBloqueo
from app.domain.bloqueos import (
    BloqueoConTurnosError,
    BloqueoInvalidoError,
    ProfesionalRequeridoError,
)
from app.domain.time import to_local
from app.infrastructure.db.models import Bloqueo
from app.infrastructure.db.repositorio_bloqueos import RepositorioBloqueos
from app.infrastructure.db.session import get_session

router = APIRouter(prefix="/bloqueos", tags=["bloqueos"])

DESCRIPCION_PROFESIONAL = (
    "Profesional cuya agenda se bloquea. La recepcionista debe indicarlo; el odontólogo puede "
    "omitirlo (se usa el suyo) y uno distinto del suyo se rechaza con 403."
)
DESCRIPCION_INSTANTE = (
    "Instante con zona horaria (obligatoria). El bloqueo es el intervalo semiabierto "
    "[inicio, fin): un turno que empieza justo en `fin` o termina justo en `inicio` no se pisa."
)
Motivo = Annotated[str, StringConstraints(strip_whitespace=True, max_length=255)]


class BloqueoIn(BaseModel):
    profesional_id: UUID | None = Field(default=None, description=DESCRIPCION_PROFESIONAL)
    inicio: AwareDatetime = Field(description=DESCRIPCION_INSTANTE)
    fin: AwareDatetime = Field(description=DESCRIPCION_INSTANTE)
    # Sin min_length: un motivo vacío llega al dominio y da `bloqueo_invalido` (D7)
    motivo: Motivo = Field(description="Texto corto, sin espacios en los extremos (hasta 255).")

    def a_solicitud(self) -> SolicitudBloqueo:
        return SolicitudBloqueo(self.profesional_id, self.inicio, self.fin, self.motivo)


class BloqueoOut(BaseModel):
    id: UUID
    profesional_id: UUID
    inicio: datetime
    fin: datetime
    motivo: str
    creado_por: UUID

    @classmethod
    def desde_modelo(cls, bloqueo: Bloqueo) -> "BloqueoOut":
        return cls(
            id=bloqueo.id,
            profesional_id=bloqueo.profesional_id,
            inicio=to_local(bloqueo.inicio),
            fin=to_local(bloqueo.fin),
            motivo=bloqueo.motivo,
            creado_por=bloqueo.creado_por,
        )


class TurnoAfectadoOut(BaseModel):
    id: UUID
    inicio: datetime
    fin: datetime


def get_crear(session: Annotated[Session, Depends(get_session)]) -> CrearBloqueo:
    return CrearBloqueo(RepositorioBloqueos(session))


@router.post("", status_code=status.HTTP_201_CREATED, response_model=BloqueoOut)
def crear_bloqueo(
    usuario: UsuarioDeAmbosRoles,
    datos: BloqueoIn,
    caso: Annotated[CrearBloqueo, Depends(get_crear)],
) -> BloqueoOut:
    return BloqueoOut.desde_modelo(caso.ejecutar(usuario, datos.a_solicitud()))


def registrar_manejadores_bloqueos(app: FastAPI) -> None:
    @app.exception_handler(BloqueoInvalidoError)
    def _bloqueo_invalido(_: Request, error: BloqueoInvalidoError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={"detail": {"codigo": error.codigo, "mensaje": error.mensaje}},
        )

    @app.exception_handler(ProfesionalRequeridoError)
    def _profesional_requerido(_: Request, error: ProfesionalRequeridoError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={"detail": {"codigo": error.codigo, "mensaje": error.mensaje}},
        )

    @app.exception_handler(BloqueoConTurnosError)
    def _bloqueo_con_turnos(_: Request, error: BloqueoConTurnosError) -> JSONResponse:
        turnos = [
            TurnoAfectadoOut(id=t.id, inicio=to_local(t.inicio), fin=to_local(t.fin)).model_dump(
                mode="json"
            )
            for t in error.turnos
        ]
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "detail": {"codigo": error.codigo, "mensaje": error.mensaje, "turnos": turnos}
            },
        )
