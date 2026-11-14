from __future__ import annotations

from app.crawler.extractors.woocommerce import detect, extract

WOOCOMMERCE_PAGE = """
<html><head>
<script type="application/ld+json">
{"@type": "Product", "name": "Cotton Cap", "description": "A six panel cap.",
 "sku": "CAP-01",
 "offers": [{"@type": "Offer", "price": "18.50", "priceCurrency": "GBP",
             "availability": "https://schema.org/InStock"}],
 "image": ["https://shop.example.com/wp-content/cap.jpg"]}
</script>
</head><body class="woocommerce">
<script>
  var wc_product_data = {"id": 42, "price": "18.50", "stock_quantity": 7,
                          "stock_status": "instock"};
</script>
</body></html>
"""

PLAIN_PAGE = "<html><body><p>Not a shop.</p></body></html>"


def test_detects_a_woocommerce_page() -> None:
    assert detect(WOOCOMMERCE_PAGE) is True


def test_does_not_detect_woocommerce_on_a_plain_page() -> None:
    assert detect(PLAIN_PAGE) is False


def test_extracts_the_product() -> None:
    product = extract(WOOCOMMERCE_PAGE, "https://shop.example.com/product/cotton-cap")

    assert product is not None
    assert product.platform == "woocommerce"
    assert product.title == "Cotton Cap"
    assert product.price == "18.50"
    assert product.currency == "GBP"
    assert product.sku == "CAP-01"
    assert product.images == ["https://shop.example.com/wp-content/cap.jpg"]


def test_extracts_the_stock_quantity() -> None:
    product = extract(WOOCOMMERCE_PAGE, "https://shop.example.com/product/cotton-cap")

    assert product is not None
    assert product.stock == 7


def test_extracts_the_description() -> None:
    product = extract(WOOCOMMERCE_PAGE, "https://shop.example.com/product/cotton-cap")

    assert product is not None
    assert product.description == "A six panel cap."
