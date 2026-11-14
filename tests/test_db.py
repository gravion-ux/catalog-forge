from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from app.db import TABLES, connect, init_db


def test_init_db_creates_every_table(db_path: Path) -> None:
    connection = connect(db_path)

    names = {
        row["name"]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
    }

    assert set(TABLES) <= names


def test_init_db_is_safe_to_run_twice(db_path: Path) -> None:
    init_db(db_path)  # must not raise

    connection = connect(db_path)
    count = connection.execute("SELECT COUNT(*) AS n FROM products").fetchone()["n"]
    assert count == 0


def test_product_round_trip(conn: sqlite3.Connection) -> None:
    conn.execute(
        "INSERT INTO products (slug, title, price, currency, created_at, updated_at)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        ("blue-shirt", "Blue Shirt", "19.90", "USD", "2026-01-01", "2026-01-01"),
    )
    conn.commit()

    row = conn.execute(
        "SELECT * FROM products WHERE slug = ?", ("blue-shirt",)
    ).fetchone()

    assert row is not None
    assert row["title"] == "Blue Shirt"
    assert row["price"] == "19.90"
    assert row["price_manually_edited"] == 0
    assert row["status"] == "active"


def test_price_history_records_the_change(conn: sqlite3.Connection) -> None:
    conn.execute(
        "INSERT INTO products (slug, title, price, created_at, updated_at)"
        " VALUES (?, ?, ?, ?, ?)",
        ("mug", "Mug", "9.00", "2026-01-01", "2026-01-01"),
    )
    product_id = conn.execute("SELECT id FROM products WHERE slug = 'mug'").fetchone()["id"]

    conn.execute(
        "INSERT INTO price_history (product_id, old_price, new_price, source, changed_at)"
        " VALUES (?, ?, ?, ?, ?)",
        (product_id, "9.00", "11.00", "admin", "2026-01-02"),
    )
    conn.commit()

    rows = conn.execute(
        "SELECT * FROM price_history WHERE product_id = ?", (product_id,)
    ).fetchall()

    assert len(rows) == 1
    assert rows[0]["old_price"] == "9.00"
    assert rows[0]["new_price"] == "11.00"
    assert rows[0]["source"] == "admin"


def test_foreign_keys_are_enforced(conn: sqlite3.Connection) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO images (product_id, local_path, position) VALUES (?, ?, ?)",
            (9999, "media/x.png", 0),
        )
