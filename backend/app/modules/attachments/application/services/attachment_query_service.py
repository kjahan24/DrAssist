"""Read-only queries against `VisitAttachment`.

Backs the module's public `AttachmentQueryPort` — the one implementation,
per `docs/backend-architecture/04_repository_and_service_patterns.md`'s
service-interface guidance (a formal interface earns its place at the
`public/` boundary; this internal service doesn't need a second one).

`get_attachment_summary`/`AttachmentSummaryDTO`'s extra fields were added
by the REST APIs task — see `app.modules.diagnosis.application.services
.diagnosis_query_service`'s own docstring for the identical reasoning.
`checksum_sha256` is coerced to `str` (the DTO boundary already treats it
as a primitive, matching `application/dto.py`'s own documented
convention).
"""

from uuid import UUID

from app.modules.attachments.application.dto import AttachmentSummaryDTO
from app.modules.attachments.domain.entities import VisitAttachment
from app.modules.attachments.domain.repositories import VisitAttachmentRepository


class VisitAttachmentQueryService:
    def __init__(self, *, attachment_repository: VisitAttachmentRepository) -> None:
        self._attachments = attachment_repository

    async def attachment_exists(self, attachment_id: UUID) -> bool:
        return await self._attachments.get_by_id(attachment_id) is not None

    async def get_attachment_summary(self, attachment_id: UUID) -> AttachmentSummaryDTO | None:
        attachment = await self._attachments.get_by_id(attachment_id)
        return _to_summary(attachment) if attachment is not None else None

    async def list_attachments_for_visit(self, visit_id: UUID) -> list[AttachmentSummaryDTO]:
        attachments = await self._attachments.list_by_visit(visit_id)
        return [_to_summary(attachment) for attachment in attachments]


def _to_summary(attachment: VisitAttachment) -> AttachmentSummaryDTO:
    return AttachmentSummaryDTO(
        attachment_id=attachment.id,
        organization_id=attachment.organization_id,
        visit_id=attachment.visit_id,
        file_name=attachment.file_name,
        attachment_type=attachment.attachment_type,
        original_file_name=attachment.original_file_name,
        mime_type=attachment.mime_type,
        file_size_bytes=attachment.file_size_bytes,
        storage_provider=attachment.storage_provider,
        storage_bucket=attachment.storage_bucket,
        storage_key=attachment.storage_key,
        checksum_sha256=str(attachment.checksum_sha256),
        uploaded_by=attachment.uploaded_by,
        uploaded_at=attachment.uploaded_at,
        description=attachment.description,
    )
