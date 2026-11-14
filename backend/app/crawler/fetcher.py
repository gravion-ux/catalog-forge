"""The HTTP client the crawler uses.

It is deliberately slow and careful: one request per host at a time, a delay
between requests, a page budget, robots.txt rules, and a redirect handler that
re-checks every hop against the URL policy instead of following blindly.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from urllib.parse import urlsplit

import httpx

from app.crawler.robots import RobotsRules
from app.crawler.urls import (
    ALLOWED_SCHEMES,
    BLOCKED_HOSTNAMES,
    is_public_url,
    normalize_url,
)

REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})
MAX_REDIRECTS = 5


@dataclass
class FetchResult:
    """What came back from one URL, or why nothing did."""

    url: str
    status_code: int = 0
    text: str = ""
    content: bytes = b""
    headers: dict[str, str] = field(default_factory=dict)
    error: str | None = None
    final_url: str = ""

    @property
    def ok(self) -> bool:
        return self.error is None and 200 <= self.status_code < 300


class Fetcher:
    """A polite HTTP client with a URL policy built in."""

    def __init__(
        self,
        *,
        user_agent: str,
        delay_seconds: float = 1.0,
        max_concurrency: int = 4,
        timeout_seconds: float = 20.0,
        max_pages: int = 500,
        allow_private: bool = False,
        transport: httpx.AsyncBaseTransport | None = None,
        resolver: Callable[[str, object], list] | None = None,
        robots: RobotsRules | None = None,
    ) -> None:
        self.user_agent = user_agent
        self.delay_seconds = delay_seconds
        self.max_concurrency = max_concurrency
        self.timeout_seconds = timeout_seconds
        self.max_pages = max_pages
        self.allow_private = allow_private
        self.robots = robots
        self.pages_fetched = 0

        self._resolver = resolver
        self._last_request: dict[str, float] = {}
        self._lock = asyncio.Lock()
        self._semaphore = asyncio.Semaphore(max(1, max_concurrency))
        self._client = httpx.AsyncClient(
            follow_redirects=False,
            timeout=timeout_seconds,
            transport=transport,
            headers={"User-Agent": user_agent},
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def get(self, url: str) -> FetchResult:
        """Fetch a URL and return its body as text."""
        return await self._request(url, want_bytes=False)

    async def get_bytes(self, url: str) -> tuple[bytes, str]:
        """Fetch a URL and return its body as bytes plus the content type."""
        result = await self._request(url, want_bytes=True)
        if result.error:
            return b"", ""
        return result.content, result.headers.get("content-type", "")

    def _allowed(self, url: str) -> bool:
        try:
            parts = urlsplit(url)
        except ValueError:
            return False
        if parts.scheme.lower() not in ALLOWED_SCHEMES:
            return False
        host = (parts.hostname or "").lower()
        if host in BLOCKED_HOSTNAMES:
            return False
        if self.allow_private:
            return True
        return is_public_url(url, self._resolver)

    async def _wait_for_slot(self, url: str) -> None:
        host = urlsplit(url).hostname or ""
        wait = 0.0
        async with self._lock:
            now = time.monotonic()
            last = self._last_request.get(host)
            if last is not None:
                wait = self.delay_seconds - (now - last)
            self._last_request[host] = now + max(0.0, wait)
        if wait > 0:
            await asyncio.sleep(wait)

    async def _request(self, url: str, *, want_bytes: bool) -> FetchResult:
        current = normalize_url(url)

        for _ in range(MAX_REDIRECTS + 1):
            if not self._allowed(current):
                return FetchResult(
                    url=url, error=f"Blocked by the URL policy: {current}"
                )
            if self.robots is not None and not self.robots.allows(current):
                return FetchResult(
                    url=url, error=f"Disallowed by robots.txt: {current}"
                )
            if self.pages_fetched >= self.max_pages:
                return FetchResult(
                    url=url, error="The crawl page budget is exhausted."
                )

            self.pages_fetched += 1
            await self._wait_for_slot(current)

            try:
                async with self._semaphore:
                    response = await self._client.get(current)
            except httpx.HTTPError as error:
                return FetchResult(url=url, error=f"The request failed: {error}")

            headers = {key.lower(): value for key, value in response.headers.items()}

            if response.status_code in REDIRECT_STATUSES:
                location = headers.get("location")
                if not location:
                    return FetchResult(
                        url=url,
                        status_code=response.status_code,
                        headers=headers,
                        error="The server sent a redirect without a target.",
                    )
                current = normalize_url(location, current)
                continue

            if response.status_code >= 400:
                return FetchResult(
                    url=url,
                    final_url=str(response.url),
                    status_code=response.status_code,
                    headers=headers,
                    error=f"The server answered {response.status_code}.",
                )

            if want_bytes:
                return FetchResult(
                    url=url,
                    final_url=str(response.url),
                    status_code=response.status_code,
                    content=response.content,
                    headers=headers,
                )
            return FetchResult(
                url=url,
                final_url=str(response.url),
                status_code=response.status_code,
                text=response.text,
                headers=headers,
            )

        return FetchResult(url=url, error="Too many redirects.")
