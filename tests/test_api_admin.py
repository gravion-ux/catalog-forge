from __future__ import annotations

import sqlite3
import time

from fastapi.testclient import TestClient

from conftest import seed_category, seed_product

CSRF_HEADER = {"X-CSRF-Token": ""}


def login(client: TestClient, password: str = "admin-password") -> str:
    """Log in and return the CSRF token of the session."""
    response = client.post(
        "/api/admin/login",
        json={"username": "admin", "password": password},
    )
    assert response.status_code == 200, response.text
    return str(response.json()["csrf_token"])


def csrf(token: str) -> dict[str, str]:
    return {"X-CSRF-Token": token}


def test_an_unauthenticated_admin_request_is_a_401(client: TestClient) -> None:
    response = client.get("/api/admin/products")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_the_session_endpoint_needs_a_session(client: TestClient) -> None:
    response = client.get("/api/admin/session")

    assert response.status_code == 401


def test_a_login_with_the_wrong_password_is_a_401(client: TestClient) -> None:
    response = client.post(
        "/api/admin/login",
        json={"username": "admin", "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_the_sixth_login_attempt_is_rate_limited(client: TestClient) -> None:
    for _ in range(5):
        response = client.post(
            "/api/admin/login",
            json={"username": "admin", "password": "wrong-password"},
        )
        assert response.status_code == 401

    blocked = client.post(
        "/api/admin/login",
        json={"username": "admin", "password": "wrong-password"},
    )

    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "rate_limited"


def test_a_login_sets_a_session_cookie(client: TestClient) -> None:
    response = client.post(
        "/api/admin/login",
        json={"username": "admin", "password": "admin-password"},
    )

    assert response.status_code == 200
    assert response.json()["username"] == "admin"
    assert response.json()["csrf_token"]

    cookie = response.headers.get("set-cookie", "")
    assert "cf_admin=" in cookie
    assert "HttpOnly" in cookie
    assert "samesite=lax" in cookie.lower()


def test_the_session_endpoint_reports_the_user(client: TestClient) -> None:
    token = login(client)

    response = client.get("/api/admin/session")

    assert response.status_code == 200
    assert response.json()["username"] == "admin"
    assert response.json()["csrf_token"] == token


def test_logout_clears_the_session(client: TestClient) -> None:
    token = login(client)

    response = client.post("/api/admin/logout", headers=csrf(token))
    assert response.status_code == 200

    assert client.get("/api/admin/products").status_code == 401


def test_a_write_without_the_csrf_header_is_a_403(
    conn: sqlite3.Connection, client: TestClient
) -> None:
    product_id = seed_product(conn, slug="blue-shirt", price="19.90")
    login(client)

    response = client.patch(
        f"/api/admin/products/{product_id}/price", json={"price": "25.00"}
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


def test_editing_a_price_updates_the_product_and_writes_history(
    conn: sqlite3.Connection, client: TestClient
) -> None:
    product_id = seed_product(conn, slug="blue-shirt", price="19.90")
    token = login(client)

    response = client.patch(
        f"/api/admin/products/{product_id}/price",
        json={"price": "25.00"},
        headers=csrf(token),
    )

    assert response.status_code == 200
    assert response.json()["price"] == "25.00"

    rows = conn.execute(
        "SELECT * FROM price_history WHERE product_id = ?", (product_id,)
    ).fetchall()
    assert len(rows) == 1
    assert rows[0]["old_price"] == "19.90"
    assert rows[0]["new_price"] == "25.00"
    assert rows[0]["source"] == "admin"

    row = conn.execute(
        "SELECT price, price_manually_edited FROM products WHERE id = ?", (product_id,)
    ).fetchone()
    assert row["price"] == "25.00"
    assert row["price_manually_edited"] == 1


def test_a_markup_bulk_update_multiplies_the_prices(
    conn: sqlite3.Connection, client: TestClient
) -> None:
    first = seed_product(conn, slug="blue-shirt", title="Blue Shirt", price="19.90")
    second = seed_product(conn, slug="red-hat", title="Red Hat", price="5.00")
    token = login(client)

    response = client.post(
        "/api/admin/products/bulk-price",
        json={"mode": "markup", "value": "10", "product_ids": [first, second]},
        headers=csrf(token),
    )

    assert response.status_code == 200
    assert response.json()["updated"] == 2

    prices = {
        row["id"]: row["price"]
        for row in conn.execute("SELECT id, price FROM products").fetchall()
    }
    assert prices[first] == "21.89"
    assert prices[second] == "5.50"


def test_a_bulk_update_can_target_a_category(
    conn: sqlite3.Connection, client: TestClient
) -> None:
    category_id = seed_category(conn, "Shirts")
    inside = seed_product(conn, slug="blue-shirt", price="10.00")
    outside = seed_product(conn, slug="red-hat", price="10.00")
    conn.execute(
        "INSERT INTO product_categories (product_id, category_id) VALUES (?, ?)",
        (inside, category_id),
    )
    conn.commit()
    token = login(client)

    response = client.post(
        "/api/admin/products/bulk-price",
        json={"mode": "set", "value": "3.00", "category_id": category_id},
        headers=csrf(token),
    )

    assert response.status_code == 200
    assert response.json()["updated"] == 1

    prices = {
        row["id"]: row["price"]
        for row in conn.execute("SELECT id, price FROM products").fetchall()
    }
    assert prices[inside] == "3.00"
    assert prices[outside] == "10.00"


def test_the_product_listing_shows_the_source_price(
    conn: sqlite3.Connection, client: TestClient
) -> None:
    seed_product(
        conn,
        slug="blue-shirt",
        title="Blue Shirt",
        price="25.00",
        source_price="19.90",
        price_manually_edited=1,
    )
    token = login(client)

    response = client.get("/api/admin/products", headers=csrf(token))

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["price"] == "25.00"
    assert item["source_price"] == "19.90"
    assert item["source_price_changed"] is True
    assert item["price_manually_edited"] is True


def test_a_product_can_be_edited(
    conn: sqlite3.Connection, client: TestClient
) -> None:
    product_id = seed_product(conn, slug="blue-shirt", title="Blue Shirt")
    token = login(client)

    response = client.patch(
        f"/api/admin/products/{product_id}",
        json={"title": "Blue Shirt v2", "stock": 3, "status": "hidden"},
        headers=csrf(token),
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Blue Shirt v2"
    assert response.json()["stock"] == 3
    assert response.json()["status"] == "hidden"


def test_a_product_can_be_hidden_from_the_storefront(
    conn: sqlite3.Connection, client: TestClient
) -> None:
    product_id = seed_product(conn, slug="blue-shirt", title="Blue Shirt")
    token = login(client)

    client.patch(
        f"/api/admin/products/{product_id}",
        json={"status": "hidden"},
        headers=csrf(token),
    )

    listing = client.get("/api/products").json()
    assert listing["total"] == 0


def test_categories_can_be_created_and_renamed(
    conn: sqlite3.Connection, client: TestClient
) -> None:
    token = login(client)

    created = client.post(
        "/api/admin/categories", json={"name": "Shirts"}, headers=csrf(token)
    )
    assert created.status_code == 201
    category_id = created.json()["id"]
    assert created.json()["slug"] == "shirts"

    renamed = client.patch(
        f"/api/admin/categories/{category_id}",
        json={"name": "T-Shirts"},
        headers=csrf(token),
    )
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "T-Shirts"


def test_orders_can_be_listed(conn: sqlite3.Connection, client: TestClient) -> None:
    conn.execute(
        "INSERT INTO orders (code, email, name, address, subtotal, shipping,"
        " discount, total, currency, status, created_at)"
        " VALUES ('CF-TEST', 'buyer@example.com', 'Buyer', '{}', '19.90',"
        " '0.00', '0.00', '19.90', 'USD', 'placed', '2026-01-01T00:00:00')"
    )
    conn.commit()
    token = login(client)

    response = client.get("/api/admin/orders", headers=csrf(token))

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["code"] == "CF-TEST"


def test_a_crawl_can_be_started_and_read_back(client: TestClient) -> None:
    token = login(client)

    started = client.post(
        "/api/admin/crawls",
        json={"url": "http://127.0.0.1/shop"},
        headers=csrf(token),
    )

    assert started.status_code == 202
    run_id = started.json()["id"]

    deadline = time.time() + 10
    payload: dict[str, object] = {}
    while time.time() < deadline:
        response = client.get(f"/api/admin/crawls/{run_id}")
        assert response.status_code == 200
        payload = dict(response.json())
        if payload["status"] not in {"pending", "running"}:
            break
        time.sleep(0.05)

    assert payload["status"] in {"completed", "failed"}
    assert payload["url"] == "http://127.0.0.1/shop"


def test_crawl_runs_can_be_listed(client: TestClient) -> None:
    token = login(client)

    client.post(
        "/api/admin/crawls",
        json={"url": "http://127.0.0.1/shop"},
        headers=csrf(token),
    )

    response = client.get("/api/admin/crawls", headers=csrf(token))

    assert response.status_code == 200
    assert response.json()["total"] >= 1


def test_an_unknown_crawl_run_is_a_404(client: TestClient) -> None:
    token = login(client)

    response = client.get("/api/admin/crawls/9999", headers=csrf(token))

    assert response.status_code == 404
