"""create patient histories table

Creates the Patient History foundation schema: patient_histories.

`organization_id` references `organizations.id`, `patient_id`
references `patients.id`, `visit_id` references `patient_visits.id`,
and `doctor_review_id` references `doctor_reviews.id` (all chained
before this migration) — this is why this migration's `down_revision`
chains after the Doctor Review migration, not a modification to any
prior module's tables. No column is added to, or constraint changed on,
`organizations`/`patients`/`patient_visits`/`doctor_reviews`/any other
prior table here.

`patient_id` and `visit_id` use `ON DELETE CASCADE`, matching every
prior module's own choice for those two columns. `organization_id` uses
`ON DELETE RESTRICT`, matching every other module's `organization_id`.
`doctor_review_id` also uses `ON DELETE RESTRICT` (deliberately not
`SET NULL`/`CASCADE`): `PatientHistory` is meant to be *more* durable
than the review that authorized it — see `PatientHistoryModel`'s own
comment for the full reasoning.

`reference_id` carries **no** foreign key: it is a polymorphic reference
(`reference_type` names one of eight different tables it points into),
which Postgres cannot express as a single FK constraint. "Reference
validation" is enforced exclusively at the application layer.

"Duplicate history records for the same source are prohibited" is
enforced by a partial unique index on `(reference_type, reference_id)
WHERE deleted_at IS NULL`. `(patient_id, encounter_date)` is a composite
index serving both `list_by_patient` and the chronological-timeline
ordering every stated Future Compatibility consumer needs, so there is
no separate plain index on `patient_id` alone.

Revision ID: 2de01f040eb8
Revises: f724c5e0af47
Create Date: 2026-07-30

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "2de01f040eb8"
down_revision: str | None = "f724c5e0af47"
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
    history_type_enum = postgresql.ENUM(
        "encounter",
        "diagnosis",
        "medication",
        "lab",
        "procedure",
        "clinical_note",
        "soap_note",
        name="patient_history_type_enum",
        create_type=False,
    )
    history_type_enum.create(op.get_bind(), checkfirst=True)

    reference_type_enum = postgresql.ENUM(
        "clinical_note",
        "soap_note",
        "prescription",
        "lab_order",
        "lab_result",
        "differential_diagnosis",
        "icd10",
        "doctor_review",
        name="patient_history_reference_type_enum",
        create_type=False,
    )
    reference_type_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "patient_histories",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("visit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("doctor_review_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("history_type", history_type_enum, nullable=False),
        sa.Column("reference_type", reference_type_enum, nullable=False),
        sa.Column("reference_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("encounter_date", sa.Date(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column(
            "created_from_review", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("id", name="pk_patient_histories"),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_patient_histories_organization_id_organizations",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patients.id"],
            name="fk_patient_histories_patient_id_patients",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["visit_id"],
            ["patient_visits.id"],
            name="fk_patient_histories_visit_id_patient_visits",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["doctor_review_id"],
            ["doctor_reviews.id"],
            name="fk_patient_histories_doctor_review_id_doctor_reviews",
            ondelete="RESTRICT",
        ),
        *_audit_fks("patient_histories"),
    )
    op.create_index(
        "uq_patient_histories_reference_type_reference_id",
        "patient_histories",
        ["reference_type", "reference_id"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "ix_patient_histories_patient_id_encounter_date",
        "patient_histories",
        ["patient_id", "encounter_date"],
    )
    op.create_index(
        "ix_patient_histories_organization_id", "patient_histories", ["organization_id"]
    )
    op.create_index("ix_patient_histories_visit_id", "patient_histories", ["visit_id"])
    op.create_index(
        "ix_patient_histories_doctor_review_id", "patient_histories", ["doctor_review_id"]
    )


def downgrade() -> None:
    op.drop_table("patient_histories")

    postgresql.ENUM(name="patient_history_reference_type_enum").drop(
        op.get_bind(), checkfirst=True
    )
    postgresql.ENUM(name="patient_history_type_enum").drop(op.get_bind(), checkfirst=True)
