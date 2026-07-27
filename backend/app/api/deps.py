"""Shared FastAPI dependency callables.

Kept separate from `app/infrastructure/database/session.py` so endpoint
modules only ever import from this one place, regardless of which
concrete infrastructure backs a dependency.
"""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.session import async_session_factory


async def get_db_session() -> AsyncIterator[AsyncSession]:
    async with async_session_factory() as session:
        yield session


async def get_current_user() -> None:
    """Resolve the authenticated principal from the incoming request.

    Placeholder dependency — no auth scheme is wired up yet. Replace the
    body with real token verification once `app/core/security.py` is
    implemented, and update the return type accordingly.
    """
    raise NotImplementedError
