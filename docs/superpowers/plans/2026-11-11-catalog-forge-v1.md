# Catalog Forge v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Crawl any public shop's catalog into a local database, serve it as your own storefront, and give you a separate admin panel to edit the catalog and prices.

**Architecture:** A FastAPI backend owns a SQLite database through a thin repository layer, with a crawler subsystem (robots, rate-limited fetching, sitemap discovery, platform extractors, image import) feeding the same catalog the storefront reads. A React/TypeScript SPA serves two surfaces from one build: the public storefront and the admin panel, separated by route and by session auth. Every price edit is written to `price_history`, and a re-crawl never overwrites a price you edited by hand.

**Tech Stack:** Python 3.11+ (tested on 3.15), FastAPI 0.162, uvicorn 0.54, httpx 0.28, pydantic 2.14, beautifulsoup4, standard-library `sqlite3`, pytest 9. React 18, TypeScript (strict), Vite 6, plain CSS.

## Global Constraints

- The repository is `gravion-ux/catalog-forge`. It shares no code, no venv and no data with any other project.
- Python dependencies are exactly the five runtime packages in `backend/requirements.txt` plus pytest in `backend/requirements-dev.txt`. No ORM, no UI library, no router library, no state library, no icon library.
- SQLite is accessed through `backend/app/db.py` only. SQL never appears in API or crawler modules.
- Prices are stored as TEXT holding a fixed 2-decimal string. Money never touches a float.
- The crawler only requests `http` and `https` URLs that resolve to public addresses. Loopback, private, link-local and cloud-metadata addresses are refused unless `CATALOG_FORGE_ALLOW_PRIVATE=1` is set explicitly.
- `robots.txt` is honored for every target host. `Crawl-delay` is respected when present.
- No CAPTCHA, anti-bot, or paywall bypass. No login-walled content. No credential harvesting.
- Frontend TypeScript runs with `strict: true`. No `any` in an exported signature. No `@ts-ignore`.
- The frontend talks to the API through `VITE_API_BASE`, defaulting to `http://localhost:8000`.
- Every admin mutating request requires a valid CSRF token and a valid admin session.
- Tests never touch the public network. The crawler tests use `httpx.MockTransport` and a local fixture server.

---

### Task 1: Scaffold, configuration, database and domain models

**Files:**
- Create: `backend/app/__init__.py`, `backend/app/config.py`, `backend/app/db.py`, `backend/app/models.py`
- Create: `backend/requirements.txt`, `backend/requirements-dev.txt`, `pytest.ini`, `.gitignore`, `README.md`
- Test: `tests/conftest.py`, `tests/test_config.py`, `tests/test_db.py`

**Interfaces:**
- Produces: `config.Settings` (frozen dataclass), `config.load_settings(environ=None) -> Settings`
- Produces: `db.connect(path) -> sqlite3.Connection`, `db.init_db(path) -> None`, `db.session(path)` context manager
- Produces: `models.Product`, `models.Variant`, `models.Category`, `models.ProductImage`, `models.Order`, `models.OrderItem`, `models.CrawlRun`, `models.PriceChange`

- [ ] **Step 1: Write the failing tests** — `tests/test_config.py` asserts defaults (`database_path` under `data/`, `crawler_delay_seconds` default 1.0, `admin_username` default `admin`) and that environment overrides win; `tests/test_db.py` asserts `init_db` creates all eleven tables and that a product row survives a round trip.
- [ ] **Step 2: Run the tests and watch them fail** — `pytest tests/test_config.py tests/test_db.py -v` fails with `ModuleNotFoundError: No module named 'app'`.
- [ ] **Step 3: Implement `config.py`, `db.py`, `models.py`** — `Settings` reads `CATALOG_FORGE_*` environment variables; `load_settings()` generates and persists a 32-byte secret at `data/.secret_key` when none is supplied. `db.py` holds the full `SCHEMA` DDL string and `init_db` executes it. `models.py` holds dataclasses plus `row_to_product(row)` style mappers.
- [ ] **Step 4: Run the tests and watch them pass** — `pytest tests/test_config.py tests/test_db.py -v` passes.
- [ ] **Step 5: Commit** — `git add backend tests pytest.ini .gitignore README.md && git commit -m "feat: scaffold config, database and domain models"`

