"""In-memory test doubles for the Audit Log module's repository, Unit of
Work, and the Authentication module's public port
(`AuditLogConsistencyService` depends on it) — each implements the exact
same interface its real counterpart does, per
`docs/backend-architecture/12_testing_architecture.md` ("fakes over mocks
as the default"). Application-layer use case/service tests depend on
these, never on a real database or another module's facade.
"""

from uuid import UUID, uuid4

from app.modules.audit_log.domain.entities import AuditLog
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
