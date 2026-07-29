"""create clinical notes table

Creates the Clinical Notes foundation schema: clinical_notes — the
master record every future clinical document module (SOAP Note,
Prescription, Lab Order, Lab Result, Imaging Report, Clinical Reasoning,
Differential Diagnosis, ICD-10/CPT Coding, AI Copilot, Doctor Review,
Clinical Timeline) will add its own `clinical_note_id` foreign key to;
nothing here needs to change to support that.

`organization_id` references `organizations.id`, `patient_id`
references `patients.id`, `visit_id` references `patient_visits.id`, and
`doctor_id`/`signed_by` reference `doctors.id` (all chained before this
migration) — this is why this migration's `down_revision` chains after
the Attachments migration, not a modification to any prior module's
tables. No column is added to, or constraint changed on,
`organizations`/`patients`/`patient_visits`/`doctors`/`users`/any other
prior table here.

`patient_id` and `visit_id` use `ON DELETE CASCADE`, matching
`patient_visits.patient_id`'s and `visit_attachments.visit_id`'s own
choices respectively. `doctor_id` (required, the authoring doctor) uses
`ON DELETE RESTRICT`, matching `patient_visits.doctor_id`. `signed_by`
(nullable, best-effort attribution) uses `ON DELETE SET NULL`, matching
`visit_attachments.uploaded_by`.

"note_number must be globally unique" is enforced by a partial unique
index on `note_number WHERE deleted_at IS NULL`, the same shape
`visit_attachments.storage_key`/`checksum_sha256` already use.

Four business rules are enforced as DB `CHECK` constraints (in addition
to `ClinicalNote.__post_init__`, the same defense-in-depth pattern
applied to every prior module) — see `ClinicalNoteModel`'s own comment
for why `locked_at` gets the identical bidirectional treatment as
`signed_at`/`signed_by` even though only the latter two are named
explicitly in this task's business rules:
- "signed_at exists only when status = Signed or Locked" (both
  directions) -> `signed_requires_signature` / `unsigned_forbids_signature`.
- The same bidirectional shape for `locked_at` ->
  `locked_requires_locked_at` / `unlocked_forbids_locked_at`.

Revision ID: bb6e2214d986
Revises: 1aec9a7ff32b
Create Date: 2026-07-29

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "bb6e2214d986"
down_revision: str | None = "1aec9a7ff32b"
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
    clinical_note_type_enum = postgresql.ENUM(
        "initial",
        "follow_up",
        "emergency",
        "consultation",
        "discharge",
        name="clinical_note_type_enum",
        create_type=False,
    )
    clinical_note_type_enum.create(op.get_bind(), checkfirst=True)

    clinical_note_status_enum = postgresql.ENUM(
        "draft",
        "in_review",
        "signed",
        "locked",
        name="clinical_note_status_enum",
        create_type=False,
    )
    clinical_note_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "clinical_notes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("visit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("doctor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("note_number", sa.Text(), nullable=False),
        sa.Column("note_type", clinical_note_type_enum, nullable=False),
        sa.Column("status", clinical_note_status_enum, nullable=False, server_default="draft"),
        sa.Column("encounter_datetime", _TIMESTAMPTZ, nullable=False),
        sa.Column("chief_complaint_summary", sa.Text(), nullable=True),
        sa.Column("history_summary", sa.Text(), nullable=True),
        sa.Column("examination_summary", sa.Text(), nullable=True),
        sa.Column("assessment_summary", sa.Text(), nullable=True),
        sa.Column("plan_summary", sa.Text(), nullable=True),
        sa.Column("ai_generated", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("ai_model", sa.Text(), nullable=True),
        sa.Column("ai_version", sa.Text(), nullable=True),
        sa.Column("signed_at", _TIMESTAMPTZ, nullable=True),
        sa.Column("signed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("locked_at", _TIMESTAMPTZ, nullable=True),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("id", name="pk_clinical_notes"),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_clinical_notes_organization_id_organizations",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patients.id"],
            name="fk_clinical_notes_patient_id_patients",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["visit_id"],
            ["patient_visits.id"],
            name="fk_clinical_notes_visit_id_patient_visits",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["doctor_id"],
            ["doctors.id"],
            name="fk_clinical_notes_doctor_id_doctors",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["signed_by"],
            ["doctors.id"],
            name="fk_clinical_notes_signed_by_doctors",
            ondelete="SET NULL",
        ),
        *_audit_fks("clinical_notes"),
        sa.CheckConstraint(
            "status NOT IN ('signed', 'locked') OR "
            "(signed_at IS NOT NULL AND signed_by IS NOT NULL)",
            name="signed_requires_signature",
        ),
        sa.CheckConstraint(
            "status IN ('signed', 'locked') OR (signed_at IS NULL AND signed_by IS NULL)",
            name="unsigned_forbids_signature",
        ),
        sa.CheckConstraint(
            "status != 'locked' OR locked_at IS NOT NULL",
            name="locked_requires_locked_at",
        ),
        sa.CheckConstraint(
            "status = 'locked' OR locked_at IS NULL",
            name="unlocked_forbids_locked_at",
        ),
    )
    op.create_index(
        "uq_clinical_notes_note_number",
        "clinical_notes",
        ["note_number"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index("ix_clinical_notes_organization_id", "clinical_notes", ["organization_id"])
    op.create_index("ix_clinical_notes_patient_id", "clinical_notes", ["patient_id"])
    op.create_index("ix_clinical_notes_visit_id", "clinical_notes", ["visit_id"])
    op.create_index("ix_clinical_notes_doctor_id", "clinical_notes", ["doctor_id"])


def downgrade() -> None:
    op.drop_table("clinical_notes")

    postgresql.ENUM(name="clinical_note_status_enum").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="clinical_note_type_enum").drop(op.get_bind(), checkfirst=True)
