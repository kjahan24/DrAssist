"""Pydantic v2 request/response schemas for the Attachments module.

Not yet wired to any route — `api/router.py` registers no endpoints in
this phase. Schemas never expose a domain entity directly, and never
accept server-controlled fields (`id`, `organization_id`, ...) from the
client — see `docs/backend-architecture/07_security_layer.md §7`
(mass-assignment prevention). Note that no endpoint here ever accepts raw
file bytes either — this module only ever handles upload *metadata*
(see `domain/entities.py`); the actual file transfer to object storage
is out of scope for this task.
"""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.modules.attachments.domain.enums import AttachmentType, StorageProvider
from app.schemas.base import ORJSONModel


class VisitAttachmentResponse(ORJSONModel):
    id: UUID
    organization_id: UUID
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
    uploaded_by: UUID | None = None
    uploaded_at: datetime
    description: str | None = None


class UploadVisitAttachmentRequest(ORJSONModel):
    visit_id: UUID
    attachment_type: AttachmentType
    file_name: str = Field(min_length=1, max_length=255)
    original_file_name: str = Field(min_length=1, max_length=255)
    mime_type: str = Field(min_length=1, max_length=255)
    file_size_bytes: int = Field(gt=0)
    storage_provider: StorageProvider
    storage_bucket: str = Field(min_length=1, max_length=255)
    storage_key: str = Field(min_length=1, max_length=1024)
    checksum_sha256: str = Field(min_length=64, max_length=64)
    uploaded_by: UUID | None = None
    uploaded_at: datetime
    description: str | None = Field(default=None, max_length=1000)
