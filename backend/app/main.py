from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from urllib.parse import urlsplit

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy import Engine

from app.config import Settings, get_settings
from app.db import create_db_engine, create_session_factory
from app.deps import SAFE_METHODS
from app.routers import admin, auth, capsules, me


def _utc_now() -> datetime:
    return datetime.now(UTC)


def create_app(
    settings: Settings | None = None,
    engine: Engine | None = None,
    clock: Callable[[], datetime] | None = None,
) -> FastAPI:
    """Application factory. Run with: uvicorn app.main:create_app --factory"""
    settings = settings or get_settings()
    engine = engine or create_db_engine(settings.database_url)
    dev = settings.env == "development"

    app = FastAPI(
        title="birthday-savepoint",
        docs_url="/docs" if dev else None,
        redoc_url=None,
        openapi_url="/openapi.json" if dev else None,
    )
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = create_session_factory(engine)
    app.state.clock = clock or _utc_now

    @app.middleware("http")
    async def guard_and_harden(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if request.method not in SAFE_METHODS:
            origin = request.headers.get("origin")
            if origin is not None and not _origin_allowed(origin, request, settings):
                return JSONResponse(status_code=403, content={"detail": "Forbidden"})
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
            response.headers["Content-Security-Policy"] = (
                "default-src 'none'; frame-ancestors 'none'"
            )
        return response

    @app.get("/api/health", tags=["meta"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(auth.router)
    app.include_router(me.router)
    app.include_router(capsules.router)
    app.include_router(admin.router)
    return app


def _origin_allowed(origin: str, request: Request, settings: Settings) -> bool:
    """Browsers send Origin on cross-site and state-changing requests. Accept the site's own
    origin (matching Host) and explicitly configured origins; reject everything else."""
    if origin in settings.allowed_origins:
        return True
    return urlsplit(origin).netloc == request.headers.get("host")
