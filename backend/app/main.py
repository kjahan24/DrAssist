"""ASGI application factory.

This module wires together configuration, logging, middlewares, and
routers. It intentionally defines no routes itself — see
`app/api/v1/router.py` for the (currently empty) route aggregator that
future endpoint modules register against.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.middlewares.error_handler import register_exception_handlers
from app.middlewares.logging_middleware import LoggingMiddleware
from app.middlewares.request_id_middleware import RequestIDMiddleware

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage startup/shutdown of shared resources (DB engine, caches, clients).

    Concrete resource wiring belongs in `app/infrastructure/*`; this hook
    only calls into that layer's lifecycle functions once they exist.
    """
    logger.info("application_startup", environment=get_settings().environment)
    yield
    logger.info("application_shutdown")


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()

    app = FastAPI(
        title=settings.project_name,
        version=settings.api_version,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.backend.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.backend.allowed_hosts_list)
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(RequestIDMiddleware)

    register_exception_handlers(app)

    app.include_router(api_router, prefix=f"/api/{settings.api_version}")

    return app


app = create_app()
