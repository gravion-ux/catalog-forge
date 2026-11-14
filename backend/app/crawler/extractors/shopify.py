"""The extractor for Shopify shops.

Shopify pages carry schema.org markup like any other shop, but they also embed
the product object itself in the page, and that object is the only place the
variant list and the compare-at price live. Shopify states prices in cents.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from urllib.parse import urljoin

from app.crawler.extractors import generic
from app.crawler.extractors.base import (
    ExtractedProduct,
    embedded_json_objects,
    image_urls,
    text_value,
)
from app.money import format_money

SHOPIFY_MARKERS = (
    "cdn.shopify.com",
    "shopifycdn",
    "shopify.theme",
    "shopifyanalytics",
)

PRODUCT_ASSIGNMENTS = (
    r"(?:var|let|const)\s+product\s*=\s*",
    r"window\.product\s*=\s*",
    r'"product"\s*:\s*',
    r"ShopifyAnalytics\s*=\s*",
)

CENTS = Decimal(100)


def detect(html_text: str) -> bool:
    """True when the page is served by Shopify."""
    lowered = (html_text or "").lower()
    return any(marker in lowered for marker in SHOPIFY_MARKERS)


def extract(html_text: str, url: str) -> ExtractedProduct | None:
    """Read the product off a Shopify page."""
    product = generic.extract(html_text, url)
    embedded = _embedded_product(html_text)

    if product is None and embedded is None:
        return None

    if product is None:
        product = ExtractedProduct()

    product.platform = "shopify"
    product.source_url = url

    if embedded:
        product.title = text_value(embedded.get("title")) or product.title
        if not product.price:
            product.price = price_from_cents(embedded.get("price"))
        if not product.compare_at_price:
            product.compare_at_price = price_from_cents(
                embedded.get("compare_at_price")
            )
        if not product.vendor:
            product.vendor = text_value(embedded.get("vendor")) or None
        if not product.images:
            product.images = [
                urljoin(url, image)
                for image in image_urls(embedded.get("images"))
            ]
        variants = _variants(embedded)
        if variants:
            product.variants = variants

    return product


def price_from_cents(value: Any) -> str | None:
    """Turn a Shopify price into a two-decimal price string.

    Shopify states prices in whole cents, so ``4500`` is ``45.00``. A value
    that already carries a decimal point is read as an amount.
    """
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return format_money(Decimal(value) / CENTS)
    if isinstance(value, float):
        if value.is_integer():
            return format_money(Decimal(int(value)) / CENTS)
        return format_money(value)

    text = str(value).strip()
    if not text:
        return None
    if "." in text:
        return format_money(text)
    try:
        cents = int(text)
    except ValueError:
        return format_money(text)
    return format_money(Decimal(cents) / CENTS)


def _embedded_product(html_text: str) -> dict[str, Any] | None:
    """The product object a Shopify page embeds in its inline scripts."""
    for data in embedded_json_objects(html_text, PRODUCT_ASSIGNMENTS):
        found = _find_product_blob(data)
        if found is not None:
            return found
    return None


def _find_product_blob(data: Any) -> dict[str, Any] | None:
    """The object that holds the variant list, wherever it is nested."""
    if not isinstance(data, dict):
        return None
    if isinstance(data.get("variants"), list):
        return data
    for key in ("product", "Product"):
        nested = data.get(key)
        if isinstance(nested, dict):
            found = _find_product_blob(nested)
            if found is not None:
                return found
    return None


def _variants(data: dict[str, Any]) -> list[dict[str, Any]]:
    """The variant list of an embedded Shopify product."""
    raw = data.get("variants")
    if not isinstance(raw, list):
        return []

    variants: list[dict[str, Any]] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        variants.append(
            {
                "id": entry.get("id"),
                "title": text_value(entry.get("title")),
                "price": price_from_cents(entry.get("price")),
                "compare_at_price": price_from_cents(entry.get("compare_at_price")),
                "available": bool(entry.get("available", True)),
                "sku": text_value(entry.get("sku")) or None,
                "options": entry.get("options") or [],
            }
        )
    return variants
