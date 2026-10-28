"""Engine y sesiones SQLAlchemy 2 (sincronico, psycopg 3)."""

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings


@lru_cache
def get_engine() -> Engine:
    # hide_parameters: los errores de SQLAlchemy no incluyen los parámetros (p. ej. el hash).
    return create_engine(get_settings().DATABASE_URL, pool_pre_ping=True, hide_parameters=True)


def get_session() -> Iterator[Session]:
    """Dependencia FastAPI: una sesion por request, cerrada al terminar."""
    factory = sessionmaker(bind=get_engine(), expire_on_commit=False)
    with factory() as session:
        yield session


def dispose_engine() -> None:
    """Cierra el pool si el engine fue creado (se llama al apagar la app)."""
    if get_engine.cache_info().currsize:
        get_engine().dispose()
        get_engine.cache_clear()
