from __future__ import annotations

import os
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool
from sqlalchemy import create_engine
from alembic import context

# Import application models metadata
from opencontext.db.models import metadata as target_metadata

# this is the Alembic Config object, which provides access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging. This line sets up loggers basically.
if config.config_file_name is not None and Path(config.config_file_name).exists():
    fileConfig(config.config_file_name)


def get_database_url() -> str:
    # Environment override primarily for tests
    env_url = os.environ.get("OPENCONTEXT_DATABASE_URL")
    if env_url:
        return env_url
    # Use value from alembic.ini if present
    ini_url = config.get_main_option("sqlalchemy.url")
    if ini_url:
        return ini_url
    # Fallback
    return "sqlite:///./persist/sqlite/app.db"


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    url = get_database_url()
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}

    engine = create_engine(url, poolclass=pool.NullPool, connect_args=connect_args, future=True)

    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
