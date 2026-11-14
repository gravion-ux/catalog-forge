"""Which URLs the crawler is allowed to request.

The rule is simple: only ``http`` and ``https``, only public addresses, and
never a URL that carries credentials in it. Private, loopback, link-local and
cloud-metadata addresses are refused, because a crawler that can reach
``169.254.169.254`` is a crawler that can leak the host's cloud credentials.
"""

from __future__ import annotations

import ipaddress
import socket
from collections.abc import Callable
from urllib.parse import urljoin, urlsplit, urlunsplit

ALLOWED_SCHEMES = frozenset({"http", "https"})

BLOCKED_HOSTNAMES = frozenset(
    {
        "169.254.169.254",
        "metadata.google.internal",
        "metadata.goog",
        "metadata",
        "instance-data",
        "fd00:ec2::254",
    }
)

Resolver = Callable[[str, object], list]


class UrlNotAllowed(ValueError):
    """Raised when a URL is not allowed to be fetched."""


def normalize_url(url: str, base: str | None = None) -> str:
    """Make a URL absolute, lowercase its scheme and host, drop the fragment."""
    cleaned = (url or "").strip()
    if not cleaned:
        return ""
    try:
        joined = urljoin(base or "", cleaned)
        parts = urlsplit(joined)
    except ValueError:
        return cleaned
    return urlunsplit(
        (
            parts.scheme.lower(),
            parts.netloc.lower(),
            parts.path or "/",
            parts.query,
            "",
        )
    )


def is_public_ip(address: str) -> bool:
    """True when the address is routable on the public internet.

    The order of the checks matters. Python classifies the IPv6 loopback
    address as *reserved* as well as *loopback*, so the loopback test has to
    come before the reserved test.
    """
    try:
        ip = ipaddress.ip_address(address)
    except ValueError:
        return False
    if ip.is_unspecified:
        return False
    if ip.is_multicast:
        return False
    if ip.is_link_local:
        return False
    if ip.is_loopback:
        return False
    if ip.is_reserved:
        return False
    if ip.is_private:
        return False
    return True


def resolve_host(host: str, resolver: Resolver | None = None) -> list[str]:
    """Resolve a hostname to its addresses. An empty list means it failed."""
    lookup = resolver or socket.getaddrinfo
    try:
        infos = lookup(host, None)
    except (socket.gaierror, OSError, UnicodeError, ValueError):
        return []
    addresses: list[str] = []
    for info in infos:
        sockaddr = info[4]
        if sockaddr:
            addresses.append(str(sockaddr[0]))
    return addresses


def is_public_url(url: str, resolver: Resolver | None = None) -> bool:
    """True when the URL may be requested.

    A name that cannot be resolved is refused: the request would fail anyway,
    and refusing keeps the decision on the safe side.
    """
    try:
        parts = urlsplit(url)
    except ValueError:
        return False

    if parts.scheme.lower() not in ALLOWED_SCHEMES:
        return False
    try:
        if parts.username or parts.password:
            return False
    except ValueError:
        return False

    host = (parts.hostname or "").lower()
    if not host:
        return False
    if host in BLOCKED_HOSTNAMES:
        return False

    try:
        ipaddress.ip_address(host)
    except ValueError:
        addresses = resolve_host(host, resolver)
        if not addresses:
            return False
        return all(is_public_ip(address) for address in addresses)

    return is_public_ip(host)


def same_site(first: str, second: str) -> bool:
    """True when both URLs point at the same host."""
    try:
        host_a = (urlsplit(first).hostname or "").lower()
        host_b = (urlsplit(second).hostname or "").lower()
    except ValueError:
        return False
    return bool(host_a) and host_a == host_b
