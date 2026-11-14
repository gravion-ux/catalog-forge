"""The product shape that every extractor produces, plus the shared parsing tools.

The extractors differ in where they read a product from, but they all end up
filling the same :class:`ExtractedProduct` record, so the importer only ever
has to understand one shape.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

from bs4 import BeautifulSoup

JSON_LD_TYPE = "application/ld+json"


@dataclass
class ExtractedProduct:
    """One product as it was found on a page."""

    title: str = ""
    description: str = ""
    price: str | None = None
    compare_at_price: str | None = None
    currency: str | None = None
    images: list[str] = field(default_factory=list)
    vendor: str | None = None
    sku: str | None = None
    availability: str | None = None
    variants: list[dict[str, Any]] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)
    platform: str = "generic"
    source_url: str = ""
    #: The stock count when the shop publishes one. ``None`` means unknown.
    stock: int | None = None


def soup(html_text: str) -> BeautifulSoup:
    """Parse a page once."""
    return BeautifulSoup(html_text or "", "html.parser")


def clean_json_text(raw: str) -> str:
    """Strip the comment wrappers some sites put around a JSON-LD block."""
    return raw.replace("<!--", "").replace("-->", "").strip()


def json_ld_blocks(html_text: str) -> list[Any]:
    """Every JSON-LD block on the page, parsed. Bad blocks are skipped."""
    blocks: list[Any] = []
    document = soup(html_text)
    for script in document.find_all("script", attrs={"type": JSON_LD_TYPE}):
        raw = script.string
        if raw is None:
            raw = script.get_text()
        text = clean_json_text(raw or "")
        if not text:
            continue
        try:
            blocks.append(json.loads(text))
        except (json.JSONDecodeError, ValueError):
            continue
    return blocks


def iter_nodes(data: Any) -> Iterator[dict[str, Any]]:
    """Every object in a JSON-LD document, including the members of ``@graph``."""
    if isinstance(data, list):
        for item in data:
            yield from iter_nodes(item)
        return
    if not isinstance(data, dict):
        return
    yield data
    graph = data.get("@graph")
    if graph is not None:
        yield from iter_nodes(graph)


def is_type(node: dict[str, Any], wanted: str) -> bool:
    """True when a JSON-LD node declares the given ``@type``."""
    value = node.get("@type")
    if isinstance(value, str):
        return value.lower() == wanted.lower()
    if isinstance(value, list):
        return any(
            isinstance(item, str) and item.lower() == wanted.lower() for item in value
        )
    return False


def first_offer(node: dict[str, Any]) -> dict[str, Any]:
    """The first offer of a product node, whether it is a list or a single one."""
    offers = node.get("offers")
    if isinstance(offers, list):
        offers = offers[0] if offers else None
    return offers if isinstance(offers, dict) else {}


def text_value(value: Any) -> str:
    """A trimmed string for a JSON value, or an empty string."""
    if value is None or isinstance(value, bool):
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float)):
        return str(value)
    return ""


def brand_name(value: Any) -> str | None:
    """The brand of a product, whether it is a string or a schema.org object."""
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, list):
        for item in value:
            name = brand_name(item)
            if name:
                return name
        return None
    if isinstance(value, dict):
        name = value.get("name")
        if isinstance(name, str) and name.strip():
            return name.strip()
    return None


def string_list(value: Any) -> list[str]:
    """A list of strings from a JSON value that may be a string or a list."""
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if isinstance(value, list):
        items: list[str] = []
        for item in value:
            items.extend(string_list(item))
        return items
    return []


def image_urls(value: Any) -> list[str]:
    """Every image URL in a schema.org ``image`` value."""
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if isinstance(value, list):
        images: list[str] = []
        for item in value:
            images.extend(image_urls(item))
        return images
    if isinstance(value, dict):
        for key in ("url", "@id", "contentUrl"):
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate.strip():
                return [candidate.strip()]
    return []


def scan_json_object(text: str, start: int) -> str | None:
    """The JSON object that begins at ``start``, honouring braces inside strings."""
    depth = 0
    in_string = False
    escaped = False

    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    return None


def embedded_json_objects(text: str, patterns: tuple[str, ...]) -> list[dict[str, Any]]:
    """The JSON objects that inline scripts assign to the given names."""
    found: list[dict[str, Any]] = []
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            brace = text.find("{", match.end())
            if brace == -1:
                continue
            raw = scan_json_object(text, brace)
            if raw is None:
                continue
            try:
                data = json.loads(raw)
            except (json.JSONDecodeError, ValueError):
                continue
            if isinstance(data, dict):
                found.append(data)
    return found


def extract(html_text: str, url: str) -> ExtractedProduct | None:
    """Read a product off a page, whatever platform the page comes from.

    The platform-specific extractors are imported here rather than at module
    level because they share this module, and importing them eagerly would be a
    cycle.
    """
    from app.crawler.extractors import generic, shopify, woocommerce

    if shopify.detect(html_text):
        return shopify.extract(html_text, url)
    if woocommerce.detect(html_text):
        return woocommerce.extract(html_text, url)
    if generic.detect(html_text):
        return generic.extract(html_text, url)
    return None
