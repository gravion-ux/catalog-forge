"""The admin API: one user, one session, and a CSRF token on every change.

Nothing here is linked from the storefront. The session lives in an HttpOnly
cookie, the CSRF token is derived from that session, and every write checks
both before it touches the catalog.
"""

from __future__ import annotations

import time
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Query, Request, Response

from app.catalog.admin_users import find_admin_user
from app.catalog.categories import get_category, list_categories, slugify
from app.catalog.crawls import (
    count_crawl_runs,
    get_crawl_run,
    list_crawl_runs,
)
from app.catalog.images import images_for, media_url
from app.catalog.orders import list_orders
from app.catalog.products import (
    category_ids_for,
    get_product,
    list_admin_products,
    product_ids_for_bulk,
    replace_product_images,
    set_product_categories,
    update_product_fields,
    variants_for,
)
from app.crawler.importer import set_price
from app.db import session
from app.errors import ApiError
from app.money import format_money, to_decimal
from app.schemas import (
    AdminCategoryListing,
    AdminCategoryOut,
    AdminImageOut,
    AdminOrderListing,
    AdminOrderOut,
    AdminProductDetail,
    AdminProductListing,
    AdminProductOut,
    BulkPriceRequest,
    BulkPriceResult,
    CategoryCreate,
    CategoryPatch,
    CrawlRequest,
    CrawlRunListing,
    CrawlRunOut,
    LoginRequest,
    PriceChangeOut,
    PricePatch,
    ProductPatch,
    SessionOut,
    VariantOut,
)
from app.security import (
    check_csrf,
    create_session_token,
    csrf_token,
    verify_password,
    verify_session_token,
)

router = APIRouter(prefix="/api/admin", tags=["admin"])

SESSION_COOKIE = "cf_admin"
CSRF_HEADER = "X-CSRF-Token"
ALLOWED_STATUSES = ("active", "hidden", "draft")


def _client_key(request: Request) -> str:
    """The key the login rate limiter counts attempts by."""
    client = request.client
    return client.host if client else "unknown"


def _session_token(request: Request) -> str:
    return request.cookies.get(SESSION_COOKIE, "")


def _require_session(request: Request) -> tuple[str, str]:
    """The username and the session token of the current admin, or a 401."""
    token = _session_token(request)
    settings = request.app.state.settings
    if not token:
        raise ApiError(401, "unauthorized", "You need to log in first.")
    username = verify_session_token(token, settings.secret_key)
    if username is None:
        raise ApiError(401, "unauthorized", "Your session has expired.")
    return username, token


def _require_csrf(request: Request, token: str) -> None:
    """Refuse a change that does not carry the CSRF token of this session."""
    settings = request.app.state.settings
    supplied = request.headers.get(CSRF_HEADER, "")
    if not check_csrf(token, supplied, settings.secret_key):
        raise ApiError(
            403, "forbidden", "The request was missing a valid CSRF token."
        )


@router.post("/login", response_model=SessionOut)
def login(request: Request, payload: LoginRequest, response: Response) -> SessionOut:
    """Log in and start an admin session."""
    settings = request.app.state.settings
    limiter = request.app.state.login_limiter
    key = _client_key(request)

    if limiter.blocked(key):
        raise ApiError(
            429,
            "rate_limited",
            "Too many login attempts. Wait a little and try again.",
        )

    username = payload.username.strip()
    with session(settings.database_path) as connection:
        stored = find_admin_user(connection, username)

    accepted = stored is not None and verify_password(
        payload.password, stored[0], stored[1]
    )
    if not accepted:
        limiter.allow(key)
        raise ApiError(401, "unauthorized", "That username and password do not match.")

    expires_at = int(time.time()) + settings.session_max_age_seconds
    token = create_session_token(username, settings.secret_key, expires_at)
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=settings.session_max_age_seconds,
        httponly=True,
        samesite="lax",
        path="/",
    )
    return SessionOut(username=username, csrf_token=csrf_token(token, settings.secret_key))


@router.post("/logout")
def logout(request: Request, response: Response) -> dict[str, bool]:
    """End the admin session."""
    _, token = _require_session(request)
    _require_csrf(request, token)
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"ok": True}


@router.get("/session", response_model=SessionOut)
def session_info(request: Request) -> SessionOut:
    """Who is logged in, and the CSRF token of this session."""
    username, _ = _require_session(request)
    settings = request.app.state.settings
    return SessionOut(
        username=username,
        csrf_token=csrf_token(_session_token(request), settings.secret_key),
    )


