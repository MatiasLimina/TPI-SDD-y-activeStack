"""Rutas de pacientes: /pacientes (alta, búsqueda, detalle, edición y desactivación)."""

from typing import Annotated, ClassVar
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, JsonValue
from sqlalchemy.orm import Session

from app.api.auth import RecepcionistaAutenticada
from app.api.recursos import Entrada
from app.application.gestion_recursos import CrearRecurso
from app.infrastructure.db.models import Paciente
from app.infrastructure.db.repositorio_pacientes import RepositorioPacientes
from app.infrastructure.db.session import get_session


class PacienteIn(Entrada):
    ESTADO: ClassVar[str] = "activo"

    nombre: str
    apellido: str
    documento: str
    telefono: str
    email: str | None = None
    activo: JsonValue = None


class PacienteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    nombre: str
    apellido: str
    documento: str
    telefono: str
    email: str | None
    activo: bool


router = APIRouter(prefix="/pacientes", tags=["pacientes"])


def get_crear(
    session: Annotated[Session, Depends(get_session)], usuario: RecepcionistaAutenticada
) -> CrearRecurso[Paciente]:
    return CrearRecurso(RepositorioPacientes(session))


@router.post("", status_code=status.HTTP_201_CREATED, response_model=PacienteOut)
def crear(
    usuario: RecepcionistaAutenticada,
    datos: PacienteIn,
    caso: Annotated[CrearRecurso[Paciente], Depends(get_crear)],
) -> Paciente:
    return caso.ejecutar(datos.datos(), campos_estado=datos.campos_estado())
