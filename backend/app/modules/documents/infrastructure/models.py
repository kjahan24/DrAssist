"""SQLAlchemy ORM model for the Documents module.

One table: `medical_documents`. See `app.modules.documents.container` for
the module's scope note.

Postgres enum type names are database-global, not per-table — this
module's own `StorageProvider` enum (`local`/`s3`/`azure_blob`/
`google_cloud_storage`) has different membership than
`app.modules.attachments.infrastructure.models`'s already-migrated
`storage_provider_enum` type (`local`/`minio`/`s3`), so this module binds
its own distinctly-named `document_storage_provider_enum` type rather
than colliding with (or reusing) that one.

`organization_id` uses `RESTRICT` and `patient_id` uses `CASCADE`, the
same choice every other per-patient clinical table in this schema makes
(e.g. `clinical_notes`, `appointments`, `lab_orders`, `prescriptions`).
`uploaded_by_user_id` is a *required* reference (unlike attachments'
optional, `SET NULL` `uploaded_by`) — it uses `RESTRICT`, mirroring
`doctors.user_id`'s own required-reference choice, so the audit trail of
who uploaded a medical document can never be silently lost to a user
deletion. `visit_id`/`appointment_id` are optional context links and use
`SET NULL`, mirroring `appointments.visit_id`'s identical nullable
FK-to-`patient_visits` choice.

`stored_filename` is globally unique (partial index `WHERE deleted_at IS
NULL`, the same soft-delete-aware shape every other uniqueness constraint
in this schema uses) — matching this task's "same stored filename must
never exist twice" rule. `checksum_sha256` is deliberately *not* unique:
this task's own rule states "same checksum may exist across different
patients" (unlike attachments' globally-unique checksum), so only a plain
index is added for lookup performance. `file_size_bytes` is `BigInteger`,
not the default `Integer`, matching `visit_attachments.file_size_bytes`'s
same reasoning (documents can exceed a 32-bit column's ~2 GiB ceiling).

`metadata` is mapped as `document_metadata` in Python — the identical
`Base.metadata`-collision workaround `notification_metadata` already
establishes in `app.modules.notification.infrastructure.models` — while
the actual database column stays named `metadata`.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Index, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import (
    AuditActorMixin,
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    pg_enum,
)
from app.modules.documents.domain.enums import DocumentCategory, DocumentStatus, StorageProvider

_document_category_enum = pg_enum(DocumentCategory, "document_category_enum")
_document_storage_provider_enum = pg_enum(StorageProvider, "document_storage_provider_enum")
_document_status_enum = pg_enum(DocumentStatus, "document_status_enum")


class MedicalDocumentModel(
    Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, AuditActorMixin
):
    __tablename__ = "medical_documents"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), nullable=False
    )
    uploaded_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    visit_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("patient_visits.id", ondelete="SET NULL"), default=None
    )
    appointment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("appointments.id", ondelete="SET NULL"), default=None
    )
    category: Mapped[DocumentCategory] = mapped_column(_document_category_enum, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    original_filename: Mapped[str] = mapped_column(Text, nullable=False)
    stored_filename: Mapped[str] = mapped_column(Text, nullable=False)
    mime_type: Mapped[str] = mapped_column(Text, nullable=False)
    extension: Mapped[str] = mapped_column(Text, nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    storage_provider: Mapped[StorageProvider] = mapped_column(
        _document_storage_provider_enum, nullable=False
    )
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[DocumentStatus] = mapped_column(_document_status_enum, nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(nullable=False)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    tags: Mapped[list[str] | None] = mapped_column(JSONB, default=None)
    document_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSONB, default=None
    )

    __table_args__ = (
        Index(
            "uq_medical_documents_stored_filename",
            "stored_filename",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("ix_medical_documents_organization_id", "organization_id"),
        Index("ix_medical_documents_patient_id", "patient_id"),
        Index("ix_medical_documents_visit_id", "visit_id"),
        Index("ix_medical_documents_appointment_id", "appointment_id"),
        Index("ix_medical_documents_checksum_sha256", "checksum_sha256"),
        CheckConstraint("file_size_bytes > 0", name="file_size_bytes_positive"),
    )