@router.get("/products", response_model=AdminProductListing)
def products(
    request: Request,
    q: str | None = Query(default=None),
    status: str | None = Query(default=None),
    category_id: int | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=24, ge=1, le=200),
) -> AdminProductListing:
    """Every product, hidden ones included."""
    _require_session(request)
    settings = request.app.state.settings
    with session(settings.database_path) as connection:
        found, total = list_admin_products(
            connection,
            search=q,
            status=status,
            category_id=category_id,
            page=page,
            page_size=page_size,
        )
        items = [_product_out(connection, product) for product in found]

    pages = (total + page_size - 1) // page_size if page_size else 0
    return AdminProductListing(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/products/{product_id}", response_model=AdminProductDetail)
def product_detail(request: Request, product_id: int) -> AdminProductDetail:
    """One product, with everything the editor needs."""
    _require_session(request)
    settings = request.app.state.settings
    with session(settings.database_path) as connection:
        product = get_product(connection, product_id)
        if product is None:
            raise ApiError(404, "not_found", "No such product.")
        return _product_detail(connection, product)


@router.patch("/products/{product_id}", response_model=AdminProductDetail)
def patch_product(
    request: Request, product_id: int, payload: ProductPatch
) -> AdminProductDetail:
    """Edit a product. The price goes through the price history."""
    _, token = _require_session(request)
    _require_csrf(request, token)
    settings = request.app.state.settings

    with session(settings.database_path) as connection:
        product = get_product(connection, product_id)
        if product is None:
            raise ApiError(404, "not_found", "No such product.")

        fields = payload.model_dump(
            exclude_unset=True, exclude={"price", "category_ids", "images"}
        )
        if fields.get("status") is not None and fields["status"] not in ALLOWED_STATUSES:
            raise ApiError(
                422, "invalid_request", "The status must be active, hidden or draft."
            )
        if fields.get("stock") is not None:
            fields["stock"] = max(0, int(fields["stock"]))

        update_product_fields(connection, product_id, fields)

        if payload.price is not None:
            set_price(connection, product_id, payload.price, source="admin")
        if payload.category_ids is not None:
            set_product_categories(connection, product_id, payload.category_ids)
        if payload.images is not None:
            replace_product_images(connection, product_id, payload.images)

    return product_detail(request, product_id)


@router.patch("/products/{product_id}/price", response_model=AdminProductDetail)
def patch_price(
    request: Request, product_id: int, payload: PricePatch
) -> AdminProductDetail:
    """Set the price of a product by hand."""
    _, token = _require_session(request)
    _require_csrf(request, token)
    settings = request.app.state.settings

    with session(settings.database_path) as connection:
        product = get_product(connection, product_id)
        if product is None:
            raise ApiError(404, "not_found", "No such product.")
        if payload.price is None and payload.compare_at_price is None:
            raise ApiError(422, "invalid_request", "Give a price to set.")
        if payload.price is not None:
            set_price(connection, product_id, payload.price, source="admin")
        if payload.compare_at_price is not None:
            update_product_fields(
                connection,
                product_id,
                {"compare_at_price": format_money(payload.compare_at_price)},
            )

    return product_detail(request, product_id)


@router.post("/products/bulk-price", response_model=BulkPriceResult)
def bulk_price(request: Request, payload: BulkPriceRequest) -> BulkPriceResult:
    """Change the price of many products at once.

    ``markup`` reads the value as a percentage (``10`` means ten percent),
    unless it is written as a factor between one and two (``1.10`` means
    multiply by 1.10). ``delta`` adds the value, ``set`` replaces the price.
    """
    _, token = _require_session(request)
    _require_csrf(request, token)
    settings = request.app.state.settings

    mode = payload.mode.strip().lower()
    if mode not in {"markup", "delta", "set"}:
        raise ApiError(422, "invalid_request", "The mode must be markup, delta or set.")

    text = str(payload.value).strip().replace("%", "").replace(",", "")
    try:
        value = Decimal(text)
    except (InvalidOperation, ValueError):
        raise ApiError(422, "invalid_request", "The value must be a number.")

    unit = (payload.unit or "").strip().lower()
    factor: Decimal | None = None
    if mode == "markup":
        if unit == "factor":
            factor = value
        elif unit == "percent":
            factor = Decimal(1) + value / Decimal(100)
        elif "." in text and Decimal(1) < value < Decimal(2):
            factor = value
        else:
            factor = Decimal(1) + value / Decimal(100)

    changes: list[PriceChangeOut] = []
    with session(settings.database_path) as connection:
        product_ids = product_ids_for_bulk(
            connection,
            product_ids=payload.product_ids,
            category_id=payload.category_id,
        )
        for product_id in product_ids:
            product = get_product(connection, product_id)
            if product is None:
                continue
            old_price = to_decimal(product.price)
            if mode == "set":
                new_price = value
            elif mode == "delta":
                new_price = old_price + value
            else:
                new_price = old_price * (factor or Decimal(1))
            if new_price < 0:
                new_price = Decimal(0)
            change = set_price(
                connection, product_id, format_money(new_price), source="admin"
            )
            changes.append(
                PriceChangeOut(
                    id=change.id,
                    old_price=change.old_price,
                    new_price=change.new_price,
                    source=change.source,
                    changed_at=change.changed_at,
                )
            )

    return BulkPriceResult(
        mode=mode,
        value=payload.value,
        factor=format_money(factor) if factor is not None else None,
        updated=len(changes),
        products=changes,
    )


@router.get("/categories", response_model=AdminCategoryListing)
def categories(request: Request) -> AdminCategoryListing:
    """Every category."""
    _require_session(request)
    settings = request.app.state.settings
    with session(settings.database_path) as connection:
        summaries = list_categories(connection)
        items = []
        for summary in summaries:
            row = get_category(connection, summary.id)
            items.append(
                AdminCategoryOut(
                    id=summary.id,
                    slug=summary.slug,
                    name=summary.name,
                    parent_id=row.parent_id if row else None,
                    position=row.position if row else 0,
                    product_count=summary.product_count,
                )
            )
    return AdminCategoryListing(items=items)


@router.post("/categories", response_model=AdminCategoryOut, status_code=201)
def create_category(
    request: Request, payload: CategoryCreate
) -> AdminCategoryOut:
    """Create a category."""
    _, token = _require_session(request)
    _require_csrf(request, token)
    settings = request.app.state.settings

    name = payload.name.strip()
    if not name:
        raise ApiError(422, "invalid_request", "The category needs a name.")

    with session(settings.database_path) as connection:
        if payload.parent_id is not None and get_category(
            connection, payload.parent_id
        ) is None:
            raise ApiError(422, "invalid_request", "No such parent category.")

        slug = slugify(name)
        existing = connection.execute(
            "SELECT id FROM categories WHERE slug = ?", (slug,)
        ).fetchone()
        if existing is not None:
            raise ApiError(409, "conflict", "A category with that name already exists.")

        cursor = connection.execute(
            "INSERT INTO categories (slug, name, parent_id, created_at)"
            " VALUES (?, ?, ?, ?)",
            (slug, name, payload.parent_id, _now()),
        )
        connection.commit()
        category_id = int(cursor.lastrowid)

    return AdminCategoryOut(
        id=category_id, slug=slug, name=name, parent_id=payload.parent_id
    )


@router.patch("/categories/{category_id}", response_model=AdminCategoryOut)
def patch_category(
    request: Request, category_id: int, payload: CategoryPatch
) -> AdminCategoryOut:
    """Rename a category or move it under another one."""
    _, token = _require_session(request)
    _require_csrf(request, token)
    settings = request.app.state.settings

    with session(settings.database_path) as connection:
        category = get_category(connection, category_id)
        if category is None:
            raise ApiError(404, "not_found", "No such category.")

        name = category.name
        slug = category.slug
        if payload.name is not None:
            name = payload.name.strip()
            if not name:
                raise ApiError(422, "invalid_request", "The category needs a name.")
            slug = slugify(name)
            taken = connection.execute(
                "SELECT id FROM categories WHERE slug = ? AND id != ?",
                (slug, category_id),
            ).fetchone()
            if taken is not None:
                raise ApiError(
                    409, "conflict", "A category with that name already exists."
                )
            connection.execute(
                "UPDATE categories SET name = ?, slug = ? WHERE id = ?",
                (name, slug, category_id),
            )

        if payload.parent_id is not None:
            if payload.parent_id == category_id:
                raise ApiError(422, "invalid_request", "A category cannot be its own parent.")
            if get_category(connection, payload.parent_id) is None:
                raise ApiError(422, "invalid_request", "No such parent category.")
            connection.execute(
                "UPDATE categories SET parent_id = ? WHERE id = ?",
                (payload.parent_id, category_id),
            )

        if payload.position is not None:
            connection.execute(
                "UPDATE categories SET position = ? WHERE id = ?",
                (payload.position, category_id),
            )

        connection.commit()
        updated = get_category(connection, category_id)

    if updated is None:
        raise ApiError(404, "not_found", "No such category.")
    return AdminCategoryOut(
        id=updated.id,
        slug=updated.slug,
        name=updated.name,
        parent_id=updated.parent_id,
        position=updated.position,
    )


@router.get("/orders", response_model=AdminOrderListing)
def orders(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
) -> AdminOrderListing:
    """Every order, newest first."""
    _require_session(request)
    settings = request.app.state.settings
    with session(settings.database_path) as connection:
        found, total = list_orders(connection, page=page, page_size=page_size)
    return AdminOrderListing(
        items=[
            AdminOrderOut(
                code=order.code,
                email=order.email,
                name=order.name,
                total=order.total,
                currency=order.currency,
                status=order.status,
                created_at=order.created_at,
                item_count=order.item_count,
            )
            for order in found
        ],
        total=total,
    )


@router.post("/crawls", response_model=CrawlRunOut, status_code=202)
async def start_crawl(request: Request, payload: CrawlRequest) -> CrawlRunOut:
    """Start a crawl in the background."""
    _, token = _require_session(request)
    _require_csrf(request, token)

    url = payload.url.strip()
    if not url.startswith(("http://", "https://")):
        raise ApiError(
            422, "invalid_request", "The address must be an http or https URL."
        )

    jobs = request.app.state.jobs
    run_id = await jobs.start(url)

    settings = request.app.state.settings
    with session(settings.database_path) as connection:
        run = get_crawl_run(connection, run_id)
    if run is None:
        raise ApiError(404, "not_found", "The crawl did not start.")
    return _crawl_out(run)


@router.get("/crawls", response_model=CrawlRunListing)
def crawls(request: Request) -> CrawlRunListing:
    """The crawl runs so far."""
    _require_session(request)
    settings = request.app.state.settings
    with session(settings.database_path) as connection:
        runs = list_crawl_runs(connection)
        total = count_crawl_runs(connection)
    return CrawlRunListing(items=[_crawl_out(run) for run in runs], total=total)


@router.get("/crawls/{run_id}", response_model=CrawlRunOut)
def crawl_detail(request: Request, run_id: int) -> CrawlRunOut:
    """The progress of one crawl."""
    _require_session(request)
    settings = request.app.state.settings
    with session(settings.database_path) as connection:
        run = get_crawl_run(connection, run_id)
    if run is None:
        raise ApiError(404, "not_found", "No such crawl run.")
    return _crawl_out(run)


def _product_out(connection, product) -> AdminProductOut:
    """The admin view of one product."""
    images = images_for(connection, product.id)
    source_changed = bool(
        product.price_manually_edited
        and product.source_price
        and product.source_price != product.price
    )
    return AdminProductOut(
        id=product.id,
        slug=product.slug,
        title=product.title,
        price=product.price,
        source_price=product.source_price,
        source_price_changed=source_changed,
        price_manually_edited=product.price_manually_edited,
        compare_at_price=product.compare_at_price,
        currency=product.currency,
        stock=product.stock,
        vendor=product.vendor,
        sku=product.sku,
        status=product.status,
        image=media_url(images[0].local_path) if images else None,
        source_url=product.source_url,
        source_platform=product.source_platform,
        source_fetched_at=product.source_fetched_at,
        updated_at=product.updated_at,
    )


def _product_detail(connection, product) -> AdminProductDetail:
    """The admin view of one product, with everything else it carries."""
    base = _product_out(connection, product)
    images = images_for(connection, product.id)
    categories = [
        get_category(connection, category_id)
        for category_id in category_ids_for(connection, product.id)
    ]
    variants = variants_for(connection, product.id)

    return AdminProductDetail(
        **base.model_dump(),
        description=product.description,
        attributes=product.attributes,
        images=[
            AdminImageOut(
                id=image.id,
                local_path=image.local_path,
                remote_url=image.remote_url,
                alt=image.alt,
                position=image.position,
            )
            for image in images
        ],
        categories=[
            AdminCategoryOut(
                id=category.id,
                slug=category.slug,
                name=category.name,
                parent_id=category.parent_id,
                position=category.position,
            )
            for category in categories
            if category is not None
        ],
        variants=[
            VariantOut(
                id=variant.id,
                title=variant.title,
                sku=variant.sku,
                price=variant.price,
                compare_at_price=variant.compare_at_price,
                stock=variant.stock,
                options=variant.options,
            )
            for variant in variants
        ],
    )


def _crawl_out(run) -> CrawlRunOut:
    return CrawlRunOut(
        id=run.id,
        url=run.url,
        platform=run.platform,
        status=run.status,
        products_found=run.products_found,
        products_imported=run.products_imported,
        pages_crawled=run.pages_crawled,
        error=run.error,
        started_at=run.started_at,
        finished_at=run.finished_at,
    )


def _now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat(timespec="seconds")
