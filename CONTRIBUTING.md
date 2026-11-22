# Contributing to Catalog Forge

Thanks for helping! Catalog Forge crawls a public shop's catalog and
runs it as your own storefront, with a separate admin panel for
editing the catalog and prices. It imports products, images, prices,
variants and categories into a local SQLite database and serves them
through a storefront of your own.

The most valuable contributions are crawler/extractor support for
more shop platforms, importer hardening, and tests.

## Ground rules

- **Crawl only what you have the right to copy — hard rule.** The
  README's legal note is part of the product: respect each site's
  terms and robots rules (the crawler has a dedicated robots module
  and tests — do not weaken them), and never add features whose
  purpose is to evade a site's access controls.
- **Admin stays separate.** The storefront is public-facing; the
  admin panel is not. Changes must preserve that boundary — nothing
  admin-only may leak into the public API.

## Development setup

Backend — Python (see `pytest.ini`: tests live in `tests/`, the
backend package is on the path as `backend/`):

```bash
git clone https://github.com/gravion-ux/catalog-forge.git
cd catalog-forge
python -m pip install -r backend/requirements.txt
python -m pip install -r backend/requirements-dev.txt
python -m pytest -q
```

Frontend — TypeScript/Vite, in `frontend/`:

```bash
cd frontend
npm ci
npm run typecheck
npm run build
```

## Running the tests

```bash
python -m pytest -q                          # backend suite
cd frontend && npm run typecheck && npm run build
```

That is exactly what CI runs. The backend suite covers the API
(public, orders, admin), catalog, crawler (discovery, fetcher,
images, robots, URLs), extractors (generic, Shopify, WooCommerce),
importer, database, config and security.

## Adding an extractor

Extractors live in the backend crawler package, one module per
platform (see the generic, Shopify and WooCommerce extractors). A
new extractor needs tests alongside the existing
`tests/test_extractor_*.py` files, built from saved fixture pages —
tests never crawl a live shop.

## Code style

- Backend: plain pytest functions with descriptive names; fixtures
  in `tests/fixtures/`.
- Frontend: TypeScript must pass `npm run typecheck` cleanly.
- Comments explain *why* a crawl, import or pricing rule behaves as
  it does.

## Pull request workflow

1. Fork and branch from `main`: `feat/<short-name>`,
   `fix/<short-name>`, `extractor/<platform>`, `docs/<short-name>`.
2. Run the backend suite and the frontend typecheck/build locally.
3. Open the PR against `main` with: what changed, why, how you
   tested it.
4. CI must be green. One logical change per PR.
