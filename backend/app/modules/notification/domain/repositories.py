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
from collections.abc import Sequence
from datetime import datetime
from typing import Literal
from uuid import UUID

from app.modules.notification.domain.entities import Notification
from app.modules.notification.domain.enums import NotificationPriority, NotificationStatus


class NotificationRepository(ABC):
    @abstractmethod
    async def get_by_id(self, notification_id: UUID) -> Notification | None: ...

    @abstractmethod
    async def list_by_recipient(self, recipient_user_id: UUID) -> list[Notification]: ...

    @abstractmethod
    async def list_unread_by_recipient(self, recipient_user_id: UUID) -> list[Notification]: ...

    @abstractmethod
    async def search(
        self,
        *,
        organization_id: UUID,
        query: str | None = None,
        statuses: Sequence[NotificationStatus] | None = None,
        priorities: Sequence[NotificationPriority] | None = None,
        recipient_user_id: UUID | None = None,
        reference_type: str | None = None,
        reference_id: UUID | None = None,
        scheduled_from: datetime | None = None,
        scheduled_to: datetime | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        updated_from: datetime | None = None,
        updated_to: datetime | None = None,
        include_deleted: bool = False,
        sort_by: str = "created_at",
        sort_order: Literal["asc", "desc"] = "desc",
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[Notification], int]:
        """Search & Filtering module: organization-scoped search over
        notifications — `query` is a full-text match over `title`/
        `message`; `reference_type` is an exact match (free-form, not an
        enum — see `NotificationModel.reference_type`) paired with
        `reference_id` for exact-match polymorphic lookups. This method's
        own `sort_order` default is `"desc"`, matching every existing
        `list_*` method here (`created_at.desc()`) — but the search
        endpoint (`app.modules.notification.api.router.search_notifications`)
        always forwards the caller's `SortParams.sort_order`, which
        defaults to `"asc"` like every other module's search endpoint, so
        this default only takes effect for callers that omit the argument
        entirely (e.g. a future non-HTTP caller). Returns
        `(page_of_notifications, total_matching_count)`."""
        ...

    @abstractmethod
    async def add(self, notification: Notification) -> None: ...
