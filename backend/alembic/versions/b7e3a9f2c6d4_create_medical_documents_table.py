"""create medical documents table

Creates the Documents (Personal Health Document Vault) foundation
schema: medical_documents.

`organization_id` references `organizations.id`, `patient_id` references
`patients.id`, `uploaded_by_user_id` references `users.id`, and
`visit_id`/`appointment_id` reference `patient_visits.id`/`appointments.id`
(all chained before this migration) — this is why this migration's
`down_revision` chains after the Search & Filtering migration, not a
modification to any prior module's tables. No column is added to, or
constraint changed on, `organizations`/`patients`/`users`/
`patient_visits`/`appointments`/any other prior table here.

`patient_id` uses `ON DELETE CASCADE`, matching every other per-patient
clinical table in this schema (`clinical_notes`, `appointments`,
`lab_orders`, `prescriptions`, ...). `uploaded_by_user_id` is a
*required* reference and uses `ON DELETE RESTRICT`, matching
`doctors.user_id`'s own required-reference choice, so the audit trail of
who uploaded a document can never be silently lost to a user deletion.
`visit_id`/`appointment_id` are optional context links and use
`ON DELETE SET NULL`, matching `appointments.visit_id`'s identical
nullable FK-to-`patient_visits` choice.

Postgres enum type names are database-global, not per-table:
`document_storage_provider_enum` (`local`/`s3`/`azure_blob`/
`google_cloud_storage`) is a deliberately distinct name from
`visit_attachments`' own already-migrated `storage_provider_enum`
(`local`/`minio`/`s3`) — the two enums have different membership, so
this table cannot reuse that type.

`stored_filename` is globally unique (partial index `WHERE deleted_at IS
NULL`, the same soft-delete-aware shape every other uniqueness
constraint in this schema uses) — matching this task's "same stored
filename must never exist twice" rule. `checksum_sha256` is
deliberately *not* unique (unlike `visit_attachments.checksum_sha256`):
this task's own rule states "same checksum may exist across different
patients", so only a plain index is added for lookup performance.

One business rule is enforced as a DB constraint (in addition to
`MedicalDocument.__post_init__`, the same defense-in-depth pattern
applied to every prior module):
- "file size must be positive" -> `file_size_bytes > 0`.

Revision ID: b7e3a9f2c6d4
Revises: f1a2b3c4d5e6
Create Date: 2026-07-31

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b7e3a9f2c6d4"
down_revision: str | None = "f1a2b3c4d5e6"
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
    document_category_enum = postgresql.ENUM(
        "prescription",
        "lab_report",
        "radiology",
        "medical_image",
        "clinical_note",
        "referral_letter",
        "discharge_summary",
        "insurance",
        "consent_form",
        "vaccination",
        "other",
        name="document_category_enum",
        create_type=False,
    )
    document_category_enum.create(op.get_bind(), checkfirst=True)

    document_storage_provider_enum = postgresql.ENUM(
        "local",
        "s3",
        "azure_blob",
        "google_cloud_storage",
        name="document_storage_provider_enum",
        create_type=False,
    )
    document_storage_provider_enum.create(op.get_bind(), checkfirst=True)

    document_status_enum = postgresql.ENUM(
        "uploading",
        "active",
        "archived",
        "deleted",
        name="document_status_enum",
        create_type=False,
    )
    document_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "medical_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("uploaded_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("visit_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("appointment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("category", document_category_enum, nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("original_filename", sa.Text(), nullable=False),
        sa.Column("stored_filename", sa.Text(), nullable=False),
        sa.Column("mime_type", sa.Text(), nullable=False),
        sa.Column("extension", sa.Text(), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("storage_provider", document_storage_provider_enum, nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("checksum_sha256", sa.Text(), nullable=False),
        sa.Column("status", document_status_enum, nullable=False),
        sa.Column("uploaded_at", _TIMESTAMPTZ, nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("id", name="pk_medical_documents"),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_medical_documents_organization_id_organizations",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patients.id"],
            name="fk_medical_documents_patient_id_patients",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["uploaded_by_user_id"],
            ["users.id"],
            name="fk_medical_documents_uploaded_by_user_id_users",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["visit_id"],
            ["patient_visits.id"],
            name="fk_medical_documents_visit_id_patient_visits",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["appointment_id"],
            ["appointments.id"],
            name="fk_medical_documents_appointment_id_appointments",
            ondelete="SET NULL",
        ),
        *_audit_fks("medical_documents"),
        sa.CheckConstraint("file_size_bytes > 0", name="file_size_bytes_positive"),
    )
    op.create_index(
        "uq_medical_documents_stored_filename",
        "medical_documents",
        ["stored_filename"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "ix_medical_documents_organization_id", "medical_documents", ["organization_id"]
    )
    op.create_index("ix_medical_documents_patient_id", "medical_documents", ["patient_id"])
    op.create_index("ix_medical_documents_visit_id", "medical_documents", ["visit_id"])
    op.create_index("ix_medical_documents_appointment_id", "medical_documents", ["appointment_id"])
    op.create_index(
        "ix_medical_documents_checksum_sha256", "medical_documents", ["checksum_sha256"]
    )


def downgrade() -> None:
    op.drop_table("medical_documents")

    postgresql.ENUM(name="document_status_enum").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="document_storage_provider_enum").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="document_category_enum").drop(op.get_bind(), checkfirst=True)
