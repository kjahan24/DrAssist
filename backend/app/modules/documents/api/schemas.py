"""Pydantic v2 request/response schemas for the Documents module.

The upload endpoint (`POST` in `api/router.py`) accepts
`multipart/form-data` (`UploadFile` + individual `Form(...)` fields) —
the first endpoint in this codebase to handle real file bytes (contrast
`app.modules.attachments.api.schemas`, which only ever records upload
*metadata* and has no request schema for bytes at all). FastAPI cannot
bind a JSON body model to a multipart request, so those fields are
declared directly as parameters on the router's `upload_document`
handler rather than as a `BaseModel` here; only the JSON-bodied
"update details" endpoint gets a request schema below.

Schemas never expose a domain entity directly, and never accept
server-controlled fields (`id`, `organization_id`, `stored_filename`,
`storage_path`, `checksum_sha256`, `status`, ...) from the client — see
`docs/backend-architecture/07_security_layer.md §7` (mass-assignment
prevention). `checksum_sha256` and `file_size_bytes` are computed by the
server from the uploaded bytes themselves — a client-supplied checksum
couldn't be trusted without re-reading the file anyway, and re-reading it
makes the server-computed value authoritative regardless.

`metadata` (the entity's free-form JSONB column) is deliberately not
exposed on any endpoint in this phase — no requirement names a concrete
producer/consumer of it yet (a future OCR/AI-analysis integration is the
expected one — see `container.py`'s own scope note); the column exists
so that integration can populate it later without a schema change.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from app.modules.documents.domain.enums import DocumentCategory, DocumentStatus, StorageProvider
from app.schemas.base import ORJSONModel


class MedicalDocumentResponse(ORJSONModel):
    id: UUID
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


class UpdateMedicalDocumentDetailsRequest(ORJSONModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    tags: list[str] | None = None
    category: DocumentCategory | None = None
