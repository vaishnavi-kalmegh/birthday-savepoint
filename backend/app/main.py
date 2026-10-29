from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from . import config
from .db import Base, engine
from .routers import admin, auth, capsules, health

prod = config.ENVIRONMENT == "production"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Development convenience only. Production requires migrations before deployment.
    if not prod:
        Base.metadata.create_all(engine)
    yield


app = FastAPI(
    title="birthday-savepoint",
    docs_url=None if prod else "/docs",
    redoc_url=None,
    openapi_url=None if prod else "/openapi.json",
    lifespan=lifespan,
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    return response


app.include_router(health.router)
app.include_router(auth.router)
app.include_router(capsules.router)
app.include_router(admin.router)
