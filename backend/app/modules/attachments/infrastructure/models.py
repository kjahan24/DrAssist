"""SQLAlchemy ORM model for the Attachments module.

One table: `visit_attachments`. See `app.modules.attachments.container`
for the module's scope note.

`visit_attachments.organization_id` carries a real foreign key to
`organizations.id`, and `visit_id` a real foreign key to
`patient_visits.id` — brand-new columns on a brand-new table, so there is
no backward-compatibility reason to defer them; neither `organizations`
nor `patient_visits` is modified by this migration.

`visit_id` uses `ON DELETE CASCADE`, the same choice
`visit_procedures.visit_id` already makes: an attachment's metadata row
has no independent lifecycle meaning without its visit (the underlying
object-storage file's lifecycle is out of scope for this table entirely
— see the module docstring in `domain/entities.py`). `uploaded_by`
(nullable, best-effort attribution) follows `visit_procedures.performed_by`'s
`SET NULL` choice — see that column's own comment for the full reasoning.

`storage_key` and `checksum_sha256` are each globally unique (partial
indexes `WHERE deleted_at IS NULL`, the same soft-delete-aware shape
every other uniqueness constraint in this schema uses) — *not* scoped to
`visit_id` or `organization_id`, matching the unqualified "must be
unique" wording in this task's business rules. `file_size_bytes` is
`BigInteger`, not the default `Integer`: `AttachmentType.VIDEO` implies
files that can exceed the ~2 GiB ceiling a 32-bit column would impose.
"""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Index, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import (
    AuditActorMixin,
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    pg_enum,
)
from app.modules.attachments.domain.enums import AttachmentType, StorageProvider

_attachment_type_enum = pg_enum(AttachmentType, "attachment_type_enum")
_storage_provider_enum = pg_enum(StorageProvider, "storage_provider_enum")


class VisitAttachmentModel(
    Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, AuditActorMixin
):
    __tablename__ = "visit_attachments"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    visit_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("patient_visits.id", ondelete="CASCADE"), nullable=False
    )
    attachment_type: Mapped[AttachmentType] = mapped_column(_attachment_type_enum, nullable=False)
    file_name: Mapped[str] = mapped_column(Text, nullable=False)
    original_file_name: Mapped[str] = mapped_column(Text, nullable=False)
    mime_type: Mapped[str] = mapped_column(Text, nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    storage_provider: Mapped[StorageProvider] = mapped_column(
        _storage_provider_enum, nullable=False
    )
    storage_bucket: Mapped[str] = mapped_column(Text, nullable=False)
    storage_key: Mapped[str] = mapped_column(Text, nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("doctors.id", ondelete="SET NULL"), default=None
    )
    uploaded_at: Mapped[datetime] = mapped_column(nullable=False)
    description: Mapped[str | None] = mapped_column(Text, default=None)

    __table_args__ = (
        Index(
            "uq_visit_attachments_storage_key",
            "storage_key",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "uq_visit_attachments_checksum_sha256",
            "checksum_sha256",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("ix_visit_attachments_visit_id", "visit_id"),
        Index("ix_visit_attachments_organization_id", "organization_id"),
        CheckConstraint("file_size_bytes > 0", name="file_size_bytes_positive"),
    )
