"""create patient visits table

Creates the Visit Core foundation schema: patient_visits.

`organization_id` references `organizations.id`, `patient_id` references
`patients.id`, and `doctor_id` references `doctors.id` (all chained
before this migration) — this is why this migration's `down_revision`
chains after the Patient Medical Conditions migration, not a
modification to any prior module's tables. No column is added to, or
constraint changed on, `organizations`/`patients`/`doctors`/`users`/any
other prior table here.

`doctor_id` uses `ON DELETE RESTRICT` rather than `SET NULL`: it is
`NOT NULL` ("one visit belongs to one doctor"), so `SET NULL` isn't an
option, and `CASCADE` would silently destroy visit history if a doctor
row were ever removed — `RESTRICT` matches `doctors.organization_id`/
`doctors.user_id`'s own choice for required, significant relationships.

`appointment_id` is a plain nullable UUID column with **no** foreign key
— the Appointment module doesn't exist yet; see `PatientVisitModel`'s own
comment for the full reasoning.

"visit_number must be unique within an organization" is enforced by a
partial unique index on `(organization_id, visit_number) WHERE
deleted_at IS NULL` — scoped to the organization only (not to
`visit_status`, unlike Patient Allergies'/Medical Conditions' "duplicate
*active*" rules), since a visit_number is a permanent identifier for
that visit regardless of its status, the same reasoning `patients.
patient_number`'s uniqueness already follows.

Three business rules are enforced as DB `CHECK` constraints (in addition
to `PatientVisit.__post_init__`, the same defense-in-depth pattern
applied to every prior Patient sub-module):
- "check_out_time cannot be before check_in_time" ->
  `check_in_time IS NULL OR check_out_time IS NULL OR check_out_time >=
  check_in_time` (same-instant is allowed).
- "consultation_end_time cannot be before consultation_start_time" ->
  the same shape, on the consultation timestamps.
- "follow_up_date is required only if follow_up_required is true" ->
  `NOT follow_up_required OR follow_up_date IS NOT NULL`.

Revision ID: a21a9c63b7ce
Revises: 4ae0a24f2450
Create Date: 2026-07-28

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a21a9c63b7ce"
down_revision: str | None = "4ae0a24f2450"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TIMESTAMPTZ = sa.DateTime(timezone=True)
_NOW = sa.text("now()")


def _audit_columns() -> list[sa.Column]:
    """The five standard columns every table in this schema carries, minus
    `id` (added separately since its type/default is identical everywhere
    but declared first). See `docs/database/00_overview.md`.
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
    visit_type_enum = postgresql.ENUM(
        "consultation",
        "follow_up",
        "emergency",
        "telemedicine",
        "procedure",
        "lab_review",
        "vaccination",
        "home_visit",
        name="visit_type_enum",
        create_type=False,
    )
    visit_type_enum.create(op.get_bind(), checkfirst=True)

    visit_status_enum = postgresql.ENUM(
        "scheduled",
        "checked_in",
        "in_progress",
        "completed",
        "cancelled",
        "no_show",
        name="visit_status_enum",
        create_type=False,
    )
    visit_status_enum.create(op.get_bind(), checkfirst=True)

    visit_priority_enum = postgresql.ENUM(
        "low",
        "normal",
        "high",
        "urgent",
        "critical",
        name="visit_priority_enum",
        create_type=False,
    )
    visit_priority_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "patient_visits",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("doctor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("visit_number", sa.Text(), nullable=False),
        sa.Column("appointment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("visit_type", visit_type_enum, nullable=False),
        sa.Column("visit_status", visit_status_enum, nullable=False, server_default="scheduled"),
        sa.Column("priority", visit_priority_enum, nullable=False, server_default="normal"),
        sa.Column("visit_date", sa.Date(), nullable=False),
        sa.Column("check_in_time", _TIMESTAMPTZ, nullable=True),
        sa.Column("consultation_start_time", _TIMESTAMPTZ, nullable=True),
        sa.Column("consultation_end_time", _TIMESTAMPTZ, nullable=True),
        sa.Column("check_out_time", _TIMESTAMPTZ, nullable=True),
        sa.Column("chief_complaint_summary", sa.Text(), nullable=True),
        sa.Column("reason_for_visit", sa.Text(), nullable=True),
        sa.Column("room_number", sa.Text(), nullable=True),
        sa.Column("follow_up_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("follow_up_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("id", name="pk_patient_visits"),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_patient_visits_organization_id_organizations",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patients.id"],
            name="fk_patient_visits_patient_id_patients",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["doctor_id"],
            ["doctors.id"],
            name="fk_patient_visits_doctor_id_doctors",
            ondelete="RESTRICT",
        ),
        *_audit_fks("patient_visits"),
        sa.CheckConstraint(
            "check_in_time IS NULL OR check_out_time IS NULL OR check_out_time >= check_in_time",
            name="check_out_not_before_check_in",
        ),
        sa.CheckConstraint(
            "consultation_start_time IS NULL OR consultation_end_time IS NULL "
            "OR consultation_end_time >= consultation_start_time",
            name="consultation_end_not_before_start",
        ),
        sa.CheckConstraint(
            "NOT follow_up_required OR follow_up_date IS NOT NULL",
            name="follow_up_date_required",
        ),
    )
    op.create_index(
        "uq_patient_visits_organization_id_visit_number",
        "patient_visits",
        ["organization_id", "visit_number"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index("ix_patient_visits_organization_id", "patient_visits", ["organization_id"])
    op.create_index("ix_patient_visits_patient_id", "patient_visits", ["patient_id"])
    op.create_index("ix_patient_visits_doctor_id", "patient_visits", ["doctor_id"])


def downgrade() -> None:
    op.drop_table("patient_visits")

    postgresql.ENUM(name="visit_priority_enum").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="visit_status_enum").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="visit_type_enum").drop(op.get_bind(), checkfirst=True)
