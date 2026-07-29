"""create clinical reasoning table

Creates the Clinical Reasoning foundation schema: clinical_reasoning.

`organization_id` references `organizations.id`, `clinical_note_id`
references `clinical_notes.id`, `patient_id` references `patients.id`,
`visit_id` references `patient_visits.id`, and `doctor_id` references
`doctors.id` (all chained before this migration) — this is why this
migration's `down_revision` chains after the Lab Results migration, not
a modification to any prior module's tables. No column is added to, or
constraint changed on, `organizations`/`clinical_notes`/`patients`/
`patient_visits`/`doctors`/`soap_notes`/`prescriptions`/`lab_orders`/
`lab_results`/`users`/any other prior table here.

`clinical_note_id`, `patient_id`, and `visit_id` all use `ON DELETE
CASCADE`, matching `soap_notes`/`prescriptions`/`lab_orders`' own choice
for the identical parent-reference shape. `doctor_id` (required) uses
`ON DELETE RESTRICT`, matching every other module's `doctor_id`.

Unlike `soap_notes.clinical_note_id`/`prescriptions.clinical_note_id`,
`clinical_reasoning.clinical_note_id` carries **no** unique index — "One
Clinical Note may contain multiple Clinical Reasoning records" (this
task's own Business Rules), the same one-to-many shape
`lab_orders.clinical_note_id` already has. It still gets a plain index
for `list_clinical_reasoning_for_clinical_note` query performance.

No globally-unique "number" column exists on this table at all — this
task's own field list names no such field, so there is no partial unique
index to create here (unlike every other child-document module's
migration so far).

Unlike `clinical_notes`, there is **no** `CHECK` constraint here enforcing
"Approved/Rejected reasoning becomes immutable": a `CHECK` constraint
validates column *values* on write, not "can this row still be updated at
all" — that invariant is enforced exclusively at the application layer
(`ClinicalReasoning.ensure_editable()`).

Revision ID: 3f38469bb1a4
Revises: a38ecf2fe88f
Create Date: 2026-07-29

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "3f38469bb1a4"
down_revision: str | None = "a38ecf2fe88f"
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
    reasoning_source_enum = postgresql.ENUM(
        "physician",
        "ai",
        "hybrid",
        name="reasoning_source_enum",
        create_type=False,
    )
    reasoning_source_enum.create(op.get_bind(), checkfirst=True)

    review_status_enum = postgresql.ENUM(
        "pending",
        "reviewed",
        "approved",
        "rejected",
        name="review_status_enum",
        create_type=False,
    )
    review_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "clinical_reasoning",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinical_note_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("visit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("doctor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reasoning_source", reasoning_source_enum, nullable=False),
        sa.Column("reasoning_text", sa.Text(), nullable=False),
        sa.Column("ai_generated", sa.Boolean(), nullable=False),
        sa.Column("review_status", review_status_enum, nullable=False),
        sa.Column("reviewed_by_doctor", sa.Boolean(), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("id", name="pk_clinical_reasoning"),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_clinical_reasoning_organization_id_organizations",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["clinical_note_id"],
            ["clinical_notes.id"],
            name="fk_clinical_reasoning_clinical_note_id_clinical_notes",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patients.id"],
            name="fk_clinical_reasoning_patient_id_patients",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["visit_id"],
            ["patient_visits.id"],
            name="fk_clinical_reasoning_visit_id_patient_visits",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["doctor_id"],
            ["doctors.id"],
            name="fk_clinical_reasoning_doctor_id_doctors",
            ondelete="RESTRICT",
        ),
        *_audit_fks("clinical_reasoning"),
    )
    op.create_index(
        "ix_clinical_reasoning_organization_id", "clinical_reasoning", ["organization_id"]
    )
    op.create_index(
        "ix_clinical_reasoning_clinical_note_id", "clinical_reasoning", ["clinical_note_id"]
    )
    op.create_index("ix_clinical_reasoning_patient_id", "clinical_reasoning", ["patient_id"])
    op.create_index("ix_clinical_reasoning_visit_id", "clinical_reasoning", ["visit_id"])
    op.create_index("ix_clinical_reasoning_doctor_id", "clinical_reasoning", ["doctor_id"])


def downgrade() -> None:
    op.drop_table("clinical_reasoning")

    postgresql.ENUM(name="review_status_enum").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="reasoning_source_enum").drop(op.get_bind(), checkfirst=True)