### Task 2: Admin authentication and session security

**Files:**
- Create: `backend/app/security.py`
- Test: `tests/test_security.py`

**Interfaces:**
- Consumes: `config.Settings.secret_key`
- Produces: `security.hash_password(password, salt=None) -> tuple[str, str]`, `security.verify_password(password, stored_hash, salt) -> bool`
- Produces: `security.create_session_token(username, secret, expires_at) -> str`, `security.verify_session_token(token, secret, now=None) -> str | None`
- Produces: `security.csrf_token(session_token, secret) -> str`, `security.check_csrf(session_token, csrf, secret) -> bool`
- Produces: `security.RateLimiter(limit, window_seconds)` with `allow(key) -> bool` and `retry_after(key) -> int`

- [ ] **Step 1: Write the failing tests** — a wrong password fails verification, a tampered session token is rejected, an expired token is rejected, the CSRF token does not match a different session token, and the limiter blocks the 11th attempt inside the window.
- [ ] **Step 2: Run the tests and watch them fail** — `pytest tests/test_security.py -v` fails with `ModuleNotFoundError: No module named 'app.security'`.
- [ ] **Step 3: Implement `security.py`** — passwords use `hashlib.scrypt` with a per-user 16-byte salt, stored base64url. Session tokens are `base64url(payload).base64url(hmac_sha256)` over `username|expires_at`; verification recomputes the HMAC with `hmac.compare_digest` and checks the expiry. The CSRF token is `hmac_sha256(session_token, secret)`.
- [ ] **Step 4: Run the tests and watch them pass**.
- [ ] **Step 5: Commit** — `git commit -m "feat: add admin password hashing, signed sessions, CSRF and login rate limiting"`

### Task 3: Catalog repository and the public read API

**Files:**
- Create: `backend/app/catalog/__init__.py`, `backend/app/catalog/products.py`, `backend/app/catalog/categories.py`, `backend/app/catalog/images.py`
- Create: `backend/app/api/__init__.py`, `backend/app/api/public.py`, `backend/app/main.py`
- Test: `tests/test_catalog.py`, `tests/test_api_public.py`

**Interfaces:**
- Consumes: `db.connect`, `models.*`
- Produces: `catalog.products.list_products(conn, *, category_slug=None, search=None, page=1, page_size=24) -> tuple[list[Product], int]`, `catalog.products.get_product_by_slug(conn, slug) -> Product | None`, `catalog.products.get_product(conn, product_id) -> Product | None`
- Produces: `catalog.categories.list_categories(conn) -> list[Category]`, `catalog.categories.ensure_category(conn, name) -> Category`
- Produces: `catalog.images.images_for(conn, product_id) -> list[ProductImage]`
- Produces: `main.create_app(settings=None) -> FastAPI`

- [ ] **Step 1: Write the failing tests** — seed a product and a category, then assert `GET /api/products` returns it, `GET /api/products/{slug}` returns its detail, `GET /api/categories` lists categories, and searching by a title fragment filters correctly. A product with `status='hidden'` never appears.
- [ ] **Step 2: Run the tests and watch them fail**.
- [ ] **Step 3: Implement the repository and the public router** — every SQL statement lives in `catalog/`. The router returns `{"items": [...], "total": n, "page": p, "page_size": s}` for listings and the product detail includes its images and categories.
- [ ] **Step 4: Run the tests and watch them pass**.
- [ ] **Step 5: Commit** — `git commit -m "feat: add the catalog repository and the public read API"`

### Task 4: Cart, checkout and orders

**Files:**
- Create: `backend/app/api/orders.py`
- Modify: `backend/app/main.py`
- Test: `tests/test_api_orders.py`

