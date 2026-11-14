"""Writing crawled products into the catalog.

The rule that matters here is price safety: a price a human set by hand is
never overwritten by a crawl. The crawl still records what the source shop
charges, so the admin panel can show that the source price moved on.
"""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from app.catalog.categories import ensure_category
from app.catalog.products import get_product_by_source_url, set_product_categories
from app.models import PriceChange
from app.money import format_money

_SLUG_PATTERN = re.compile(r"[^a-z0-9]+")

CRAWL_SOURCE = "crawl"
ADMIN_SOURCE = "admin"


@dataclass
class ImportResult:
    """What one import did."""

    product_id: int
    created: bool
    price_kept: bool
    source_price_changed: bool


def product_slug(title: str) -> str:
    """Turn a product title into a URL-safe slug."""
    slug = _SLUG_PATTERN.sub("-", title.strip().lower()).strip("-")
    return slug or "product"


def import_product(
    conn: sqlite3.Connection,
    product: dict[str, Any],
    *,
    source_platform: str,
) -> ImportResult:
    """Insert or update the product that came from a crawl.

    A product is matched on its ``source_url``. When the price was edited by
    hand the live price is left alone and only ``source_price`` moves.
    """
    title = str(product.get("title") or "").strip()
    if not title:
        raise ValueError("A product needs a title.")

    source_url = str(product.get("source_url") or "").strip()
    new_price = format_money(product.get("price") or "0.00")
    now = _now()

    existing = get_product_by_source_url(conn, source_url) if source_url else None

    if existing is None:
        product_id = _insert(conn, product, source_platform, new_price, now)
        _replace_images(conn, product_id, product.get("images") or [])
        _replace_variants(conn, product_id, product.get("variants") or [])
        _apply_categories(conn, product_id, product.get("categories") or [])
        conn.commit()
        return ImportResult(
            product_id=product_id,
            created=True,
            price_kept=False,
            source_price_changed=False,
        )

    product_id = existing.id
    price_kept = bool(existing.price_manually_edited)
    live_price = existing.price if price_kept else new_price
    source_price_changed = existing.source_price != new_price

    conn.execute(
        "UPDATE products SET title = ?, description = ?, vendor = ?, sku = ?,"
        " price = ?, compare_at_price = ?, currency = ?, stock = ?, status = ?,"
        " source_price = ?, source_fetched_at = ?, source_platform = ?,"
        " attributes = ?, updated_at = ? WHERE id = ?",
        (
            title,
            str(product.get("description") or ""),
            product.get("vendor"),
            product.get("sku"),
            live_price,
            _optional_price(product.get("compare_at_price")),
            product.get("currency") or "USD",
            int(product.get("stock") or 0),
            existing.status,
            new_price,
            now,
            source_platform,
            _attributes(product),
            now,
            product_id,
        ),
    )

    if not price_kept and live_price != existing.price:
        _record_price_change(
            conn, product_id, existing.price, live_price, CRAWL_SOURCE, now
        )

    _replace_images(conn, product_id, product.get("images") or [])
    _replace_variants(conn, product_id, product.get("variants") or [])
    _apply_categories(conn, product_id, product.get("categories") or [])
    conn.commit()

    return ImportResult(
        product_id=product_id,
        created=False,
        price_kept=price_kept,
        source_price_changed=source_price_changed,
    )


