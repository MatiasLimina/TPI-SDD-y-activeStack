"""Engine y sesiones SQLAlchemy 2 (sincronico, psycopg 3)."""

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings


@lru_cache
def get_engine() -> Engine:
    return create_engine(get_settings().DATABASE_URL, pool_pre_ping=True)


def get_session() -> Iterator[Session]:
    """Dependencia FastAPI: una sesion por request, cerrada al terminar."""
    factory = sessionmaker(bind=get_engine(), expire_on_commit=False)
    with factory() as session:
        yield session
