"""Finding the product pages of a shop.

A sitemap is the polite way to learn what a shop sells: the site publishes the
list itself. This module reads sitemaps (both ``sitemapindex`` and ``urlset``),
follows the child sitemaps an index points at, and keeps only the URLs that
look like product pages and that robots.txt allows.
"""

from __future__ import annotations

import re
from urllib.parse import urljoin, urlsplit
from xml.etree import ElementTree

from app.crawler.robots import RobotsRules
from app.crawler.urls import same_site

DEFAULT_SITEMAP = "sitemap.xml"

PRODUCT_PATH_SEGMENTS = frozenset(
    {
        "product",
        "products",
        "item",
        "items",
        "p",
        "shop",
    }
)

_LOC_FALLBACK = re.compile(r"<loc>\s*(.*?)\s*</loc>", re.IGNORECASE | re.DOTALL)


def _local_name(tag: object) -> str:
    """The tag name without its XML namespace."""
    if not isinstance(tag, str):
        return ""
    return tag.rsplit("}", 1)[-1].lower()


def parse_sitemap(xml_text: str) -> list[str]:
    """Every ``loc`` in a sitemap document, in document order.

    Both ``sitemapindex`` and ``urlset`` documents are handled, because both
    carry their entries in ``loc`` elements. A document that is not valid XML
    is scanned for ``loc`` elements as a fallback, so one stray byte in a large
    sitemap does not throw the whole crawl away.
    """
    if not xml_text or not xml_text.strip():
        return []

    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError:
        return [
            match.strip()
            for match in _LOC_FALLBACK.findall(xml_text)
            if match.strip()
        ]

    locations: list[str] = []
    for element in root.iter():
        if _local_name(element.tag) != "loc":
            continue
        text = (element.text or "").strip()
        if text:
            locations.append(text)
    return locations


def looks_like_product_url(url: str) -> bool:
    """True when the URL path looks like it points at a single product."""
    try:
        parts = urlsplit(url)
    except ValueError:
        return False
    segments = [segment for segment in (parts.path or "").split("/") if segment]
    return any(segment.lower() in PRODUCT_PATH_SEGMENTS for segment in segments)


def looks_like_sitemap_url(url: str) -> bool:
    """True when the URL points at a sitemap document rather than a page."""
    try:
        parts = urlsplit(url)
    except ValueError:
        return False
    path = (parts.path or "").lower()
    return path.endswith(".xml") or path.endswith(".xml.gz")


def _sitemap_urls(base_url: str, robots: RobotsRules) -> list[str]:
    """The sitemaps to read, in order: the ones robots.txt names, else the default."""
    if robots.sitemaps:
        return list(robots.sitemaps)
    root = base_url if base_url.endswith("/") else base_url + "/"
    return [urljoin(root, DEFAULT_SITEMAP)]


async def discover_product_urls(
    fetcher: object,
    base_url: str,
    robots: RobotsRules,
) -> list[str]:
    """The product URLs of a shop, discovered through its sitemaps.

    URLs that robots.txt disallows are left out, duplicates are dropped, and a
    sitemap index is followed down to its children.
    """
    queue = _sitemap_urls(base_url, robots)
    visited_sitemaps: set[str] = set()
    found: list[str] = []
    seen: set[str] = set()

    while queue:
        sitemap_url = queue.pop(0)
        if sitemap_url in visited_sitemaps:
            continue
        visited_sitemaps.add(sitemap_url)

        result = await fetcher.get(sitemap_url)  # type: ignore[attr-defined]
        text = getattr(result, "text", "") or ""
        if getattr(result, "error", None) or not text:
            continue

        for location in parse_sitemap(text):
            if looks_like_sitemap_url(location):
                if location not in visited_sitemaps:
                    queue.append(location)
                continue
            if not looks_like_product_url(location):
                continue
            if not same_site(location, base_url):
                continue
            if not robots.allows(location):
                continue
            if location in seen:
                continue
            seen.add(location)
            found.append(location)

    return found
