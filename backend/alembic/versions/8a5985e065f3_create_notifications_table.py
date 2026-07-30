"""create notifications table

Creates the Notification module's foundation schema: `notifications`.

`organization_id` references `organizations.id` (`ON DELETE RESTRICT`,
matching every other module's own treatment of that column).
`recipient_user_id` references `users.id` (`ON DELETE CASCADE` — a
notification has no purpose once its recipient account is gone, the same
treatment `appointments.patient_id` receives for an analogous "this
record is meaningless without its subject" relationship). Neither table
is modified by this migration.

`reference_id` carries no foreign key — it is a polymorphic pointer
whose target table varies by `reference_type` (a free-form nullable
text column, not a Postgres enum: no closed set of valid values was
specified for this task — see `app.modules.notification.domain.entities`
for the full reasoning). No existence check is performed against it at
any layer.

`metadata` is a nullable JSONB column. The ORM's Python attribute is
named `notification_metadata` (see
`app.modules.notification.infrastructure.models` for why), but the
actual database column created here is named `metadata`, matching the
domain entity's own field name.

"Scheduled time must not be after expiration time" has a `CHECK`
constraint (defense-in-depth alongside
`Notification.__post_init__`'s own validation), the same treatment
`appointments.start_time`/`end_time` already receives for an analogous
same-row ordering invariant.

There is no `CHECK` constraint for "valid status transitions", "Read
notifications cannot become unread", "Expired notifications cannot be
sent", or "Cancelled notifications cannot be delivered": a `CHECK`
constraint can only see this table's own row, never the *previous* value
of `status`, so all four are enforced exclusively at the application
layer.

Revision ID: 8a5985e065f3
Revises: 0dc952d8d776
Create Date: 2026-07-30

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "8a5985e065f3"
down_revision: str | None = "0dc952d8d776"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TIMESTAMPTZ = sa.DateTime(timezone=True)
_NOW = sa.text("now()")


def _audit_columns() -> list[sa.Column]:
    """The five standard columns every soft-deletable table in this schema
    carries, minus `id` (added separately since its type/default is
    identical everywhere but declared first). See
    `docs/database/00_overview.md`.
    """
    return [
        sa.Column("created_at", _TIMESTAMPTZ, nullable=False, server_default=_NOW),
        sa.Column("updated_at", _TIMESTAMPTZ, nullable=False, server_default=_NOW),
        sa.Column("deleted_at", _TIMESTAMPTZ, nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
    ]


def _audit_fks(table: str) -> list[sa.ForeignKeyConstraint]:
    return [
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name=f"fk_{table}_created_by_users", ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"], ["users.id"], name=f"fk_{table}_updated_by_users", ondelete="SET NULL"
        ),
    ]


def upgrade() -> None:
    notification_type_enum = postgresql.ENUM(
        "appointment_reminder",
        "appointment_confirmed",
        "appointment_cancelled",
        "visit_completed",
        "prescription_ready",
        "lab_result_ready",
        "general",
        "system",
        name="notification_type_enum",
        create_type=False,
    )
    notification_type_enum.create(op.get_bind(), checkfirst=True)

    notification_priority_enum = postgresql.ENUM(
        "low",
        "normal",
        "high",
        "critical",
        name="notification_priority_enum",
        create_type=False,
    )
    notification_priority_enum.create(op.get_bind(), checkfirst=True)

    notification_status_enum = postgresql.ENUM(
        "pending",
        "scheduled",
        "sent",
        "delivered",
        "read",
        "cancelled",
        "expired",
        name="notification_status_enum",
        create_type=False,
    )
    notification_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("recipient_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("notification_type", notification_type_enum, nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("priority", notification_priority_enum, nullable=False),
        sa.Column("status", notification_status_enum, nullable=False),
        sa.Column("reference_type", sa.Text(), nullable=True),
        sa.Column("reference_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("scheduled_at", _TIMESTAMPTZ, nullable=True),
        sa.Column("sent_at", _TIMESTAMPTZ, nullable=True),
        sa.Column("read_at", _TIMESTAMPTZ, nullable=True),
        sa.Column("expires_at", _TIMESTAMPTZ, nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("id", name="pk_notifications"),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_notifications_organization_id_organizations",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["recipient_user_id"],
            ["users.id"],
            name="fk_notifications_recipient_user_id_users",
            ondelete="CASCADE",
        ),
        *_audit_fks("notifications"),
        sa.CheckConstraint(
            "scheduled_at IS NULL OR expires_at IS NULL OR scheduled_at <= expires_at",
            name="scheduled_at_before_expires_at",
        ),
    )
    op.create_index("ix_notifications_organization_id", "notifications", ["organization_id"])
    op.create_index("ix_notifications_recipient_user_id", "notifications", ["recipient_user_id"])
    op.create_index(
        "ix_notifications_recipient_user_id_status",
        "notifications",
        ["recipient_user_id", "status"],
    )
    op.create_index(
        "ix_notifications_reference_type_reference_id",
        "notifications",
        ["reference_type", "reference_id"],
    )


def downgrade() -> None:
    op.drop_table("notifications")

    postgresql.ENUM(name="notification_status_enum").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="notification_priority_enum").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="notification_type_enum").drop(op.get_bind(), checkfirst=True)
