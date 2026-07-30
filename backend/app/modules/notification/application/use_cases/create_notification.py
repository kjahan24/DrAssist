"""`CreateNotification` — resolves `organization_id` from the recipient
`User` via `NotificationConsistencyService
.resolve_organization_for_recipient()`, which is what makes "every
notification belongs to one organization" true by construction and
"recipient existence" a real runtime check — see `domain/entities.py` for
why `organization_id` is never independently trusted input.
"""

from app.modules.notification.application.dto import (
    CreateNotificationInput,
    CreateNotificationOutput,
)
from app.modules.notification.application.services.notification_consistency_service import (
    NotificationConsistencyService,
)
from app.modules.notification.domain.entities import Notification
from app.modules.notification.domain.repositories import NotificationRepository
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class CreateNotification(UseCase[CreateNotificationInput, CreateNotificationOutput]):
    def __init__(
        self,
        *,
        notification_repository: NotificationRepository,
        consistency_service: NotificationConsistencyService,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._notifications = notification_repository
        self._consistency = consistency_service
        self._uow = unit_of_work

    async def execute(self, input_dto: CreateNotificationInput) -> CreateNotificationOutput:
        organization_id = await self._consistency.resolve_organization_for_recipient(
            input_dto.recipient_user_id
        )

        notification = Notification.create(
            organization_id=organization_id,
            recipient_user_id=input_dto.recipient_user_id,
            notification_type=input_dto.notification_type,
            title=input_dto.title,
            message=input_dto.message,
            priority=input_dto.priority,
            reference_type=input_dto.reference_type,
            reference_id=input_dto.reference_id,
            scheduled_at=input_dto.scheduled_at,
            expires_at=input_dto.expires_at,
            metadata=input_dto.metadata,
        )
        await self._notifications.add(notification)
        self._uow.collect_events(notification.pull_events())
        await self._uow.commit()

        return CreateNotificationOutput(
            notification_id=notification.id,
            organization_id=notification.organization_id,
            status=notification.status,
        )
