"""POST /turnos, cancelar, PATCH reprogramar y traducción de errores de dominio a HTTP."""

from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, FastAPI, Request, status
from fastapi.responses import JSONResponse
from pydantic import AwareDatetime, BaseModel, Field, JsonValue, model_validator
from sqlalchemy.orm import Session

from app.api.auth import requiere_rol
from app.application.auditoria_turnos import AuditorTurnos
from app.application.cancelar_turno import CancelarTurno
from app.application.crear_turno import CrearTurno, Reloj, SolicitudTurno
from app.application.reprogramar_turno import (
    OMITIDO,
    ReprogramarTurno,
    SolicitudReprogramacion,
)
from app.domain.time import to_local
from app.domain.turnos import (
    CampoNoEditableError,
    ReferenciaInvalidaError,
    SolapamientoError,
    TurnoCreado,
    TurnoInexistenteError,
    TurnoInvalidoError,
    TurnoNoModificableError,
    TurnoRegistrado,
)
from app.domain.usuarios import Rol, UsuarioAutenticado
from app.infrastructure.db.repositorio_auditoria import RepositorioAuditoria
from app.infrastructure.db.repositorio_turnos import RepositorioTurnos
from app.infrastructure.db.session import get_session

router = APIRouter(prefix="/turnos", tags=["turnos"])

RecepcionistaAutenticada = Annotated[UsuarioAutenticado, Depends(requiere_rol(Rol.RECEPCIONISTA))]


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


class ReprogramacionIn(BaseModel):
    """PATCH parcial: lo omitido se conserva; `null` explícito solo vale para el sillón."""

    inicio: AwareDatetime | None = None
    profesional_id: UUID | None = None
    sillon_id: UUID | None = None
    duracion_min: int | None = None
    # Solo se detecta su presencia: el paciente y la prestación no se pueden modificar
    paciente_id: JsonValue = None
    prestacion_id: JsonValue = None

    @model_validator(mode="after")
    def _sin_nulos_en_campos_obligatorios(self) -> "ReprogramacionIn":
        for campo in ("inicio", "profesional_id", "duracion_min"):
            if campo in self.model_fields_set and getattr(self, campo) is None:
                raise ValueError(f"{campo} no admite null")
        return self

    def a_solicitud(self) -> SolicitudReprogramacion:
        enviados = self.model_fields_set

        def valor(campo: str) -> Any:
            return getattr(self, campo) if campo in enviados else OMITIDO

        return SolicitudReprogramacion(
            inicio=valor("inicio"),
            profesional_id=valor("profesional_id"),
            sillon_id=valor("sillon_id"),
            duracion_min=valor("duracion_min"),
            campos_no_editables=tuple(
                campo for campo in ("paciente_id", "prestacion_id") if campo in enviados
            ),
        )


def get_reloj() -> Reloj:
    """Dependencia del reloj; los tests la sobreescriben con un reloj fijo."""
    return lambda: datetime.now(UTC)


def _auditor(session: Session, usuario: UsuarioAutenticado, reloj: Reloj) -> AuditorTurnos:
    """Auditor del request: el autor es el usuario autenticado, nunca un valor del body."""
    return AuditorTurnos(RepositorioAuditoria(session), usuario.id, reloj)


# Las fábricas dependen de `RecepcionistaAutenticada`, el mismo alias que usa cada ruta: FastAPI
# resuelve el usuario una sola vez por request y sin usuario no se arma el caso de uso.
def get_crear_turno(
    session: Annotated[Session, Depends(get_session)],
    reloj: Annotated[Reloj, Depends(get_reloj)],
    usuario: RecepcionistaAutenticada,
) -> CrearTurno:
    auditor = _auditor(session, usuario, reloj)
    return CrearTurno(RepositorioTurnos(session), reloj, observadores=[auditor.al_crear])


def get_cancelar_turno(
    session: Annotated[Session, Depends(get_session)],
    reloj: Annotated[Reloj, Depends(get_reloj)],
    usuario: RecepcionistaAutenticada,
) -> CancelarTurno:
    auditor = _auditor(session, usuario, reloj)
    return CancelarTurno(RepositorioTurnos(session), reloj, observadores=[auditor.al_cancelar])


def get_reprogramar_turno(
    session: Annotated[Session, Depends(get_session)],
    reloj: Annotated[Reloj, Depends(get_reloj)],
    usuario: RecepcionistaAutenticada,
) -> ReprogramarTurno:
    auditor = _auditor(session, usuario, reloj)
    return ReprogramarTurno(
        RepositorioTurnos(session), reloj, observadores=[auditor.al_reprogramar]
    )


@router.post("", status_code=status.HTTP_201_CREATED, response_model=TurnoOut)
def crear_turno(
    # FastAPI resuelve las dependencias (401/403) antes de validar path y body (422), sin importar
    # el orden de los parámetros. Excepción: un body con JSON inválido se parsea antes y da 422.
    usuario: RecepcionistaAutenticada,
    datos: TurnoIn,
    caso: Annotated[CrearTurno, Depends(get_crear_turno)],
) -> TurnoOut:
    creado = caso.ejecutar(SolicitudTurno(**datos.model_dump()), creado_por=usuario.id)
    return TurnoOut.desde_dominio(creado)


@router.post("/{turno_id}/cancelar", response_model=TurnoOut)
def cancelar_turno(
    usuario: RecepcionistaAutenticada,
    turno_id: UUID,
    caso: Annotated[CancelarTurno, Depends(get_cancelar_turno)],
    datos: CancelacionIn | None = None,
) -> TurnoOut:
    cancelado = caso.ejecutar(turno_id, None if datos is None else datos.motivo)
    return TurnoOut.desde_registrado(cancelado)


@router.patch("/{turno_id}/reprogramar", response_model=TurnoOut)
def reprogramar_turno(
    usuario: RecepcionistaAutenticada,
    turno_id: UUID,
    datos: ReprogramacionIn,
    caso: Annotated[ReprogramarTurno, Depends(get_reprogramar_turno)],
) -> TurnoOut:
    reprogramado = caso.ejecutar(turno_id, datos.a_solicitud())
    return TurnoOut.desde_registrado(reprogramado)


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

    @app.exception_handler(CampoNoEditableError)
    def _campo_no_editable(_: Request, error: CampoNoEditableError) -> JSONResponse:
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
