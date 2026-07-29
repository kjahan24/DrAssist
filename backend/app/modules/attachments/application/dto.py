"""Data Transfer Objects for the Attachments module's application layer.

Distinct from both domain entities (never leave the module) and API
schemas (`api/schemas.py`, not yet wired to any endpoint). Use-case
input/output DTOs are plain, immutable dataclasses; `AttachmentSummaryDTO`
is also re-exported from `public/dto.py` for other modules to depend on.
`checksum_sha256` is a plain `str` here (not `Sha256Checksum`) — DTOs
carry primitives across the use-case boundary, matching how
`app.modules.patient.application.dto.AddPatientContactInput.phone_number`
is `str`, not `PhoneNumber`; the use case wraps it into the value object
when constructing the domain entity.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.modules.attachments.domain.enums import AttachmentType, StorageProvider

# --- UploadVisitAttachment -----------------------------------------------


@dataclass(frozen=True, slots=True)
class UploadVisitAttachmentInput:
    visit_id: UUID
    attachment_type: AttachmentType
    file_name: str
    original_file_name: str
    mime_type: str
    file_size_bytes: int
    storage_provider: StorageProvider
    storage_bucket: str
    storage_key: str
    checksum_sha256: str
    uploaded_at: datetime
    uploaded_by: UUID | None = None
    description: str | None = None
    created_by: UUID | None = None


@dataclass(frozen=True, slots=True)
class UploadVisitAttachmentOutput:
    attachment_id: UUID
    organization_id: UUID
    visit_id: UUID
    storage_key: str


# --- Cross-cutting read models (also re-exported via public/dto.py) --------


@dataclass(frozen=True, slots=True)
class AttachmentSummaryDTO:
    attachment_id: UUID
    organization_id: UUID
    visit_id: UUID
    file_name: str
    attachment_type: AttachmentType
