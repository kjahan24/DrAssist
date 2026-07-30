"""Repository interface for the `AuditLog` entity, expressed in domain
vocabulary only (no session, no SQL). Concrete implementation lives in
`app.modules.audit_log.infrastructure.repositories`. See
`docs/backend-architecture/04_repository_and_service_patterns.md`.

Unlike every other module's repository in this codebase, there is no
`update()` method *and* `add()` is not an upsert — see `add()`'s own
docstring. There is also no `delete()` method at all. This is the
concrete mechanism behind "the repository must reject update/delete
operations": the interface makes those operations structurally
impossible to call, and the concrete implementation additionally raises
if `add()` is ever given an id that already exists, rather than silently
overwriting the way every other module's own `add()` does.
"""

from abc import ABC, abstractmethod
from uuid import UUID

from app.modules.audit_log.domain.entities import AuditLog


class AuditLogRepository(ABC):
    @abstractmethod
    async def get_by_id(self, audit_log_id: UUID) -> AuditLog | None: ...

    @abstractmethod
    async def list_for_entity(self, *, entity_type: str, entity_id: UUID) -> list[AuditLog]: ...

    @abstractmethod
    async def list_for_organization(
        self, organization_id: UUID, *, offset: int = 0, limit: int = 50
    ) -> list[AuditLog]: ...

    @abstractmethod
    async def list_for_actor(self, actor_user_id: UUID) -> list[AuditLog]: ...

    @abstractmethod
    async def add(self, audit_log: AuditLog) -> None:
        """Insert-only. Raises `AuditLogImmutableError` if a row with
        `audit_log.id` already exists — unlike every other module's own
        `add()` (look up by id, create if missing, otherwise overwrite),
        this one never overwrites."""
        ...
