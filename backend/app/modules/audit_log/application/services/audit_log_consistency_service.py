"""`AuditLogConsistencyService` — enforces "Organization consistency"
for the one optional cross-module reference `AuditLog` carries:
`actor_user_id`.

This is the module's "domain service" in spirit — logic that spans more
than one aggregate and isn't naturally owned by `AuditLog` itself — but
it lives in the *application* layer, not `domain/`, because it requires
I/O (reading the Authentication module's public port). The domain layer
in this codebase never performs I/O (see every prior module's
`domain/entities.py`), so a literal `domain/services` package would
violate that boundary — the same reasoning
`app.modules.notification.application.services
.notification_consistency_service.NotificationConsistencyService`
already documents for its own identically-shaped situation.

Unlike `NotificationConsistencyService` (which *derives*
`organization_id` from its always-required recipient), this service only
*validates* an already-supplied `organization_id` against the actor's
own — `actor_user_id` is nullable ("actor_user_id may be null for
system-generated events"), so it cannot be the single source
`organization_id` is derived from; see `application/dto.py` for the full
reasoning. When `actor_user_id` is `None`, there is nothing to validate
against, so `validate_actor_organization` is a no-op.
"""

from uuid import UUID

from app.modules.audit_log.domain.exceptions import (
    ActorNotFoundError,
    ActorOrganizationMismatchError,
)
from app.modules.authentication.public.interfaces import UserQueryPort


class AuditLogConsistencyService:
    def __init__(self, *, user_query_port: UserQueryPort) -> None:
        self._users = user_query_port

    async def validate_actor_organization(
        self, *, actor_user_id: UUID | None, organization_id: UUID
    ) -> None:
        if actor_user_id is None:
            return

        user_summary = await self._users.get_user_summary(actor_user_id)
        if user_summary is None:
            raise ActorNotFoundError(actor_user_id)

        if user_summary.organization_id != organization_id:
            raise ActorOrganizationMismatchError(actor_user_id, organization_id)
