"""Category queries."""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass

from app.models import Category

_SLUG_PATTERN = re.compile(r"[^a-z0-9]+")


def slugify(name: str) -> str:
    """Turn a category name into a URL-safe slug."""
    slug = _SLUG_PATTERN.sub("-", name.strip().lower()).strip("-")
    return slug or "category"


@dataclass
class CategorySummary:
    id: int
    slug: str
    name: str
    product_count: int = 0


def list_categories(conn: sqlite3.Connection) -> list[CategorySummary]:
    rows = conn.execute(
        "SELECT c.id, c.slug, c.name,"
        " (SELECT COUNT(*) FROM product_categories pc"
        "  JOIN products p ON p.id = pc.product_id"
        "  WHERE pc.category_id = c.id AND p.status = 'active') AS product_count"
        " FROM categories c ORDER BY c.position, c.name COLLATE NOCASE"
    ).fetchall()
    return [
        CategorySummary(
            id=int(row["id"]),
            slug=row["slug"],
            name=row["name"],
            product_count=int(row["product_count"]),
        )
        for row in rows
    ]


def get_category(conn: sqlite3.Connection, category_id: int) -> Category | None:
    row = conn.execute(
        "SELECT * FROM categories WHERE id = ?", (category_id,)
    ).fetchone()
    return Category.from_row(row) if row else None


def get_category_by_slug(conn: sqlite3.Connection, slug: str) -> Category | None:
    row = conn.execute("SELECT * FROM categories WHERE slug = ?", (slug,)).fetchone()
    return Category.from_row(row) if row else None


def ensure_category(conn: sqlite3.Connection, name: str) -> Category:
    """Return the category with this name, creating it when it is new."""
    cleaned = name.strip()
    slug = slugify(cleaned)
    existing = get_category_by_slug(conn, slug)
    if existing is not None:
        return existing
    cursor = conn.execute(
        "INSERT INTO categories (slug, name, created_at) VALUES (?, ?, ?)",
        (slug, cleaned, _now()),
    )
    conn.commit()
    return get_category(conn, int(cursor.lastrowid))  # type: ignore[return-value]


def _now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat(timespec="seconds")
