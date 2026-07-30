"""The Notification module's public port — the only contract another
module may depend on. See
`docs/backend-architecture/03_module_architecture.md` and
`10_module_communication.md`.

Never import from `app.modules.notification.domain`, `.application`
(beyond this package), or `.infrastructure` from outside this module —
this file and `dto.py` are the entire allowed surface today. This port
is the contract every future notification-aware consumer (a future
Email/SMS/Push delivery-channel integration, WebSocket, Mobile Apps,
Family/Caregiver Access, or an AI Reminder System) is expected to depend
on to read a recipient's notifications — the same shape
`app.modules.appointment.public.interfaces.AppointmentQueryPort` already
establishes for its own place under Patient/Doctor.
"""

from abc import ABC, abstractmethod
from uuid import UUID

from app.modules.notification.public.dto import NotificationSummaryDTO


class NotificationQueryPort(ABC):
    @abstractmethod
    async def notification_exists(self, notification_id: UUID) -> bool: ...

    @abstractmethod
    async def get_notification_summary(
        self, notification_id: UUID
    ) -> NotificationSummaryDTO | None: ...

    @abstractmethod
    async def list_notifications_for_recipient(
        self, recipient_user_id: UUID
    ) -> list[NotificationSummaryDTO]: ...

    @abstractmethod
    async def list_unread_notifications_for_recipient(
        self, recipient_user_id: UUID
    ) -> list[NotificationSummaryDTO]: ...
