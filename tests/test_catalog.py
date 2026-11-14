from __future__ import annotations

import sqlite3

from app.catalog.categories import ensure_category, list_categories
from app.catalog.images import images_for
from app.catalog.products import (
    get_product,
    get_product_by_slug,
    list_products,
)
from conftest import seed_category, seed_product


def test_list_products_returns_the_active_products(conn: sqlite3.Connection) -> None:
    seed_product(conn, slug="blue-shirt", title="Blue Shirt")
    seed_product(conn, slug="red-hat", title="Red Hat", status="hidden")

    items, total = list_products(conn)

    assert total == 1
    assert [item.slug for item in items] == ["blue-shirt"]


def test_list_products_can_include_hidden_products(conn: sqlite3.Connection) -> None:
    seed_product(conn, slug="blue-shirt")
    seed_product(conn, slug="red-hat", status="hidden")

    items, total = list_products(conn, include_hidden=True)

    assert total == 2
    assert {item.slug for item in items} == {"blue-shirt", "red-hat"}


def test_list_products_filters_by_search_text(conn: sqlite3.Connection) -> None:
    seed_product(conn, slug="blue-shirt", title="Blue Shirt")
    seed_product(conn, slug="red-hat", title="Red Hat")

    items, total = list_products(conn, search="shirt")

    assert total == 1
    assert items[0].slug == "blue-shirt"


def test_list_products_filters_by_category(conn: sqlite3.Connection) -> None:
    shirts = seed_category(conn, "Shirts")
    seed_product(conn, slug="blue-shirt", title="Blue Shirt")
    seed_product(conn, slug="red-hat", title="Red Hat")
    conn.execute(
        "INSERT INTO product_categories (product_id, category_id) VALUES (?, ?)",
        (1, shirts),
    )
    conn.commit()

    items, total = list_products(conn, category_slug="shirts")

    assert total == 1
    assert items[0].slug == "blue-shirt"


def test_list_products_paginates(conn: sqlite3.Connection) -> None:
    for index in range(5):
        seed_product(conn, slug=f"product-{index}", title=f"Product {index}")

    items, total = list_products(conn, page=2, page_size=2)

    assert total == 5
    assert len(items) == 2
    assert items[0].slug == "product-2"


def test_get_product_by_slug(conn: sqlite3.Connection) -> None:
    seed_product(conn, slug="blue-shirt")

    product = get_product_by_slug(conn, "blue-shirt")

    assert product is not None
    assert product.title == "Blue Shirt"
    assert product.price == "19.90"


def test_get_product_by_slug_returns_none_when_missing(conn: sqlite3.Connection) -> None:
    assert get_product_by_slug(conn, "nope") is None


def test_get_product_by_id(conn: sqlite3.Connection) -> None:
    product_id = seed_product(conn, slug="blue-shirt")

    product = get_product(conn, product_id)

    assert product is not None
    assert product.id == product_id


def test_ensure_category_is_idempotent(conn: sqlite3.Connection) -> None:
    first = ensure_category(conn, "Shirts")
    second = ensure_category(conn, "Shirts")

    assert first.id == second.id
    assert len(list_categories(conn)) == 1


def test_list_categories_counts_products(conn: sqlite3.Connection) -> None:
    shirts = seed_category(conn, "Shirts")
    seed_product(conn, slug="blue-shirt")
    conn.execute(
        "INSERT INTO product_categories (product_id, category_id) VALUES (?, ?)",
        (1, shirts),
    )
    conn.commit()

    categories = list_categories(conn)

    assert len(categories) == 1
    assert categories[0].name == "Shirts"
    assert categories[0].product_count == 1


def test_images_for_returns_the_product_images(conn: sqlite3.Connection) -> None:
    product_id = seed_product(conn)
    conn.execute(
        "INSERT INTO images (product_id, local_path, position) VALUES (?, ?, ?)",
        (product_id, "media/ab/cd.jpg", 0),
    )
    conn.commit()

    images = images_for(conn, product_id)

    assert len(images) == 1
    assert images[0].local_path == "media/ab/cd.jpg"
