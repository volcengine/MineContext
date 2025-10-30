# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
from typing import Tuple

from sqlalchemy.orm import Session

from opencontext.db import get_engine, get_session, run_migrations, get_database_url


def create_test_database(tmp_dir: Path) -> str:
    db_path = tmp_dir / "test_core.db"
    url = f"sqlite:///{db_path}"
    run_migrations(url)
    return url


def get_test_session(database_url: str) -> Session:
    # Ensure engine/session bound to this URL
    engine = get_engine(database_url)
    return get_session()
