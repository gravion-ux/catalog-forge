"""Domain objects and the mappers that turn database rows into them."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from typing import Any


def _loads(raw: str | None, fallback: Any) -> Any:
    if not raw:
        return fallback
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return fallback


@dataclass
class Variant:
    id: int
    product_id: int
    title: str = ""
    sku: str | None = None
    price: str = "0.00"
    compare_at_price: str | None = None
    stock: int = 0
    options: dict[str, Any] = field(default_factory=dict)
    position: int = 0

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Variant":
        return cls(
            id=row["id"],
            product_id=row["product_id"],
            title=row["title"] or "",
            sku=row["sku"],
            price=row["price"],
            compare_at_price=row["compare_at_price"],
            stock=row["stock"],
            options=_loads(row["options"], {}),
            position=row["position"],
        )


@dataclass
class Product:
    id: int
    slug: str
    title: str
    description: str = ""
    vendor: str | None = None
    sku: str | None = None
    price: str = "0.00"
    compare_at_price: str | None = None
    currency: str = "USD"
    stock: int = 0
    status: str = "active"
    source_url: str | None = None
    source_platform: str | None = None
    source_price: str | None = None
    source_fetched_at: str | None = None
    price_manually_edited: bool = False
    attributes: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Product":
        return cls(
            id=row["id"],
            slug=row["slug"],
            title=row["title"],
            description=row["description"] or "",
            vendor=row["vendor"],
            sku=row["sku"],
            price=row["price"],
            compare_at_price=row["compare_at_price"],
            currency=row["currency"],
            stock=row["stock"],
            status=row["status"],
            source_url=row["source_url"],
            source_platform=row["source_platform"],
            source_price=row["source_price"],
            source_fetched_at=row["source_fetched_at"],
            price_manually_edited=bool(row["price_manually_edited"]),
            attributes=_loads(row["attributes"], {}),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


@dataclass
class Category:
    id: int
    slug: str
    name: str
    parent_id: int | None = None
    position: int = 0
    created_at: str = ""

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Category":
        return cls(
            id=row["id"],
            slug=row["slug"],
            name=row["name"],
            parent_id=row["parent_id"],
            position=row["position"],
            created_at=row["created_at"],
        )


@dataclass
class ProductImage:
    id: int
    product_id: int
    local_path: str | None = None
    remote_url: str | None = None
    width: int | None = None
    height: int | None = None
    alt: str | None = None
    position: int = 0
    content_hash: str | None = None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "ProductImage":
        return cls(
            id=row["id"],
            product_id=row["product_id"],
            local_path=row["local_path"],
            remote_url=row["remote_url"],
            width=row["width"],
            height=row["height"],
            alt=row["alt"],
            position=row["position"],
            content_hash=row["content_hash"],
        )


@dataclass
class OrderItem:
    id: int
    order_id: int
    product_id: int | None
    title: str
    unit_price: str
    quantity: int

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "OrderItem":
        return cls(
            id=row["id"],
            order_id=row["order_id"],
            product_id=row["product_id"],
            title=row["title"],
            unit_price=row["unit_price"],
            quantity=row["quantity"],
        )


@dataclass
class Order:
    id: int
    code: str
    email: str
    name: str
    address: dict[str, Any] = field(default_factory=dict)
    subtotal: str = "0.00"
    shipping: str = "0.00"
    discount: str = "0.00"
    total: str = "0.00"
    currency: str = "USD"
    status: str = "placed"
    created_at: str = ""
    items: list[OrderItem] = field(default_factory=list)

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Order":
        return cls(
            id=row["id"],
            code=row["code"],
            email=row["email"],
            name=row["name"],
            address=_loads(row["address"], {}),
            subtotal=row["subtotal"],
            shipping=row["shipping"],
            discount=row["discount"],
            total=row["total"],
            currency=row["currency"],
            status=row["status"],
            created_at=row["created_at"],
        )


@dataclass
class CrawlRun:
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

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "CrawlRun":
        return cls(
            id=row["id"],
            url=row["url"],
            platform=row["platform"],
            status=row["status"],
            products_found=row["products_found"],
            products_imported=row["products_imported"],
            pages_crawled=row["pages_crawled"],
            error=row["error"],
            started_at=row["started_at"],
            finished_at=row["finished_at"],
        )


@dataclass
class PriceChange:
    id: int
    product_id: int
    old_price: str
    new_price: str
    source: str = "admin"
    changed_at: str = ""

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "PriceChange":
        return cls(
            id=row["id"],
            product_id=row["product_id"],
            old_price=row["old_price"],
            new_price=row["new_price"],
            source=row["source"],
            changed_at=row["changed_at"],
        )
