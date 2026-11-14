"""Runtime settings, read from the environment.

Every setting has a safe default so the application runs with no
configuration at all. Values are resolved once at start-up and passed
around as a frozen dataclass.
"""

from __future__ import annotations

import os
import secrets
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = BASE_DIR / "data"
SECRET_FILE_NAME = ".secret_key"

DEFAULT_USER_AGENT = (
    "CatalogForge/1.0 (+https://github.com/gravion-ux/catalog-forge)"
)


def _get_float(environ: Mapping[str, str], key: str, default: float) -> float:
    raw = environ.get(key)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _get_int(environ: Mapping[str, str], key: str, default: int) -> int:
    raw = environ.get(key)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _get_bool(environ: Mapping[str, str], key: str, default: bool) -> bool:
    raw = environ.get(key)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _load_or_create_secret(environ: Mapping[str, str], data_dir: Path) -> str:
    explicit = environ.get("CATALOG_FORGE_SECRET")
    if explicit and explicit.strip():
        return explicit.strip()

    data_dir.mkdir(parents=True, exist_ok=True)
    secret_file = data_dir / SECRET_FILE_NAME
    if secret_file.exists():
        stored = secret_file.read_text(encoding="utf-8").strip()
        if stored:
            return stored

    generated = secrets.token_urlsafe(48)
    secret_file.write_text(generated, encoding="utf-8")
    return generated


@dataclass(frozen=True)
class Settings:
    """Everything the application needs to know about its environment."""

    data_dir: Path
    database_path: Path
    media_dir: Path
    secret_key: str
    admin_username: str
    admin_password: str
    crawler_user_agent: str
    crawler_delay_seconds: float
    crawler_max_concurrency: int
    crawler_max_pages: int
    crawler_timeout_seconds: float
    allow_private_targets: bool
    session_max_age_seconds: int
    login_rate_limit_attempts: int
    login_rate_limit_window_seconds: int
    store_currency: str


def load_settings(environ: Mapping[str, str] | None = None) -> Settings:
    """Build the settings from the environment.

    Passing an explicit mapping replaces the process environment entirely,
    which is what the tests use to get an isolated configuration.
    """
    env: Mapping[str, str] = dict(os.environ if environ is None else environ)

    data_dir = Path(env.get("CATALOG_FORGE_DATA") or DEFAULT_DATA_DIR).expanduser()
    media_dir = Path(
        env.get("CATALOG_FORGE_MEDIA_DIR") or (data_dir / "media")
    ).expanduser()

    return Settings(
        data_dir=data_dir,
        database_path=Path(
            env.get("CATALOG_FORGE_DATABASE") or (data_dir / "catalog.db")
        ).expanduser(),
        media_dir=media_dir,
        secret_key=_load_or_create_secret(env, data_dir),
        admin_username=env.get("CATALOG_FORGE_ADMIN_USERNAME") or "admin",
        admin_password=env.get("CATALOG_FORGE_ADMIN_PASSWORD") or "",
        crawler_user_agent=env.get("CATALOG_FORGE_USER_AGENT") or DEFAULT_USER_AGENT,
        crawler_delay_seconds=_get_float(
            env, "CATALOG_FORGE_CRAWLER_DELAY_SECONDS", 1.0
        ),
        crawler_max_concurrency=_get_int(
            env, "CATALOG_FORGE_CRAWLER_MAX_CONCURRENCY", 4
        ),
        crawler_max_pages=_get_int(env, "CATALOG_FORGE_CRAWLER_MAX_PAGES", 500),
        crawler_timeout_seconds=_get_float(
            env, "CATALOG_FORGE_CRAWLER_TIMEOUT_SECONDS", 20.0
        ),
        allow_private_targets=_get_bool(env, "CATALOG_FORGE_ALLOW_PRIVATE", False),
        session_max_age_seconds=_get_int(
            env, "CATALOG_FORGE_SESSION_MAX_AGE_SECONDS", 8 * 3600
        ),
        login_rate_limit_attempts=_get_int(
            env, "CATALOG_FORGE_LOGIN_RATE_LIMIT_ATTEMPTS", 5
        ),
        login_rate_limit_window_seconds=_get_int(
            env, "CATALOG_FORGE_LOGIN_RATE_LIMIT_WINDOW_SECONDS", 300
        ),
        store_currency=env.get("CATALOG_FORGE_STORE_CURRENCY") or "USD",
    )
