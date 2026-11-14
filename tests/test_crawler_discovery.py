from __future__ import annotations

import asyncio

from app.crawler.discovery import (
    discover_product_urls,
    looks_like_product_url,
    parse_sitemap,
)
from app.crawler.fetcher import FetchResult
from app.crawler.robots import RobotsRules

URLSET = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://shop.example.com/products/blue-shirt</loc></url>
  <url><loc>https://shop.example.com/products/red-hat</loc></url>
  <url><loc>https://shop.example.com/collections/shoes</loc></url>
</urlset>
"""

SITEMAP_INDEX = """<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap><loc>https://shop.example.com/sitemap-products.xml</loc></sitemap>
  <sitemap><loc>https://shop.example.com/sitemap-pages.xml</loc></sitemap>
</sitemapindex>
"""


class FakeFetcher:
    def __init__(self, pages: dict[str, str]) -> None:
        self.pages = pages
        self.requested: list[str] = []

    async def get(self, url: str) -> FetchResult:
        self.requested.append(url)
        text = self.pages.get(url, "")
        return FetchResult(
            url=url,
            status_code=200 if text else 404,
            text=text,
            error=None if text else "not found",
        )


def test_parse_sitemap_reads_a_urlset() -> None:
    urls = parse_sitemap(URLSET)

    assert urls == [
        "https://shop.example.com/products/blue-shirt",
        "https://shop.example.com/products/red-hat",
        "https://shop.example.com/collections/shoes",
    ]


def test_parse_sitemap_reads_a_sitemap_index() -> None:
    urls = parse_sitemap(SITEMAP_INDEX)

    assert urls == [
        "https://shop.example.com/sitemap-products.xml",
        "https://shop.example.com/sitemap-pages.xml",
    ]


def test_parse_sitemap_survives_broken_xml() -> None:
    assert parse_sitemap("<urlset><url><loc>oops") == []


def test_looks_like_product_url() -> None:
    assert looks_like_product_url("https://shop.example.com/products/blue-shirt") is True
    assert looks_like_product_url("https://shop.example.com/product/123") is True
    assert looks_like_product_url("https://shop.example.com/p/blue-shirt") is True
    assert looks_like_product_url("https://shop.example.com/collections/shoes") is False
    assert looks_like_product_url("https://shop.example.com/") is False


def test_discovery_follows_the_robots_sitemap() -> None:
    fetcher = FakeFetcher(
        {
            "https://shop.example.com/sitemap-products.xml": URLSET,
        }
    )
    robots = RobotsRules(sitemaps=("https://shop.example.com/sitemap-products.xml",))

    urls = asyncio.run(discover_product_urls(fetcher, "https://shop.example.com", robots))

    assert urls == [
        "https://shop.example.com/products/blue-shirt",
        "https://shop.example.com/products/red-hat",
    ]


def test_discovery_falls_back_to_the_default_sitemap() -> None:
    fetcher = FakeFetcher({"https://shop.example.com/sitemap.xml": URLSET})

    urls = asyncio.run(discover_product_urls(fetcher, "https://shop.example.com", RobotsRules()))

    assert "https://shop.example.com/products/blue-shirt" in urls
    assert "https://shop.example.com/sitemap.xml" in fetcher.requested


def test_discovery_skips_disallowed_urls() -> None:
    fetcher = FakeFetcher(
        {
            "https://shop.example.com/sitemap.xml": URLSET,
        }
    )
    robots = RobotsRules(
        disallow=("/products/red-hat",),
        sitemaps=("https://shop.example.com/sitemap.xml",),
    )

    urls = asyncio.run(discover_product_urls(fetcher, "https://shop.example.com", robots))

    assert "https://shop.example.com/products/red-hat" not in urls
    assert "https://shop.example.com/products/blue-shirt" in urls


def test_discovery_removes_duplicates() -> None:
    duplicated = URLSET + URLSET
    fetcher = FakeFetcher({"https://shop.example.com/sitemap.xml": duplicated})

    urls = asyncio.run(discover_product_urls(fetcher, "https://shop.example.com", RobotsRules()))

    assert len(urls) == len(set(urls))
