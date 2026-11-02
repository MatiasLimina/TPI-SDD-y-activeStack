"""GET /turnos/{id}/auditoria: historial de auditoría de un turno (solo lectura, recepcionista)."""

from datetime import datetime
from typing import Annotated, Self
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.turnos import RecepcionistaAutenticada
from app.application.auditoria_turnos import ConsultarAuditoriaTurno
from app.domain.auditoria import Instantanea, RegistroAuditoria
from app.domain.time import to_local
from app.infrastructure.db.repositorio_auditoria import RepositorioAuditoria
from app.infrastructure.db.repositorio_turnos import RepositorioTurnos
from app.infrastructure.db.session import get_session

router = APIRouter(tags=["auditoria"])


class InstantaneaTurnoOut(BaseModel):
    """Valores del turno en un momento dado; `inicio` y `fin` se presentan en hora local."""

    profesional_id: UUID
    paciente_id: UUID
    prestacion_id: UUID
    sillon_id: UUID | None
    inicio: datetime
    fin: datetime
    duracion_min: int
    estado: str
    motivo_cancelacion: str | None

    @classmethod
    def desde_dominio(cls, instantanea: Instantanea) -> Self:
        valores = cls.model_validate(instantanea)
        return valores.model_copy(
            update={"inicio": to_local(valores.inicio), "fin": to_local(valores.fin)}
        )


class RegistroAuditoriaOut(BaseModel):
    id: int
    accion: str
    usuario_id: UUID
    ocurrido_en: datetime
    valores_previos: InstantaneaTurnoOut | None
    valores_nuevos: InstantaneaTurnoOut

    @classmethod
    def desde_dominio(cls, registro: RegistroAuditoria) -> Self:
        previos = registro.valores_previos
        return cls(
            id=registro.id,
            accion=registro.accion.value,
            usuario_id=registro.usuario_id,
            ocurrido_en=to_local(registro.ocurrido_en),
            valores_previos=None if previos is None else InstantaneaTurnoOut.desde_dominio(previos),
            valores_nuevos=InstantaneaTurnoOut.desde_dominio(registro.valores_nuevos),
        )


def get_consultar_auditoria(
    session: Annotated[Session, Depends(get_session)],
) -> ConsultarAuditoriaTurno:
    return ConsultarAuditoriaTurno(RepositorioTurnos(session), RepositorioAuditoria(session))


@router.get("/turnos/{turno_id}/auditoria", response_model=list[RegistroAuditoriaOut])
def consultar_auditoria(
    # La dependencia de rol se resuelve antes que el path (422) y que la existencia (404)
    usuario: RecepcionistaAutenticada,
    turno_id: UUID,
    caso: Annotated[ConsultarAuditoriaTurno, Depends(get_consultar_auditoria)],
) -> list[RegistroAuditoriaOut]:
    return [RegistroAuditoriaOut.desde_dominio(r) for r in caso.ejecutar(turno_id)]
