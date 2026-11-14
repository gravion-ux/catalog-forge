from __future__ import annotations

import socket

from app.crawler.urls import (
    UrlNotAllowed,
    is_public_url,
    normalize_url,
    same_site,
)


def fake_resolver(address: str):
    def resolver(host: str, port: object) -> list[tuple]:
        return [
            (
                socket.AF_INET,
                socket.SOCK_STREAM,
                6,
                "",
                (address, 0),
            )
        ]

    return resolver


PUBLIC = fake_resolver("93.184.216.34")
PRIVATE = fake_resolver("10.0.0.5")
LOOPBACK = fake_resolver("127.0.0.1")


def test_normalize_url_joins_a_relative_path() -> None:
    result = normalize_url("/products/blue-shirt", "https://shop.example.com/collections/")

    assert result == "https://shop.example.com/products/blue-shirt"


def test_normalize_url_drops_the_fragment() -> None:
    result = normalize_url("https://shop.example.com/products/blue-shirt#reviews")

    assert result == "https://shop.example.com/products/blue-shirt"


def test_normalize_url_keeps_the_query() -> None:
    result = normalize_url("https://shop.example.com/search?q=shirt")

    assert result == "https://shop.example.com/search?q=shirt"


def test_non_http_schemes_are_not_public() -> None:
    assert is_public_url("ftp://example.com/file.txt", resolver=PUBLIC) is False
    assert is_public_url("file:///etc/passwd", resolver=PUBLIC) is False
    assert is_public_url("javascript:alert(1)", resolver=PUBLIC) is False


def test_embedded_credentials_are_refused() -> None:
    url = "https://user:secret@example.com/products/blue-shirt"

    assert is_public_url(url, resolver=PUBLIC) is False


def test_the_cloud_metadata_address_is_refused() -> None:
    assert is_public_url("http://169.254.169.254/latest/meta-data/", resolver=PUBLIC) is False


def test_metadata_hostnames_are_refused() -> None:
    assert is_public_url("http://metadata.google.internal/", resolver=PUBLIC) is False


def test_loopback_is_refused() -> None:
    assert is_public_url("http://127.0.0.1:8000/", resolver=LOOPBACK) is False


def test_private_ranges_are_refused() -> None:
    assert is_public_url("http://10.0.0.5/", resolver=PRIVATE) is False
    assert is_public_url("http://192.168.1.10/", resolver=PUBLIC) is False


def test_a_public_address_is_allowed() -> None:
    assert is_public_url("https://shop.example.com/products/blue-shirt", resolver=PUBLIC) is True


def test_a_name_that_resolves_privately_is_refused() -> None:
    assert is_public_url("https://internal.example.com/", resolver=LOOPBACK) is False


def test_a_name_that_cannot_be_resolved_is_refused() -> None:
    def broken(host: str, port: object) -> list[tuple]:
        raise socket.gaierror("no such host")

    assert is_public_url("https://nowhere.example.com/", resolver=broken) is False


def test_same_site_compares_the_host() -> None:
    assert same_site("https://shop.example.com/a", "https://shop.example.com/b") is True
    assert same_site("https://shop.example.com/a", "https://other.example.com/b") is False


def test_normalize_url_rejects_nothing_on_its_own() -> None:
    # normalize_url is purely syntactic; the policy lives in is_public_url.
    assert normalize_url("http://127.0.0.1/x") == "http://127.0.0.1/x"


def test_url_not_allowed_is_a_value_error() -> None:
    assert issubclass(UrlNotAllowed, ValueError)
