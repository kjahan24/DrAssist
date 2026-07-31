"""In-memory test doubles for the Audit Log module's repository, Unit of
Work, and the Authentication module's public port
(`AuditLogConsistencyService` depends on it) — each implements the exact
same interface its real counterpart does, per
`docs/backend-architecture/12_testing_architecture.md` ("fakes over mocks
as the default"). Application-layer use case/service tests depend on
these, never on a real database or another module's facade.
"""

from collections.abc import Sequence
from datetime import datetime
from typing import Literal
from uuid import UUID, uuid4

from app.modules.audit_log.domain.entities import AuditLog
from app.modules.audit_log.domain.enums import AuditAction, AuditSource
from app.modules.audit_log.domain.exceptions import AuditLogImmutableError
from app.modules.audit_log.domain.repositories import AuditLogRepository
from app.modules.authentication.application.dto import UserSummaryDTO
from app.modules.authentication.domain.enums import UserStatus
from app.modules.authentication.public.interfaces import UserQueryPort
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.domain.domain_event import DomainEvent


class FakeAuditLogRepository(AuditLogRepository):
    def __init__(self) -> None:
        self._audit_logs: dict[UUID, AuditLog] = {}

    async def get_by_id(self, audit_log_id: UUID) -> AuditLog | None:
        return self._audit_logs.get(audit_log_id)

    async def list_for_entity(self, *, entity_type: str, entity_id: UUID) -> list[AuditLog]:
        matches = [
            a
            for a in self._audit_logs.values()
            if a.entity_type == entity_type and a.entity_id == entity_id
        ]
        return sorted(matches, key=lambda a: a.created_at, reverse=True)

    async def list_for_organization(
        self, organization_id: UUID, *, offset: int = 0, limit: int = 50
    ) -> list[AuditLog]:
        matches = [a for a in self._audit_logs.values() if a.organization_id == organization_id]
        matches.sort(key=lambda a: a.created_at, reverse=True)
        return matches[offset : offset + limit]

    async def list_for_actor(self, actor_user_id: UUID) -> list[AuditLog]:
        matches = [a for a in self._audit_logs.values() if a.actor_user_id == actor_user_id]
        return sorted(matches, key=lambda a: a.created_at, reverse=True)

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
        matches = [a for a in self._audit_logs.values() if a.organization_id == organization_id]
        if actions:
            matches = [a for a in matches if a.action in actions]
        if sources:
            matches = [a for a in matches if a.source in sources]
        if entity_type is not None:
            matches = [a for a in matches if a.entity_type == entity_type]
        if entity_id is not None:
            matches = [a for a in matches if a.entity_id == entity_id]
        if actor_user_id is not None:
            matches = [a for a in matches if a.actor_user_id == actor_user_id]
        if correlation_id is not None:
            matches = [a for a in matches if a.correlation_id == correlation_id]
        if created_from is not None:
            matches = [a for a in matches if a.created_at >= created_from]
        if created_to is not None:
            matches = [a for a in matches if a.created_at <= created_to]
        if query:
            term = query.strip().lower()

            def _matches_query(a: AuditLog) -> bool:
                fields = (a.entity_type, a.correlation_id, a.request_id)
                return any(f is not None and term in f.lower() for f in fields)

            matches = [a for a in matches if _matches_query(a)]
        matches.sort(key=lambda a: getattr(a, sort_by, None) or "", reverse=sort_order == "desc")
        total = len(matches)
        return matches[offset : offset + limit], total

    async def add(self, audit_log: AuditLog) -> None:
        if audit_log.id in self._audit_logs:
            raise AuditLogImmutableError(audit_log.id)
        self._audit_logs[audit_log.id] = audit_log


class FakeUnitOfWork(UnitOfWork):
    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False
        self.published_events: list[DomainEvent] = []
        self._pending_events: list[DomainEvent] = []

    def collect_events(self, events: list[DomainEvent]) -> None:
        self._pending_events.extend(events)

    async def commit(self) -> None:
        self.committed = True
        self.published_events.extend(self._pending_events)
        self._pending_events = []

    async def rollback(self) -> None:
        self.rolled_back = True
        self._pending_events = []

    async def flush(self) -> None:
        pass


class FakeUserQueryPort(UserQueryPort):
    def __init__(self, *, existing_users: dict[UUID, UserSummaryDTO] | None = None) -> None:
        self.existing_users = existing_users or {}

    async def user_exists(self, user_id: UUID) -> bool:
        return user_id in self.existing_users

    async def get_user_summary(self, user_id: UUID) -> UserSummaryDTO | None:
        return self.existing_users.get(user_id)


def make_user_summary(**overrides: object) -> UserSummaryDTO:
    defaults: dict[str, object] = {
        "user_id": uuid4(),
        "organization_id": uuid4(),
        "email": "actor@example.com",
        "first_name": "Ada",
        "last_name": "Actor",
        "status": UserStatus.ACTIVE,
    }
    defaults.update(overrides)
    return UserSummaryDTO(**defaults)  # type: ignore[arg-type]