**Interfaces:**
- Consumes: `catalog.products.get_product`, `models.Order`
- Produces: `POST /api/checkout` accepting `{"email", "name", "address": {...}, "items": [{"product_id", "quantity"}]}` and returning `{"code", "total", "items"}`
- Produces: `GET /api/orders/{code}` returning the order summary
- Produces: `POST /api/orders/quote` returning `{"subtotal", "total", "lines"}` for a cart

- [ ] **Step 1: Write the failing tests** — checkout creates an order with the right line totals, decrements nothing but records stock at order time, an unknown product id is a 422, an empty cart is a 422, and `GET /api/orders/{code}` returns the order for an unknown code as a 404.
- [ ] **Step 2: Run the tests and watch them fail**.
- [ ] **Step 3: Implement `orders.py`** — the order code is `CF-` plus 10 uppercase base32 characters. Totals are computed from the database price, never from a client-supplied price.
- [ ] **Step 4: Run the tests and watch them pass**.
- [ ] **Step 5: Commit** — `git commit -m "feat: add cart quoting, checkout and order lookup"`

### Task 5: Crawler URL guard, robots.txt and the rate-limited fetcher

**Files:**
- Create: `backend/app/crawler/__init__.py`, `backend/app/crawler/urls.py`, `backend/app/crawler/robots.py`, `backend/app/crawler/fetcher.py`
- Test: `tests/test_crawler_urls.py`, `tests/test_crawler_robots.py`, `tests/test_crawler_fetcher.py`

**Interfaces:**
- Produces: `crawler.urls.UrlNotAllowed(ValueError)`, `crawler.urls.normalize_url(url, base=None) -> str`, `crawler.urls.is_public_url(url, resolver=socket.getaddrinfo) -> bool`, `crawler.urls.same_site(a, b) -> bool`
- Produces: `crawler.robots.RobotsRules` with `.allows(url) -> bool` and `.crawl_delay`, `crawler.robots.parse_robots(text, user_agent) -> RobotsRules`, `crawler.robots.fetch_robots(client, base_url, user_agent) -> RobotsRules`
- Produces: `crawler.fetcher.Fetcher(user_agent, delay_seconds=1.0, max_concurrency=4, timeout_seconds=20.0, max_pages=500, allow_private=False)` with `async get(url) -> FetchResult` and `async get_bytes(url) -> tuple[bytes, str]`

- [ ] **Step 1: Write the failing tests** — `file://` and `ftp://` URLs are refused; a URL with embedded credentials is refused; `http://169.254.169.254/` is refused; `http://127.0.0.1/` is refused; `robots.txt` with `Disallow: /private` blocks that path and allows the rest; a `Crawl-delay: 2` is reported; the fetcher refuses a disallowed URL without requesting it; the fetcher stops after `max_pages`.
- [ ] **Step 2: Run the tests and watch them fail**.
- [ ] **Step 3: Implement the three modules** — `Fetcher` uses one `httpx.AsyncClient` with `follow_redirects=True`, a per-host last-request timestamp enforcing the delay, an `asyncio.Semaphore` capping concurrency, and a page counter. Redirect targets are re-validated by the guard before they are followed.
- [ ] **Step 4: Run the tests and watch them pass**.
- [ ] **Step 5: Commit** — `git commit -m "feat: add the crawler URL guard, robots.txt rules and rate-limited fetcher"`

### Task 6: Sitemap and product URL discovery

**Files:**
- Create: `backend/app/crawler/discovery.py`
- Test: `tests/test_crawler_discovery.py`

**Interfaces:**
- Produces: `crawler.discovery.parse_sitemap(xml_text) -> list[str]`, `crawler.discovery.looks_like_product_url(url) -> bool`, `crawler.discovery.discover_product_urls(fetcher, base_url, robots) -> list[str]`