def set_price(
    conn: sqlite3.Connection,
    product_id: int,
    new_price: str | Decimal | int | float,
    source: str = ADMIN_SOURCE,
) -> PriceChange:
    """Set the live price of a product and record the change.

    A price set from the admin panel is marked as hand-edited, which is what
    stops a later crawl from overwriting it.
    """
    row = conn.execute(
        "SELECT price, price_manually_edited FROM products WHERE id = ?",
        (product_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"There is no product with id {product_id}.")

    old_price = format_money(row["price"])
    new_value = format_money(new_price)
    now = _now()

    manually_edited = row["price_manually_edited"]
    if source == ADMIN_SOURCE:
        manually_edited = 1

    conn.execute(
        "UPDATE products SET price = ?, price_manually_edited = ?, updated_at = ?"
        " WHERE id = ?",
        (new_value, manually_edited, now, product_id),
    )
    change = _record_price_change(
        conn, product_id, old_price, new_value, source, now
    )
    conn.commit()
    return change


def _insert(
    conn: sqlite3.Connection,
    product: dict[str, Any],
    source_platform: str,
    new_price: str,
    now: str,
) -> int:
    cursor = conn.execute(
        "INSERT INTO products (slug, title, description, vendor, sku, price,"
        " compare_at_price, currency, stock, status, source_url, source_platform,"
        " source_price, source_fetched_at, price_manually_edited, attributes,"
        " created_at, updated_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?)",
        (
            _unique_slug(conn, str(product.get("title") or "")),
            str(product.get("title") or "").strip(),
            str(product.get("description") or ""),
            product.get("vendor"),
            product.get("sku"),
            new_price,
            _optional_price(product.get("compare_at_price")),
            product.get("currency") or "USD",
            int(product.get("stock") or 0),
            "active",
            str(product.get("source_url") or "").strip() or None,
            source_platform,
            new_price,
            now,
            _attributes(product),
            now,
            now,
        ),
    )
    return int(cursor.lastrowid)


def _unique_slug(conn: sqlite3.Connection, title: str) -> str:
    """A slug that no other product is using."""
    base = product_slug(title)
    slug = base
    counter = 2
    while True:
        row = conn.execute("SELECT id FROM products WHERE slug = ?", (slug,)).fetchone()
        if row is None:
            return slug
        slug = f"{base}-{counter}"
        counter += 1


def _optional_price(value: Any) -> str | None:
    """A price string, or ``None`` when there is no price."""
    if value is None or str(value).strip() == "":
        return None
    return format_money(value)


def _attributes(product: dict[str, Any]) -> str:
    """The extra product data that has no column of its own."""
    payload: dict[str, Any] = {}
    availability = product.get("availability")
    if availability:
        payload["availability"] = str(availability)
    return json.dumps(payload)


def _replace_images(
    conn: sqlite3.Connection, product_id: int, images: list[Any]
) -> None:
    """Replace the crawled images of a product, keeping any added by hand."""
    conn.execute(
        "DELETE FROM images WHERE product_id = ? AND remote_url IS NOT NULL",
        (product_id,),
    )
    position = 0
    for image in images:
        if isinstance(image, str):
            remote_url: str | None = image
            local_path: str | None = None
            content_hash: str | None = None
        elif isinstance(image, dict):
            remote_url = image.get("url") or image.get("remote_url")
            local_path = image.get("local_path")
            content_hash = image.get("content_hash") or image.get("sha256")
        else:
            continue
        if not remote_url and not local_path:
            continue
        conn.execute(
            "INSERT INTO images (product_id, local_path, remote_url, position,"
            " content_hash) VALUES (?, ?, ?, ?, ?)",
            (product_id, local_path, remote_url, position, content_hash),
        )
        position += 1


def _replace_variants(
    conn: sqlite3.Connection, product_id: int, variants: list[Any]
) -> None:
    """Replace the variant list of a product with the one that was crawled."""
    conn.execute("DELETE FROM variants WHERE product_id = ?", (product_id,))
    for position, variant in enumerate(variants):
        if not isinstance(variant, dict):
            continue
        options = variant.get("options")
        if not isinstance(options, dict):
            options = {"values": options} if options else {}
        conn.execute(
            "INSERT INTO variants (product_id, title, sku, price, compare_at_price,"
            " stock, options, position) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                product_id,
                str(variant.get("title") or ""),
                variant.get("sku"),
                format_money(variant.get("price") or "0.00"),
                _optional_price(variant.get("compare_at_price")),
                1 if variant.get("available") else 0,
                json.dumps(options),
                position,
            ),
        )


def _apply_categories(
    conn: sqlite3.Connection, product_id: int, categories: list[Any]
) -> None:
    """Attach the product to the categories it was crawled with."""
    names = [str(name).strip() for name in categories if str(name).strip()]
    if not names:
        return
    category_ids = [ensure_category(conn, name).id for name in names]
    set_product_categories(conn, product_id, category_ids)


def _record_price_change(
    conn: sqlite3.Connection,
    product_id: int,
    old_price: str,
    new_price: str,
    source: str,
    now: str,
) -> PriceChange:
    """Append one row to the price history."""
    cursor = conn.execute(
        "INSERT INTO price_history (product_id, old_price, new_price, source,"
        " changed_at) VALUES (?, ?, ?, ?, ?)",
        (product_id, old_price, new_price, source, now),
    )
    return PriceChange(
        id=int(cursor.lastrowid),
        product_id=product_id,
        old_price=old_price,
        new_price=new_price,
        source=source,
        changed_at=now,
    )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
