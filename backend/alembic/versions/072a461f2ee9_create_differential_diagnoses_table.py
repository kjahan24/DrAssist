"""create differential diagnoses table

Creates the Differential Diagnosis foundation schema:
differential_diagnoses.

`organization_id` references `organizations.id`, `clinical_note_id`
references `clinical_notes.id`, `clinical_reasoning_id` (nullable)
references `clinical_reasoning.id`, `patient_id` references
`patients.id`, `visit_id` references `patient_visits.id`, and
`doctor_id` references `doctors.id` (all chained before this migration)
— this is why this migration's `down_revision` chains after the Clinical
Reasoning migration, not a modification to any prior module's tables. No
column is added to, or constraint changed on, `organizations`/
`clinical_notes`/`clinical_reasoning`/`patients`/`patient_visits`/
`doctors`/any other prior table here.

`clinical_note_id`, `patient_id`, and `visit_id` all use `ON DELETE
CASCADE`, matching `clinical_reasoning`/`lab_orders`' own choice for the
identical parent-reference shape. `doctor_id` (required) uses `ON DELETE
RESTRICT`, matching every other module's `doctor_id`.

`clinical_reasoning_id` (nullable) uses `ON DELETE SET NULL`: it is an
optional cross-reference to a peer document, not an ownership
relationship, so a hard-deleted `clinical_reasoning` row should clear
this link rather than cascading the deletion or blocking it — see
`DifferentialDiagnosisModel`'s own comment for the full reasoning.

"Ranking must be unique within a Clinical Note" is enforced by a partial
unique index on `(clinical_note_id, ranking) WHERE deleted_at IS NULL`,
the same shape `visit_diagnoses`' own `sequence_number` uniqueness
already uses; following that same precedent, there is no separate plain
index on `clinical_note_id` alone, since it is already this composite
index's leading column. `ranking >= 1` is additionally enforced as a
`CHECK` constraint (defense-in-depth alongside
`DifferentialDiagnosis.__post_init__`), the same treatment
`visit_diagnoses.sequence_number` already receives.

"Duplicate diagnosis prevention" (case-insensitive `diagnosis_name`
uniqueness within a Clinical Note) has no database-level enforcement — a
plain unique index cannot express case-insensitive matching without a
functional index this task never asked for — so it is enforced
exclusively at the application layer
(`application/use_cases/create_differential_diagnosis.py`), as is "if
linked to Clinical Reasoning, both records must belong to the same
Clinical Note" (a cross-table invariant no `CHECK` constraint can
express) and "Approved and Rejected diagnoses become read-only" (an
editability concept, not a column-value constraint).

Revision ID: 072a461f2ee9
Revises: 3f38469bb1a4
Create Date: 2026-07-29

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "072a461f2ee9"
down_revision: str | None = "3f38469bb1a4"
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
    diagnosis_source_enum = postgresql.ENUM(
        "physician",
        "ai",
        "hybrid",
        name="differential_diagnosis_source_enum",
        create_type=False,
    )
    diagnosis_source_enum.create(op.get_bind(), checkfirst=True)

    review_status_enum = postgresql.ENUM(
        "pending",
        "reviewed",
        "approved",
        "rejected",
        name="differential_diagnosis_review_status_enum",
        create_type=False,
    )
    review_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "differential_diagnoses",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinical_note_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinical_reasoning_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("visit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("doctor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("diagnosis_name", sa.Text(), nullable=False),
        sa.Column("diagnosis_source", diagnosis_source_enum, nullable=False),
        sa.Column("ranking", sa.SmallInteger(), nullable=False),
        sa.Column("review_status", review_status_enum, nullable=False),
        sa.Column("likelihood_score", sa.Float(), nullable=True),
        sa.Column("supporting_evidence", sa.Text(), nullable=True),
        sa.Column("excluded", sa.Boolean(), nullable=False, server_default=sa.false()),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("id", name="pk_differential_diagnoses"),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_differential_diagnoses_organization_id_organizations",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["clinical_note_id"],
            ["clinical_notes.id"],
            name="fk_differential_diagnoses_clinical_note_id_clinical_notes",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["clinical_reasoning_id"],
            ["clinical_reasoning.id"],
            # Deliberately omits the usual `_{referred_table_name}` suffix
            # (`fk_{table}_{column}_{referred_table}`) — with it, this name
            # is 66 bytes, over Postgres's 63-byte NAMEDATALEN limit, and
            # the referenced table is already obvious from the column name.
            name="fk_differential_diagnoses_clinical_reasoning_id",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patients.id"],
            name="fk_differential_diagnoses_patient_id_patients",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["visit_id"],
            ["patient_visits.id"],
            name="fk_differential_diagnoses_visit_id_patient_visits",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["doctor_id"],
            ["doctors.id"],
            name="fk_differential_diagnoses_doctor_id_doctors",
            ondelete="RESTRICT",
        ),
        *_audit_fks("differential_diagnoses"),
        sa.CheckConstraint("ranking >= 1", name="ranking_starts_at_one"),
    )
    op.create_index(
        "uq_differential_diagnoses_clinical_note_id_ranking",
        "differential_diagnoses",
        ["clinical_note_id", "ranking"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "ix_differential_diagnoses_organization_id", "differential_diagnoses", ["organization_id"]
    )
    op.create_index(
        "ix_differential_diagnoses_clinical_reasoning_id",
        "differential_diagnoses",
        ["clinical_reasoning_id"],
    )
    op.create_index(
        "ix_differential_diagnoses_patient_id", "differential_diagnoses", ["patient_id"]
    )
    op.create_index("ix_differential_diagnoses_visit_id", "differential_diagnoses", ["visit_id"])
    op.create_index("ix_differential_diagnoses_doctor_id", "differential_diagnoses", ["doctor_id"])


def downgrade() -> None:
    op.drop_table("differential_diagnoses")

    postgresql.ENUM(name="differential_diagnosis_review_status_enum").drop(
        op.get_bind(), checkfirst=True
    )
    postgresql.ENUM(name="differential_diagnosis_source_enum").drop(op.get_bind(), checkfirst=True)
