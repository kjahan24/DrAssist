"""Authentication context middleware.

Decodes the bearer token if present and binds `(organization_id, user_id)`
into `TenantContext` for the duration of the request — it does **not**
reject unauthenticated requests (not every route requires auth: health
checks, and eventually login/register, must still work). Rejection is the
job of the `get_current_user`/`require_permission` dependencies
(`app/api/deps.py`), applied per-route. See
`docs/backend-architecture/07_security_layer.md §1` and
`05_dependency_injection_and_lifecycle.md` (middleware ordering — this
runs after `RequestIDMiddleware`/`LoggingMiddleware`, before route
dependency resolution).

A malformed or expired token here is silently ignored (context stays
unbound) rather than raising — a route that actually requires
authentication will still reject the request via its own dependency, with
a clear 401; this middleware's only job is to make tenant context
available to routes that *do* proceed.
"""

from uuid import UUID

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import get_settings
from app.core.security.jwt import InvalidTokenError, TokenType, decode_token
from app.shared.infrastructure.tenant_context import TenantContext

_BEARER_PREFIX = "Bearer "


class AuthenticationContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        organization_id: UUID | None = None
        user_id: UUID | None = None

        header = request.headers.get("Authorization")
        if header and header.startswith(_BEARER_PREFIX):
            raw_token = header.removeprefix(_BEARER_PREFIX).strip()
            settings = get_settings()
            try:
                claims = decode_token(
                    raw_token,
                    secret_key=settings.backend.secret_key,
                    algorithm=settings.jwt.algorithm,
                    expected_type=TokenType.ACCESS,
                )
                organization_id = UUID(claims.organization_id)
                user_id = UUID(claims.subject)
            except (InvalidTokenError, ValueError):
                pass  # Left unbound; a route requiring auth will reject via `get_current_user`.

        tokens = TenantContext.bind(organization_id=organization_id, user_id=user_id)
        try:
            return await call_next(request)
        finally:
            TenantContext.reset(tokens)
