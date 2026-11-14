"""Order queries for the admin panel."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200


@dataclass
class OrderSummary:
    """One order, as the admin panel shows it."""

    code: str
    email: str
    name: str
    total: str
    currency: str
    status: str
    created_at: str
    item_count: int = 0


def list_orders(
    conn: sqlite3.Connection,
    *,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> tuple[list[OrderSummary], int]:
    """One page of orders, newest first, and the number of orders there are."""
    page = max(1, page)
    page_size = max(1, min(page_size, MAX_PAGE_SIZE))

    total = int(conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0])

    rows = conn.execute(
        "SELECT o.code, o.email, o.name, o.total, o.currency, o.status, o.created_at,"
        " (SELECT COUNT(*) FROM order_items i WHERE i.order_id = o.id) AS item_count"
        " FROM orders o ORDER BY o.id DESC LIMIT ? OFFSET ?",
        (page_size, (page - 1) * page_size),
    ).fetchall()

    return [
        OrderSummary(
            code=str(row["code"]),
            email=str(row["email"]),
            name=str(row["name"]),
            total=str(row["total"]),
            currency=str(row["currency"]),
            status=str(row["status"]),
            created_at=str(row["created_at"]),
            item_count=int(row["item_count"]),
        )
        for row in rows
    ], total
