from __future__ import annotations

import sqlite3
from typing import Any

from app.catalog.products import get_product_by_source_url
from app.crawler.importer import import_product, set_price

SOURCE_URL = "https://shop.example.com/products/blue-shirt"


def make_product(**overrides: Any) -> dict[str, Any]:
    product: dict[str, Any] = {
        "title": "Blue Shirt",
        "description": "A comfortable blue shirt.",
        "price": "19.90",
        "compare_at_price": None,
        "currency": "USD",
        "stock": 10,
        "vendor": "Northwind",
        "sku": "SHIRT-BLUE",
        "images": [],
        "variants": [],
        "categories": [],
        "availability": "https://schema.org/InStock",
        "platform": "generic",
        "source_url": SOURCE_URL,
    }
    product.update(overrides)
    return product


def history_rows(conn: sqlite3.Connection, product_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM price_history WHERE product_id = ? ORDER BY id",
        (product_id,),
    ).fetchall()


def test_import_creates_a_product(conn: sqlite3.Connection) -> None:
    result = import_product(conn, make_product(), source_platform="generic")

    assert result.created is True
    assert result.price_kept is False
    assert result.source_price_changed is False

    row = get_product_by_source_url(conn, SOURCE_URL)
    assert row is not None
    assert row.title == "Blue Shirt"
    assert row.price == "19.90"
    assert row.source_price == "19.90"
    assert row.price_manually_edited is False


def test_importing_the_same_source_url_twice_updates(conn: sqlite3.Connection) -> None:
    first = import_product(conn, make_product(), source_platform="generic")
    second = import_product(
        conn,
        make_product(title="Blue Shirt v2", price="21.00"),
        source_platform="generic",
    )

    assert second.created is False
    assert second.product_id == first.product_id
    assert conn.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 1

    row = get_product_by_source_url(conn, SOURCE_URL)
    assert row is not None
    assert row.title == "Blue Shirt v2"
    assert row.price == "21.00"
    assert row.source_price == "21.00"


def test_two_products_with_the_same_title_get_different_slugs(
    conn: sqlite3.Connection,
) -> None:
    first = import_product(conn, make_product(), source_platform="generic")
    second = import_product(
        conn,
        make_product(source_url="https://shop.example.com/products/blue-shirt-2"),
        source_platform="generic",
    )

    assert first.product_id != second.product_id
    slugs = [row[0] for row in conn.execute("SELECT slug FROM products ORDER BY id")]
    assert len(set(slugs)) == 2


def test_a_hand_edited_price_survives_a_recrawl(conn: sqlite3.Connection) -> None:
    first = import_product(conn, make_product(), source_platform="generic")
    change = set_price(conn, first.product_id, "25.00")

    assert change.old_price == "19.90"
    assert change.new_price == "25.00"

    result = import_product(
        conn, make_product(price="12.00"), source_platform="generic"
    )

    assert result.price_kept is True
    assert result.source_price_changed is True

    row = get_product_by_source_url(conn, SOURCE_URL)
    assert row is not None
    assert row.price == "25.00"
    assert row.source_price == "12.00"
    assert row.price_manually_edited is True


def test_set_price_writes_a_price_history_row(conn: sqlite3.Connection) -> None:
    first = import_product(conn, make_product(), source_platform="generic")

    set_price(conn, first.product_id, "25.00")

    rows = history_rows(conn, first.product_id)
    assert len(rows) == 1
    assert rows[0]["old_price"] == "19.90"
    assert rows[0]["new_price"] == "25.00"
    assert rows[0]["source"] == "admin"


def test_a_crawl_price_change_is_written_to_price_history(
    conn: sqlite3.Connection,
) -> None:
    first = import_product(conn, make_product(), source_platform="generic")

    import_product(conn, make_product(price="21.00"), source_platform="generic")

    rows = history_rows(conn, first.product_id)
    assert len(rows) == 1
    assert rows[0]["old_price"] == "19.90"
    assert rows[0]["new_price"] == "21.00"
    assert rows[0]["source"] == "crawl"


def test_import_stores_the_images_of_the_product(conn: sqlite3.Connection) -> None:
    product = make_product(
        images=[
            {
                "url": "https://cdn.example.com/blue.png",
                "local_path": "media/ab/abcdef.png",
                "content_hash": "abcdef",
            }
        ]
    )

    result = import_product(conn, product, source_platform="generic")

    rows = conn.execute(
        "SELECT * FROM images WHERE product_id = ?", (result.product_id,)
    ).fetchall()
    assert len(rows) == 1
    assert rows[0]["remote_url"] == "https://cdn.example.com/blue.png"
    assert rows[0]["local_path"] == "media/ab/abcdef.png"
    assert rows[0]["content_hash"] == "abcdef"
