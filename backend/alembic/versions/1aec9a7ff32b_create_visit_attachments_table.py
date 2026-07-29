"""create visit attachments table

Creates the Attachments foundation schema: visit_attachments.

`organization_id` references `organizations.id` and `visit_id` references
`patient_visits.id` (both chained before this migration) — this is why
this migration's `down_revision` chains after the Procedures migration,
not a modification to any prior module's tables. No column is added to,
or constraint changed on, `organizations`/`patient_visits`/`doctors`/
`users`/any other prior table here.

`visit_id` uses `ON DELETE CASCADE`, the same choice
`visit_procedures.visit_id` already makes: this row is metadata about a
file, with no independent lifecycle meaning without its visit (the
underlying object-storage file's own lifecycle is entirely out of scope
for this table — see `VisitAttachmentModel`'s own comment). `uploaded_by`
(nullable, best-effort attribution) uses `ON DELETE SET NULL`, matching
`visit_procedures.performed_by`.

`storage_key` and `checksum_sha256` are each globally unique (partial
indexes `WHERE deleted_at IS NULL`) — *not* scoped to `visit_id` or
`organization_id`, matching the unqualified "must be unique" wording in
this task's business rules; see `VisitAttachmentModel`'s own comment for
the full reasoning, including why `checksum_sha256` uniqueness is a
genuine system-wide content-addressable dedup constraint.

Two business rules are enforced as DB constraints (in addition to
`VisitAttachment.__post_init__`, the same defense-in-depth pattern
applied to every prior module):
- "file_size_bytes must be greater than zero" -> `file_size_bytes > 0`.
- "Store only metadata in PostgreSQL. Never store binary file data in the
  database" -> there is no column here capable of holding binary file
  content; enforced by omission, not a constraint.

Revision ID: 1aec9a7ff32b
Revises: cf2ff02702b8
Create Date: 2026-07-29

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "1aec9a7ff32b"
down_revision: str | None = "cf2ff02702b8"
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
    attachment_type_enum = postgresql.ENUM(
        "image",
        "pdf",
        "document",
        "audio",
        "video",
        "other",
        name="attachment_type_enum",
        create_type=False,
    )
    attachment_type_enum.create(op.get_bind(), checkfirst=True)

    storage_provider_enum = postgresql.ENUM(
        "local",
        "minio",
        "s3",
        name="storage_provider_enum",
        create_type=False,
    )
    storage_provider_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "visit_attachments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("visit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("attachment_type", attachment_type_enum, nullable=False),
        sa.Column("file_name", sa.Text(), nullable=False),
        sa.Column("original_file_name", sa.Text(), nullable=False),
        sa.Column("mime_type", sa.Text(), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("storage_provider", storage_provider_enum, nullable=False),
        sa.Column("storage_bucket", sa.Text(), nullable=False),
        sa.Column("storage_key", sa.Text(), nullable=False),
        sa.Column("checksum_sha256", sa.Text(), nullable=False),
        sa.Column("uploaded_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("uploaded_at", _TIMESTAMPTZ, nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("id", name="pk_visit_attachments"),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_visit_attachments_organization_id_organizations",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["visit_id"],
            ["patient_visits.id"],
            name="fk_visit_attachments_visit_id_patient_visits",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["uploaded_by"],
            ["doctors.id"],
            name="fk_visit_attachments_uploaded_by_doctors",
            ondelete="SET NULL",
        ),
        *_audit_fks("visit_attachments"),
        sa.CheckConstraint("file_size_bytes > 0", name="file_size_bytes_positive"),
    )
    op.create_index(
        "uq_visit_attachments_storage_key",
        "visit_attachments",
        ["storage_key"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "uq_visit_attachments_checksum_sha256",
        "visit_attachments",
        ["checksum_sha256"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index("ix_visit_attachments_visit_id", "visit_attachments", ["visit_id"])
    op.create_index(
        "ix_visit_attachments_organization_id", "visit_attachments", ["organization_id"]
    )


def downgrade() -> None:
    op.drop_table("visit_attachments")

    postgresql.ENUM(name="storage_provider_enum").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="attachment_type_enum").drop(op.get_bind(), checkfirst=True)
