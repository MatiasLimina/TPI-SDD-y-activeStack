"""Rutas de pacientes: /pacientes (alta, búsqueda, detalle, edición y desactivación)."""

from typing import Annotated, Any, ClassVar
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    JsonValue,
    StringConstraints,
)
from sqlalchemy.orm import Session

from app.api.auth import RecepcionistaAutenticada
from app.api.recursos import Entrada
from app.application.gestion_recursos import CrearRecurso
from app.infrastructure.db.models import Paciente
from app.infrastructure.db.repositorio_pacientes import RepositorioPacientes
from app.infrastructure.db.session import get_session


def _sin_caracter_nulo(valor: str) -> str:
    """`U+0000` hace fallar al driver con un 500: se rechaza antes (el mensaje no cita el valor)."""
    if "\x00" in valor:
        raise ValueError("no admite el carácter nulo")
    return valor


def _texto(largo: int) -> Any:
    """Texto obligatorio: sin espacios extremos, no vacío, con el largo de su columna y sin NUL."""
    return Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=largo),
        AfterValidator(_sin_caracter_nulo),
    ]


def _email_en_blanco_a_nulo(valor: Any) -> Any:
    if isinstance(valor, str):
        return valor.strip() or None
    return valor


Nombre = _texto(100)
Apellido = _texto(100)
Documento = _texto(20)
Telefono = _texto(30)
Email = Annotated[
    Annotated[str, StringConstraints(max_length=254), AfterValidator(_sin_caracter_nulo)] | None,
    BeforeValidator(_email_en_blanco_a_nulo),
]


class PacienteIn(Entrada):
    ESTADO: ClassVar[str] = "activo"

    nombre: Nombre
    apellido: Apellido
    documento: Documento
    telefono: Telefono
    email: Email = None
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
