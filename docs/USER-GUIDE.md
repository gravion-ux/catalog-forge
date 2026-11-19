# Catalog Forge User Guide

How to crawl a shop, run it as your own storefront, and edit what it found.

This guide assumes you have already installed the project. If you have not, see
the [README](../README.md) first.

---

## 1. Start the server

From the repository root:

```sh
# The admin password is required. Pick your own.
export CATALOG_FORGE_ADMIN_PASSWORD="your-password"

# Start the API and the storefront together.
python -m uvicorn app.main:app --app-dir backend
```

The `--app-dir backend` is what puts the `app` package on the import path. On
Windows PowerShell, set the password with `$env:CATALOG_FORGE_ADMIN_PASSWORD = "your-password"`
instead of `export`.

Open <http://localhost:8000>. That is the storefront. The admin panel is at
<http://localhost:8000/admin/login>.

> If you skip the frontend build, the server still starts but the root URL
> returns a JSON note saying the frontend has not been built yet. The API
> under `/api` works either way.

### Sign in

- **Username:** `admin`, unless you set `CATALOG_FORGE_ADMIN_USERNAME`.
- **Password:** whatever you set in `CATALOG_FORGE_ADMIN_PASSWORD`.

If the password is left empty, no account is created and you cannot sign in.
Five failed attempts inside five minutes lock the form for that window; the
session lasts eight hours.

---

## 2. Crawl a shop

Go to **Crawls** in the admin sidebar.

1. Type the address of the shop into **Address of the shop**, for example
   `https://example-store.com`.
2. Press **Start the crawl**.
3. The run appears in the table below and the panel above shows it live. While
   the run is going, the page refreshes every two seconds.

The panel shows the status, the platform that was detected, how many pages were
crawled, how many products were found, and how many were imported. If a run
fails, the reason is shown in red on the same panel.

### What the crawler does

| Step | What happens |
|------|--------------|
| robots.txt | Read first. Paths it disallows are never requested. A missing robots.txt allows everything. |
| Sitemaps | The sitemaps named by robots.txt are read; if robots.txt names none, `/sitemap.xml` is tried. A sitemap index is followed down to its children. |
| Product URLs | A URL is kept when one of its path segments is `product`, `products`, `item`, `items`, `p` or `shop`, and robots.txt allows it. Duplicates are dropped. |
| Pages | Each product page is fetched politely — one request per host at a time, with a delay between them. |
| Products | The title, description, price, compare-at price, currency, images, vendor, SKU, stock, variants and categories are read off the page. |
| Images | Each image is downloaded and stored under `data/media/`, keyed by the hash of its bytes. The same image is stored once, however many products use it. |
| Catalog | Each product is matched on its source URL. A product that is already in the catalog is updated rather than duplicated. |

### Which shops it understands

The extractor is chosen from the page itself:

- **Shopify** — detected from `cdn.shopify.com`. Reads the embedded product
  JSON and the variant list.
- **WooCommerce** — detected from the `woocommerce` body class. Reads the
  schema.org block and the embedded product-details JSON.
- **Generic** — anything else that publishes a schema.org `Product` in a
  JSON-LD block, including inside an `@graph`. Falls back to microdata
  (`itemprop="price"`) and then to OpenGraph (`og:price:amount`).

The **Platform** field on the run tells you which one was used. A page with no
recognisable product markup is skipped, not guessed at.

### What the crawler will not do

- It will not request a URL with credentials in it, or a scheme other than
  `http` and `https`.
- It will not touch a private, loopback, link-local or cloud-metadata address.
  `169.254.169.254` and the common metadata hostnames are refused by name as
  well. This is why a crawl of `http://127.0.0.1/` is refused.
- It will not break a CAPTCHA, a paywall or a login.
- It identifies itself honestly in its user agent.

`CATALOG_FORGE_ALLOW_PRIVATE` exists for testing against a local server. Leave
it off unless you understand what it turns off.

---

## 3. Edit a price

Every imported product carries two prices:

- the **source price** — what the shop had when it was last crawled;
- the **live price** — what your storefront actually charges.

A live price that follows the source moves when you crawl again. A live price
**set by hand** never does.

### The price-safety rule

When you change a price by hand, the product is marked `Set by hand`. Every
later crawl leaves that live price alone and only refreshes the source price.
This is deliberate: a price you chose is not something a crawl should undo.

The product list shows both states:

| Badge | Meaning |
|-------|---------|
| `Set by hand` | You changed the price. A crawl will not touch it. |
| `Source changed` | The shop has changed its price since the last crawl, but your hand-set price is still in force. |

### Change one price

1. Go to **Products** and press **Edit** on a product.
2. Change the **Price** field.
3. Press **Save the product**.

The editor sends the price only when the value actually changed. Editing the
description alone leaves the price following the source.

The side panel of the editor always states which rule is in force for that
product: *Set by hand — a crawl will not change it*, or *Follows the source*.

### Change many prices at once

1. Go to **Products**.
2. Tick the products you want. The tick box in the header selects the whole
   page.
3. Press **Change the price of the selected**.
4. On the **Bulk pricing** page, choose:
   - **What to change** — the selected products, a category, or every product.
   - **How** — raise or lower by a percentage, add or take away an amount, or
     set the same price on all of them.
   - **Value** — the number, for example `10`, `1.10` or `5.00`.
   - **Read the value as** — *Work it out*, *A percentage* or *A factor*.
5. The new prices are listed in a table **before** anything changes.
6. Press **Change N prices** to apply.

