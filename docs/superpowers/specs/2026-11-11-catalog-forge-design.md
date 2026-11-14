# Catalog Forge — design

**Date:** 2026-11-11
**Repository:** `gravion-ux/catalog-forge` (new, standalone)
**Status:** approved for implementation

---

## 1. What this is

Catalog Forge crawls an existing shop's public catalog and turns it into a
working storefront of your own, with a separate admin panel where you edit
the catalog and the prices.

Three concrete moves:

1. **Crawl.** Point it at a shop URL. It discovers products, categories,
   images, prices, variants and stock, and imports them into a local catalog
   database. Every imported product keeps the URL it came from and the time
   it was seen.
2. **Sell.** The imported catalog is served by our own storefront: home page,
   category pages, product pages, search, cart, checkout, order confirmation.
3. **Control.** A separate admin panel (its own login, its own routes) lets
   you edit any product, change prices one-by-one or in bulk, manage
   categories, review orders, and start new crawls with live progress.

The storefront is *not* a pixel copy of the source site's theme. We rebuild
the catalog and present it with our own layout. The value is in the data, not
in someone else's CSS.

## 2. Scope

### In scope

- Crawler: robots.txt handling, sitemap discovery, product-page detection,
  extraction, normalization, local image import.
- Extractors: generic schema.org/JSON-LD, Shopify, WooCommerce.
- Storefront API and UI.
- Admin API and UI, including price editing and bulk price operations.
- Orders captured in the database.
- Tests, docs, CI.

### Explicitly out of scope (v1)

- Live payment gateway. Checkout records an order; a payment provider hook
  can be added later (it needs credentials we do not have).
- Republishing the source site's HTML pages, blog, or theme.
- Multi-tenant stores. One catalog per deployment.
- Any CAPTCHA, anti-bot, or paywall bypass.

## 3. Architecture

### Stack

- **Backend:** Python 3.11+, FastAPI, SQLite through the standard-library
  `sqlite3` module with a thin typed repository layer, httpx, BeautifulSoup4,
  uvicorn.
- **Frontend:** React 18 + TypeScript (strict) + Vite, plain CSS. No UI
  library, no state library, no icon library.
- **Tests:** pytest + httpx mock transport for the crawler's own client, and
  a local fixture site served by `http.server` for end-to-end crawler tests.

### Repository layout

```
catalog-forge/
  backend/
    app/
      main.py            FastAPI app factory, static SPA serving, routers
      config.py          settings from env + .env
      db.py              engine, session, schema creation
      models.py          domain dataclasses and row mappers
      schemas.py         Pydantic request/response models
      security.py        admin auth, password hashing, session cookie, CSRF
      catalog/           repository layer (products, categories, images, orders)
      crawler/
        robots.py        robots.txt fetching and rule evaluation
        fetcher.py       HTTP client: rate limit, concurrency, retries
        discovery.py     sitemap parsing, product URL discovery
        extractors/
          base.py        ExtractResult dataclasses
          generic.py     JSON-LD / microdata / OpenGraph
          shopify.py     Shopify product JSON endpoints
          woocommerce.py WooCommerce product data
        normalize.py     platform output -> canonical Product
        images.py        download, store locally, content-hash dedupe
        runner.py        crawl orchestration, progress, persistence
      api/
        public.py        catalog, products, cart, checkout, orders
        admin.py         products, prices, bulk ops, categories, orders, crawls
  frontend/
    src/
      storefront/        home, category, product, cart, checkout, order
      admin/             login, dashboard, products, editor, bulk, categories,
                         orders, crawl
      lib/               api client, types, formatting, cart context
  tests/
    fixtures/sites/      fake shopify / woocommerce / generic sites
  docs/
  scripts/
```

### Data model

| Table | Purpose |
|---|---|
| `products` | title, slug, description, vendor, price, compare_at_price, currency, stock, status, source_url, source_platform, source_price, source_fetched_at, `price_manually_edited` flag, attributes JSON |
| `variants` | product_id, title, sku, price, compare_at_price, stock, options JSON |
| `categories` | slug, name, parent_id, position |
| `product_categories` | product_id, category_id |
| `images` | product_id, local path, remote url, width, height, alt, position, content hash |
| `crawl_runs` | url, platform, status, counters, error, timestamps |
| `crawled_pages` | run_id, url, status_code, kind, error |
| `orders` | code, customer fields, totals, status, currency |
| `order_items` | order_id, product_id, title, unit_price, quantity |
| `admin_users` | username, password hash, salt, created_at |
| `price_history` | product_id, old_price, new_price, source (`crawl`\|`admin`), changed_at |

