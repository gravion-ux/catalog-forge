"""Running a crawl over a shop.

The runner is the piece that ties the crawler together: it reads robots.txt,
asks the discovery module for product URLs, reads each product page, stores
the images locally and writes the products into the catalog.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

from app.crawler.discovery import discover_product_urls
from app.crawler.extractors import extract
from app.crawler.images import store_image
from app.crawler.importer import import_product
from app.crawler.normalize import normalize
from app.crawler.robots import RobotsRules, parse_robots

DEFAULT_USER_AGENT = "CatalogForge/1.0"

ProgressCallback = Callable[[str, int, int], None]


@dataclass
class CrawlSummary:
    """What one crawl did."""

    run_id: int
    url: str
    status: str = "completed"
    products_found: int = 0
    products_imported: int = 0
    pages_crawled: int = 0
    error: str | None = None
    started_at: str = ""
    finished_at: str = ""


async def run_crawl(
    conn: sqlite3.Connection,
    fetcher: object,
    url: str,
    *,
    on_progress: ProgressCallback | None = None,
    media_dir: Path | str | None = None,
) -> CrawlSummary:
    """Crawl a shop and import what it finds."""
    started_at = _now()
    run_id = _start_run(conn, url, started_at)

    pages_crawled = 0
    products_found = 0
    products_imported = 0
    platform: str | None = None
    status = "completed"
    error: str | None = None

    try:
        robots = await _load_robots(fetcher, url)
        pages_crawled += 1

        urls = await discover_product_urls(fetcher, url, robots)
        products_found = len(urls)
        _report(on_progress, "discovered", products_found, products_found)

        for index, product_url in enumerate(urls, start=1):
            if not robots.allows(product_url):
                continue

            result = await fetcher.get(product_url)  # type: ignore[attr-defined]
            pages_crawled += 1
            status_code = int(getattr(result, "status_code", 0) or 0)
            page_error = getattr(result, "error", None)
            _record_page(conn, run_id, product_url, status_code, "product", page_error)
            if page_error:
                continue

            product = extract(getattr(result, "text", "") or "", product_url)
            if product is None:
                continue

            data = normalize(product)
            if media_dir is not None:
                data["images"] = await _import_images(
                    fetcher, data.get("images") or [], media_dir
                )

            platform = platform or str(data.get("platform") or "") or None
            import_product(conn, data, source_platform=str(data.get("platform") or "generic"))
            products_imported += 1
            _report(on_progress, "imported", index, len(urls))

    except Exception as exception:  # noqa: BLE001 - a crawl failure must be recorded
        status = "failed"
        error = str(exception)

    finished_at = _now()
    _finish_run(
        conn,
        run_id,
        status=status,
        products_found=products_found,
        products_imported=products_imported,
        pages_crawled=pages_crawled,
        error=error,
        finished_at=finished_at,
        platform=platform,
    )
    _report(on_progress, "done", products_imported, products_found)

    return CrawlSummary(
        run_id=run_id,
        url=url,
        status=status,
        products_found=products_found,
        products_imported=products_imported,
        pages_crawled=pages_crawled,
        error=error,
        started_at=started_at,
        finished_at=finished_at,
    )


async def _load_robots(fetcher: object, url: str) -> RobotsRules:
    """The robots rules of the shop. A missing file allows everything."""
    root = url if url.endswith("/") else url + "/"
    result = await fetcher.get(urljoin(root, "robots.txt"))  # type: ignore[attr-defined]
    text = getattr(result, "text", "") or ""
    if getattr(result, "error", None) or not text:
        return RobotsRules()
    user_agent = getattr(fetcher, "user_agent", DEFAULT_USER_AGENT)
    return parse_robots(text, user_agent)


async def _import_images(
    fetcher: object, images: list[Any], media_dir: Path | str
) -> list[dict[str, Any]]:
    """Download the images of a product and describe where they ended up."""
    stored: list[dict[str, Any]] = []
    for image in images:
        if isinstance(image, str):
            url = image
        elif isinstance(image, dict):
            url = str(image.get("url") or "")
        else:
            continue
        if not url:
            continue

        result = await store_image(fetcher, url, media_dir)
        if result is None:
            stored.append({"url": url, "local_path": None, "content_hash": None})
            continue
        local_path, digest = result
        stored.append({"url": url, "local_path": local_path, "content_hash": digest})
    return stored


def _start_run(conn: sqlite3.Connection, url: str, started_at: str) -> int:
    cursor = conn.execute(
        "INSERT INTO crawl_runs (url, status, started_at) VALUES (?, 'running', ?)",
        (url, started_at),
    )
    conn.commit()
    return int(cursor.lastrowid)


def _finish_run(
    conn: sqlite3.Connection,
    run_id: int,
    *,
    status: str,
    products_found: int,
    products_imported: int,
    pages_crawled: int,
    error: str | None,
    finished_at: str,
    platform: str | None,
) -> None:
    conn.execute(
        "UPDATE crawl_runs SET status = ?, products_found = ?, products_imported = ?,"
        " pages_crawled = ?, error = ?, finished_at = ?, platform = ? WHERE id = ?",
        (
            status,
            products_found,
            products_imported,
            pages_crawled,
            error,
            finished_at,
            platform,
            run_id,
        ),
    )
    conn.commit()


def _record_page(
    conn: sqlite3.Connection,
    run_id: int,
    url: str,
    status_code: int,
    kind: str,
    error: str | None,
) -> None:
    conn.execute(
        "INSERT INTO crawled_pages (run_id, url, status_code, kind, error, fetched_at)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (run_id, url, status_code, kind, error, _now()),
    )


def _report(
    callback: ProgressCallback | None, stage: str, current: int, total: int
) -> None:
    if callback is None:
        return
    try:
        callback(stage, current, total)
    except Exception:  # noqa: BLE001 - progress must never break a crawl
        pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
