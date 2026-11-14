from __future__ import annotations

from pathlib import Path

from app.config import load_settings


def test_defaults_are_used_when_nothing_is_set(tmp_path: Path) -> None:
    settings = load_settings({"CATALOG_FORGE_DATA": str(tmp_path / "data")})

    assert settings.data_dir == tmp_path / "data"
    assert settings.database_path == tmp_path / "data" / "catalog.db"
    assert settings.media_dir == tmp_path / "data" / "media"
    assert settings.admin_username == "admin"
    assert settings.crawler_delay_seconds == 1.0
    assert settings.crawler_max_concurrency == 4
    assert settings.crawler_max_pages == 500
    assert settings.crawler_timeout_seconds == 20.0
    assert settings.allow_private_targets is False
    assert settings.store_currency == "USD"


def test_environment_overrides_defaults(tmp_path: Path) -> None:
    settings = load_settings(
        {
            "CATALOG_FORGE_DATA": str(tmp_path),
            "CATALOG_FORGE_ADMIN_USERNAME": "owner",
            "CATALOG_FORGE_CRAWLER_DELAY_SECONDS": "0.25",
            "CATALOG_FORGE_CRAWLER_MAX_CONCURRENCY": "2",
            "CATALOG_FORGE_CRAWLER_MAX_PAGES": "10",
            "CATALOG_FORGE_ALLOW_PRIVATE": "1",
            "CATALOG_FORGE_STORE_CURRENCY": "EUR",
        }
    )

    assert settings.admin_username == "owner"
    assert settings.crawler_delay_seconds == 0.25
    assert settings.crawler_max_concurrency == 2
    assert settings.crawler_max_pages == 10
    assert settings.allow_private_targets is True
    assert settings.store_currency == "EUR"


def test_secret_is_generated_once_and_reused(tmp_path: Path) -> None:
    data = tmp_path / "data"

    first = load_settings({"CATALOG_FORGE_DATA": str(data)})
    second = load_settings({"CATALOG_FORGE_DATA": str(data)})

    assert first.secret_key
    assert len(first.secret_key) >= 32
    assert first.secret_key == second.secret_key


def test_explicit_secret_wins_over_the_stored_file(tmp_path: Path) -> None:
    settings = load_settings(
        {
            "CATALOG_FORGE_DATA": str(tmp_path / "data"),
            "CATALOG_FORGE_SECRET": "explicit-secret",
        }
    )

    assert settings.secret_key == "explicit-secret"
