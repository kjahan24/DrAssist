"""Repository interface for the `Notification` aggregate, expressed in
domain vocabulary only (no session, no SQL). Concrete implementation
lives in `app.modules.notification.infrastructure.repositories`. See
`docs/backend-architecture/04_repository_and_service_patterns.md`.

No `update()` method: a repository returns the actual aggregate object,
the caller mutates it via its own methods, and the Unit of Work's
`commit()` persists the change through SQLAlchemy's session-level change
tracking.
"""

from abc import ABC, abstractmethod
from uuid import UUID

from app.modules.notification.domain.entities import Notification


class NotificationRepository(ABC):
    @abstractmethod
    async def get_by_id(self, notification_id: UUID) -> Notification | None: ...

    @abstractmethod
    async def list_by_recipient(self, recipient_user_id: UUID) -> list[Notification]: ...

    @abstractmethod
    async def list_unread_by_recipient(self, recipient_user_id: UUID) -> list[Notification]: ...

    @abstractmethod
    async def add(self, notification: Notification) -> None: ...
