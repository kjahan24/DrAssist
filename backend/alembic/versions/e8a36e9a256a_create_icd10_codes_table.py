"""create icd10 codes table

Creates the ICD-10 Coding foundation schema: icd10_codes.

`organization_id` references `organizations.id`, `clinical_note_id`
references `clinical_notes.id`, `differential_diagnosis_id` (nullable)
references `differential_diagnoses.id`, `patient_id` references
`patients.id`, `visit_id` references `patient_visits.id`, and
`doctor_id` references `doctors.id` (all chained before this migration)
— this is why this migration's `down_revision` chains after the
Differential Diagnosis migration, not a modification to any prior
module's tables. No column is added to, or constraint changed on,
`organizations`/`clinical_notes`/`differential_diagnoses`/`patients`/
`patient_visits`/`doctors`/any other prior table here.

`clinical_note_id`, `patient_id`, and `visit_id` all use `ON DELETE
CASCADE`, matching `differential_diagnoses`/`clinical_reasoning`'s own
choice for the identical parent-reference shape. `doctor_id` (required)
uses `ON DELETE RESTRICT`, matching every other module's `doctor_id`.

`differential_diagnosis_id` (nullable) uses `ON DELETE SET NULL`: it is
an optional cross-reference to a peer document, not an ownership
relationship, so a hard-deleted `differential_diagnoses` row should
clear this link rather than cascading the deletion or blocking it — the
same treatment `differential_diagnoses.clinical_reasoning_id` already
receives.

"Duplicate ICD-10 prevention within a Clinical Note" is enforced by a
partial unique index on `(clinical_note_id, icd10_code) WHERE
deleted_at IS NULL`. Unlike `differential_diagnoses.diagnosis_name`
(free text, de-duplicated case-insensitively only at the application
layer, since no functional index was requested), this works at the
*database* level because `ICD10Coding.__post_init__` normalizes
`icd10_code` to uppercase first — see `domain/entities.py` for the full
reasoning. Following the same precedent `visit_diagnoses`' own
composite unique index already established, there is no *separate*
plain index on `clinical_note_id` alone, since it is already this
composite index's leading column.

"Only one ICD-10 code can be marked as Primary" is enforced by a
partial unique index on `clinical_note_id WHERE primary_code = true AND
deleted_at IS NULL`, the same shape `visit_diagnoses`' own "one Primary
diagnosis per Visit" index already uses.

There is no `CHECK` constraint here: "Approved and Rejected codes
become read-only" is an editability concept, not a column-value
constraint, and "if linked to Differential Diagnosis, both must belong
to the same Clinical Note" is a cross-table invariant no `CHECK`
constraint can express — both are enforced exclusively at the
application layer.

Revision ID: e8a36e9a256a
Revises: 072a461f2ee9
Create Date: 2026-07-29

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e8a36e9a256a"
down_revision: str | None = "072a461f2ee9"
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
    coding_source_enum = postgresql.ENUM(
        "physician",
        "ai",
        "hybrid",
        name="icd10_coding_source_enum",
        create_type=False,
    )
    coding_source_enum.create(op.get_bind(), checkfirst=True)

    review_status_enum = postgresql.ENUM(
        "pending",
        "reviewed",
        "approved",
        "rejected",
        name="icd10_coding_review_status_enum",
        create_type=False,
    )
    review_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "icd10_codes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinical_note_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("differential_diagnosis_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("visit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("doctor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("icd10_code", sa.Text(), nullable=False),
        sa.Column("diagnosis_title", sa.Text(), nullable=False),
        sa.Column("coding_source", coding_source_enum, nullable=False),
        sa.Column("primary_code", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("review_status", review_status_enum, nullable=False),
        sa.Column("coding_notes", sa.Text(), nullable=True),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("id", name="pk_icd10_codes"),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_icd10_codes_organization_id_organizations",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["clinical_note_id"],
            ["clinical_notes.id"],
            name="fk_icd10_codes_clinical_note_id_clinical_notes",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["differential_diagnosis_id"],
            ["differential_diagnoses.id"],
            name="fk_icd10_codes_differential_diagnosis_id_differential_diagnoses",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patients.id"],
            name="fk_icd10_codes_patient_id_patients",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["visit_id"],
            ["patient_visits.id"],
            name="fk_icd10_codes_visit_id_patient_visits",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["doctor_id"],
            ["doctors.id"],
            name="fk_icd10_codes_doctor_id_doctors",
            ondelete="RESTRICT",
        ),
        *_audit_fks("icd10_codes"),
    )
    op.create_index(
        "uq_icd10_codes_clinical_note_id_icd10_code",
        "icd10_codes",
        ["clinical_note_id", "icd10_code"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "uq_icd10_codes_primary_per_clinical_note",
        "icd10_codes",
        ["clinical_note_id"],
        unique=True,
        postgresql_where=sa.text("primary_code = true AND deleted_at IS NULL"),
    )
    op.create_index("ix_icd10_codes_organization_id", "icd10_codes", ["organization_id"])
    op.create_index(
        "ix_icd10_codes_differential_diagnosis_id", "icd10_codes", ["differential_diagnosis_id"]
    )
    op.create_index("ix_icd10_codes_patient_id", "icd10_codes", ["patient_id"])
    op.create_index("ix_icd10_codes_visit_id", "icd10_codes", ["visit_id"])
    op.create_index("ix_icd10_codes_doctor_id", "icd10_codes", ["doctor_id"])


def downgrade() -> None:
    op.drop_table("icd10_codes")

    postgresql.ENUM(name="icd10_coding_review_status_enum").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="icd10_coding_source_enum").drop(op.get_bind(), checkfirst=True)
