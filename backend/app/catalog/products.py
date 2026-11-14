"""Product queries."""

from __future__ import annotations

import sqlite3
from typing import Any

from app.models import Product, Variant

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


def list_admin_products(
    conn: sqlite3.Connection,
    *,
    search: str | None = None,
    status: str | None = None,
    category_id: int | None = None,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> tuple[list[Product], int]:
    """One page of products for the admin panel, hidden ones included."""
    page = max(1, page)
    page_size = max(1, min(page_size, MAX_PAGE_SIZE))

    where: list[str] = []
    params: list[object] = []

    if search:
        where.append(
            "(p.title LIKE ? OR p.description LIKE ? OR p.vendor LIKE ?"
            " OR p.sku LIKE ? OR p.source_url LIKE ?)"
        )
        pattern = f"%{search}%"
        params.extend([pattern] * 5)

    if status:
        where.append("p.status = ?")
        params.append(status)

    if category_id is not None:
        where.append(
            "EXISTS (SELECT 1 FROM product_categories pc"
            " WHERE pc.product_id = p.id AND pc.category_id = ?)"
        )
        params.append(category_id)

    clause = f" WHERE {' AND '.join(where)}" if where else ""

    total = int(
        conn.execute(
            f"SELECT COUNT(*) FROM products p{clause}", tuple(params)
        ).fetchone()[0]
    )

    rows = conn.execute(
        f"SELECT p.* FROM products p{clause}"
        " ORDER BY p.updated_at DESC, p.id DESC LIMIT ? OFFSET ?",
        (*params, page_size, (page - 1) * page_size),
    ).fetchall()

    return [Product.from_row(row) for row in rows], total


def product_ids_for_bulk(
    conn: sqlite3.Connection,
    *,
    product_ids: list[int] | None = None,
    category_id: int | None = None,
) -> list[int]:
    """The products a bulk price change should touch."""
    if product_ids:
        return [product_id for product_id in product_ids]
    if category_id is not None:
        rows = conn.execute(
            "SELECT product_id FROM product_categories WHERE category_id = ?"
            " ORDER BY product_id",
            (category_id,),
        ).fetchall()
        return [int(row["product_id"]) for row in rows]
    rows = conn.execute("SELECT id FROM products ORDER BY id").fetchall()
    return [int(row["id"]) for row in rows]


def update_product_fields(
    conn: sqlite3.Connection, product_id: int, fields: dict[str, Any]
) -> bool:
    """Update the given columns of a product. False when there is no such product."""
    allowed = {
        "title",
        "description",
        "vendor",
        "sku",
        "compare_at_price",
        "currency",
        "stock",
        "status",
    }
    updates = {key: value for key, value in fields.items() if key in allowed}
    if not updates:
        return False

    assignments = ", ".join(f"{key} = ?" for key in updates)
    cursor = conn.execute(
        f"UPDATE products SET {assignments}, updated_at = ? WHERE id = ?",
        (*updates.values(), _now(), product_id),
    )
    conn.commit()
    return cursor.rowcount > 0


def replace_product_images(
    conn: sqlite3.Connection, product_id: int, paths: list[str]
) -> None:
    """Set the images of a product to the given local paths."""
    conn.execute("DELETE FROM images WHERE product_id = ?", (product_id,))
    for position, path in enumerate(paths):
        conn.execute(
            "INSERT INTO images (product_id, local_path, position) VALUES (?, ?, ?)",
            (product_id, path, position),
        )
    conn.commit()


def variants_for(conn: sqlite3.Connection, product_id: int) -> list[Variant]:
    """The variants of a product."""
    rows = conn.execute(
        "SELECT * FROM variants WHERE product_id = ? ORDER BY position, id",
        (product_id,),
    ).fetchall()
    return [Variant.from_row(row) for row in rows]


def _now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat(timespec="seconds")
