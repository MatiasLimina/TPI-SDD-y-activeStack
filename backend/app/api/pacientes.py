"""Rutas de pacientes: /pacientes (alta, búsqueda, detalle, edición y desactivación)."""

from collections.abc import Mapping
from typing import Annotated, Any, ClassVar
from uuid import UUID

from fastapi import APIRouter, Depends, FastAPI, Query, Request, status
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    JsonValue,
    StringConstraints,
)
from sqlalchemy.orm import Session

from app.api.auth import RecepcionistaAutenticada, UsuarioDeAmbosRoles
from app.api.recursos import Cambios, Entrada
from app.application.gestion_pacientes import ConsultarPaciente
from app.application.gestion_recursos import CrearRecurso, DesactivarRecurso, EditarRecurso
from app.domain.pacientes import PacienteAjenoError, email_valido
from app.domain.usuarios import Rol
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


def _con_formato_de_email(valor: str) -> str:
    """Chequeo mínimo del dominio (DD-31 m); el mensaje no cita el valor."""
    if not email_valido(valor):
        raise ValueError("el email debe tener la forma algo@algo, sin espacios")
    return valor


def _email_en_blanco_a_nulo(valor: Any) -> Any:
    if isinstance(valor, str):
        return valor.strip() or None
    return valor


Nombre = _texto(100)
Apellido = _texto(100)
Documento = _texto(20)
Telefono = _texto(30)
Email = Annotated[
    Annotated[
        str,
        StringConstraints(max_length=254),
        AfterValidator(_sin_caracter_nulo),
        AfterValidator(_con_formato_de_email),
    ]
    | None,
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


class PacienteCambios(Cambios):
    """Body del PATCH: lo omitido se conserva; `null` solo vale para quitar el email."""

    ESTADO: ClassVar[str] = "activo"
    OBLIGATORIOS: ClassVar[tuple[str, ...]] = ("nombre", "apellido", "documento", "telefono")

    nombre: Nombre | None = None
    apellido: Apellido | None = None
    documento: Documento | None = None
    telefono: Telefono | None = None
    email: Email = None
    activo: JsonValue = None


class PacienteResumenOut(BaseModel):
    """Lo único que lee el odontólogo de un paciente de sus turnos (DD-31 a)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    nombre: str
    apellido: str


class PacienteOut(PacienteResumenOut):
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


def get_editar(
    session: Annotated[Session, Depends(get_session)], usuario: RecepcionistaAutenticada
) -> EditarRecurso[Paciente]:
    return EditarRecurso(RepositorioPacientes(session))


@router.patch("/{paciente_id}", response_model=PacienteOut)
def editar(
    usuario: RecepcionistaAutenticada,
    paciente_id: UUID,
    datos: PacienteCambios,
    caso: Annotated[EditarRecurso[Paciente], Depends(get_editar)],
) -> Paciente:
    return caso.ejecutar(paciente_id, datos.datos(), campos_estado=datos.campos_estado())


def get_desactivar(
    session: Annotated[Session, Depends(get_session)], usuario: RecepcionistaAutenticada
) -> DesactivarRecurso[Paciente]:
    return DesactivarRecurso(RepositorioPacientes(session))


@router.post("/{paciente_id}/desactivar", response_model=PacienteOut)
def desactivar(
    usuario: RecepcionistaAutenticada,
    paciente_id: UUID,
    caso: Annotated[DesactivarRecurso[Paciente], Depends(get_desactivar)],
) -> Paciente:
    return caso.ejecutar(paciente_id)


def get_consultar(
    session: Annotated[Session, Depends(get_session)], usuario: UsuarioDeAmbosRoles
) -> ConsultarPaciente:
    return ConsultarPaciente(RepositorioPacientes(session))


def _busqueda_sin_nulo(q: str | None) -> str | None:
    return None if q is None else _sin_caracter_nulo(q)


Busqueda = Annotated[
    str | None,
    Query(
        max_length=100,
        description=(
            "Texto a buscar en nombre, apellido o documento. Se separa por espacios y cada "
            "término debe aparecer en alguno de los tres campos, sin distinguir mayúsculas ni "
            "acentos. En blanco o ausente, lista sin filtrar."
        ),
    ),
    AfterValidator(_busqueda_sin_nulo),
]
MAX_DESPLAZAMIENTO = 2**63 - 1  # el OFFSET de PostgreSQL es un bigint: más allá daría un 500
Limite = Annotated[
    int, Query(ge=1, le=100, description="Máximo de pacientes a devolver (de 1 a 100).")
]
Desplazamiento = Annotated[
    int,
    Query(
        ge=0,
        le=MAX_DESPLAZAMIENTO,
        description="Cantidad de pacientes a saltear antes de devolver el resultado.",
    ),
]


@router.get("", response_model=list[PacienteOut])
def listar(
    usuario: RecepcionistaAutenticada,
    caso: Annotated[ConsultarPaciente, Depends(get_consultar)],
    q: Busqueda = None,
    limite: Limite = 50,
    desplazamiento: Desplazamiento = 0,
) -> list[Paciente]:
    return caso.listar(q, limite, desplazamiento)


@router.get("/{paciente_id}", response_model=PacienteOut | PacienteResumenOut)
def detalle(
    usuario: UsuarioDeAmbosRoles,
    paciente_id: UUID,
    caso: Annotated[ConsultarPaciente, Depends(get_consultar)],
) -> dict[str, Any]:
    """Ficha completa para la recepcionista; `id`, `nombre` y `apellido` para el odontólogo.

    Se arma el dict de cada rol y se valida contra la unión: un resumen no puede pasar por ficha
    completa porque le faltan campos obligatorios.
    """
    paciente = caso.detalle(usuario, paciente_id)
    salida = PacienteResumenOut if usuario.rol == Rol.ODONTOLOGO else PacienteOut
    return salida.model_validate(paciente).model_dump(mode="json")


def _es_ruta_de_pacientes(ruta: str) -> bool:
    return ruta == "/pacientes" or ruta.startswith("/pacientes/")


def _mensaje_sin_datos(error: Mapping[str, Any]) -> str:
    """El mensaje de pydantic, salvo los del UUID, que citan el primer carácter inválido."""
    if str(error["type"]).startswith("uuid"):
        return "Input should be a valid UUID"
    return str(error["msg"])


def registrar_manejadores_pacientes(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def _validacion(request: Request, error: RequestValidationError) -> JSONResponse:
        """422 de `/pacientes` solo con `type`, `loc` y `msg`: sin `input` ni `ctx` (DD-31 n).

        El `input` de un campo faltante es el body entero. Las demás rutas conservan el manejador
        por defecto de FastAPI, para no cambiar contratos ya entregados.
        """
        if not _es_ruta_de_pacientes(request.url.path):
            return await request_validation_exception_handler(request, error)
        errores = [
            {"type": e["type"], "loc": list(e["loc"]), "msg": _mensaje_sin_datos(e)}
            for e in error.errors()
        ]
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, content={"detail": errores}
        )

    @app.exception_handler(PacienteAjenoError)
    def _paciente_ajeno(_: Request, error: PacienteAjenoError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": {"codigo": "paciente_ajeno", "mensaje": error.mensaje}},
        )
