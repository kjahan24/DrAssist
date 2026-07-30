"""In-memory test doubles for the Notification module's repository, Unit
of Work, and the Authentication module's public port
(`NotificationConsistencyService` depends on it) — each implements the
exact same interface its real counterpart does, per
`docs/backend-architecture/12_testing_architecture.md` ("fakes over mocks
as the default"). Application-layer use case/service tests depend on
these, never on a real database or another module's facade.
"""

from uuid import UUID, uuid4

from app.modules.authentication.application.dto import UserSummaryDTO
from app.modules.authentication.domain.enums import UserStatus
from app.modules.authentication.public.interfaces import UserQueryPort
from app.modules.notification.domain.entities import Notification
from app.modules.notification.domain.enums import NotificationStatus
from app.modules.notification.domain.repositories import NotificationRepository
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.domain.domain_event import DomainEvent


class FakeNotificationRepository(NotificationRepository):
    def __init__(self) -> None:
        self._notifications: dict[UUID, Notification] = {}

    async def get_by_id(self, notification_id: UUID) -> Notification | None:
        return self._notifications.get(notification_id)

    async def list_by_recipient(self, recipient_user_id: UUID) -> list[Notification]:
        matches = [
            n for n in self._notifications.values() if n.recipient_user_id == recipient_user_id
        ]
        return sorted(matches, key=lambda n: n.created_at, reverse=True)

    async def list_unread_by_recipient(self, recipient_user_id: UUID) -> list[Notification]:
        matches = [
            n
            for n in self._notifications.values()
            if n.recipient_user_id == recipient_user_id and n.status is NotificationStatus.DELIVERED
        ]
        return sorted(matches, key=lambda n: n.created_at, reverse=True)

    async def add(self, notification: Notification) -> None:
        self._notifications[notification.id] = notification


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
        "email": "patient@example.com",
        "first_name": "Jane",
        "last_name": "Doe",
        "status": UserStatus.ACTIVE,
    }
    defaults.update(overrides)
    return UserSummaryDTO(**defaults)  # type: ignore[arg-type]
