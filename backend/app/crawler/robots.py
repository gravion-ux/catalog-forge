"""robots.txt parsing and rule evaluation.

The crawler honors ``Disallow`` and ``Allow`` for the group that matches its
user agent, and reads ``Crawl-delay`` and ``Sitemap`` directives.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit

import httpx


@dataclass(frozen=True)
class RobotsRules:
    """The rules that apply to one user agent."""

    disallow: tuple[str, ...] = ()
    allow: tuple[str, ...] = ()
    crawl_delay: float | None = None
    sitemaps: tuple[str, ...] = ()

    def allows(self, url: str) -> bool:
        """True when the crawler may request this URL."""
        target = _target(url)
        allowed_length = _best_match(self.allow, target)
        blocked_length = _best_match(self.disallow, target)
        if blocked_length is None:
            return True
        if allowed_length is None:
            return False
        return allowed_length >= blocked_length

    def delay(self, default: float) -> float:
        """The delay to wait between requests to this host."""
        return self.crawl_delay if self.crawl_delay is not None else default


def _target(url: str) -> str:
    """The path and query of a URL, which is what robots rules match."""
    try:
        parts = urlsplit(url)
    except ValueError:
        return "/"
    path = parts.path or "/"
    if parts.query:
        return f"{path}?{parts.query}"
    return path


def _pattern_to_regex(pattern: str) -> re.Pattern[str]:
    anchored = pattern.endswith("$")
    body = pattern[:-1] if anchored else pattern
    escaped = re.escape(body).replace("\\*", ".*")
    return re.compile("^" + escaped + ("$" if anchored else ""))


def _best_match(patterns: tuple[str, ...], target: str) -> int | None:
    """The length of the most specific pattern that matches, if any."""
    best: int | None = None
    for pattern in patterns:
        if not pattern:
            continue
        if _pattern_to_regex(pattern).match(target):
            if best is None or len(pattern) > best:
                best = len(pattern)
    return best


def parse_robots(text: str, user_agent: str) -> RobotsRules:
    """Parse a robots.txt body for the rules that apply to ``user_agent``."""
    groups: list[tuple[list[str], list[tuple[str, str]]]] = []
    current_agents: list[str] = []
    current_rules: list[tuple[str, str]] = []
    sitemaps: list[str] = []

    def flush() -> None:
        nonlocal current_agents, current_rules
        if current_agents:
            groups.append((list(current_agents), list(current_rules)))
        current_agents = []
        current_rules = []

    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        field, _, value = line.partition(":")
        field = field.strip().lower()
        value = value.strip()

        if field == "user-agent":
            if current_agents and current_rules:
                flush()
            current_agents.append(value.lower())
            continue
        if field == "sitemap":
            if value:
                sitemaps.append(value)
            continue
        if not current_agents:
            continue
        if field in {"disallow", "allow", "crawl-delay"}:
            current_rules.append((field, value))
    flush()

    token = user_agent.split("/")[0].strip().lower()
    selected: list[tuple[str, str]] | None = None

    for agents, rules in groups:
        for agent in agents:
            if agent == "*":
                continue
            if agent and (agent in token or token in agent):
                selected = rules
                break
        if selected is not None:
            break

    if selected is None:
        for agents, rules in groups:
            if "*" in agents:
                selected = rules
                break

    if selected is None:
        selected = []

    disallow = tuple(
        value for field, value in selected if field == "disallow" and value
    )
    allow = tuple(value for field, value in selected if field == "allow" and value)

    delay: float | None = None
    for field, value in selected:
        if field == "crawl-delay":
            try:
                delay = float(value)
            except ValueError:
                delay = None

    return RobotsRules(
        disallow=disallow,
        allow=allow,
        crawl_delay=delay,
        sitemaps=tuple(sitemaps),
    )


async def fetch_robots(
    client: httpx.AsyncClient, base_url: str, user_agent: str
) -> RobotsRules:
    """Fetch and parse robots.txt. A missing file allows everything."""
    root = base_url if base_url.endswith("/") else base_url + "/"
    robots_url = urljoin(root, "robots.txt")
    try:
        response = await client.get(robots_url, headers={"User-Agent": user_agent})
    except httpx.HTTPError:
        return RobotsRules()
    if response.status_code >= 400:
        return RobotsRules()
    return parse_robots(response.text, user_agent)
