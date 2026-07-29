"""create soap notes table

Creates the SOAP Notes foundation schema: soap_notes — a one-to-one
extension of `clinical_notes`, not a replacement for it.

`organization_id` references `organizations.id`, `clinical_note_id`
references `clinical_notes.id`, `patient_id` references `patients.id`,
`visit_id` references `patient_visits.id`, and `doctor_id` references
`doctors.id` (all chained before this migration) — this is why this
migration's `down_revision` chains after the Clinical Notes migration,
not a modification to any prior module's tables. No column is added to,
or constraint changed on, `organizations`/`clinical_notes`/`patients`/
`patient_visits`/`doctors`/`users`/any other prior table here.

`clinical_note_id`, `patient_id`, and `visit_id` all use `ON DELETE
CASCADE`: a SOAP note has no independent lifecycle meaning without its
clinical note, and `patient_id`/`visit_id` mirror
`clinical_notes.patient_id`/`visit_id`'s own CASCADE choice since
they're derived copies of exactly those columns. `doctor_id` (required)
uses `ON DELETE RESTRICT`, matching `clinical_notes.doctor_id`.

"One Clinical Note can have at most one SOAP Note" is enforced by a
partial unique index on `clinical_note_id WHERE deleted_at IS NULL`, the
same one-to-one shape `visit_vital_signs.visit_id` already uses.

Unlike every prior module, this migration adds **no** `CHECK` constraint
for "read-only when the linked Clinical Note is Signed/Locked": a
`CHECK` constraint can only see this table's own row, never
`clinical_notes.status` in another table — that invariant is enforced
exclusively at the application layer (see `SOAPNote`'s own docstring in
`app/modules/soap_notes/domain/entities.py` for the full reasoning).

Revision ID: f9cec12d02f1
Revises: bb6e2214d986
Create Date: 2026-07-29

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f9cec12d02f1"
down_revision: str | None = "bb6e2214d986"
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
    op.create_table(
        "soap_notes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinical_note_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("visit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("doctor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chief_complaint", sa.Text(), nullable=True),
        sa.Column("history_of_present_illness", sa.Text(), nullable=True),
        sa.Column("review_of_systems", sa.Text(), nullable=True),
        sa.Column("physical_examination", sa.Text(), nullable=True),
        sa.Column("vital_sign_summary", sa.Text(), nullable=True),
        sa.Column("assessment", sa.Text(), nullable=True),
        sa.Column("plan", sa.Text(), nullable=True),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("id", name="pk_soap_notes"),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_soap_notes_organization_id_organizations",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["clinical_note_id"],
            ["clinical_notes.id"],
            name="fk_soap_notes_clinical_note_id_clinical_notes",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patients.id"],
            name="fk_soap_notes_patient_id_patients",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["visit_id"],
            ["patient_visits.id"],
            name="fk_soap_notes_visit_id_patient_visits",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["doctor_id"],
            ["doctors.id"],
            name="fk_soap_notes_doctor_id_doctors",
            ondelete="RESTRICT",
        ),
        *_audit_fks("soap_notes"),
    )
    op.create_index(
        "uq_soap_notes_clinical_note_id",
        "soap_notes",
        ["clinical_note_id"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index("ix_soap_notes_organization_id", "soap_notes", ["organization_id"])
    op.create_index("ix_soap_notes_patient_id", "soap_notes", ["patient_id"])
    op.create_index("ix_soap_notes_visit_id", "soap_notes", ["visit_id"])
    op.create_index("ix_soap_notes_doctor_id", "soap_notes", ["doctor_id"])


def downgrade() -> None:
    op.drop_table("soap_notes")
