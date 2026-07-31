"""Data Transfer Objects for the Documents module's application layer.

Distinct from both domain entities (never leave the module) and API
schemas (`api/schemas.py`). Use-case input/output DTOs are plain,
immutable dataclasses; `MedicalDocumentSummaryDTO` is also re-exported
from `public/dto.py` for other modules to depend on. `checksum_sha256` is
a plain `str` here (not `Sha256Checksum`) — DTOs carry primitives across
the use-case boundary, matching
`app.modules.attachments.application.dto`'s own documented convention;
the use case wraps it into the value object when constructing the domain
entity.

`UploadMedicalDocumentInput.file_data` is the one exception: a `BinaryIO`
stream, not a primitive — the use case hands it directly to
`StoragePort.upload()`. This is the first module in this codebase to
handle real file bytes; `api/schemas.py` unwraps FastAPI's `UploadFile`
into this stdlib type before it ever reaches the application layer,
keeping this DTO framework-agnostic.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, BinaryIO
from uuid import UUID

from app.modules.documents.domain.enums import DocumentCategory, DocumentStatus, StorageProvider

# --- UploadMedicalDocument --------------------------------------------------


@dataclass(frozen=True, slots=True)
class UploadMedicalDocumentInput:
    patient_id: UUID
    uploaded_by_user_id: UUID
    category: DocumentCategory
    title: str
    original_filename: str
    mime_type: str
    extension: str
    file_size_bytes: int
    checksum_sha256: str
    file_data: BinaryIO
    visit_id: UUID | None = None
    appointment_id: UUID | None = None
    description: str | None = None
    tags: list[str] | None = None
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class UploadMedicalDocumentOutput:
    document_id: UUID
    organization_id: UUID
    patient_id: UUID
    stored_filename: str
    storage_path: str


# --- UpdateMedicalDocumentDetails ------------------------------------------


@dataclass(frozen=True, slots=True)
class UpdateMedicalDocumentDetailsInput:
    document_id: UUID
    title: str | None = None
    description: str | None = None
    tags: list[str] | None = None
    category: DocumentCategory | None = None


@dataclass(frozen=True, slots=True)
class UpdateMedicalDocumentDetailsOutput:
    document_id: UUID


# --- Status transitions (Archive / Delete) ----------------------------------


@dataclass(frozen=True, slots=True)
class ArchiveMedicalDocumentInput:
    document_id: UUID


@dataclass(frozen=True, slots=True)
class DeleteMedicalDocumentInput:
    document_id: UUID


@dataclass(frozen=True, slots=True)
class MedicalDocumentStatusOutput:
    document_id: UUID
    status: DocumentStatus


# --- DownloadMedicalDocument -------------------------------------------------


@dataclass(frozen=True, slots=True)
class DownloadMedicalDocumentInput:
    document_id: UUID


@dataclass(frozen=True, slots=True)
class DownloadMedicalDocumentOutput:
    document_id: UUID
    original_filename: str
    mime_type: str
    file_data: bytes


# --- Cross-cutting read models (also re-exported via public/dto.py) --------


@dataclass(frozen=True, slots=True)
class MedicalDocumentSummaryDTO:
    document_id: UUID
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
    checksum_sha256: str
    status: DocumentStatus
    uploaded_at: datetime
    visit_id: UUID | None = None
    appointment_id: UUID | None = None
    description: str | None = None
    tags: list[str] | None = None
    metadata: dict[str, Any] | None = None

    @property
    def id(self) -> UUID:
        """Alias for `document_id` — see `AppointmentSummaryDTO.id`'s own
        docstring in `app.modules.appointment.application.dto` for the
        full reasoning (identical situation in every module)."""
        return self.document_id
