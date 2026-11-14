"""Product queries."""

from __future__ import annotations

import sqlite3

from app.models import Product

DEFAULT_PAGE_SIZE = 24
MAX_PAGE_SIZE = 100


def list_products(
    conn: sqlite3.Connection,
    *,
    category_slug: str | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
    include_hidden: bool = False,
) -> tuple[list[Product], int]:
    """Return one page of products and the total number that match."""
    page = max(1, page)
    page_size = max(1, min(page_size, MAX_PAGE_SIZE))

    where: list[str] = []
    params: list[object] = []

    if not include_hidden:
        where.append("p.status = 'active'")

    if search:
        where.append("(p.title LIKE ? OR p.description LIKE ? OR p.vendor LIKE ?)")
        pattern = f"%{search}%"
        params.extend([pattern, pattern, pattern])

    if category_slug:
        where.append(
            "EXISTS (SELECT 1 FROM product_categories pc"
            " JOIN categories c ON c.id = pc.category_id"
            " WHERE pc.product_id = p.id AND c.slug = ?)"
        )
        params.append(category_slug)

    clause = f" WHERE {' AND '.join(where)}" if where else ""

    total = conn.execute(
        f"SELECT COUNT(*) AS n FROM products p{clause}", tuple(params)
    ).fetchone()["n"]

    rows = conn.execute(
        f"SELECT p.* FROM products p{clause}"
        " ORDER BY p.title COLLATE NOCASE, p.id LIMIT ? OFFSET ?",
        (*params, page_size, (page - 1) * page_size),
    ).fetchall()

    return [Product.from_row(row) for row in rows], int(total)


def get_product(conn: sqlite3.Connection, product_id: int) -> Product | None:
    row = conn.execute(
        "SELECT * FROM products WHERE id = ?", (product_id,)
    ).fetchone()
    return Product.from_row(row) if row else None


def get_product_by_slug(conn: sqlite3.Connection, slug: str) -> Product | None:
    row = conn.execute("SELECT * FROM products WHERE slug = ?", (slug,)).fetchone()
    return Product.from_row(row) if row else None


def get_product_by_source_url(
    conn: sqlite3.Connection, source_url: str
) -> Product | None:
    row = conn.execute(
        "SELECT * FROM products WHERE source_url = ? ORDER BY id LIMIT 1",
        (source_url,),
    ).fetchone()
    return Product.from_row(row) if row else None


def category_ids_for(conn: sqlite3.Connection, product_id: int) -> list[int]:
    rows = conn.execute(
        "SELECT category_id FROM product_categories WHERE product_id = ?",
        (product_id,),
    ).fetchall()
    return [int(row["category_id"]) for row in rows]


def set_product_categories(
    conn: sqlite3.Connection, product_id: int, category_ids: list[int]
) -> None:
    conn.execute(
        "DELETE FROM product_categories WHERE product_id = ?", (product_id,)
    )
    for category_id in category_ids:
        conn.execute(
            "INSERT OR IGNORE INTO product_categories (product_id, category_id)"
            " VALUES (?, ?)",
            (product_id, category_id),
        )
