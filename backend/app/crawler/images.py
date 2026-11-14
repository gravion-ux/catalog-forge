"""Downloading and storing the images of a crawled product.

Images are stored by the hash of their content, so the same picture is only
ever kept once no matter how many products use it.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from urllib.parse import urlsplit

CONTENT_TYPE_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/pjpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/avif": ".avif",
    "image/svg+xml": ".svg",
}

DEFAULT_EXTENSION = ".bin"


def extension_for(url: str, content_type: str) -> str:
    """The file extension an image should be stored under."""
    mime = (content_type or "").split(";")[0].strip().lower()
    if mime in CONTENT_TYPE_EXTENSIONS:
        return CONTENT_TYPE_EXTENSIONS[mime]

    try:
        path = urlsplit(url).path
    except ValueError:
        path = ""
    name = path.rsplit("/", 1)[-1].lower()
    if "." in name:
        suffix = name.rsplit(".", 1)[-1]
        if suffix.isalnum() and 1 <= len(suffix) <= 5:
            return f".{suffix}"
    return DEFAULT_EXTENSION


async def store_image(
    fetcher: object,
    url: str,
    media_dir: Path | str,
) -> tuple[str, str] | None:
    """Download an image and keep it under the media folder.

    Returns the path of the image relative to the data folder and the SHA-256
    of its content, or ``None`` when the image could not be downloaded.
    """
    content, content_type = await fetcher.get_bytes(url)  # type: ignore[attr-defined]
    if not content:
        return None

    digest = hashlib.sha256(content).hexdigest()
    extension = extension_for(url, content_type)

    root = Path(media_dir)
    target = root / digest[:2] / f"{digest}{extension}"
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)

    relative = target.relative_to(root.parent).as_posix()
    return relative, digest