- [ ] **Step 1: Write the failing tests** — a sitemap index pointing at two child sitemaps yields every child URL; a urlset yields its loc entries; `/products/blue-shirt` looks like a product while `/collections/shoes` does not; discovery skips robots-disallowed URLs and de-duplicates results.
- [ ] **Step 2: Run the tests and watch them fail**.
- [ ] **Step 3: Implement `discovery.py`** — `parse_sitemap` uses `xml.etree.ElementTree` and handles both `sitemapindex` and `urlset`. `looks_like_product_url` matches path segments containing `product`, `products`, `item`, `items`, `p/` or `shop`. Discovery reads the sitemaps named by robots, then `/sitemap.xml`.
- [ ] **Step 4: Run the tests and watch them pass**.
- [ ] **Step 5: Commit** — `git commit -m "feat: add sitemap parsing and product URL discovery"`

### Task 7: Extractors for generic, Shopify and WooCommerce shops

**Files:**
- Create: `backend/app/crawler/extractors/__init__.py`, `base.py`, `generic.py`, `shopify.py`, `woocommerce.py`
- Create: `backend/app/crawler/normalize.py`
- Test: `tests/test_extractor_generic.py`, `tests/test_extractor_shopify.py`, `tests/test_extractor_woocommerce.py`

**Interfaces:**
- Produces: `extractors.base.ExtractedProduct` dataclass with `title, description, price, compare_at_price, currency, images, vendor, sku, availability, variants, categories, platform, source_url`
- Produces: `extractors.base.extract(html_text, url) -> ExtractedProduct | None` dispatching on platform detection
- Produces: `extractors.generic.detect(html_text) -> bool`, `extractors.generic.extract(html_text, url) -> ExtractedProduct | None`
- Produces: `extractors.shopify.detect(html_text) -> bool`, `extractors.shopify.extract(html_text, url) -> ExtractedProduct | None`
- Produces: `extractors.woocommerce.detect(html_text) -> bool`, `extractors.woocommerce.extract(html_text, url) -> ExtractedProduct | None`
- Produces: `crawler.normalize.normalize(product: ExtractedProduct) -> dict` with `price` and `compare_at_price` as 2-decimal strings

- [ ] **Step 1: Write the failing tests** — a JSON-LD Product block yields title, price, currency, images and availability; a page with no product markup yields `None`; a Shopify page (detected by `cdn.shopify.com`) yields the product with its variants; a WooCommerce page (detected by the `woocommerce` body class) yields title, price and images; `normalize` turns `19.9` into `"19.90"` and keeps `"19.90"`.
- [ ] **Step 2: Run the tests and watch them fail**.
- [ ] **Step 3: Implement the extractors** — the generic extractor reads every `application/ld+json` script and picks the first `Product` node (handling `@graph`), then falls back to microdata (`itemprop="price"`) and OpenGraph (`og:price:amount`). The Shopify extractor reads the product JSON embedded in the page and the variant list from `ShopifyAnalytics`/`product.variants` data. The WooCommerce extractor reads the schema.org block plus the embedded `woocommerce-product-details` JSON.
- [ ] **Step 4: Run the tests and watch them pass**.
- [ ] **Step 5: Commit** — `git commit -m "feat: add generic, Shopify and WooCommerce extractors"`

### Task 8: Image import, product upsert, price safety and the crawl runner

**Files:**
- Create: `backend/app/crawler/images.py`, `backend/app/crawler/importer.py`, `backend/app/crawler/runner.py`
- Test: `tests/test_crawler_images.py`, `tests/test_importer.py`, `tests/test_crawl_runner.py`

**Interfaces:**
- Produces: `crawler.images.store_image(fetcher, url, media_dir) -> tuple[str, str] | None` returning `(relative_path, sha256)`
- Produces: `crawler.importer.import_product(conn, product: dict, *, source_platform: str) -> ImportResult` with `ImportResult(product_id, created, price_kept, source_price_changed)`
- Produces: `crawler.importer.set_price(conn, product_id, new_price, source="admin") -> PriceChange`
- Produces: `crawler.runner.run_crawl(conn, fetcher, url, *, on_progress=None) -> CrawlSummary`

