"""Product image storage."""

from __future__ import annotations

import sqlite3

from app.models import ProductImage


def images_for(conn: sqlite3.Connection, product_id: int) -> list[ProductImage]:
    rows = conn.execute(
        "SELECT * FROM images WHERE product_id = ? ORDER BY position, id",
        (product_id,),
    ).fetchall()
    return [ProductImage.from_row(row) for row in rows]


def add_image(
    conn: sqlite3.Connection,
    product_id: int,
    *,
    local_path: str | None = None,
    remote_url: str | None = None,
    position: int = 0,
    content_hash: str | None = None,
    alt: str | None = None,
    width: int | None = None,
    height: int | None = None,
) -> int:
    cursor = conn.execute(
        "INSERT INTO images (product_id, local_path, remote_url, width, height, alt,"
        " position, content_hash) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (product_id, local_path, remote_url, width, height, alt, position, content_hash),
    )
    conn.commit()
    return int(cursor.lastrowid)


def clear_images(conn: sqlite3.Connection, product_id: int) -> None:
    conn.execute("DELETE FROM images WHERE product_id = ?", (product_id,))
