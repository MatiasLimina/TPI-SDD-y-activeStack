from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.auditoria import router as auditoria_router
from app.api.auth import registrar_manejadores_auth
from app.api.auth import router as auth_router
from app.api.health import router as health_router
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
    registrar_manejadores(app)
    registrar_manejadores_auth(app)
    return app


app = create_app()