### Price safety rule

A re-crawl updates the *source* fields of a product. If a price was edited by
hand in the admin panel, the crawl result does **not** overwrite the live
price; it updates `source_price` and marks the product as "source price
changed since your edit" in the admin panel. Nothing you priced by hand is
silently overwritten. Every price change, from either source, is written to
`price_history`.

## 4. Data flow

### Crawl

1. Admin submits a URL. The URL is validated: `http`/`https` only, public
   addresses only, no credentials embedded, no link-local or metadata hosts.
2. `robots.txt` is fetched and parsed. Disallowed paths are never requested.
3. Sitemap discovery: the sitemaps named in `robots.txt`, then
   `/sitemap.xml`. Product URLs are identified by path heuristics and by
   pages that turn out to carry product structured data.
4. Each candidate product page is fetched through the rate-limited client
   (per-host delay, capped concurrency, bounded retries, a descriptive
   User-Agent).
5. An extractor parses the page; `normalize.py` converts the result into the
   canonical shape.
6. Products are upserted (matched on `source_url`). Images are downloaded
   into `data/media/<sha-prefix>/` and deduplicated by content hash.
7. `crawl_runs` and `crawled_pages` record what happened; the admin panel
   polls this for progress.

### Edit and sell

- Admin edits write to the product row and append to `price_history`.
- The storefront reads only live (non-hidden) products and always serves
  local image files, never hotlinks to the source site.

## 5. Guardrails

The crawler reads other people's servers, so it behaves politely and
honestly:

- `robots.txt` is honored, including `Disallow` and `Crawl-delay`.
- One request at a time per host by default, with a configurable delay.
- Public pages only. No login walls, no credential harvesting, no
  CAPTCHA or anti-bot bypass, no attempt to hide that we are a crawler.
- The User-Agent identifies the tool and links to the project.
- Only `http`/`https` to public addresses. Private, loopback, link-local and
  cloud-metadata addresses are refused (a local-run allowlist is opt-in via
  configuration and off by default).
- Product content is copied for use in a store the operator controls. The
  README states plainly that the operator is responsible for holding the
  rights to the content they resell.

## 6. Admin authentication

- A single admin user is created at first run (or from env).
- Passwords are hashed with `hashlib.scrypt` and a per-user random salt.
- The session is a signed, `HttpOnly`, `SameSite=Lax` cookie carrying an
  expiry; the signature is an HMAC over the payload using a server secret.
- Every admin mutation requires a CSRF token that is bound to the session.
- Login is rate limited per source address.
- The admin panel is served under `/admin` and is never linked from the
  public storefront.

## 7. Error handling

- Crawler: per-page failures are recorded and the crawl continues. A run
  ends as `completed`, `completed_with_errors`, or `failed`, and the reason
  is stored.
- API: consistent JSON error bodies (`{"error": {"code", "message"}}`) with
  meaningful status codes. Validation errors are 422, auth failures 401,
  forbidden writes 403, missing rows 404, conflicts 409.
- Frontend: every fetch failure surfaces a readable message; forms keep the
  operator's input when a save fails.

## 8. Testing

- **Crawler tests** run against a local fixture site that mimics a Shopify
  store, a WooCommerce store and a generic JSON-LD shop. No network access.
- **Extraction tests** assert exact normalized output for each platform.
- **API tests** cover catalog listing, product detail, cart, checkout,
  order creation, admin auth, product edit, price edit, bulk price
  operations, category management and crawl control.
- **Price safety test** proves a re-crawl does not overwrite a manually
  edited price.
- **Frontend**: `tsc --noEmit` and `vite build` must pass; a small set of
  component-level checks for the price editor and the cart maths.
- CI runs pytest, the type check and the build on every push.

## 9. Definition of done

- `pytest` green, `tsc --noEmit` green, `vite build` green.
- A crawl of a real public shop imports products with correct titles,
  prices, images and categories.
- An admin can log in, edit a price, bulk-adjust a category's prices, and
  see the change on the storefront immediately.
- A customer can browse, add to cart, check out and receive an order code.
- README, API docs and a run guide are accurate.
- CI workflow in `.github/workflows/ci.yml`.
- Everything pushed to `gravion-ux/catalog-forge` on `main`.

## 10. Open items

- **Checkout payments:** v1 records orders only. A payment provider hook is
  a later, separate change.
- **Deployment:** v1 runs locally. A hosted deployment is a separate step
  and needs a target host.
