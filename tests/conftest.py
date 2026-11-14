from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from app.config import Settings, load_settings
from app.db import connect, init_db


@pytest.fixture()
def settings(tmp_path: Path) -> Settings:
    return load_settings(
        {
            "CATALOG_FORGE_DATA": str(tmp_path / "data"),
            "CATALOG_FORGE_SECRET": "test-secret-key",
            "CATALOG_FORGE_ADMIN_PASSWORD": "admin-password",
        }
    )


@pytest.fixture()
def db_path(settings: Settings) -> Path:
    path = settings.database_path
    init_db(path)
    return path


@pytest.fixture()
def conn(db_path: Path):
    connection = connect(db_path)
    try:
        yield connection
    finally:
        connection.close()
