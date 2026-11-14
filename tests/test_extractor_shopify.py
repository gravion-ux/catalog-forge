from __future__ import annotations

from app.crawler.extractors.shopify import detect, extract

SHOPIFY_PAGE = """
<html><head>
<link rel="stylesheet" href="https://cdn.shopify.com/s/files/1/theme.css">
<script type="application/ld+json">
{"@type": "Product", "name": "Linen Shirt", "price": "45.00",
 "offers": {"@type": "Offer", "price": "45.00", "priceCurrency": "USD",
            "availability": "https://schema.org/InStock"},
 "image": "https://cdn.shopify.com/s/files/linen.jpg"}
</script>
</head><body>
<script>
  var product = {"id": 123, "title": "Linen Shirt", "variants": [
    {"id": 1, "title": "Small", "price": 4500, "available": true, "sku": "LS-S"},
    {"id": 2, "title": "Large", "price": 4900, "available": false, "sku": "LS-L"}
  ]};
</script>
</body></html>
"""

PLAIN_PAGE = "<html><body><p>Not a shop.</p></body></html>"


def test_detects_a_shopify_page() -> None:
    assert detect(SHOPIFY_PAGE) is True


def test_does_not_detect_shopify_on_a_plain_page() -> None:
    assert detect(PLAIN_PAGE) is False


def test_extracts_the_product() -> None:
    product = extract(SHOPIFY_PAGE, "https://shop.example.com/products/linen-shirt")

    assert product is not None
    assert product.platform == "shopify"
    assert product.title == "Linen Shirt"
    assert product.price == "45.00"
    assert product.currency == "USD"
    assert product.images == ["https://cdn.shopify.com/s/files/linen.jpg"]


def test_extracts_the_variants() -> None:
    product = extract(SHOPIFY_PAGE, "https://shop.example.com/products/linen-shirt")

    assert product is not None
    assert len(product.variants) == 2
    assert product.variants[0]["title"] == "Small"
    assert product.variants[0]["price"] == "45.00"
    assert product.variants[0]["available"] is True
    assert product.variants[1]["available"] is False


def test_shopify_prices_are_read_from_cents_when_needed() -> None:
    product = extract(SHOPIFY_PAGE, "https://shop.example.com/products/linen-shirt")

    assert product is not None
    assert product.variants[1]["price"] == "49.00"
