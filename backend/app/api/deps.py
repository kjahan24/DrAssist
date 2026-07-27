"""Shared FastAPI dependency callables.

Kept separate from `app/infrastructure/database/session.py` so endpoint
modules only ever import from this one place, regardless of which
concrete infrastructure backs a dependency. `get_current_user` and
`require_permission` are the "Authorization dependencies" for the whole
app — they live here, not in `app/core/security/`, because they need to
call the Authentication module's public facade, and `app/core/` may never
import from `app/modules/*` (see
`docs/backend-architecture/11_standards_and_conventions.md`). This is a
deliberate correction of `docs/backend-architecture/07_security_layer.md`,
which originally (and incorrectly, per that same document set's own
layering rule) placed this dependency inside `core/security/permissions.py`.
"""

from collections.abc import AsyncIterator, Callable, Coroutine
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.infrastructure.database.session import async_session_factory
from app.modules.authentication.application.dto import AuthenticatedPrincipalDTO
from app.modules.authentication.application.exceptions import AuthenticationError
from app.modules.authentication.container import build_authentication_facade
from app.modules.authentication.public.facade import AuthenticationFacade

_BEARER_PREFIX = "Bearer "


async def get_db_session() -> AsyncIterator[AsyncSession]:
    async with async_session_factory() as session:
        yield session


DbSession = Annotated[AsyncSession, Depends(get_db_session)]


async def get_authentication_facade(session: DbSession) -> AuthenticationFacade:
    return build_authentication_facade(session)


AuthFacade = Annotated[AuthenticationFacade, Depends(get_authentication_facade)]


def _extract_bearer_token(request: Request) -> str:
    header = request.headers.get("Authorization")
    if not header or not header.startswith(_BEARER_PREFIX):
        raise UnauthorizedError("missing or malformed Authorization header")
    return header.removeprefix(_BEARER_PREFIX).strip()


async def get_current_user(request: Request, facade: AuthFacade) -> AuthenticatedPrincipalDTO:
    """Resolve the calling request's authenticated principal from its bearer token.

    This *validates an already-issued token* — it does not authenticate
    credentials (no login flow exists yet; see
    `app.modules.authentication.container` for what this module's current
    scope deliberately excludes).
    """
    raw_token = _extract_bearer_token(request)
    try:
        return await facade.get_authenticated_principal(raw_token)
    except AuthenticationError as exc:
        raise UnauthorizedError(str(exc)) from exc


CurrentUser = Annotated[AuthenticatedPrincipalDTO, Depends(get_current_user)]


def require_permission(
    permission_code: str,
) -> Callable[[AuthenticatedPrincipalDTO], Coroutine[None, None, AuthenticatedPrincipalDTO]]:
    """Dependency factory: `Depends(require_permission("patients.write"))`.

    Resolves the current user first (so an unauthenticated request gets a
    401, not a 403) and then checks the specific permission, so a caller
    that fails only the permission check gets a clear 403.
    """

    async def _check(principal: CurrentUser) -> AuthenticatedPrincipalDTO:
        if permission_code not in principal.permissions:
            raise ForbiddenError(f"missing required permission: {permission_code}")
        return principal

    return _check