Nothing is written until you press the button. After it, the page reports how
many prices changed and the factor that was used.

With *Work it out*, a value written with a point between 1 and 2 is read as a
factor (`1.10` means ten percent more) and anything else is read as a
percentage (`10` means ten percent more). Choosing *A percentage* or *A factor*
removes the guesswork.

All arithmetic runs on exact decimals and is rounded to two decimal places. A
price is never held as a floating-point number.

---

## 4. The rest of the admin panel

**Dashboard** — counts of products, categories and orders, and the most recent
crawl runs.

**Products** — the whole catalog, including hidden and draft products, which
never appear in the storefront. Filter by status (`active`, `hidden`, `draft`),
by category, or search by title and slug. Twenty-five products to a page.

**Product editor** — title, description, vendor, SKU, price, compare-at price,
currency, stock, status, the stored image paths (one per line) and the
categories the product belongs to. The side panel shows the source platform,
the source price, when it was last crawled, and a link to the original page.

**Categories** — create and rename the categories used to group the catalog.
These are the categories the storefront uses to organise products.

**Orders** — every order placed through the storefront, with its code, the
customer's details, the line items and the totals.

**Crawls** — start a crawl and watch it, as described above.

---

## 5. The storefront

- **Home** — the categories and the products.
- **Category page** — the products of one category, with search and paging.
- **Product page** — the pictures, the price, the variants, the stock and an
  add-to-cart button.
- **Cart** — change the quantities and see the subtotal.
- **Checkout** — email, name and address. Totals are worked out on the server
  from the database price, never from what the browser sent.
- **Order page** — the order code, for example `CF-AB12CD34EF`. The same code
  can be looked up later at `/api/orders/{code}`.

An order does not take payment. Catalog Forge is the catalog and the shop
front; connecting a payment provider is a separate piece of work.

---

## 6. Settings

Every setting is an environment variable, and every one has a working default.

| Variable | Default | What it does |
|----------|---------|--------------|
| `CATALOG_FORGE_ADMIN_USERNAME` | `admin` | The admin user name. |
| `CATALOG_FORGE_ADMIN_PASSWORD` | *(empty)* | The admin password. Required. |
| `CATALOG_FORGE_DATA` | `<repo>/data` | Where the database, the media and the secret live. |
| `CATALOG_FORGE_DATABASE` | `<data>/catalog.db` | The SQLite file. |
| `CATALOG_FORGE_MEDIA_DIR` | `<data>/media` | Where the imported images are stored. |
| `CATALOG_FORGE_SECRET` | generated | The key that signs sessions. Generated once into `<data>/.secret_key` and reused. Set it yourself to keep sessions across a move. |
| `CATALOG_FORGE_USER_AGENT` | `CatalogForge/1.0 (+https://github.com/gravion-ux/catalog-forge)` | Who the crawler says it is. |
| `CATALOG_FORGE_CRAWLER_DELAY_SECONDS` | `1.0` | The wait between two requests to the same host. |
| `CATALOG_FORGE_CRAWLER_MAX_CONCURRENCY` | `4` | How many pages are fetched at once. |
| `CATALOG_FORGE_CRAWLER_MAX_PAGES` | `500` | The most pages one crawl will fetch. |
| `CATALOG_FORGE_CRAWLER_TIMEOUT_SECONDS` | `20.0` | The timeout for one request. |
| `CATALOG_FORGE_ALLOW_PRIVATE` | `false` | Allows the crawler to reach private addresses. Testing only. |
| `CATALOG_FORGE_SESSION_MAX_AGE_SECONDS` | `28800` | How long an admin session lasts (eight hours). |
| `CATALOG_FORGE_LOGIN_RATE_LIMIT_ATTEMPTS` | `5` | How many sign-in attempts are allowed in the window. |
| `CATALOG_FORGE_LOGIN_RATE_LIMIT_WINDOW_SECONDS` | `300` | The length of that window. |
| `CATALOG_FORGE_STORE_CURRENCY` | `USD` | The currency used for products that do not name one. |

---

## 7. Running the checks

```sh
# The backend suite
python -m pytest -v

# The frontend
cd frontend
npm run typecheck
npm run build

# The whole thing end to end: a crawl against a local fixture shop, a price
# changed through the admin API, and the storefront read back.
cd ..
python scripts/smoke_test.py
```

The same checks run on GitHub for every push to `main`. See
[`.github/workflows/ci.yml`](../.github/workflows/ci.yml), and the run history
at <https://github.com/gravion-ux/catalog-forge/actions>.

---

## 8. Where things live

| Path | What it holds |
|------|---------------|
| `backend/app/api/` | The public API, the order API and the admin API. |
| `backend/app/catalog/` | Every SQL statement in the project. |
| `backend/app/crawler/` | The URL guard, robots.txt, the fetcher, the extractors and the importer. |
| `backend/app/money.py` | The exact decimal money handling. |
| `frontend/src/storefront/` | The shop. |
| `frontend/src/admin/` | The admin panel. |
| `scripts/smoke_test.py` | The end-to-end check. |
| `docs/API.md` | Every endpoint, with its request and response shapes. |

---

## 9. A note on what is fair to copy

Only crawl shops you have the right to copy. Respect the terms of service of
the site you are reading and the rights of whoever owns the content. Catalog
Forge honours robots.txt, identifies itself honestly, and will not get past a
CAPTCHA, a paywall or a login — but those are the floor, not the ceiling of
what you should do.

A crawled catalog is often still the original owner's copyrighted work and
photography. Importing it does not make it yours.
