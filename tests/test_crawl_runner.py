from __future__ import annotations

import asyncio
import sqlite3
from pathlib import Path

from app.crawler.fetcher import FetchResult
from app.crawler.runner import run_crawl

SITEMAP = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://shop.example.com/products/blue-shirt</loc></url>
  <url><loc>https://shop.example.com/products/red-hat</loc></url>
  <url><loc>https://shop.example.com/collections/shoes</loc></url>
</urlset>
"""

ROBOTS = """User-agent: *
Disallow: /private
"""

BLUE_SHIRT = """
<html><head>
<script type="application/ld+json">
{"@context": "https://schema.org", "@type": "Product", "name": "Blue Shirt",
 "description": "A comfortable blue shirt.", "sku": "SHIRT-BLUE",
 "brand": {"@type": "Brand", "name": "Northwind"},
 "image": "https://cdn.example.com/blue.png",
 "offers": {"@type": "Offer", "price": "19.90", "priceCurrency": "USD",
            "availability": "https://schema.org/InStock"}}
</script>
</head><body></body></html>
"""

RED_HAT = """
<html><head>
<script type="application/ld+json">
{"@context": "https://schema.org", "@type": "Product", "name": "Red Hat",
 "offers": {"@type": "Offer", "price": "5.00", "priceCurrency": "EUR"}}
</script>
</head><body></body></html>
"""

PNG = b"\x89PNG\r\n\x1a\n" + b"blue-shirt"


class FixtureFetcher:
    """A tiny shop, served from memory."""

    user_agent = "CatalogForge/1.0"

    def __init__(self, pages: dict[str, str], images: dict[str, bytes]) -> None:
        self.pages = pages
        self.images = images
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

    async def get_bytes(self, url: str) -> tuple[bytes, str]:
        self.requested.append(url)
        return self.images.get(url, b""), "image/png"


def make_fetcher() -> FixtureFetcher:
    return FixtureFetcher(
        {
            "https://shop.example.com/robots.txt": ROBOTS,
            "https://shop.example.com/sitemap.xml": SITEMAP,
            "https://shop.example.com/products/blue-shirt": BLUE_SHIRT,
            "https://shop.example.com/products/red-hat": RED_HAT,
        },
        {"https://cdn.example.com/blue.png": PNG},
    )


def test_a_crawl_imports_the_products(conn: sqlite3.Connection, tmp_path: Path) -> None:
    fetcher = make_fetcher()

    summary = asyncio.run(
        run_crawl(
            conn,
            fetcher,
            "https://shop.example.com",
            media_dir=tmp_path / "data" / "media",
        )
    )

    assert summary.status == "completed"
    assert summary.products_found == 2
    assert summary.products_imported == 2
    assert summary.error is None
    assert conn.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 2


def test_a_crawl_records_the_run(conn: sqlite3.Connection) -> None:
    fetcher = make_fetcher()

    summary = asyncio.run(run_crawl(conn, fetcher, "https://shop.example.com"))

    row = conn.execute(
        "SELECT * FROM crawl_runs WHERE id = ?", (summary.run_id,)
    ).fetchone()
    assert row is not None
    assert row["url"] == "https://shop.example.com"
    assert row["status"] == "completed"
    assert row["products_found"] == 2
    assert row["products_imported"] == 2
    assert row["pages_crawled"] >= 2
    assert row["started_at"]
    assert row["finished_at"]


def test_a_crawl_stores_the_images(conn: sqlite3.Connection, tmp_path: Path) -> None:
    fetcher = make_fetcher()

    asyncio.run(
        run_crawl(
            conn,
            fetcher,
            "https://shop.example.com",
            media_dir=tmp_path / "data" / "media",
        )
    )

    rows = conn.execute("SELECT * FROM images").fetchall()
    assert len(rows) == 1
    assert rows[0]["remote_url"] == "https://cdn.example.com/blue.png"
    assert rows[0]["local_path"] is not None
    assert rows[0]["content_hash"] is not None


def test_a_crawl_reports_progress(conn: sqlite3.Connection) -> None:
    seen: list[tuple[str, int, int]] = []

    def on_progress(stage: str, current: int, total: int) -> None:
        seen.append((stage, current, total))

    asyncio.run(
        run_crawl(conn, make_fetcher(), "https://shop.example.com", on_progress=on_progress)
    )

    assert seen
    assert seen[-1][0] == "done"


def test_a_crawl_of_a_site_without_products_finishes_cleanly(
    conn: sqlite3.Connection,
) -> None:
    fetcher = FixtureFetcher(
        {
            "https://empty.example.com/robots.txt": "",
            "https://empty.example.com/sitemap.xml": (
                '<?xml version="1.0"?><urlset></urlset>'
            ),
        },
        {},
    )

    summary = asyncio.run(run_crawl(conn, fetcher, "https://empty.example.com"))

    assert summary.status == "completed"
    assert summary.products_found == 0
    assert summary.products_imported == 0
