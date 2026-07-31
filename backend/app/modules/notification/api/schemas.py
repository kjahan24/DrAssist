"""Pydantic v2 request/response schemas for the Notification module.

New — this module had no `api/` package before the REST APIs task (see
`container.py`'s scope note: it explicitly built no HTTP endpoint).
Schemas never expose a domain entity directly, and never accept
server-controlled fields (`id`, `organization_id`, `status`, `sent_at`,
`read_at`, ...) from the client — see
`docs/backend-architecture/07_security_layer.md §7` (mass-assignment
prevention).
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from app.modules.notification.domain.enums import (
    NotificationPriority,
    NotificationStatus,
    NotificationType,
)
from app.schemas.base import ORJSONModel


class NotificationResponse(ORJSONModel):
    id: UUID
    organization_id: UUID
    recipient_user_id: UUID
    notification_type: NotificationType
    title: str
    message: str
    priority: NotificationPriority
    status: NotificationStatus
    reference_type: str | None = None
    reference_id: UUID | None = None
    scheduled_at: datetime | None = None
    sent_at: datetime | None = None
    read_at: datetime | None = None
    expires_at: datetime | None = None
    metadata: dict[str, Any] | None = None


class CreateNotificationRequest(ORJSONModel):
    recipient_user_id: UUID
    notification_type: NotificationType
    title: str = Field(min_length=1, max_length=200)
    message: str = Field(min_length=1, max_length=4000)
    priority: NotificationPriority = NotificationPriority.NORMAL
    reference_type: str | None = Field(default=None, max_length=100)
    reference_id: UUID | None = None
    scheduled_at: datetime | None = None
    expires_at: datetime | None = None
    metadata: dict[str, Any] | None = None
