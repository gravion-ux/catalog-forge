"""The FastAPI application factory."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.api.admin import router as admin_router
from app.api.orders import router as orders_router
from app.api.public import router as public_router
from app.catalog.admin_users import ensure_admin_user
from app.config import BASE_DIR, Settings, load_settings
from app.db import init_db, session
from app.errors import ApiError, api_error_handler, error_response
from app.jobs import CrawlJobs
from app.security import RateLimiter

DIST_DIR = BASE_DIR / "frontend" / "dist"


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the application. The database is created on startup."""
    resolved = settings or load_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        settings = app.state.settings
        init_db(settings.database_path)
        settings.media_dir.mkdir(parents=True, exist_ok=True)
        with session(settings.database_path) as connection:
            ensure_admin_user(
                connection, settings.admin_username, settings.admin_password
            )
        yield

    app = FastAPI(
        title="Catalog Forge",
        version=__version__,
        description=(
            "Crawl a shop's public catalog and run it as your own storefront, "
            "with an admin panel for editing the catalog and the prices."
        ),
        lifespan=lifespan,
    )
    app.state.settings = resolved
    app.state.jobs = CrawlJobs(resolved)
    app.state.login_limiter = RateLimiter(
        limit=resolved.login_rate_limit_attempts,
        window_seconds=resolved.login_rate_limit_window_seconds,
    )
    app.add_exception_handler(ApiError, api_error_handler)  # type: ignore[arg-type]
    app.include_router(public_router)
    app.include_router(orders_router)
    app.include_router(admin_router)

    app.mount(
        "/media",
        StaticFiles(directory=str(resolved.media_dir), check_dir=False),
        name="media",
    )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        messages = "; ".join(str(error.get("msg", "")) for error in exc.errors())
        return error_response(
            422, "invalid_request", messages or "The request was not valid."
        )

    if DIST_DIR.exists():
        assets = DIST_DIR / "assets"
        if assets.exists():
            app.mount("/assets", StaticFiles(directory=assets), name="assets")

        @app.get("/{full_path:path}", include_in_schema=False)
        def spa(full_path: str) -> FileResponse:
            if full_path.startswith("api/"):
                return error_response(404, "not_found", "No such endpoint.")  # type: ignore[return-value]
            candidate = DIST_DIR / full_path
            if full_path and candidate.is_file():
                return FileResponse(candidate)
            return FileResponse(DIST_DIR / "index.html")

    else:

        @app.get("/", include_in_schema=False)
        def root() -> JSONResponse:
            return JSONResponse(
                {
                    "name": "Catalog Forge",
                    "version": __version__,
                    "api": "/api/health",
                    "docs": "/docs",
                    "note": (
                        "The frontend has not been built yet. Run "
                        "`npm install && npm run build` in frontend/."
                    ),
                }
            )

    return app


_app: FastAPI | None = None


def __getattr__(name: str) -> object:
    """Build the default application on first use.

    Keeping this lazy means importing the module never touches the data
    directory, which keeps test runs clean.
    """
    if name == "app":
        global _app
        if _app is None:
            _app = create_app()
        return _app
    raise AttributeError(name)
