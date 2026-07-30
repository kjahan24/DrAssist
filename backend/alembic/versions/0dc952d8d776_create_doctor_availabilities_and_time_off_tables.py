"""create doctor availabilities and time off tables

Creates the Schedule/Availability foundation schema:
doctor_availabilities, doctor_time_off_periods.

`organization_id`/`doctor_id` reference `organizations.id`/`doctors.id`
(both chained before this migration) — this is why this migration's
`down_revision` chains after the Appointment migration, not a
modification to any prior module's tables. No column is added to, or
constraint changed on, `organizations`/`doctors`/any other prior
table here — **in particular, the pre-existing `doctor_schedules` table
(from `b5b8105d18b8_create_doctor_tables`) is untouched**: this
migration's `doctor_availabilities` table is a deliberately
separately-named table for a materially different, newly-specified
`DoctorSchedule` concept (adds `organization_id`/
`slot_duration_minutes`, which `doctor_schedules` has no column for) —
see `DoctorScheduleModel`'s own comment and
`app.modules.schedule.container`'s scope note for the full discussion of
this pre-existing naming collision, which this migration does not
attempt to resolve.

`organization_id`/`doctor_id` use `ON DELETE RESTRICT` on both tables,
matching every other module's own treatment of those two columns.

"End time must be later than start time" has a `CHECK` constraint on
both tables (defense-in-depth alongside each entity's own
`__post_init__` validation), the same treatment
`doctor_schedules.start_time`/`end_time` and
`appointments.start_time`/`end_time` already receive. "Slot duration
must be greater than zero" has its own `CHECK` constraint on
`doctor_availabilities`.

There is no `CHECK`/exclusion constraint for "no overlapping
schedules"/"no overlapping time-off periods", or "Doctor and
Organization must match" — the first two are cross-row invariants (and,
following the same precedent `doctor_schedules` itself already sets, no
Postgres `EXCLUDE` constraint is used either), and the third requires
reading another table's data; a `CHECK` constraint can do neither, so
all three are enforced exclusively at the application layer.

Revision ID: 0dc952d8d776
Revises: 0aff7fca1bb4
Create Date: 2026-07-30

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0dc952d8d776"
down_revision: str | None = "0aff7fca1bb4"
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
    weekday_enum = postgresql.ENUM(
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
        name="doctor_availability_weekday_enum",
        create_type=False,
    )
    weekday_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "doctor_availabilities",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("doctor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("weekday", weekday_enum, nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("slot_duration_minutes", sa.SmallInteger(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("id", name="pk_doctor_availabilities"),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_doctor_availabilities_organization_id_organizations",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["doctor_id"],
            ["doctors.id"],
            name="fk_doctor_availabilities_doctor_id_doctors",
            ondelete="RESTRICT",
        ),
        *_audit_fks("doctor_availabilities"),
        sa.CheckConstraint("end_time > start_time", name="end_time_after_start_time"),
        sa.CheckConstraint("slot_duration_minutes > 0", name="slot_duration_positive"),
    )
    op.create_index(
        "ix_doctor_availabilities_organization_id", "doctor_availabilities", ["organization_id"]
    )
    op.create_index("ix_doctor_availabilities_doctor_id", "doctor_availabilities", ["doctor_id"])
    op.create_index(
        "ix_doctor_availabilities_doctor_id_weekday",
        "doctor_availabilities",
        ["doctor_id", "weekday"],
    )

    op.create_table(
        "doctor_time_off_periods",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("doctor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("start_datetime", _TIMESTAMPTZ, nullable=False),
        sa.Column("end_datetime", _TIMESTAMPTZ, nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("id", name="pk_doctor_time_off_periods"),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_doctor_time_off_periods_organization_id_organizations",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["doctor_id"],
            ["doctors.id"],
            name="fk_doctor_time_off_periods_doctor_id_doctors",
            ondelete="RESTRICT",
        ),
        *_audit_fks("doctor_time_off_periods"),
        sa.CheckConstraint("end_datetime > start_datetime", name="end_after_start"),
    )
    op.create_index(
        "ix_doctor_time_off_periods_organization_id",
        "doctor_time_off_periods",
        ["organization_id"],
    )
    op.create_index(
        "ix_doctor_time_off_periods_doctor_id", "doctor_time_off_periods", ["doctor_id"]
    )


def downgrade() -> None:
    op.drop_table("doctor_time_off_periods")
    op.drop_table("doctor_availabilities")

    postgresql.ENUM(name="doctor_availability_weekday_enum").drop(
        op.get_bind(), checkfirst=True
    )
