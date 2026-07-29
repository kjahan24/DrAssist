"""Shared fixtures for Clinical Reasoning module repository (integration)
tests.

Require a real, migrated PostgreSQL instance reachable via `DATABASE_URL` —
see the identical fixture (and rationale for a per-test engine) in
`tests.integration.modules.organization.conftest`.
"""

from collections.abc import AsyncIterator

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

# Guarantees every module's ORM classes are registered on `Base.metadata`
# before any session is used — see the identical import in
# `app/infrastructure/database/session.py` for why this is required.
from app.infrastructure.database import models  # noqa: F401


@pytest_asyncio.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    settings = get_settings()
    engine = create_async_engine(str(settings.database.url), pool_pre_ping=True)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    try:
        async with session_factory() as session:
            yield session
    finally:
        await engine.dispose()
