# -*- coding: utf-8 -*-

# Core database setup for MineContext
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from sqlalchemy import event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

# Resolve default DB path (shared with existing SQLite backend)
DEFAULT_SQLITE_PATH = Path("./persist/sqlite/app.db")

_engine: Optional[Engine] = None
_SessionLocal: Optional[sessionmaker] = None


def _get_sqlite_path_from_config() -> Path:
    try:
        from opencontext.config.global_config import get_config

        storage_cfg = get_config("storage") or {}
        for backend in storage_cfg.get("backends", []):
            if (
                backend.get("storage_type") == "document_db"
                and backend.get("backend") == "sqlite"
            ):
                cfg = backend.get("config", {})
                if cfg.get("path"):
                    return Path(cfg["path"]).expanduser()
    except Exception:
        pass
    return DEFAULT_SQLITE_PATH


def _ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def get_database_url(explicit_path: Optional[Path] = None) -> str:
    # Allow full URL override
    env_url = os.environ.get("OPENCONTEXT_DATABASE_URL")
    if env_url:
        return env_url

    db_path = explicit_path or _get_sqlite_path_from_config()
    _ensure_parent_dir(db_path)
    # Use absolute path for stability
    abs_path = db_path.resolve()
    return f"sqlite:///{abs_path}"


def _apply_sqlite_pragmas(dbapi_connection) -> None:
    try:
        cursor = dbapi_connection.cursor()
        # Enable WAL so sqlite3/sqlalchemy can coexist across processes
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.close()
    except Exception:
        # Don't crash app on pragma set failure
        pass


def get_engine(database_url: Optional[str] = None) -> Engine:
    global _engine
    if _engine is not None:
        return _engine

    url = database_url or get_database_url()

    connect_args = {}
    if url.startswith("sqlite"):
        # Required for multi-threaded FastAPI and background jobs
        connect_args = {"check_same_thread": False}

    engine = create_engine(
        url,
        future=True,
        pool_pre_ping=True,
        connect_args=connect_args,
    )

    if url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):  # type: ignore
            _apply_sqlite_pragmas(dbapi_connection)

    _engine = engine
    return engine


def get_session() -> Session:
    global _SessionLocal
    if _SessionLocal is None:
        engine = get_engine()
        _SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    return _SessionLocal()


# Alembic helpers

def run_migrations(database_url: Optional[str] = None) -> None:
    """Run Alembic migrations up to head. Safe to call multiple times."""
    try:
        from alembic import command
        from alembic.config import Config

        alembic_cfg = Config(str(Path(__file__).parent.parent.parent / "alembic.ini"))
        url = database_url or get_database_url()
        alembic_cfg.set_main_option("sqlalchemy.url", url)
        # Ensure script location resolves correctly when bundled
        script_location = str(Path(__file__).parent / "migrations")
        alembic_cfg.set_main_option("script_location", script_location)

        command.upgrade(alembic_cfg, "head")

        # Verify WAL and PRAGMAs are set once afterwards
        engine = get_engine(url)
        with engine.connect() as conn:
            if url.startswith("sqlite"):
                conn.execute(text("PRAGMA journal_mode=WAL"))
                conn.execute(text("PRAGMA synchronous=NORMAL"))
                conn.execute(text("PRAGMA busy_timeout=30000"))
    except Exception as e:
        # Do not fail hard on migration errors in dev; raise in production scenarios as needed
        raise
