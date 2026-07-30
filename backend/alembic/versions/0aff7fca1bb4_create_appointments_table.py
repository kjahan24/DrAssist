"""create appointments table

Creates the Appointment foundation schema: appointments.

`organization_id` references `organizations.id`, `patient_id`
references `patients.id`, `doctor_id` references `doctors.id`,
`booked_by_user_id` (nullable) references `users.id`, and `visit_id`
(nullable) references `patient_visits.id` (all chained before this
migration) — this is why this migration's `down_revision` chains after
the Patient History migration, not a modification to any prior module's
tables. No column is added to, or constraint changed on,
`organizations`/`patients`/`doctors`/`users`/`patient_visits`/any other
prior table here.

`patient_id` uses `ON DELETE CASCADE`, matching every prior module's own
choice for that column. `organization_id`/`doctor_id` use `ON DELETE
RESTRICT`, matching every other module's treatment of those two columns.
`booked_by_user_id` uses `ON DELETE SET NULL`, the same treatment
`created_by`/`updated_by` already receive. `visit_id` also uses `ON
DELETE SET NULL`: it is an optional cross-reference to a peer document
("one completed appointment *may optionally* create one Visit"), not an
ownership relationship — see `AppointmentModel`'s own comment for the
full reasoning.

"Appointment number must be globally unique" is enforced by a plain
(non-composite) partial unique index on `appointment_number WHERE
deleted_at IS NULL`. "Appointment end_time must be later than start_time"
is additionally enforced as a `CHECK` constraint (defense-in-depth
alongside `Appointment.__post_init__`), the same treatment
`doctor_schedules.start_time`/`end_time` already receives.

There is no `CHECK` constraint for "valid status transitions",
"Completed/NoShow become immutable", or "Patient and Doctor must belong
to the same Organization" — all three require reading either the
*previous* value of a column or another table's data, neither of which a
`CHECK` constraint can do, so both are enforced exclusively at the
application layer.

Revision ID: 0aff7fca1bb4
Revises: 2de01f040eb8
Create Date: 2026-07-30

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0aff7fca1bb4"
down_revision: str | None = "2de01f040eb8"
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
    appointment_type_enum = postgresql.ENUM(
        "consultation",
        "follow_up",
        "emergency",
        "telemedicine",
        "procedure",
        name="appointment_type_enum",
        create_type=False,
    )
    appointment_type_enum.create(op.get_bind(), checkfirst=True)

    appointment_status_enum = postgresql.ENUM(
        "scheduled",
        "confirmed",
        "checked_in",
        "in_progress",
        "completed",
        "cancelled",
        "no_show",
        name="appointment_status_enum",
        create_type=False,
    )
    appointment_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "appointments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("doctor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("appointment_number", sa.Text(), nullable=False),
        sa.Column("appointment_date", sa.Date(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("appointment_type", appointment_type_enum, nullable=False),
        sa.Column("status", appointment_status_enum, nullable=False),
        sa.Column("reason_for_visit", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("booked_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("visit_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("checked_in_at", _TIMESTAMPTZ, nullable=True),
        sa.Column("completed_at", _TIMESTAMPTZ, nullable=True),
        sa.Column("cancelled_at", _TIMESTAMPTZ, nullable=True),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("id", name="pk_appointments"),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_appointments_organization_id_organizations",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patients.id"],
            name="fk_appointments_patient_id_patients",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["doctor_id"],
            ["doctors.id"],
            name="fk_appointments_doctor_id_doctors",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["booked_by_user_id"],
            ["users.id"],
            name="fk_appointments_booked_by_user_id_users",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["visit_id"],
            ["patient_visits.id"],
            name="fk_appointments_visit_id_patient_visits",
            ondelete="SET NULL",
        ),
        *_audit_fks("appointments"),
        sa.CheckConstraint("end_time > start_time", name="end_time_after_start_time"),
    )
    op.create_index(
        "uq_appointments_appointment_number",
        "appointments",
        ["appointment_number"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index("ix_appointments_organization_id", "appointments", ["organization_id"])
    op.create_index("ix_appointments_patient_id", "appointments", ["patient_id"])
    op.create_index("ix_appointments_doctor_id", "appointments", ["doctor_id"])
    op.create_index(
        "ix_appointments_doctor_id_appointment_date",
        "appointments",
        ["doctor_id", "appointment_date"],
    )
    op.create_index("ix_appointments_visit_id", "appointments", ["visit_id"])
    op.create_index("ix_appointments_booked_by_user_id", "appointments", ["booked_by_user_id"])


def downgrade() -> None:
    op.drop_table("appointments")

    postgresql.ENUM(name="appointment_status_enum").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="appointment_type_enum").drop(op.get_bind(), checkfirst=True)
