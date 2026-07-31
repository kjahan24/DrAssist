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
from collections.abc import Sequence
from datetime import datetime
from typing import Literal
from uuid import UUID

from app.modules.audit_log.domain.entities import AuditLog
from app.modules.audit_log.domain.enums import AuditAction, AuditSource


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
    async def search(
        self,
        *,
        organization_id: UUID,
        query: str | None = None,
        actions: Sequence[AuditAction] | None = None,
        sources: Sequence[AuditSource] | None = None,
        entity_type: str | None = None,
        entity_id: UUID | None = None,
        actor_user_id: UUID | None = None,
        correlation_id: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        sort_by: str = "created_at",
        sort_order: Literal["asc", "desc"] = "desc",
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[AuditLog], int]:
        """Search & Filtering module: organization-scoped search over
        audit logs — always filters by `organization_id` at the SQL layer
        (unlike `list_for_entity`/`list_for_actor`, which take no
        organization filter at all and rely on their caller to
        post-filter defensively; see
        `app.modules.audit_log.api.router`'s own docstring for that
        history). No `include_deleted`/`updated_*` parameters — audit
        logs have neither column (immutable, insert-only; see this
        module's own `add()` docstring). `query` is a partial (`ILIKE`)
        match across `entity_type`/`correlation_id`/`request_id` — there
        is no free-text prose column on this table for genuine full-text
        search. Returns `(page_of_audit_logs,
        total_matching_count)`."""
        ...

    @abstractmethod
    async def add(self, audit_log: AuditLog) -> None:
        """Insert-only. Raises `AuditLogImmutableError` if a row with
        `audit_log.id` already exists — unlike every other module's own
        `add()` (look up by id, create if missing, otherwise overwrite),
        this one never overwrites."""
        ...
