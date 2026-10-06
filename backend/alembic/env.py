"""Entorno de Alembic. La URL nunca vive en alembic.ini."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

import app.infrastructure.db.models  # noqa: E402,F401  registra las tablas en Base.metadata
from app.infrastructure.db.base import Base  # noqa: E402

target_metadata = Base.metadata


def get_url() -> str:
    """Prioridad: config.attributes['db_url'] > -x db_url=... > Settings.DATABASE_URL."""
    url = config.attributes.get("db_url") or context.get_x_argument(as_dictionary=True).get(
        "db_url"
    )
    if url:
        return str(url)
    from app.config import get_settings

    return get_settings().DATABASE_URL


def run_migrations_offline() -> None:
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(get_url(), poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
