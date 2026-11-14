"""Crawl run queries."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from app.models import CrawlRun

DEFAULT_LIMIT = 50
MAX_LIMIT = 200


def create_crawl_run(conn: sqlite3.Connection, url: str) -> int:
    """Open a crawl run row and return its id."""
    cursor = conn.execute(
        "INSERT INTO crawl_runs (url, status, started_at) VALUES (?, 'pending', ?)",
        (url, _now()),
    )
    conn.commit()
    return int(cursor.lastrowid)


def get_crawl_run(conn: sqlite3.Connection, run_id: int) -> CrawlRun | None:
    """One crawl run."""
    row = conn.execute(
        "SELECT * FROM crawl_runs WHERE id = ?", (run_id,)
    ).fetchone()
    return CrawlRun.from_row(row) if row else None


def list_crawl_runs(
    conn: sqlite3.Connection, *, limit: int = DEFAULT_LIMIT
) -> list[CrawlRun]:
    """The most recent crawl runs."""
    limit = max(1, min(limit, MAX_LIMIT))
    rows = conn.execute(
        "SELECT * FROM crawl_runs ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    return [CrawlRun.from_row(row) for row in rows]


def count_crawl_runs(conn: sqlite3.Connection) -> int:
    """How many crawl runs there are."""
    return int(conn.execute("SELECT COUNT(*) FROM crawl_runs").fetchone()[0])


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
