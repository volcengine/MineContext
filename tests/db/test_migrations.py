from __future__ import annotations

from pathlib import Path

import os
import json
import pytest
from sqlalchemy import inspect, text

from opencontext.db import get_engine, run_migrations
from opencontext.db.models import Base, Job


@pytest.fixture()
def temp_db_url(tmp_path: Path) -> str:
    db_path = tmp_path / "core.db"
    return f"sqlite:///{db_path}"


def test_upgrade_creates_tables_and_wal(temp_db_url: str):
    # Fresh upgrade
    run_migrations(temp_db_url)

    engine = get_engine(temp_db_url)
    insp = inspect(engine)
    tables = set(insp.get_table_names())

    expected = {"events", "documents", "chunks", "entities", "embeddings", "jobs"}
    assert expected.issubset(tables)

    # WAL mode active
    with engine.connect() as conn:
        wal_mode = conn.execute(text("PRAGMA journal_mode")).scalar()
        assert str(wal_mode).lower() == "wal"

    # Subsequent runs are no-ops
    run_migrations(temp_db_url)


def test_downgrade_and_upgrade_cycle(temp_db_url: str):
    from alembic.config import Config
    from alembic import command

    run_migrations(temp_db_url)

    alembic_cfg = Config(str(Path(__file__).parents[2] / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(Path(__file__).parents[1] / ".." / "opencontext" / "db" / "migrations"))
    alembic_cfg.set_main_option("sqlalchemy.url", temp_db_url)

    # Downgrade to base
    command.downgrade(alembic_cfg, "base")
    # Upgrade back to head
    command.upgrade(alembic_cfg, "head")


def test_basic_crud_job(temp_db_url: str):
    run_migrations(temp_db_url)
    engine = get_engine(temp_db_url)

    # Basic CRUD using raw SQL for compatibility
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO jobs(job_type, status, payload, priority, attempts, dedupe_key) VALUES (:jt, :st, :pl, :pr, :at, :dk)"
            ),
            {
                "jt": "test",
                "st": "queued",
                "pl": json.dumps({"a": 1}),
                "pr": 5,
                "at": 0,
                "dk": "unique-key-1",
            },
        )

    with engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM jobs WHERE job_type='test'"))
        assert count.scalar_one() == 1
