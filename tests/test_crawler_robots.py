from __future__ import annotations

import asyncio

import httpx

from app.crawler.robots import RobotsRules, fetch_robots, parse_robots

ROBOTS = """
User-agent: *
Disallow: /private
Allow: /private/public-page
Crawl-delay: 2

User-agent: BadBot
Disallow: /

Sitemap: https://shop.example.com/sitemap.xml
"""


def test_disallow_blocks_the_path() -> None:
    rules = parse_robots(ROBOTS, "CatalogForge/1.0")

    assert rules.allows("https://shop.example.com/private/secret") is False
    assert rules.allows("https://shop.example.com/products/blue-shirt") is True


def test_allow_overrides_a_shorter_disallow() -> None:
    rules = parse_robots(ROBOTS, "CatalogForge/1.0")

    assert rules.allows("https://shop.example.com/private/public-page") is True


def test_crawl_delay_is_read() -> None:
    rules = parse_robots(ROBOTS, "CatalogForge/1.0")

    assert rules.crawl_delay == 2.0


def test_sitemaps_are_read() -> None:
    rules = parse_robots(ROBOTS, "CatalogForge/1.0")

    assert "https://shop.example.com/sitemap.xml" in rules.sitemaps


def test_a_named_agent_group_is_used_when_it_matches() -> None:
    rules = parse_robots(ROBOTS, "BadBot/2.0")

    assert rules.allows("https://shop.example.com/products/blue-shirt") is False


def test_an_empty_disallow_allows_everything() -> None:
    rules = parse_robots("User-agent: *\nDisallow:\n", "CatalogForge/1.0")

    assert rules.allows("https://shop.example.com/anything") is True


def test_wildcards_and_end_anchors_are_supported() -> None:
    rules = parse_robots(
        "User-agent: *\nDisallow: /*.pdf$\nDisallow: /tmp/*\n", "CatalogForge/1.0"
    )

    assert rules.allows("https://shop.example.com/docs/manual.pdf") is False
    assert rules.allows("https://shop.example.com/docs/manual.pdf?x=1") is True
    assert rules.allows("https://shop.example.com/tmp/cache") is False


def test_empty_rules_allow_everything() -> None:
    rules = RobotsRules()

    assert rules.allows("https://shop.example.com/anything") is True
    assert rules.crawl_delay is None


def test_fetch_robots_reads_the_file() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=ROBOTS)

    async def run() -> RobotsRules:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await fetch_robots(client, "https://shop.example.com", "CatalogForge/1.0")

    rules = asyncio.run(run())

    assert rules.allows("https://shop.example.com/private/secret") is False


def test_a_missing_robots_file_allows_everything() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="not found")

    async def run() -> RobotsRules:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await fetch_robots(client, "https://shop.example.com", "CatalogForge/1.0")

    rules = asyncio.run(run())

    assert rules.allows("https://shop.example.com/anything") is True
