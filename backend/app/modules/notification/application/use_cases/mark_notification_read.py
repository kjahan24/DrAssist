"""`MarkNotificationRead` (Delivered -> Read) —
`Notification.mark_read()` also stamps `read_at`. `Read` is terminal (see
`domain/entities.py`), which is what enforces "Read notifications cannot
become unread"."""

from app.modules.notification.application.dto import (
    MarkNotificationReadInput,
    NotificationStatusOutput,
)
from app.modules.notification.domain.exceptions import NotificationNotFoundError
from app.modules.notification.domain.repositories import NotificationRepository
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class MarkNotificationRead(UseCase[MarkNotificationReadInput, NotificationStatusOutput]):
    def __init__(
        self, *, notification_repository: NotificationRepository, unit_of_work: UnitOfWork
    ) -> None:
        self._notifications = notification_repository
        self._uow = unit_of_work

    async def execute(self, input_dto: MarkNotificationReadInput) -> NotificationStatusOutput:
        notification = await self._notifications.get_by_id(input_dto.notification_id)
        if notification is None:
            raise NotificationNotFoundError(input_dto.notification_id)

        notification.mark_read()
        await self._notifications.add(notification)
        self._uow.collect_events(notification.pull_events())
        await self._uow.commit()

        return NotificationStatusOutput(notification_id=notification.id, status=notification.status)
