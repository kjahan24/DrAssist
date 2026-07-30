"""Concrete SQLAlchemy repository implementation.

`add()` is "upsert": look up the row by id, create it if missing, then
overwrite its mapped columns from the domain entity's current in-memory
state — see the identical pattern (and rationale) in
`app.modules.icd10_coding.infrastructure.repositories`.

No repository calls `session.commit()` — that is exclusively the
`UnitOfWork`'s responsibility.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.notification.domain.entities import Notification
from app.modules.notification.domain.enums import NotificationStatus
from app.modules.notification.domain.repositories import NotificationRepository
from app.modules.notification.infrastructure.mappers import (
    apply_notification_to_model,
    notification_to_domain,
)
from app.modules.notification.infrastructure.models import NotificationModel


class SqlAlchemyNotificationRepository(NotificationRepository):
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

    async def add(self, notification: Notification) -> None:
        model = await self._session.get(NotificationModel, notification.id)
        if model is None:
            model = NotificationModel()
            self._session.add(model)
        apply_notification_to_model(notification, model)
