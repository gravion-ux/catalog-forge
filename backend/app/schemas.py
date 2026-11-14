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
