"""The extractor for shops that publish schema.org markup.

Three sources are tried in order: JSON-LD (the richest), microdata (the older
schema.org markup) and OpenGraph (the fallback every social meta tag uses).
"""

from __future__ import annotations

from typing import Any

from app.crawler.extractors.base import (
    ExtractedProduct,
    brand_name,
    first_offer,
    image_urls,
    is_type,
    iter_nodes,
    json_ld_blocks,
    soup,
    string_list,
    text_value,
)


def detect(html_text: str) -> bool:
    """True when the page carries product markup in any of the three formats."""
    return (
        _from_json_ld(html_text) is not None
        or _from_microdata(html_text) is not None
        or _from_open_graph(html_text) is not None
    )


def extract(html_text: str, url: str) -> ExtractedProduct | None:
    """Read the product off a page, or ``None`` when it holds no product data."""
    for reader in (_from_json_ld, _from_microdata, _from_open_graph):
        product = reader(html_text)
        if product is not None:
            product.platform = "generic"
            product.source_url = url
            return product
    return None


def _from_json_ld(html_text: str) -> ExtractedProduct | None:
    """The first ``Product`` node in any JSON-LD block on the page."""
    for block in json_ld_blocks(html_text):
        for node in iter_nodes(block):
            if not is_type(node, "Product"):
                continue
            product = _product_from_node(node)
            if product is not None:
                return product
    return None


def _product_from_node(node: dict[str, Any]) -> ExtractedProduct | None:
    title = text_value(node.get("name"))
    if not title:
        return None

    offer = first_offer(node)
    return ExtractedProduct(
        title=title,
        description=text_value(node.get("description")),
        price=text_value(offer.get("price")) or None,
        compare_at_price=text_value(offer.get("highPrice")) or None,
        currency=text_value(offer.get("priceCurrency")) or None,
        images=image_urls(node.get("image")),
        vendor=brand_name(node.get("brand")),
        sku=text_value(node.get("sku")) or None,
        availability=text_value(offer.get("availability")) or None,
        categories=string_list(node.get("category")),
    )


def _from_microdata(html_text: str) -> ExtractedProduct | None:
    """The product described with schema.org ``itemprop`` attributes."""
    document = soup(html_text)

    scope = None
    for element in document.find_all(attrs={"itemscope": True}):
        item_type = (element.get("itemtype") or "").lower()
        if "product" in item_type:
            scope = element
            break
    if scope is None:
        return None

    title = _property(scope, "name")
    if not title:
        return None

    images: list[str] = []
    for element in scope.find_all(attrs={"itemprop": "image"}):
        source = element.get("src") or element.get("content") or element.get("href")
        if isinstance(source, str) and source.strip():
            images.append(source.strip())

    return ExtractedProduct(
        title=title,
        description=_property(scope, "description") or "",
        price=_property(scope, "price"),
        currency=_property(scope, "priceCurrency"),
        images=images,
        sku=_property(scope, "sku"),
    )


def _property(scope: Any, name: str) -> str | None:
    """The value of an ``itemprop`` inside a microdata scope."""
    element = scope.find(attrs={"itemprop": name})
    if element is None:
        return None
    content = element.get("content")
    if isinstance(content, str) and content.strip():
        return content.strip()
    text = element.get_text(strip=True)
    return text or None


def _from_open_graph(html_text: str) -> ExtractedProduct | None:
    """The product described by OpenGraph meta tags."""
    document = soup(html_text)

    title = _meta(document, "og:title")
    if not title:
        return None

    price = _meta(document, "product:price:amount")
    og_type = (_meta(document, "og:type") or "").lower()
    if not price and og_type != "product":
        return None

    images: list[str] = []
    image = _meta(document, "og:image")
    if image:
        images.append(image)

    return ExtractedProduct(
        title=title,
        description=_meta(document, "og:description") or "",
        price=price,
        currency=_meta(document, "product:price:currency"),
        images=images,
    )


def _meta(document: Any, prop: str) -> str | None:
    """The content of a meta tag, by ``property`` or by ``name``."""
    element = document.find("meta", attrs={"property": prop})
    if element is None:
        element = document.find("meta", attrs={"name": prop})
    if element is None:
        return None
    content = element.get("content")
    if isinstance(content, str) and content.strip():
        return content.strip()
    return None
