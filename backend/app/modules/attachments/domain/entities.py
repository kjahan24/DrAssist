"""Attachments module aggregate root: `VisitAttachment`.

A single aggregate for this foundation task. `VisitAttachment` is not
"owned by" the Visit module — like `VisitProcedure`, it references
`Visit` (`visit_id`) and, optionally, `Doctor` (`uploaded_by`) as peers,
each by ID only (never an object reference), validated by the
application layer via those modules' public `VisitQueryPort`/
`DoctorQueryPort` (see `application/use_cases/upload_attachment.py`),
never by importing across `domain/` packages — see
`docs/backend-architecture/03_module_architecture.md`. Unlike the prior
four Visit sub-modules, there is no `sequence_number` here — nothing in
this task orders attachments relative to each other, so none is
invented; `list_by_visit` orders by `uploaded_at` instead (see
`infrastructure/repositories.py`).

This entity stores **only file metadata** — `storage_provider`/
`storage_bucket`/`storage_key` are pointers into external object storage,
never the file bytes themselves ("Store only metadata in PostgreSQL.
Never store binary file data in the database" is a hard constraint this
task states explicitly, not a style preference); there is deliberately
no column here that could hold binary content.

`checksum_sha256` is the one value object this module needs
(`Sha256Checksum`, in `value_objects.py`) — see that module's own
docstring for why a format constraint is justified here where it wasn't
for `icd10_code`/`procedure_code` in prior modules.

`update_details()` only allows changing `description` — every other
field (`file_name`, `mime_type`, `storage_*`, `checksum_sha256`,
`attachment_type`, ...) describes the *physical file itself*; mutating
any of them without re-uploading would desync the database record from
what's actually in object storage. This is a stricter version of the
"exclude identity/attribution fields" pattern every prior module's
`update_details()` follows, taken to its logical conclusion given how
little of this aggregate is actually free-text metadata.

All mutation goes through named methods that enforce the aggregate's
invariants and record domain events; nothing here performs I/O.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.modules.attachments.domain.enums import AttachmentType, StorageProvider
from app.modules.attachments.domain.events import (
    VisitAttachmentUpdated,
    VisitAttachmentUploaded,
)
from app.modules.attachments.domain.exceptions import (
    FileNameRequiredError,
    MimeTypeRequiredError,
    NonPositiveFileSizeError,
    OriginalFileNameRequiredError,
    StorageBucketRequiredError,
    StorageKeyRequiredError,
)
from app.modules.attachments.domain.value_objects import Sha256Checksum
from app.shared.domain.entity import AggregateRoot


@dataclass(kw_only=True, eq=False)
class VisitAttachment(AggregateRoot):
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
    checksum_sha256: Sha256Checksum
    uploaded_at: datetime
    uploaded_by: UUID | None = None
    description: str | None = None

    def __post_init__(self) -> None:
        if not self.file_name or not self.file_name.strip():
            raise FileNameRequiredError()
        self.file_name = self.file_name.strip()
        if not self.original_file_name or not self.original_file_name.strip():
            raise OriginalFileNameRequiredError()
        self.original_file_name = self.original_file_name.strip()
        if not self.mime_type or not self.mime_type.strip():
            raise MimeTypeRequiredError()
        self.mime_type = self.mime_type.strip()
        if not self.storage_bucket or not self.storage_bucket.strip():
            raise StorageBucketRequiredError()
        self.storage_bucket = self.storage_bucket.strip()
        if not self.storage_key or not self.storage_key.strip():
            raise StorageKeyRequiredError()
        self.storage_key = self.storage_key.strip()
        _validate_file_size_bytes(self.file_size_bytes)

    @classmethod
    def create(
        cls,
        *,
        organization_id: UUID,
        visit_id: UUID,
        attachment_type: AttachmentType,
        file_name: str,
        original_file_name: str,
        mime_type: str,
        file_size_bytes: int,
        storage_provider: StorageProvider,
        storage_bucket: str,
        storage_key: str,
        checksum_sha256: Sha256Checksum,
        uploaded_at: datetime,
        uploaded_by: UUID | None = None,
        description: str | None = None,
    ) -> "VisitAttachment":
        attachment = cls(
            organization_id=organization_id,
            visit_id=visit_id,
            attachment_type=attachment_type,
            file_name=file_name,
            original_file_name=original_file_name,
            mime_type=mime_type,
            file_size_bytes=file_size_bytes,
            storage_provider=storage_provider,
            storage_bucket=storage_bucket,
            storage_key=storage_key,
            checksum_sha256=checksum_sha256,
            uploaded_at=uploaded_at,
            uploaded_by=uploaded_by,
            description=description,
        )
        attachment.record_event(
            VisitAttachmentUploaded(
                attachment_id=attachment.id,
                organization_id=organization_id,
                visit_id=visit_id,
                storage_key=attachment.storage_key,
            )
        )
        return attachment

    def update_details(self, *, description: str | None = None) -> None:
        if description is not None:
            self.description = description

        self.touch()
        self.record_event(VisitAttachmentUpdated(attachment_id=self.id, visit_id=self.visit_id))


def _validate_file_size_bytes(value: int) -> None:
    if value <= 0:
        raise NonPositiveFileSizeError(value)
