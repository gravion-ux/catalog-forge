from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, load_settings
from app.db import connect, init_db
from app.main import create_app


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


def seed_product(conn: sqlite3.Connection, **overrides: Any) -> int:
    """Insert a product and return its id."""
    values: dict[str, Any] = {
        "slug": "blue-shirt",
        "title": "Blue Shirt",
        "description": "A standard catalog item.",
        "price": "19.90",
        "currency": "USD",
        "stock": 12,
        "status": "active",
        "created_at": "2026-01-01T00:00:00",
        "updated_at": "2026-01-01T00:00:00",
    }
    values.update(overrides)
    columns = ", ".join(values)
    placeholders = ", ".join("?" for _ in values)
    cursor = conn.execute(
        f"INSERT INTO products ({columns}) VALUES ({placeholders})", tuple(values.values())
    )
    conn.commit()
    return int(cursor.lastrowid)


def seed_category(conn: sqlite3.Connection, name: str, slug: str | None = None) -> int:
    """Insert a category and return its id."""
    slug = slug or name.lower().replace(" ", "-")
    cursor = conn.execute(
        "INSERT INTO categories (slug, name, created_at) VALUES (?, ?, ?)",
        (slug, name, "2026-01-01T00:00:00"),
    )
    conn.commit()
    return int(cursor.lastrowid)


@pytest.fixture()
def client(settings: Settings) -> TestClient:
    app = create_app(settings)
    with TestClient(app) as test_client:
        yield test_client
