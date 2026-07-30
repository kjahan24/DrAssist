"""SQLAlchemy ORM model for the Notification module.

One table: `notifications`. See `app.modules.notification.container` for
the module's scope note.

`organization_id` carries a real foreign key to `organizations.id`
(`ON DELETE RESTRICT`, matching every other module's own treatment of
that column). `recipient_user_id` carries a real foreign key to
`users.id` (`ON DELETE CASCADE` — a notification has no purpose once its
recipient account is gone, the same treatment `appointments.patient_id`
receives for an analogous "this record is meaningless without its
subject" relationship).

`reference_id` carries **no** foreign key: it is a polymorphic pointer
whose target table varies by `reference_type` (a free-form nullable
string, not a closed enum — see `domain/entities.py` and
`application/services/notification_consistency_service.py` for why no
enum is defined and no existence check is performed against it). This
differs from `patient_history.reference_id`, which is likewise
FK-less but *is* existence-validated at the application layer against a
closed set of `reference_type`s — no such validation exists here because
no closed set was specified for this task.

`metadata` is the first JSONB column outside the Organization module
(`organizations.working_hours`/`feature_flags`/`ai_settings`). The
Python/ORM attribute is named `notification_metadata`, not `metadata`,
because `Base.metadata` (SQLAlchemy's `MetaData` instance) already
occupies that name on every declarative model; the actual database
column is still named `metadata` via the explicit column-name argument
below — only the ORM-level Python attribute differs. The domain entity's
own field is named `metadata` (a plain dataclass, not a `Base` subclass,
so no such collision exists there) — `infrastructure/mappers.py` is the
only place that bridges the two names.

There is no `CHECK` constraint for "valid status transitions", "Read
notifications cannot become unread", "Expired notifications cannot be
sent", or "Cancelled notifications cannot be delivered": a `CHECK`
constraint can only see this table's own row, never the *previous* value
of `status`, so all four are enforced exclusively at the application
layer (`Notification._transition_to`, see `domain/entities.py`).
"Scheduled time must not be after expiration time" *is* expressible as a
same-row `CHECK` (both columns live on this table), so it gets one in
addition to `Notification.__post_init__`'s own validation — the same
defense-in-depth precedent `appointments.end_time`/`start_time` already
establishes.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import (
    AuditActorMixin,
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    pg_enum,
)
from app.modules.notification.domain.enums import (
    NotificationPriority,
    NotificationStatus,
    NotificationType,
)

_notification_type_enum = pg_enum(NotificationType, "notification_type_enum")
_notification_priority_enum = pg_enum(NotificationPriority, "notification_priority_enum")
_notification_status_enum = pg_enum(NotificationStatus, "notification_status_enum")


class NotificationModel(
    Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, AuditActorMixin
):
    __tablename__ = "notifications"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    recipient_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    notification_type: Mapped[NotificationType] = mapped_column(
        _notification_type_enum, nullable=False
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[NotificationPriority] = mapped_column(
        _notification_priority_enum, nullable=False
    )
    status: Mapped[NotificationStatus] = mapped_column(_notification_status_enum, nullable=False)
    reference_type: Mapped[str | None] = mapped_column(Text, default=None)
    reference_id: Mapped[uuid.UUID | None] = mapped_column(default=None)
    scheduled_at: Mapped[datetime | None] = mapped_column(default=None)
    sent_at: Mapped[datetime | None] = mapped_column(default=None)
    read_at: Mapped[datetime | None] = mapped_column(default=None)
    expires_at: Mapped[datetime | None] = mapped_column(default=None)
    notification_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSONB, default=None
    )

    __table_args__ = (
        Index("ix_notifications_organization_id", "organization_id"),
        Index("ix_notifications_recipient_user_id", "recipient_user_id"),
        Index("ix_notifications_recipient_user_id_status", "recipient_user_id", "status"),
        Index("ix_notifications_reference_type_reference_id", "reference_type", "reference_id"),
        CheckConstraint(
            "scheduled_at IS NULL OR expires_at IS NULL OR scheduled_at <= expires_at",
            name="scheduled_at_before_expires_at",
        ),
    )
