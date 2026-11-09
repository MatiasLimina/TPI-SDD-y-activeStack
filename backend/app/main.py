from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from app.api.auditoria import router as auditoria_router
from app.api.auth import registrar_manejadores_auth
from app.api.auth import router as auth_router
from app.api.bloqueos import registrar_manejadores_bloqueos
from app.api.bloqueos import router as bloqueos_router
from app.api.health import router as health_router
from app.api.horarios import registrar_manejadores_horarios
from app.api.horarios import router as horarios_router
from app.api.pacientes import registrar_manejadores_pacientes
from app.api.pacientes import router as pacientes_router
from app.api.recursos import (
    prestaciones_router,
    profesionales_router,
    registrar_manejadores_recursos,
    sillones_router,
)
from app.api.turnos import registrar_manejadores
from app.api.turnos import router as turnos_router
from app.config import ConfiguracionCors
from app.infrastructure.db.session import dispose_engine
from app.infrastructure.log_acceso import instalar_filtro_log_acceso


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Un CORS_ORIGINS inválido (p. ej. "*") corta el arranque; create_app() no puede lanzarlo
    # porque se ejecuta al importar y rompería la importación de la app.
    ConfiguracionCors()
    # Acá y no al importar: uvicorn configura su logging antes de arrancar el lifespan
    instalar_filtro_log_acceso()
    yield
    dispose_engine()


def _origenes_cors() -> list[str]:
    try:
        return ConfiguracionCors().origenes_permitidos
    except ValidationError:
        return []  # nunca llega un "*" al middleware; el lifespan rechaza el arranque


def create_app() -> FastAPI:
    app = FastAPI(title="Turnos y Agenda", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_origenes_cors(),
        allow_credentials=False,  # el token viaja en un encabezado, no en una cookie
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(turnos_router)
    app.include_router(auditoria_router)
    app.include_router(profesionales_router)
    app.include_router(sillones_router)
    app.include_router(prestaciones_router)
    app.include_router(horarios_router)
    app.include_router(bloqueos_router)
    app.include_router(pacientes_router)
    registrar_manejadores(app)
    registrar_manejadores_auth(app)
    registrar_manejadores_recursos(app)
    registrar_manejadores_horarios(app)
    registrar_manejadores_bloqueos(app)
    registrar_manejadores_pacientes(app)
    return app


app = create_app()
