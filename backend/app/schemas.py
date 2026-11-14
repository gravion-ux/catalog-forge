"""Request and response shapes for the HTTP API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ErrorBody(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorBody


class CategoryOut(BaseModel):
    id: int
    slug: str
    name: str
    product_count: int = 0


class CategoriesOut(BaseModel):
    items: list[CategoryOut] = Field(default_factory=list)


class ImageOut(BaseModel):
    id: int
    local_path: str | None = None
    remote_url: str | None = None
    alt: str | None = None
    position: int = 0


class ProductOut(BaseModel):
    id: int
    slug: str
    title: str
    price: str
    compare_at_price: str | None = None
    currency: str
    stock: int
    vendor: str | None = None
    image: str | None = None


class ProductDetail(ProductOut):
    description: str = ""
    sku: str | None = None
    source_url: str | None = None
    source_platform: str | None = None
    source_price: str | None = None
    source_fetched_at: str | None = None
    price_manually_edited: bool = False
    attributes: dict[str, object] = Field(default_factory=dict)
    images: list[ImageOut] = Field(default_factory=list)
    categories: list[CategoryOut] = Field(default_factory=list)


class ProductListing(BaseModel):
    items: list[ProductOut] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 24
    pages: int = 0


class CartItemIn(BaseModel):
    product_id: int
    quantity: int = Field(default=1, ge=1, le=999)


class QuoteRequest(BaseModel):
    items: list[CartItemIn] = Field(min_length=1)


class QuoteLine(BaseModel):
    product_id: int
    title: str
    unit_price: str
    quantity: int
    line_total: str
    currency: str = "USD"


class QuoteOut(BaseModel):
    lines: list[QuoteLine] = Field(default_factory=list)
    subtotal: str = "0.00"
    total: str = "0.00"
    currency: str = "USD"


class CheckoutRequest(BaseModel):
    email: str = Field(min_length=3)
    name: str = Field(min_length=1)
    address: dict[str, str] = Field(default_factory=dict)
    items: list[CartItemIn] = Field(min_length=1)


class OrderItemOut(BaseModel):
    product_id: int | None = None
    title: str
    unit_price: str
    quantity: int


class OrderOut(BaseModel):
    code: str
    email: str
    name: str
    address: dict[str, str] = Field(default_factory=dict)
    subtotal: str = "0.00"
    shipping: str = "0.00"
    discount: str = "0.00"
    total: str = "0.00"
    currency: str = "USD"
    status: str = "placed"
    created_at: str = ""
    items: list[OrderItemOut] = Field(default_factory=list)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class SessionOut(BaseModel):
    username: str
    csrf_token: str


class VariantOut(BaseModel):
    id: int
    title: str = ""
    sku: str | None = None
    price: str = "0.00"
    compare_at_price: str | None = None
    stock: int = 0
    options: dict[str, object] = Field(default_factory=dict)


class AdminImageOut(BaseModel):
    id: int
    local_path: str | None = None
    remote_url: str | None = None
    alt: str | None = None
    position: int = 0


class AdminProductOut(BaseModel):
    id: int
    slug: str
    title: str
    price: str
    source_price: str | None = None
    source_price_changed: bool = False
    price_manually_edited: bool = False
    compare_at_price: str | None = None
    currency: str
    stock: int
    vendor: str | None = None
    sku: str | None = None
    status: str = "active"
    image: str | None = None
    source_url: str | None = None
    source_platform: str | None = None
    source_fetched_at: str | None = None
    updated_at: str = ""


class AdminProductDetail(AdminProductOut):
    description: str = ""
    attributes: dict[str, object] = Field(default_factory=dict)
    images: list[AdminImageOut] = Field(default_factory=list)
    categories: list[CategoryOut] = Field(default_factory=list)
    variants: list[VariantOut] = Field(default_factory=list)


class AdminProductListing(BaseModel):
    items: list[AdminProductOut] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 24
    pages: int = 0


class ProductPatch(BaseModel):
    title: str | None = None
    description: str | None = None
    vendor: str | None = None
    sku: str | None = None
    price: str | None = None
    compare_at_price: str | None = None
    currency: str | None = None
    stock: int | None = None
    status: str | None = None
    category_ids: list[int] | None = None
    images: list[str] | None = None


class PricePatch(BaseModel):
    price: str | None = None
    compare_at_price: str | None = None


class PriceChangeOut(BaseModel):
    id: int
    old_price: str
    new_price: str
    source: str = "admin"
    changed_at: str = ""


class BulkPriceRequest(BaseModel):
    mode: str
    value: str
    unit: str | None = None
    product_ids: list[int] | None = None
    category_id: int | None = None


class BulkPriceResult(BaseModel):
    mode: str
    value: str
    factor: str | None = None
    updated: int = 0
    products: list[PriceChangeOut] = Field(default_factory=list)


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1)
    parent_id: int | None = None


class CategoryPatch(BaseModel):
    name: str | None = None
    parent_id: int | None = None
    position: int | None = None


class AdminCategoryOut(BaseModel):
    id: int
    slug: str
    name: str
    parent_id: int | None = None
    position: int = 0
    product_count: int = 0


class AdminCategoryListing(BaseModel):
    items: list[AdminCategoryOut] = Field(default_factory=list)


class AdminOrderOut(BaseModel):
    code: str
    email: str
    name: str
    total: str
    currency: str
    status: str
    created_at: str
    item_count: int = 0


class AdminOrderListing(BaseModel):
    items: list[AdminOrderOut] = Field(default_factory=list)
    total: int = 0


class CrawlRequest(BaseModel):
    url: str = Field(min_length=1)


class CrawlRunOut(BaseModel):
    id: int
    url: str
    platform: str | None = None
    status: str = "pending"
    products_found: int = 0
    products_imported: int = 0
    pages_crawled: int = 0
    error: str | None = None
    started_at: str | None = None
    finished_at: str | None = None


class CrawlRunListing(BaseModel):
    items: list[CrawlRunOut] = Field(default_factory=list)
    total: int = 0
