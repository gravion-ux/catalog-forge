from __future__ import annotations

import asyncio

import httpx

from app.crawler.fetcher import Fetcher
from app.crawler.robots import RobotsRules

PUBLIC = "93.184.216.34"


def resolver(host: str, port: object) -> list[tuple]:
    import socket

    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (PUBLIC, 0))]


def build_fetcher(handler, **kwargs) -> Fetcher:
    settings: dict[str, object] = {
        "user_agent": "CatalogForge/1.0",
        "delay_seconds": 0.0,
        "max_concurrency": 2,
        "timeout_seconds": 5.0,
        "max_pages": 10,
        "transport": httpx.MockTransport(handler),
        "resolver": resolver,
    }
    settings.update(kwargs)
    return Fetcher(**settings)  # type: ignore[arg-type]


def test_get_returns_the_page_text() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<html>hello</html>")

    async def run() -> tuple[int, str]:
        fetcher = build_fetcher(handler)
        result = await fetcher.get("https://shop.example.com/products/blue-shirt")
        await fetcher.aclose()
        return result.status_code, result.text

    status, text = asyncio.run(run())

    assert status == 200
    assert "hello" in text


def test_a_blocked_url_is_refused_without_a_request() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        return httpx.Response(200, text="never used")

    async def run() -> None:
        fetcher = build_fetcher(handler)
        result = await fetcher.get("http://127.0.0.1/admin")
        await fetcher.aclose()
        assert result.error is not None
        assert result.status_code == 0

    asyncio.run(run())

    assert calls == []


def test_robots_rules_are_honoured() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        return httpx.Response(200, text="ok")

    async def run() -> None:
        rules = RobotsRules(disallow=("/private",))
        fetcher = build_fetcher(handler, robots=rules)
        result = await fetcher.get("https://shop.example.com/private/secret")
        await fetcher.aclose()
        assert result.error is not None

    asyncio.run(run())

    assert calls == []


def test_a_redirect_to_a_private_address_is_refused() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            302, headers={"Location": "http://127.0.0.1/admin"}, text=""
        )

    async def run() -> None:
        fetcher = build_fetcher(handler)
        result = await fetcher.get("https://shop.example.com/products/blue-shirt")
        await fetcher.aclose()
        assert result.error is not None
        assert result.status_code == 0

    asyncio.run(run())


def test_a_redirect_to_a_public_address_is_followed() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/products/blue-shirt":
            return httpx.Response(
                302, headers={"Location": "https://shop.example.com/products/red-shirt"}
            )
        return httpx.Response(200, text="followed")

    async def run() -> str:
        fetcher = build_fetcher(handler)
        result = await fetcher.get("https://shop.example.com/products/blue-shirt")
        await fetcher.aclose()
        return result.text

    assert "followed" in asyncio.run(run())


def test_the_page_budget_is_enforced() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="ok")

    async def run() -> tuple[int, str | None]:
        fetcher = build_fetcher(handler, max_pages=1)
        first = await fetcher.get("https://shop.example.com/a")
        second = await fetcher.get("https://shop.example.com/b")
        await fetcher.aclose()
        return second.status_code, second.error

    status, error = asyncio.run(run())

    assert status == 0
    assert error is not None
    assert "budget" in error.lower()


def test_get_bytes_returns_the_body_and_content_type() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"\x89PNG", headers={"Content-Type": "image/png"})

    async def run() -> tuple[bytes, str]:
        fetcher = build_fetcher(handler)
        payload, content_type = await fetcher.get_bytes(
            "https://shop.example.com/media/blue.png"
        )
        await fetcher.aclose()
        return payload, content_type

    payload, content_type = asyncio.run(run())

    assert payload == b"\x89PNG"
    assert content_type == "image/png"


def test_a_failed_request_is_reported_not_raised() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="server error")

    async def run() -> tuple[int, str | None]:
        fetcher = build_fetcher(handler)
        result = await fetcher.get("https://shop.example.com/products/blue-shirt")
        await fetcher.aclose()
        return result.status_code, result.error

    status, error = asyncio.run(run())

    assert status == 500
    assert error is not None
