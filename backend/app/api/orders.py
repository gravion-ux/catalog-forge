"""Cart quoting, checkout and order lookup."""

from __future__ import annotations

import json
import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Request

from app.catalog.products import get_product
from app.db import session
from app.errors import ApiError
from app.money import format_money, to_decimal
from app.schemas import (
    CheckoutRequest,
    OrderItemOut,
    OrderOut,
    QuoteLine,
    QuoteOut,
    QuoteRequest,
)

router = APIRouter(prefix="/api", tags=["orders"])

CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def new_order_code() -> str:
    """Generate a short, unambiguous order code."""
    suffix = "".join(secrets.choice(CODE_ALPHABET) for _ in range(10))
    return f"CF-{suffix}"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _build_lines(
    connection, items: list[tuple[int, int]]
) -> tuple[list[QuoteLine], str, str]:
    lines: list[QuoteLine] = []
    subtotal = to_decimal("0")
    currency = "USD"

    for product_id, quantity in items:
        product = get_product(connection, product_id)
        if product is None or product.status != "active":
            raise ApiError(
                422, "invalid_request", f"Product {product_id} is not available."
            )
        unit_price = to_decimal(product.price)
        line_total = unit_price * quantity
        subtotal += line_total
        currency = product.currency
        lines.append(
            QuoteLine(
                product_id=product.id,
                title=product.title,
                unit_price=format_money(unit_price),
                quantity=quantity,
                line_total=format_money(line_total),
                currency=product.currency,
            )
        )

    return lines, format_money(subtotal), currency


@router.post("/orders/quote", response_model=QuoteOut)
def quote(request: Request, payload: QuoteRequest) -> QuoteOut:
    settings = request.app.state.settings
    items = [(item.product_id, item.quantity) for item in payload.items]
    with session(settings.database_path) as connection:
        lines, subtotal, currency = _build_lines(connection, items)
    return QuoteOut(
        lines=lines,
        subtotal=subtotal,
        total=subtotal,
        currency=currency,
    )


@router.post("/checkout", response_model=OrderOut, status_code=201)
def checkout(request: Request, payload: CheckoutRequest) -> OrderOut:
    settings = request.app.state.settings
    items = [(item.product_id, item.quantity) for item in payload.items]

    with session(settings.database_path) as connection:
        lines, subtotal, currency = _build_lines(connection, items)

        code = new_order_code()
        cursor = connection.execute(
            "INSERT INTO orders (code, email, name, address, subtotal, shipping,"
            " discount, total, currency, status, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                code,
                payload.email.strip(),
                payload.name.strip(),
                json.dumps(payload.address),
                subtotal,
                "0.00",
                "0.00",
                subtotal,
                currency,
                "placed",
                _now(),
            ),
        )
        order_id = int(cursor.lastrowid)

        for line in lines:
            connection.execute(
                "INSERT INTO order_items (order_id, product_id, title, unit_price,"
                " quantity) VALUES (?, ?, ?, ?, ?)",
                (order_id, line.product_id, line.title, line.unit_price, line.quantity),
            )

    return OrderOut(
        code=code,
        email=payload.email.strip(),
        name=payload.name.strip(),
        address=payload.address,
        subtotal=subtotal,
        shipping="0.00",
        discount="0.00",
        total=subtotal,
        currency=currency,
        status="placed",
        created_at=_now(),
        items=[
            OrderItemOut(
                product_id=line.product_id,
                title=line.title,
                unit_price=line.unit_price,
                quantity=line.quantity,
            )
            for line in lines
        ],
    )


@router.get("/orders/{code}", response_model=OrderOut)
def order_detail(request: Request, code: str) -> OrderOut:
    settings = request.app.state.settings
    with session(settings.database_path) as connection:
        row = connection.execute(
            "SELECT * FROM orders WHERE code = ?", (code,)
        ).fetchone()
        if row is None:
            raise ApiError(404, "not_found", "No such order.")
        item_rows = connection.execute(
            "SELECT * FROM order_items WHERE order_id = ? ORDER BY id",
            (row["id"],),
        ).fetchall()

    return OrderOut(
        code=row["code"],
        email=row["email"],
        name=row["name"],
        address=json.loads(row["address"] or "{}"),
        subtotal=row["subtotal"],
        shipping=row["shipping"],
        discount=row["discount"],
        total=row["total"],
        currency=row["currency"],
        status=row["status"],
        created_at=row["created_at"],
        items=[
            OrderItemOut(
                product_id=item["product_id"],
                title=item["title"],
                unit_price=item["unit_price"],
                quantity=item["quantity"],
            )
            for item in item_rows
        ],
    )