- [ ] **Step 1: Write the failing tests** — an image is written under `data/media/` and the same bytes fetched twice produce one file; importing the same source URL twice updates instead of duplicating; importing a product whose price was edited by hand keeps the edited price, stores the new source price, and reports `source_price_changed`; `set_price` appends a `price_history` row; a crawl over the local fixture site imports its products and records a completed run.
- [ ] **Step 2: Run the tests and watch them fail**.
- [ ] **Step 3: Implement the three modules** — `import_product` matches on `source_url`. When `price_manually_edited` is true, the live price is left alone and `source_price` is updated instead. Images are stored as `media/<sha[:2]>/<sha>.<ext>` and the relative path is recorded on the product.
- [ ] **Step 4: Run the tests and watch them pass**.
- [ ] **Step 5: Commit** — `git commit -m "feat: add image import, product upsert with price safety and the crawl runner"`

### Task 9: The admin API

**Files:**
- Create: `backend/app/api/admin.py`, `backend/app/jobs.py`
- Modify: `backend/app/main.py`
- Test: `tests/test_api_admin.py`

**Interfaces:**
- Produces: `POST /api/admin/login`, `POST /api/admin/logout`, `GET /api/admin/session`
- Produces: `GET /api/admin/products`, `GET /api/admin/products/{id}`, `PATCH /api/admin/products/{id}`, `PATCH /api/admin/products/{id}/price`
- Produces: `POST /api/admin/products/bulk-price` with `{"mode": "markup"|"delta"|"set", "value": str, "product_ids": [..]|null, "category_id": int|null}`
- Produces: `GET /api/admin/categories`, `POST /api/admin/categories`, `PATCH /api/admin/categories/{id}`
- Produces: `GET /api/admin/orders`
- Produces: `POST /api/admin/crawls`, `GET /api/admin/crawls`, `GET /api/admin/crawls/{id}`

- [ ] **Step 1: Write the failing tests** — an unauthenticated admin request is a 401; a login with the wrong password is a 401 and the 6th attempt inside the window is a 429; a write without the CSRF header is a 403; editing a price updates the product and writes `price_history`; a markup bulk update multiplies every selected price by 1.10 and rounds to 2 decimals; a crawl can be started and its status read back.
- [ ] **Step 2: Run the tests and watch them fail**.
- [ ] **Step 3: Implement `admin.py` and `jobs.py`** — the session cookie is `HttpOnly`, `SameSite=Lax`, path `/`. Crawls run as a background `asyncio` task whose progress is written to the `crawl_runs` table.
- [ ] **Step 4: Run the tests and watch them pass**.
- [ ] **Step 5: Commit** — `git commit -m "feat: add the admin API with price editing, bulk pricing and crawl control"`

### Task 10: Frontend scaffold and the storefront

**Files:**
- Create: `frontend/package.json`, `frontend/vite.config.ts`, `frontend/tsconfig.json`, `frontend/tsconfig.node.json`, `frontend/index.html`
- Create: `frontend/src/main.tsx`, `frontend/src/App.tsx`, `frontend/src/styles.css`, `frontend/src/lib/api.ts`, `frontend/src/lib/types.ts`, `frontend/src/lib/format.ts`, `frontend/src/lib/cart.tsx`, `frontend/src/lib/router.tsx`
- Create: `frontend/src/storefront/Layout.tsx`, `HomePage.tsx`, `CategoryPage.tsx`, `ProductPage.tsx`, `CartPage.tsx`, `CheckoutPage.tsx`, `OrderPage.tsx`
- Test: `frontend/src/lib/format.test.ts` (run through `tsc` only; logic is covered by the backend tests)

**Interfaces:**
- Consumes: `GET /api/products`, `GET /api/products/{slug}`, `GET /api/categories`, `POST /api/orders/quote`, `POST /api/checkout`, `GET /api/orders/{code}`
- Produces: `lib.api.get<T>(path)`, `lib.api.post<T>(path, body)`, `lib.api.patch<T>(path, body)` — all throwing `ApiError` with the server message
- Produces: `lib.cart.CartProvider` with `items`, `add`, `remove`, `setQuantity`, `clear`, `count`, `subtotal`
- Produces: `lib.router.useRoute()` returning `{path, params}` and `lib.router.navigate(path)`

