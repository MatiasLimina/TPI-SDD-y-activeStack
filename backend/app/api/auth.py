"""Autenticación de la API: login, dependencias de hasher y emisor de tokens y manejador 401."""

from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.application.autenticacion import IniciarSesion
from app.config import get_settings
from app.domain.usuarios import CredencialesInvalidasError
from app.infrastructure.db.repositorio_usuarios import RepositorioUsuarios
from app.infrastructure.db.session import get_session
from app.infrastructure.security.contrasenas import Hasher
from app.infrastructure.security.contrasenas import get_hasher as _get_hasher_produccion
from app.infrastructure.security.tokens import EmisorTokens

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginIn(BaseModel):
    # Sin EmailStr: un email mal formado debe dar el mismo 401 que uno desconocido (DD-24)
    email: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


def get_hasher() -> Hasher:
    """Dependencia del hasher; los tests la sobreescriben con uno de costo mínimo."""
    return _get_hasher_produccion()


def get_emisor_tokens() -> EmisorTokens:
    """Dependencia del emisor de tokens, configurado desde `Settings`."""
    settings = get_settings()
    return EmisorTokens(settings.JWT_SECRET, settings.JWT_EXPIRE_MINUTES)


def get_iniciar_sesion(
    session: Annotated[Session, Depends(get_session)],
    hasher: Annotated[Hasher, Depends(get_hasher)],
    emisor: Annotated[EmisorTokens, Depends(get_emisor_tokens)],
) -> IniciarSesion:
    return IniciarSesion(RepositorioUsuarios(session), hasher, emisor)


@router.post("/login", response_model=TokenOut)
def login(datos: LoginIn, caso: Annotated[IniciarSesion, Depends(get_iniciar_sesion)]) -> TokenOut:
    return TokenOut(access_token=caso.ejecutar(datos.email, datos.password))


def registrar_manejadores_auth(app: FastAPI) -> None:
    @app.exception_handler(CredencialesInvalidasError)
    def _credenciales_invalidas(_: Request, __: CredencialesInvalidasError) -> JSONResponse:
        # Cuerpo y mensaje constantes: nada de la causa del rechazo llega al cliente (DD-24)
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "detail": {"codigo": "credenciales_invalidas", "mensaje": "Credenciales inválidas"}
            },
            headers={"WWW-Authenticate": "Bearer"},
        )
