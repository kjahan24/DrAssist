"""Documents module aggregate root: `MedicalDocument`.

References `Patient` (`patient_id`), and optionally `Visit`/`Appointment`
(`visit_id`/`appointment_id`), as peers by ID only (never an object
reference) — validated by the application layer via those modules' public
`PatientQueryPort`/`VisitQueryPort`/`AppointmentQueryPort` (see
`application/use_cases/upload_medical_document.py`), never by importing
across `domain/` packages, the same rule every prior module's own entity
docstring states.

This entity stores **only file metadata** — `storage_provider`/
`storage_path` are a pointer into wherever `StorageProvider`'s configured
adapter actually put the bytes (local disk today; S3/Azure/GCS are
recorded as possible values but have no adapter yet — see `domain/enums
.py`), never the file bytes themselves. `checksum_sha256` is the one
value object this module needs (`Sha256Checksum`, in `value_objects.py`).

Status is a strict, linear workflow — `Uploading -> Active -> Archived ->
Deleted`, no skipping — matching this task's own explicit rule almost
verbatim and the identical strict-chain enforcement
`app.modules.clinical_notes.domain.entities.ClinicalNote` already
establishes for its own `Draft -> In Review -> Signed -> Locked` chain.
`activate()` is called once the use case has confirmed the file was
actually written to storage (see the upload use case); a document that
never leaves `Uploading` in the database only happens if that write, or
the surrounding transaction, failed — nothing here performs I/O, so this
entity has no way to know which.

Unlike `created_at`/`updated_at` (inherited from `AggregateRoot`),
`deleted_at` is never a field on this — or any — domain entity in this
codebase; it is a purely infrastructure-level soft-delete marker. "Deleted
documents are soft deleted" is satisfied by the *mapper* setting the ORM
model's `deleted_at` the moment it sees `status is DocumentStatus.DELETED`
(see `infrastructure/mappers.py`) — the same "mapper is the only place
that knows both shapes" principle already used everywhere else, applied
here to bridge a business status to the infrastructure-only soft-delete
column without teaching the domain layer about it.

`update_details()` only allows changing `title`/`description`/`tags`/
`category` — organizational metadata a caller might reasonably want to
correct after the fact. Every other field (`original_filename`,
`stored_filename`, `mime_type`, `extension`, `storage_*`,
`checksum_sha256`, `file_size_bytes`) describes the *physical file
itself*; mutating any of them without re-uploading would desync the
database record from what is actually in storage — the identical
reasoning `app.modules.attachments.domain.entities.VisitAttachment
.update_details()` documents for its own, stricter (description-only)
version of this same rule.

All mutation goes through named methods that enforce the aggregate's
invariants and record domain events; nothing here performs I/O.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from app.modules.documents.domain.enums import DocumentCategory, DocumentStatus, StorageProvider
from app.modules.documents.domain.events import (
    MedicalDocumentStatusChanged,
    MedicalDocumentUpdated,
    MedicalDocumentUploaded,
)
from app.modules.documents.domain.exceptions import (
    ExtensionRequiredError,
    InvalidDocumentStatusTransitionError,
    MimeTypeRequiredError,
    NonPositiveFileSizeError,
    OriginalFilenameRequiredError,
    StoragePathRequiredError,
    StoredFilenameRequiredError,
    TitleRequiredError,
)
from app.modules.documents.domain.value_objects import Sha256Checksum
from app.shared.domain.entity import AggregateRoot

_TRANSITIONS: dict[DocumentStatus, DocumentStatus] = {
    DocumentStatus.UPLOADING: DocumentStatus.ACTIVE,
    DocumentStatus.ACTIVE: DocumentStatus.ARCHIVED,
    DocumentStatus.ARCHIVED: DocumentStatus.DELETED,
}


@dataclass(kw_only=True, eq=False)
class MedicalDocument(AggregateRoot):
    organization_id: UUID
    patient_id: UUID
    uploaded_by_user_id: UUID
    category: DocumentCategory
    title: str
    original_filename: str
    stored_filename: str
    mime_type: str
    extension: str
    file_size_bytes: int
    storage_provider: StorageProvider
    storage_path: str
    checksum_sha256: Sha256Checksum
    uploaded_at: datetime
    visit_id: UUID | None = None
    appointment_id: UUID | None = None
    status: DocumentStatus = DocumentStatus.UPLOADING
    description: str | None = None
    tags: list[str] | None = None
    metadata: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if not self.title or not self.title.strip():
            raise TitleRequiredError()
        self.title = self.title.strip()
        if not self.original_filename or not self.original_filename.strip():
            raise OriginalFilenameRequiredError()
        self.original_filename = self.original_filename.strip()
        if not self.stored_filename or not self.stored_filename.strip():
            raise StoredFilenameRequiredError()
        self.stored_filename = self.stored_filename.strip()
        if not self.mime_type or not self.mime_type.strip():
            raise MimeTypeRequiredError()
        self.mime_type = self.mime_type.strip()
        if not self.extension or not self.extension.strip():
            raise ExtensionRequiredError()
        self.extension = self.extension.strip()
        if not self.storage_path or not self.storage_path.strip():
            raise StoragePathRequiredError()
        self.storage_path = self.storage_path.strip()
        _validate_file_size_bytes(self.file_size_bytes)

    @classmethod
    def create(
        cls,
        *,
        organization_id: UUID,
        patient_id: UUID,
        uploaded_by_user_id: UUID,
        category: DocumentCategory,
        title: str,
        original_filename: str,
        stored_filename: str,
        mime_type: str,
        extension: str,
        file_size_bytes: int,
        storage_provider: StorageProvider,
        storage_path: str,
        checksum_sha256: Sha256Checksum,
        uploaded_at: datetime,
        visit_id: UUID | None = None,
        appointment_id: UUID | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "MedicalDocument":
        document = cls(
            organization_id=organization_id,
            patient_id=patient_id,
            uploaded_by_user_id=uploaded_by_user_id,
            category=category,
            title=title,
            original_filename=original_filename,
            stored_filename=stored_filename,
            mime_type=mime_type,
            extension=extension,
            file_size_bytes=file_size_bytes,
            storage_provider=storage_provider,
            storage_path=storage_path,
            checksum_sha256=checksum_sha256,
            uploaded_at=uploaded_at,
            visit_id=visit_id,
            appointment_id=appointment_id,
            description=description,
            tags=tags,
            metadata=metadata,
        )
        document.record_event(
            MedicalDocumentUploaded(
                document_id=document.id,
                organization_id=organization_id,
                patient_id=patient_id,
                stored_filename=document.stored_filename,
            )
        )
        return document

    def activate(self) -> None:
        """Uploading -> Active. Called once the use case has confirmed the
        file was actually written to storage."""
        self._transition(DocumentStatus.ACTIVE)

    def archive(self) -> None:
        """Active -> Archived."""
        self._transition(DocumentStatus.ARCHIVED)

    def soft_delete(self) -> None:
        """Archived -> Deleted. See this module's own docstring for how
        the ORM mapper translates this into the infrastructure-level
        `deleted_at` soft-delete column."""
        self._transition(DocumentStatus.DELETED)

    def update_details(
        self,
        *,
        title: str | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
        category: DocumentCategory | None = None,
    ) -> None:
        if title is not None:
            if not title.strip():
                raise TitleRequiredError()
            self.title = title.strip()
        if description is not None:
            self.description = description
        if tags is not None:
            self.tags = tags
        if category is not None:
            self.category = category

        self.touch()
        self.record_event(MedicalDocumentUpdated(document_id=self.id))

    def _transition(self, target_status: DocumentStatus) -> None:
        expected_next = _TRANSITIONS.get(self.status)
        if expected_next is not target_status:
            raise InvalidDocumentStatusTransitionError(self.status.value, target_status.value)
        old_status = self.status
        self.status = target_status
        self.touch()
        self.record_event(
            MedicalDocumentStatusChanged(
                document_id=self.id, old_status=old_status, new_status=target_status
            )
        )


def _validate_file_size_bytes(value: int) -> None:
    if value <= 0:
        raise NonPositiveFileSizeError(value)