- [ ] **Step 1: Scaffold the frontend** — `package.json` depends on `react`, `react-dom` and dev-depends on `vite`, `typescript`, `@types/react`, `@types/react-dom`. `npm install` succeeds.
- [ ] **Step 2: Write the storefront pages** — home lists categories and featured products; category pages list products with pagination and search; the product page shows images, price, variants, stock and an add-to-cart button; the cart page edits quantities and shows the subtotal; checkout takes contact and address details and shows the order code; the order page confirms the order.
- [ ] **Step 3: Type check and build** — `npm run typecheck` and `npm run build` both exit 0.
- [ ] **Step 4: Commit** — `git commit -m "feat: add the storefront frontend"`

### Task 11: The admin panel frontend

**Files:**
- Create: `frontend/src/admin/AdminLayout.tsx`, `LoginPage.tsx`, `DashboardPage.tsx`, `ProductsPage.tsx`, `ProductEditorPage.tsx`, `BulkPricePage.tsx`, `CategoriesPage.tsx`, `OrdersPage.tsx`, `CrawlPage.tsx`
- Modify: `frontend/src/lib/api.ts` (add the CSRF header to mutating calls)

**Interfaces:**
- Consumes: every `/api/admin/*` endpoint
- Produces: `lib.api` sends `X-CSRF-Token` on every mutating request, taken from the session response

- [ ] **Step 1: Write the admin pages** — login posts credentials and stores the session; the product table searches, filters and shows the live price beside the source price with a "source changed" badge; the product editor edits title, description, prices, stock, images and categories; the bulk-price page previews the new prices before applying them; the crawl page starts a crawl and polls its progress.
- [ ] **Step 2: Type check and build** — both exit 0.
- [ ] **Step 3: Commit** — `git commit -m "feat: add the admin panel frontend"`

### Task 12: CI, documentation and final verification

**Files:**
- Create: `.github/workflows/ci.yml`, `docs/API.md`, `docs/ARCHITECTURE.md`, `docs/USER-GUIDE.md`, `scripts/run.ps1`
- Modify: `README.md`

**Interfaces:**
- Produces: a CI workflow that runs `pytest` and the frontend type check and build

- [ ] **Step 1: Write the CI workflow** — a `push` and `pull_request` trigger on `main` that installs the backend requirements, runs `pytest -q`, then installs the frontend dependencies and runs `npm run typecheck` and `npm run build`.
- [ ] **Step 2: Write the docs** — the README states what the tool does, the legal position, the install steps and the quick start. `docs/API.md` lists every endpoint with its request and response shapes. `docs/USER-GUIDE.md` walks through crawling a site and editing prices.
- [ ] **Step 3: Run the whole suite and the frontend build** — `pytest -q` and `npm run typecheck && npm run build` both pass.
- [ ] **Step 4: Smoke test the running server** — start uvicorn, log into the admin API, start a crawl against the local fixture site, edit a price through the admin API and confirm the storefront API returns the new price.
- [ ] **Step 5: Commit and push** — `git commit -m "ci: add the GitHub Actions workflow, documentation and smoke test" && git push origin main`

---

## Self-review notes

- Every spec section maps to a task: crawler (Tasks 5-8), data model (Task 1), storefront (Tasks 3, 4, 10), admin panel (Tasks 2, 9, 11), guardrails (Task 5), price safety (Task 8), testing (all tasks), CI and docs (Task 12).
- The one deliberate deviation from the design spec: SQLite is accessed through the standard-library `sqlite3` module with a hand-written repository layer instead of SQLAlchemy. The spec was updated to match before implementation.
- `price_manually_edited` is the single flag that implements the price-safety rule; `importer.import_product` and `importer.set_price` are its only two writers.
