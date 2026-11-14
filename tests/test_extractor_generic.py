from __future__ import annotations

from app.crawler.extractors.generic import detect, extract
from app.crawler.normalize import normalize

JSON_LD_PAGE = """
<html><head>
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Product",
  "name": "Blue Shirt",
  "description": "A comfortable blue shirt.",
  "sku": "SHIRT-BLUE",
  "brand": {"@type": "Brand", "name": "Northwind"},
  "image": ["https://cdn.example.com/blue-1.jpg", "https://cdn.example.com/blue-2.jpg"],
  "offers": {
    "@type": "Offer",
    "price": "19.90",
    "priceCurrency": "USD",
    "availability": "https://schema.org/InStock"
  }
}
</script>
</head><body></body></html>
"""

GRAPH_PAGE = """
<html><head>
<script type="application/ld+json">
{"@graph": [
  {"@type": "WebPage", "name": "Home"},
  {"@type": "Product", "name": "Red Hat", "offers": {"price": "5.00", "priceCurrency": "EUR"}}
]}
</script>
</head><body></body></html>
"""

MICRODATA_PAGE = """
<html><body>
<div itemscope itemtype="https://schema.org/Product">
  <h1 itemprop="name">Canvas Bag</h1>
  <span itemprop="description">A sturdy bag.</span>
  <meta itemprop="price" content="24.00">
  <meta itemprop="priceCurrency" content="USD">
  <img itemprop="image" src="https://cdn.example.com/bag.jpg">
</div>
</body></html>
"""

OPEN_GRAPH_PAGE = """
<html><head>
<meta property="og:title" content="Sticker Pack">
<meta property="og:image" content="https://cdn.example.com/stickers.jpg">
<meta property="product:price:amount" content="3.50">
<meta property="product:price:currency" content="USD">
</head><body></body></html>
"""

NO_PRODUCT_PAGE = "<html><body><p>Just a page.</p></body></html>"


def test_detects_a_json_ld_product() -> None:
    assert detect(JSON_LD_PAGE) is True


def test_detects_nothing_on_an_ordinary_page() -> None:
    assert detect(NO_PRODUCT_PAGE) is False


def test_extracts_a_json_ld_product() -> None:
    product = extract(JSON_LD_PAGE, "https://shop.example.com/products/blue-shirt")

    assert product is not None
    assert product.title == "Blue Shirt"
    assert product.price == "19.90"
    assert product.currency == "USD"
    assert product.sku == "SHIRT-BLUE"
    assert product.vendor == "Northwind"
    assert product.availability == "https://schema.org/InStock"
    assert product.images == [
        "https://cdn.example.com/blue-1.jpg",
        "https://cdn.example.com/blue-2.jpg",
    ]


def test_extracts_a_product_from_a_json_ld_graph() -> None:
    product = extract(GRAPH_PAGE, "https://shop.example.com/products/red-hat")

    assert product is not None
    assert product.title == "Red Hat"
    assert product.price == "5.00"
    assert product.currency == "EUR"


def test_extracts_a_microdata_product() -> None:
    product = extract(MICRODATA_PAGE, "https://shop.example.com/products/canvas-bag")

    assert product is not None
    assert product.title == "Canvas Bag"
    assert product.price == "24.00"
    assert product.images == ["https://cdn.example.com/bag.jpg"]


def test_extracts_an_open_graph_product() -> None:
    product = extract(OPEN_GRAPH_PAGE, "https://shop.example.com/products/stickers")

    assert product is not None
    assert product.title == "Sticker Pack"
    assert product.price == "3.50"
    assert product.images == ["https://cdn.example.com/stickers.jpg"]


def test_extract_returns_none_without_product_data() -> None:
    assert extract(NO_PRODUCT_PAGE, "https://shop.example.com/about") is None


def test_normalize_formats_the_price() -> None:
    product = extract(JSON_LD_PAGE, "https://shop.example.com/products/blue-shirt")
    assert product is not None

    result = normalize(product)

    assert result["price"] == "19.90"
    assert result["currency"] == "USD"
    assert result["stock"] == 10


def test_normalize_rounds_a_raw_number() -> None:
    product = extract(JSON_LD_PAGE, "https://shop.example.com/products/blue-shirt")
    assert product is not None
    product.price = "19.9"

    result = normalize(product)

    assert result["price"] == "19.90"


def test_normalize_keeps_an_already_formatted_price() -> None:
    product = extract(JSON_LD_PAGE, "https://shop.example.com/products/blue-shirt")
    assert product is not None
    product.price = "19.90"

    result = normalize(product)

    assert result["price"] == "19.90"


def test_normalize_marks_an_out_of_stock_product() -> None:
    product = extract(JSON_LD_PAGE, "https://shop.example.com/products/blue-shirt")
    assert product is not None
    product.availability = "https://schema.org/OutOfStock"

    result = normalize(product)

    assert result["stock"] == 0
