"""Async SQLAlchemy engine and session factory.

`async_session_factory` is the single place a database session is
constructed; everything else (FastAPI dependency, Celery tasks, scripts)
should obtain a session through it rather than creating engines ad hoc.
"""

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings

# Importing the aggregator (not any one module's models directly) guarantees
# every module's ORM classes are registered on `Base.metadata` before this
# session factory is ever used — required so cross-module foreign keys (e.g.
# every module's `created_by`/`updated_by` -> `users.id`) can be resolved at
# mapper-configuration time. Without this, a process that only ever imports
# one module's `infrastructure.repositories` (any test or script that
# doesn't happen to also import the Authentication module first) hits
# `sqlalchemy.exc.NoReferencedTableError` the moment it flushes a row with
# such a foreign key — confirmed against a real Postgres instance while
# building the Organization module's repository tests.
from app.infrastructure.database import models  # noqa: F401

settings = get_settings()

engine: AsyncEngine = create_async_engine(
    str(settings.database.url),
    echo=settings.database.echo,
    pool_size=settings.database.pool_size,
    max_overflow=settings.database.max_overflow,
    pool_pre_ping=True,
)

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)
