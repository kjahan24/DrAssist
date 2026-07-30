"""Domain exceptions for the Notification module.

Each names the invariant it protects, not the eventual HTTP outcome — see
`docs/backend-architecture/06_configuration_logging_exceptions.md`.

`RecipientNotFoundError` is defined locally rather than reused from
`app.modules.authentication` — the same situation every prior
child-document module documents: Authentication exposes no "not found"
error a peer module is allowed to import, so a module that *references*
an existing row by id defines the exception locally (see
`app.modules.appointment.domain.exceptions.PatientNotFoundError` for the
identical precedent).
"""

from uuid import UUID

from app.shared.domain.exceptions import DomainError


class RecipientNotFoundError(DomainError):
    def __init__(self, recipient_user_id: UUID) -> None:
        super().__init__(f"no user found with id {recipient_user_id}")
        self.recipient_user_id = recipient_user_id


class NotificationNotFoundError(DomainError):
    def __init__(self, notification_id: UUID) -> None:
        super().__init__(f"no notification found with id {notification_id}")
        self.notification_id = notification_id


class NotificationTitleRequiredError(DomainError):
    def __init__(self) -> None:
        super().__init__("title must not be blank")


class NotificationMessageRequiredError(DomainError):
    def __init__(self) -> None:
        super().__init__("message must not be blank")


class InvalidNotificationReferenceError(DomainError):
    def __init__(self) -> None:
        super().__init__("reference_type and reference_id must both be set or both be omitted")


class InvalidNotificationScheduleError(DomainError):
    def __init__(self) -> None:
        super().__init__("scheduled_at must not be after expires_at")


class NotificationExpiredError(DomainError):
    def __init__(self, notification_id: UUID) -> None:
        super().__init__(f"notification {notification_id} has expired and cannot be sent")
        self.notification_id = notification_id


class InvalidNotificationStatusTransitionError(DomainError):
    def __init__(self, current_status: str, target_status: str) -> None:
        super().__init__(f"cannot transition notification from {current_status} to {target_status}")
        self.current_status = current_status
        self.target_status = target_status
