"""Turn an extracted product into the row shape the database stores.

This is the one place where a crawled price becomes a stored price, so it is
also the one place that guarantees money never touches a float.
"""

from __future__ import annotations

from typing import Any

from app.crawler.extractors.base import ExtractedProduct
from app.money import format_money

#: The stock count a shop implies with "in stock" but does not count.
ASSUMED_STOCK = 10
#: The stock count a shop implies with "out of stock".
NO_STOCK = 0

OUT_OF_STOCK_MARKERS = ("outofstock", "soldout", "discontinued", "unavailable")


def normalize(product: ExtractedProduct) -> dict[str, Any]:
    """The product as a dictionary of database-ready values."""
    availability = (product.availability or "").lower()

    if product.stock is not None:
        stock = product.stock
    elif any(marker in availability for marker in OUT_OF_STOCK_MARKERS):
        stock = NO_STOCK
    else:
        stock = ASSUMED_STOCK

    return {
        "title": product.title,
        "description": product.description,
        "price": _price(product.price),
        "compare_at_price": _price(product.compare_at_price, allow_empty=True),
        "currency": product.currency or "USD",
        "stock": stock,
        "vendor": product.vendor,
        "sku": product.sku,
        "images": list(product.images),
        "variants": list(product.variants),
        "categories": list(product.categories),
        "availability": product.availability,
        "platform": product.platform,
        "source_url": product.source_url,
    }


def _price(value: str | None, *, allow_empty: bool = False) -> str | None:
    """A two-decimal price string, or ``None`` when there is no price."""
    if value is None or str(value).strip() == "":
        return None if allow_empty else "0.00"
    return format_money(value)
