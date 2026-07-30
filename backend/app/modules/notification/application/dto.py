"""Data Transfer Objects for the Notification module's application layer.

Distinct from both domain entities (never leave the module) and API
schemas (this task builds no HTTP endpoint — see `container.py`'s scope
note).

`CreateNotificationInput` deliberately has no `organization_id` field —
see `domain/entities.py` for why it is always derived from the
recipient's own `User`. It also has no `status` field — a new
notification's starting status is always derived from whether
`scheduled_at` is given (see `Notification.create`). `created_by`
mirrors the same not-yet-consumed audit field
`app.modules.appointment.application.dto.CreateAppointmentInput` and
`app.modules.schedule.application.dto.CreateDoctorScheduleInput` already
carry — kept for consistency, not read by `CreateNotification` today.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from app.modules.notification.domain.enums import (
    NotificationPriority,
    NotificationStatus,
    NotificationType,
)

# --- CreateNotification -----------------------------------------------------


@dataclass(frozen=True, slots=True)
class CreateNotificationInput:
    recipient_user_id: UUID
    notification_type: NotificationType
    title: str
    message: str
    priority: NotificationPriority
    reference_type: str | None = None
    reference_id: UUID | None = None
    scheduled_at: datetime | None = None
    expires_at: datetime | None = None
    metadata: dict[str, Any] | None = None
    created_by: UUID | None = None


@dataclass(frozen=True, slots=True)
class CreateNotificationOutput:
    notification_id: UUID
    organization_id: UUID
    status: NotificationStatus


# --- Status workflow transitions --------------------------------------------


@dataclass(frozen=True, slots=True)
class MarkNotificationSentInput:
    notification_id: UUID


@dataclass(frozen=True, slots=True)
class MarkNotificationDeliveredInput:
    notification_id: UUID


@dataclass(frozen=True, slots=True)
class MarkNotificationReadInput:
    notification_id: UUID


@dataclass(frozen=True, slots=True)
class CancelNotificationInput:
    notification_id: UUID


@dataclass(frozen=True, slots=True)
class ExpireNotificationInput:
    notification_id: UUID


@dataclass(frozen=True, slots=True)
class NotificationStatusOutput:
    notification_id: UUID
    status: NotificationStatus


# --- Cross-cutting read model (also re-exported via public/dto.py) --------


@dataclass(frozen=True, slots=True)
class NotificationSummaryDTO:
    notification_id: UUID
    organization_id: UUID
    recipient_user_id: UUID
    notification_type: NotificationType
    title: str
    message: str
    priority: NotificationPriority
    status: NotificationStatus
    reference_type: str | None
    reference_id: UUID | None
    scheduled_at: datetime | None
    sent_at: datetime | None
    read_at: datetime | None
    expires_at: datetime | None
    metadata: dict[str, Any] | None
