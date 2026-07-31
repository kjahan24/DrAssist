"""Concrete SQLAlchemy repository implementation.

`add()` is "upsert": look up the row by id, create it if missing, then
overwrite its mapped columns from the domain entity's current in-memory
state — see the identical pattern (and rationale) in
`app.modules.icd10_coding.infrastructure.repositories`.

No repository calls `session.commit()` — that is exclusively the
`UnitOfWork`'s responsibility.
"""

from collections.abc import Sequence
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

from app.infrastructure.database.query_utils import (
    apply_date_range,
    apply_equality,
    apply_full_text_search,
    apply_in_filter,
    apply_pagination,
    apply_sort,
    count_total,
    exclude_soft_deleted,
    scope_to_organization,
)
from app.modules.notification.domain.entities import Notification
from app.modules.notification.domain.enums import NotificationPriority, NotificationStatus
from app.modules.notification.domain.repositories import NotificationRepository
from app.modules.notification.infrastructure.mappers import (
    apply_notification_to_model,
    notification_to_domain,
)
from app.modules.notification.infrastructure.models import NotificationModel


class SqlAlchemyNotificationRepository(NotificationRepository):
    _SORT_COLUMNS: dict[str, InstrumentedAttribute[Any]] = {
        "created_at": NotificationModel.created_at,
        "updated_at": NotificationModel.updated_at,
        "notification_type": NotificationModel.notification_type,
        "priority": NotificationModel.priority,
        "status": NotificationModel.status,
        "scheduled_at": NotificationModel.scheduled_at,
    }

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, notification_id: UUID) -> Notification | None:
        model = await self._session.get(NotificationModel, notification_id)
        if model is None or model.deleted_at is not None:
            return None
        return notification_to_domain(model)

    async def list_by_recipient(self, recipient_user_id: UUID) -> list[Notification]:
        stmt = (
            select(NotificationModel)
            .where(
                NotificationModel.recipient_user_id == recipient_user_id,
                NotificationModel.deleted_at.is_(None),
            )
            .order_by(NotificationModel.created_at.desc())
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [notification_to_domain(model) for model in models]

    async def list_unread_by_recipient(self, recipient_user_id: UUID) -> list[Notification]:
        stmt = (
            select(NotificationModel)
            .where(
                NotificationModel.recipient_user_id == recipient_user_id,
                NotificationModel.status == NotificationStatus.DELIVERED,
                NotificationModel.deleted_at.is_(None),
            )
            .order_by(NotificationModel.created_at.desc())
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [notification_to_domain(model) for model in models]

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
        stmt = select(NotificationModel)
        stmt = scope_to_organization(stmt, NotificationModel.organization_id, organization_id)
        stmt = exclude_soft_deleted(
            stmt, NotificationModel.deleted_at, include_deleted=include_deleted
        )
        stmt = apply_equality(stmt, NotificationModel.recipient_user_id, recipient_user_id)
        stmt = apply_equality(stmt, NotificationModel.reference_type, reference_type)
        stmt = apply_equality(stmt, NotificationModel.reference_id, reference_id)
        stmt = apply_in_filter(stmt, NotificationModel.status, statuses)
        stmt = apply_in_filter(stmt, NotificationModel.priority, priorities)
        stmt = apply_date_range(
            stmt, NotificationModel.scheduled_at, start=scheduled_from, end=scheduled_to
        )
        stmt = apply_date_range(
            stmt, NotificationModel.created_at, start=created_from, end=created_to
        )
        stmt = apply_date_range(
            stmt, NotificationModel.updated_at, start=updated_from, end=updated_to
        )
        stmt = apply_full_text_search(
            stmt, [NotificationModel.title, NotificationModel.message], query
        )

        total = await count_total(self._session, stmt)
        column = self._SORT_COLUMNS.get(sort_by, NotificationModel.created_at)
        stmt = apply_sort(stmt, column, sort_order)
        stmt = apply_pagination(stmt, offset=offset, limit=limit)
        models = (await self._session.execute(stmt)).scalars().all()
        return [notification_to_domain(model) for model in models], total

    async def add(self, notification: Notification) -> None:
        model = await self._session.get(NotificationModel, notification.id)
        if model is None:
            model = NotificationModel()
            self._session.add(model)
        apply_notification_to_model(notification, model)
