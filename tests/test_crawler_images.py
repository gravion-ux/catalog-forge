from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path

from app.crawler.images import store_image

PNG = b"\x89PNG\r\n\x1a\n" + b"catalog-forge-image-bytes"


class FakeFetcher:
    def __init__(self, pages: dict[str, bytes], content_type: str = "image/png") -> None:
        self.pages = pages
        self.content_type = content_type
        self.requested: list[str] = []

    async def get_bytes(self, url: str) -> tuple[bytes, str]:
        self.requested.append(url)
        return self.pages.get(url, b""), self.content_type


def test_stores_an_image_under_the_media_folder(tmp_path: Path) -> None:
    media_dir = tmp_path / "data" / "media"
    fetcher = FakeFetcher({"https://cdn.example.com/blue.png": PNG})

    result = asyncio.run(
        store_image(fetcher, "https://cdn.example.com/blue.png", media_dir)
    )

    assert result is not None
    relative_path, digest = result
    assert digest == hashlib.sha256(PNG).hexdigest()
    assert relative_path == f"media/{digest[:2]}/{digest}.png"
    assert (media_dir / digest[:2] / f"{digest}.png").read_bytes() == PNG


def test_the_same_bytes_are_stored_once(tmp_path: Path) -> None:
    media_dir = tmp_path / "data" / "media"
    fetcher = FakeFetcher({"https://cdn.example.com/blue.png": PNG})

    first = asyncio.run(
        store_image(fetcher, "https://cdn.example.com/blue.png", media_dir)
    )
    second = asyncio.run(
        store_image(fetcher, "https://cdn.example.com/blue.png", media_dir)
    )

    assert first == second
    stored = [path for path in media_dir.rglob("*") if path.is_file()]
    assert len(stored) == 1


def test_a_missing_image_is_not_stored(tmp_path: Path) -> None:
    media_dir = tmp_path / "data" / "media"
    fetcher = FakeFetcher({})

    result = asyncio.run(
        store_image(fetcher, "https://cdn.example.com/gone.png", media_dir)
    )

    assert result is None
    assert not [path for path in media_dir.rglob("*") if path.is_file()]
