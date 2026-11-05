from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.auditoria import router as auditoria_router
from app.api.auth import registrar_manejadores_auth
from app.api.auth import router as auth_router
from app.api.bloqueos import registrar_manejadores_bloqueos
from app.api.bloqueos import router as bloqueos_router
from app.api.health import router as health_router
from app.api.horarios import registrar_manejadores_horarios
from app.api.horarios import router as horarios_router
from app.api.recursos import (
    prestaciones_router,
    profesionales_router,
    registrar_manejadores_recursos,
    sillones_router,
)
from app.api.turnos import registrar_manejadores
from app.api.turnos import router as turnos_router
from app.infrastructure.db.session import dispose_engine


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield
    dispose_engine()


def create_app() -> FastAPI:
    app = FastAPI(title="Turnos y Agenda", lifespan=lifespan)
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(turnos_router)
    app.include_router(auditoria_router)
    app.include_router(profesionales_router)
    app.include_router(sillones_router)
    app.include_router(prestaciones_router)
    app.include_router(horarios_router)
    app.include_router(bloqueos_router)
    registrar_manejadores(app)
    registrar_manejadores_auth(app)
    registrar_manejadores_recursos(app)
    registrar_manejadores_horarios(app)
    registrar_manejadores_bloqueos(app)
    return app


app = create_app()
