"""Autenticación de la API: login, dependencias de hasher y emisor de tokens y manejador 401."""

from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.application.autenticacion import AutenticarToken, IniciarSesion
from app.config import get_settings
from app.domain.usuarios import (
    CredencialesInvalidasError,
    NoAutenticadoError,
    Rol,
    RolInsuficienteError,
    UsuarioAutenticado,
)
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


# auto_error=False: el 401 lo arma nuestro manejador, con el mismo cuerpo para todo caso (DD-24)
_bearer = HTTPBearer(auto_error=False)


def usuario_actual(
    credenciales: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    session: Annotated[Session, Depends(get_session)],
    emisor: Annotated[EmisorTokens, Depends(get_emisor_tokens)],
) -> UsuarioAutenticado:
    """Usuario del request, releído de la base; comparte la sesión con el caso de uso."""
    token = None if credenciales is None else credenciales.credentials
    return AutenticarToken(RepositorioUsuarios(session), emisor).ejecutar(token)


def requiere_rol(*roles: Rol) -> Callable[..., UsuarioAutenticado]:
    """Dependencia que exige un usuario autenticado con alguno de `roles` (rol de la base)."""
    permitidos = frozenset(roles)

    def dependencia(
        usuario: Annotated[UsuarioAutenticado, Depends(usuario_actual)],
    ) -> UsuarioAutenticado:
        if usuario.rol not in permitidos:
            raise RolInsuficienteError
        return usuario

    return dependencia


@router.post("/login", response_model=TokenOut)
def login(datos: LoginIn, caso: Annotated[IniciarSesion, Depends(get_iniciar_sesion)]) -> TokenOut:
    return TokenOut(access_token=caso.ejecutar(datos.email, datos.password))


def registrar_manejadores_auth(app: FastAPI) -> None:
    @app.exception_handler(NoAutenticadoError)
    def _no_autenticado(_: Request, __: NoAutenticadoError) -> JSONResponse:
        # Mismo cuerpo para toda causa: ausente, malformado, vencido, de otro usuario o inactivo
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": {"codigo": "no_autenticado", "mensaje": "No autenticado"}},
            headers={"WWW-Authenticate": "Bearer"},
        )

    @app.exception_handler(RolInsuficienteError)
    def _rol_insuficiente(_: Request, __: RolInsuficienteError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": {"codigo": "rol_insuficiente", "mensaje": "Rol insuficiente"}},
        )

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
