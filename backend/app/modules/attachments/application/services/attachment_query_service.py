"""Read-only queries against `VisitAttachment`.

Backs the module's public `AttachmentQueryPort` — the one implementation,
per `docs/backend-architecture/04_repository_and_service_patterns.md`'s
service-interface guidance (a formal interface earns its place at the
`public/` boundary; this internal service doesn't need a second one).
"""

from uuid import UUID

from app.modules.attachments.application.dto import AttachmentSummaryDTO
from app.modules.attachments.domain.repositories import VisitAttachmentRepository


class VisitAttachmentQueryService:
    def __init__(self, *, attachment_repository: VisitAttachmentRepository) -> None:
        self._attachments = attachment_repository

    async def attachment_exists(self, attachment_id: UUID) -> bool:
        return await self._attachments.get_by_id(attachment_id) is not None

    async def list_attachments_for_visit(self, visit_id: UUID) -> list[AttachmentSummaryDTO]:
        attachments = await self._attachments.list_by_visit(visit_id)
        return [
            AttachmentSummaryDTO(
                attachment_id=attachment.id,
                organization_id=attachment.organization_id,
                visit_id=attachment.visit_id,
                file_name=attachment.file_name,
                attachment_type=attachment.attachment_type,
            )
            for attachment in attachments
        ]
