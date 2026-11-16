# API Reference

## Public API (Storefront)

### GET /api/health

Returns the health of the service.

```json
{
  "status": "ok",
  "version": "1.0.0"
}
```

### GET /api/categories

Lists all product categories.

```json
{
  "items": [
    { "id": 1, "slug": "clothing", "name": "Clothing", "product_count": 12 }
  ]
}
```

### GET /api/products

Paginated product listing.

**Query parameters:**

| Parameter | Type   | Description                        |
|-----------|--------|------------------------------------|
| category  | string | Filter to `slug` of a category     |
| q         | string | Full-text search in title/sku/vendor |
| page      | int    | Page number (default: 1)           |
| page_size | int    | Items per page (default: 24)       |

```json
{
  "items": [
    {
      "id": 1,
      "slug": "blue-shirt",
      "title": "Blue Shirt",
      "price": "29.00",
      "compare_at_price": null,
      "currency": "USD",
      "stock": 10,
      "vendor": "My Store",
      "image": "/media/ab/cdef1234.../blue-shirt.svg"
    }
  ],
  "total": 12,
  "page": 1,
  "page_size": 24,
  "pages": 1
}
```

### GET /api/products/{slug}

Product detail.

```json
{
  "id": 1,
  "slug": "blue-shirt",
  "title": "Blue Shirt",
  "price": "29.00",
  "compare_at_price": null,
  "currency": "USD",
  "stock": 10,
  "vendor": "My Store",
  "image": "/media/ab/cdef1234.../blue-shirt.svg",
  "description": "A comfortable cotton shirt.",
  "sku": "SHIRT-BLUE",
  "source_url": "https://example-store.com/products/blue-shirt",
  "source_platform": "shopify",
  "source_price": "29.00",
  "source_fetched_at": "2026-11-16T12:00:00Z",
  "price_manually_edited": false,
  "attributes": {},
  "images": [
    { "id": 1, "local_path": "/media/ab/...", "remote_url": null, "alt": null, "position": 0 }
  ],
  "categories": [
    { "id": 1, "slug": "clothing", "name": "Clothing", "product_count": 12 }
  ]
}
```

### POST /api/orders/quote

Get a price estimate for items in the cart.

**Body:**

```json
{
  "items": [
    { "product_id": 1, "quantity": 2 }
  ]
}
```

**Response:**

```json
{
  "lines": [
    {
      "product_id": 1,
      "title": "Blue Shirt",
      "unit_price": "29.00",
      "quantity": 2,
      "line_total": "58.00",
      "currency": "USD"
    }
  ],
  "subtotal": "58.00",
  "total": "58.00",
  "currency": "USD"
}
```

### POST /api/checkout

Place an order. Returns order code on success.

**Body:**

```json
{
  "email": "buyer@example.com",
  "name": "Buyer Name",
  "address": {
    "line1": "123 Main St",
    "city": "Anytown",
    "postcode": "12345",
    "country": "US"
  },
  "items": [
    { "product_id": 1, "quantity": 2 }
  ]
}
```

**Response (201):**

```json
{
  "code": "CF-AB12CD34EF",
  "email": "buyer@example.com",
  "name": "Buyer Name",
  "address": { "line1": "...", "city": "...", ... },
  "subtotal": "58.00",
  "shipping": "0.00",
  "discount": "0.00",
  "total": "58.00",
  "currency": "USD",
  "status": "placed",
  "created_at": "2026-11-16T14:30:00Z",
  "items": [
    {
      "product_id": 1,
      "title": "Blue Shirt",
      "unit_price": "29.00",
      "quantity": 2
    }
  ]
}
```

### GET /api/orders/{code}

Look up an order by its code.

```json
{
  "code": "CF-AB12CD34EF",
  "email": "buyer@example.com",
  "name": "Buyer Name",
  "address": { ... },
  "subtotal": "58.00",
  "shipping": "0.00",
  "discount": "0.00",
  "total": "58.00",
  "currency": "USD",
  "status": "placed",
  "created_at": "2026-11-16T14:30:00Z",
  "items": [ ... ]
}
```

---

## Admin API

All admin endpoints require authentication via a session cookie (`cf_admin`)
and a CSRF token in the `X-CSRF-Token` header.

### POST /api/admin/login

Authenticate and start a session.

**Body:**

```json
{
  "username": "admin",
  "password": "your-password"
}
```

**Response:**

```json
{
  "username": "admin",
  "csrf_token": "token..."
}
```

The server also sets an `Set-Cookie` header with a `HttpOnly; SameSite=Lax`
cookie.

### GET /api/admin/session

Verify the current session.

```json
{
  "username": "admin",
  "csrf_token": "token..."
}
```

### POST /api/admin/logout

End the session.

### GET /api/admin/products

List all products (including hidden/draft ones).

### GET /api/admin/products/{id}

Get a product's full detail.

### PATCH /api/admin/products/{id}

Edit a product's details.

### PATCH /api/admin/products/{id}/price

Set the price of one product.

```json
{ "price": "19.99", "compare_at_price": "29.99" }
```

### POST /api/admin/products/bulk-price

Change prices of many products.

```json
{
  "mode": "markup",
  "value": "10",
  "unit": "percent",
  "product_ids": [1, 2, 3]
}
```

Modes:

- `markup` — increase/decrease by a percentage
- `delta` — add/subtract an amount
- `set` — set to an absolute price

### GET /api/admin/categories

List all categories.

### POST /api/admin/categories

Create a category.

```json
{ "name": "New Category", "parent_id": null }
```

### GET /api/admin/orders

List all orders.

### POST /api/admin/crawls

Start a new crawl.

```json
{ "url": "https://example-store.com" }
```

Returns immediately with a `202 Accepted` and a crawl run object:

```json
{
  "id": 1,
  "url": "https://example-store.com",
  "platform": null,
  "status": "pending",
  "products_found": 0,
  "products_imported": 0,
  "pages_crawled": 0,
  "error": null,
  "started_at": null,
  "finished_at": null
}
```

### GET /api/admin/crawls

List recent crawl runs.

### GET /api/admin/crawls/{id}

Get the progress of one crawl run.