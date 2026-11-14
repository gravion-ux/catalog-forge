from __future__ import annotations

from fastapi.testclient import TestClient

from app.db import connect
from conftest import seed_product


def cart_item(product_id: int, quantity: int = 1) -> dict[str, int]:
    return {"product_id": product_id, "quantity": quantity}


def test_quote_totals_the_cart(client: TestClient, settings) -> None:
    with connect(settings.database_path) as connection:
        shirt = seed_product(connection, slug="blue-shirt", price="19.90")
        hat = seed_product(connection, slug="red-hat", price="5.00")

    response = client.post(
        "/api/orders/quote",
        json={"items": [cart_item(shirt, 2), cart_item(hat)]},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["subtotal"] == "44.80"
    assert payload["total"] == "44.80"
    assert len(payload["lines"]) == 2


def test_quote_rejects_an_empty_cart(client: TestClient) -> None:
    response = client.post("/api/orders/quote", json={"items": []})

    assert response.status_code == 422


def test_checkout_creates_an_order(client: TestClient, settings) -> None:
    with connect(settings.database_path) as connection:
        shirt = seed_product(connection, slug="blue-shirt", price="19.90")

    response = client.post(
        "/api/checkout",
        json={
            "email": "buyer@example.com",
            "name": "Ada Buyer",
            "address": {"line1": "1 Example Street", "city": "Springfield"},
            "items": [cart_item(shirt, 2)],
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["code"].startswith("CF-")
    assert payload["total"] == "39.80"
    assert payload["items"][0]["title"] == "Blue Shirt"


def test_checkout_uses_the_stored_price_not_a_client_price(client: TestClient, settings) -> None:
    with connect(settings.database_path) as connection:
        shirt = seed_product(connection, slug="blue-shirt", price="19.90")

    response = client.post(
        "/api/checkout",
        json={
            "email": "buyer@example.com",
            "name": "Ada Buyer",
            "items": [{"product_id": shirt, "quantity": 1, "price": "0.01"}],
        },
    )

    assert response.status_code == 201
    assert response.json()["total"] == "19.90"


def test_checkout_rejects_an_empty_cart(client: TestClient) -> None:
    response = client.post(
        "/api/checkout",
        json={"email": "buyer@example.com", "name": "Ada Buyer", "items": []},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"


def test_checkout_rejects_an_unknown_product(client: TestClient) -> None:
    response = client.post(
        "/api/checkout",
        json={
            "email": "buyer@example.com",
            "name": "Ada Buyer",
            "items": [cart_item(9999)],
        },
    )

    assert response.status_code == 422


def test_checkout_rejects_a_bad_quantity(client: TestClient, settings) -> None:
    with connect(settings.database_path) as connection:
        shirt = seed_product(connection, slug="blue-shirt")

    response = client.post(
        "/api/checkout",
        json={
            "email": "buyer@example.com",
            "name": "Ada Buyer",
            "items": [cart_item(shirt, 0)],
        },
    )

    assert response.status_code == 422


def test_checkout_requires_an_email(client: TestClient, settings) -> None:
    with connect(settings.database_path) as connection:
        shirt = seed_product(connection, slug="blue-shirt")

    response = client.post(
        "/api/checkout",
        json={"name": "Ada Buyer", "items": [cart_item(shirt)]},
    )

    assert response.status_code == 422


def test_order_lookup(client: TestClient, settings) -> None:
    with connect(settings.database_path) as connection:
        shirt = seed_product(connection, slug="blue-shirt", price="19.90")

    created = client.post(
        "/api/checkout",
        json={
            "email": "buyer@example.com",
            "name": "Ada Buyer",
            "items": [cart_item(shirt)],
        },
    )
    code = created.json()["code"]

    response = client.get(f"/api/orders/{code}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == code
    assert payload["email"] == "buyer@example.com"
    assert payload["items"][0]["unit_price"] == "19.90"


def test_unknown_order_is_a_404(client: TestClient) -> None:
    response = client.get("/api/orders/CF-NOPE")

    assert response.status_code == 404
