"""create doctor reviews table

Creates the Doctor Review foundation schema: doctor_reviews.

`organization_id` references `organizations.id`, `patient_id`
references `patients.id`, `visit_id` references `patient_visits.id`,
`doctor_id` references `doctors.id`, and `clinical_note_id` references
`clinical_notes.id` (all chained before this migration) — this is why
this migration's `down_revision` chains after the ICD-10 Coding
migration, not a modification to any prior module's tables. No column
is added to, or constraint changed on, `organizations`/`patients`/
`patient_visits`/`doctors`/`clinical_notes`/any other prior table here.

`clinical_note_id`, `patient_id`, and `visit_id` all use `ON DELETE
CASCADE`, matching `soap_notes`/`icd10_codes`'s own choice for the
identical parent-reference shape. `doctor_id` (required) uses `ON DELETE
RESTRICT`, matching every other module's `doctor_id`.

"One Clinical Note has exactly zero or one Doctor Review" is enforced by
a partial unique index on `clinical_note_id WHERE deleted_at IS NULL`,
the same one-to-one shape `soap_notes.clinical_note_id` already uses.

There is no `CHECK` constraint here: "Review status transitions must be
validated" is enforced exclusively by the application layer's transition
map (a `CHECK` constraint cannot see the *previous* value of a column),
and "Cross-module consistency" for the `approved_*` columns is a
cross-table invariant no `CHECK` constraint can express either — both
are enforced exclusively at the application layer.

Revision ID: f724c5e0af47
Revises: e8a36e9a256a
Create Date: 2026-07-30

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f724c5e0af47"
down_revision: str | None = "e8a36e9a256a"
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
    review_status_enum = postgresql.ENUM(
        "pending",
        "approved",
        "rejected",
        "returned_for_revision",
        name="doctor_review_status_enum",
        create_type=False,
    )
    review_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "doctor_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("visit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("doctor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinical_note_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("review_status", review_status_enum, nullable=False),
        sa.Column("review_comment", sa.Text(), nullable=True),
        sa.Column("reviewed_at", _TIMESTAMPTZ, nullable=True),
        sa.Column(
            "approved_clinical_note", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("approved_soap_note", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "approved_prescription", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("approved_lab_orders", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "approved_lab_results", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("approved_reasoning", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "approved_differential_diagnosis",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("approved_icd10", sa.Boolean(), nullable=False, server_default=sa.false()),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("id", name="pk_doctor_reviews"),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_doctor_reviews_organization_id_organizations",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patients.id"],
            name="fk_doctor_reviews_patient_id_patients",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["visit_id"],
            ["patient_visits.id"],
            name="fk_doctor_reviews_visit_id_patient_visits",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["doctor_id"],
            ["doctors.id"],
            name="fk_doctor_reviews_doctor_id_doctors",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["clinical_note_id"],
            ["clinical_notes.id"],
            name="fk_doctor_reviews_clinical_note_id_clinical_notes",
            ondelete="CASCADE",
        ),
        *_audit_fks("doctor_reviews"),
    )
    op.create_index(
        "uq_doctor_reviews_clinical_note_id",
        "doctor_reviews",
        ["clinical_note_id"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index("ix_doctor_reviews_organization_id", "doctor_reviews", ["organization_id"])
    op.create_index("ix_doctor_reviews_patient_id", "doctor_reviews", ["patient_id"])
    op.create_index("ix_doctor_reviews_visit_id", "doctor_reviews", ["visit_id"])
    op.create_index("ix_doctor_reviews_doctor_id", "doctor_reviews", ["doctor_id"])


def downgrade() -> None:
    op.drop_table("doctor_reviews")

    postgresql.ENUM(name="doctor_review_status_enum").drop(op.get_bind(), checkfirst=True)
