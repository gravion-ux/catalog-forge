"""The extractor for WooCommerce shops.

A WooCommerce product page carries schema.org markup for the search engines and
embeds ``wc_product_data`` for the shop's own scripts. The embedded object is
where the stock count lives, which schema.org never states.
"""

from __future__ import annotations

import re
from typing import Any

from app.crawler.extractors import generic
from app.crawler.extractors.base import (
    ExtractedProduct,
    embedded_json_objects,
    text_value,
)
from app.money import format_money

WOOCOMMERCE_CLASS = re.compile(
    r"""class\s*=\s*["'][^"']*\bwoocommerce\b[^"']*["']""",
    re.IGNORECASE,
)

PRODUCT_DATA_ASSIGNMENTS = (
    r"wc_product_data\s*=\s*",
    r"woocommerce-product-details\s*=\s*",
    r"woocommerce_product_data\s*=\s*",
)


def detect(html_text: str) -> bool:
    """True when the page is served by WooCommerce."""
    text = html_text or ""
    if WOOCOMMERCE_CLASS.search(text):
        return True
    lowered = text.lower()
    return "wc_product_data" in lowered or "woocommerce-product-details" in lowered


def extract(html_text: str, url: str) -> ExtractedProduct | None:
    """Read the product off a WooCommerce page."""
    product = generic.extract(html_text, url)
    data = _product_data(html_text)

    if product is None and data is None:
        return None

    if product is None:
        product = ExtractedProduct()

    product.platform = "woocommerce"
    product.source_url = url

    if data:
        quantity = data.get("stock_quantity")
        if quantity is not None and not isinstance(quantity, bool):
            try:
                product.stock = int(quantity)
            except (TypeError, ValueError):
                product.stock = None
        if not product.price:
            product.price = format_money(data.get("price")) if data.get("price") else None
        if not product.currency:
            product.currency = text_value(data.get("currency")) or None

    return product


def _product_data(html_text: str) -> dict[str, Any] | None:
    """The ``wc_product_data`` object a WooCommerce page embeds."""
    for data in embedded_json_objects(html_text, PRODUCT_DATA_ASSIGNMENTS):
        if "stock_quantity" in data or "stock_status" in data or "price" in data:
            return data
    return None
