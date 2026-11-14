"""Public storefront API. No authentication, no admin surface."""

from __future__ import annotations

from fastapi import APIRouter, Query, Request

from app import __version__
from app.catalog.categories import list_categories
from app.catalog.images import images_for
from app.catalog.products import (
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    get_product_by_slug,
    list_products,
)
from app.db import session
from app.errors import ApiError
from app.schemas import (
    CategoriesOut,
    CategoryOut,
    ImageOut,
    ProductDetail,
    ProductListing,
    ProductOut,
)

router = APIRouter(prefix="/api", tags=["public"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@router.get("/categories", response_model=CategoriesOut)
def categories(request: Request) -> CategoriesOut:
    settings = request.app.state.settings
    with session(settings.database_path) as connection:
        summaries = list_categories(connection)
    return CategoriesOut(
        items=[
            CategoryOut(
                id=summary.id,
                slug=summary.slug,
                name=summary.name,
                product_count=summary.product_count,
            )
            for summary in summaries
        ]
    )


@router.get("/products", response_model=ProductListing)
def products(
    request: Request,
    category: str | None = Query(default=None),
    q: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
) -> ProductListing:
    settings = request.app.state.settings
    with session(settings.database_path) as connection:
        found, total = list_products(
            connection,
            category_slug=category,
            search=q,
            page=page,
            page_size=page_size,
        )
        items = []
        for product in found:
            images = images_for(connection, product.id)
            items.append(
                ProductOut(
                    id=product.id,
                    slug=product.slug,
                    title=product.title,
                    price=product.price,
                    compare_at_price=product.compare_at_price,
                    currency=product.currency,
                    stock=product.stock,
                    vendor=product.vendor,
                    image=images[0].local_path if images else None,
                )
            )

    pages = (total + page_size - 1) // page_size if page_size else 0
    return ProductListing(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/products/{slug}", response_model=ProductDetail)
def product_detail(request: Request, slug: str) -> ProductDetail:
    settings = request.app.state.settings
    with session(settings.database_path) as connection:
        product = get_product_by_slug(connection, slug)
        if product is None or product.status != "active":
            raise ApiError(404, "not_found", f"No product named {slug}.")
        images = images_for(connection, product.id)
        from app.catalog.products import category_ids_for
        from app.catalog.categories import get_category

        category_rows = [
            get_category(connection, category_id)
            for category_id in category_ids_for(connection, product.id)
        ]
        category_items = [
            CategoryOut(id=item.id, slug=item.slug, name=item.name)
            for item in category_rows
            if item is not None
        ]

    return ProductDetail(
        id=product.id,
        slug=product.slug,
        title=product.title,
        price=product.price,
        compare_at_price=product.compare_at_price,
        currency=product.currency,
        stock=product.stock,
        vendor=product.vendor,
        image=images[0].local_path if images else None,
        description=product.description,
        sku=product.sku,
        source_url=product.source_url,
        source_platform=product.source_platform,
        source_price=product.source_price,
        source_fetched_at=product.source_fetched_at,
        price_manually_edited=product.price_manually_edited,
        attributes=product.attributes,
        images=[
            ImageOut(
                id=image.id,
                local_path=image.local_path,
                remote_url=image.remote_url,
                alt=image.alt,
                position=image.position,
            )
            for image in images
        ],
        categories=category_items,
    )
