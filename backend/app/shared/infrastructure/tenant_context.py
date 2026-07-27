"""Per-request tenant/identity context, via `contextvars`.

Bound once per request by `AuthenticationContextMiddleware`
(`app/middlewares/authentication_middleware.py`) from the verified JWT —
never from client-supplied request data. Read by repositories (and, once
Row-Level Security is wired up alongside the Organization module, by the
session-scoped `SET LOCAL app.current_organization_id` statement). See
`docs/backend-architecture/07_security_layer.md §3`.
"""

from contextvars import ContextVar, Token
from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class TenantContextTokens:
    organization_id_token: Token[UUID | None]
    user_id_token: Token[UUID | None]


_current_organization_id: ContextVar[UUID | None] = ContextVar(
    "current_organization_id", default=None
)
_current_user_id: ContextVar[UUID | None] = ContextVar("current_user_id", default=None)


class TenantContext:
    @staticmethod
    def bind(*, organization_id: UUID | None, user_id: UUID | None) -> TenantContextTokens:
        return TenantContextTokens(
            organization_id_token=_current_organization_id.set(organization_id),
            user_id_token=_current_user_id.set(user_id),
        )

    @staticmethod
    def reset(tokens: TenantContextTokens) -> None:
        _current_organization_id.reset(tokens.organization_id_token)
        _current_user_id.reset(tokens.user_id_token)

    @staticmethod
    def get_organization_id() -> UUID | None:
        return _current_organization_id.get()

    @staticmethod
    def get_user_id() -> UUID | None:
        return _current_user_id.get()
