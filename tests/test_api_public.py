from __future__ import annotations

from fastapi.testclient import TestClient

from app.db import connect
from conftest import seed_category, seed_product


def test_health_endpoint(client: TestClient) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_listing_products(client: TestClient, settings) -> None:
    with connect(settings.database_path) as connection:
        seed_product(connection, slug="blue-shirt", title="Blue Shirt")
        seed_product(connection, slug="red-hat", title="Red Hat")

    response = client.get("/api/products")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2
    assert payload["items"][0]["title"] in {"Blue Shirt", "Red Hat"}


def test_hidden_products_are_not_public(client: TestClient, settings) -> None:
    with connect(settings.database_path) as connection:
        seed_product(connection, slug="red-hat", status="hidden")

    response = client.get("/api/products")

    assert response.json()["total"] == 0


def test_product_detail(client: TestClient, settings) -> None:
    with connect(settings.database_path) as connection:
        product_id = seed_product(connection, slug="blue-shirt", title="Blue Shirt")
        category_id = seed_category(connection, "Shirts")
        connection.execute(
            "INSERT INTO product_categories (product_id, category_id) VALUES (?, ?)",
            (product_id, category_id),
        )
        connection.execute(
            "INSERT INTO images (product_id, local_path, position) VALUES (?, ?, ?)",
            (product_id, "media/ab/cd.jpg", 0),
        )
        connection.commit()

    response = client.get("/api/products/blue-shirt")

    assert response.status_code == 200
    payload = response.json()
    assert payload["slug"] == "blue-shirt"
    assert payload["price"] == "19.90"
    assert payload["categories"][0]["name"] == "Shirts"
    assert payload["images"][0]["local_path"] == "media/ab/cd.jpg"


def test_unknown_product_is_a_404(client: TestClient) -> None:
    response = client.get("/api/products/does-not-exist")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_category_listing(client: TestClient, settings) -> None:
    with connect(settings.database_path) as connection:
        seed_category(connection, "Shirts")

    response = client.get("/api/categories")

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"][0]["name"] == "Shirts"


def test_search_filters_the_listing(client: TestClient, settings) -> None:
    with connect(settings.database_path) as connection:
        seed_product(connection, slug="blue-shirt", title="Blue Shirt")
        seed_product(connection, slug="red-hat", title="Red Hat")

    response = client.get("/api/products", params={"q": "shirt"})

    assert response.json()["total"] == 1
    assert response.json()["items"][0]["slug"] == "blue-shirt"
