"""Shared fixtures for Medical Topics module repository (integration)
tests.

Require a real, migrated PostgreSQL instance reachable via `DATABASE_URL`
(overriding the placeholder `tests/conftest.py` sets via `setdefault` —
pass a real value in the environment *before* pytest starts, e.g. via
`docker run -e DATABASE_URL=...`) — see
`docs/backend-architecture/12_testing_architecture.md`. Each test uses a
uniquely-suffixed slug/name so tests can run repeatedly against a
shared, non-torn-down database without colliding; there is deliberately
no per-test transaction-rollback wrapper, kept simple to match this
project's established verification pattern.

`db_session` builds its own engine per test rather than reusing the
process-wide `app.infrastructure.database.session.engine` singleton — see
`tests.integration.modules.organization.conftest`'s own docstring for the
full "one event loop per test function" reasoning.
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
