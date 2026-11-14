# Catalog Forge

Crawl any public shop's catalog and run it as your own storefront, with a
separate admin panel for editing the catalog and the prices.

Catalog Forge reads a shop's public product pages, imports the products,
images, prices, variants and categories into a local SQLite database, and
serves them through a storefront of your own. The admin panel lets you edit
any product, adjust prices one at a time or in bulk, manage categories,
review orders and start new crawls.

**Legal note.** Only crawl sites you have the right to copy. Respect each
site's terms of service and the rights of the content owner. The crawler
honors `robots.txt`, identifies itself honestly, and never bypasses a
CAPTCHA, a paywall or a login.

## Status

The implementation is in progress. See `docs/superpowers/specs/` for the
design and `docs/superpowers/plans/` for the build plan.

## License

MIT
