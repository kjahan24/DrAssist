"""`AttachmentFacade` — the one concrete implementation of
`AttachmentQueryPort`. Constructed per-request by
`app.modules.attachments.container.build_attachment_facade`, bound to
that request's `AsyncSession`.
"""

from uuid import UUID

from app.modules.attachments.application.services.attachment_query_service import (
    VisitAttachmentQueryService,
)
from app.modules.attachments.public.dto import AttachmentSummaryDTO
from app.modules.attachments.public.interfaces import AttachmentQueryPort


class AttachmentFacade(AttachmentQueryPort):
    def __init__(self, *, query_service: VisitAttachmentQueryService) -> None:
        self._query_service = query_service

    async def attachment_exists(self, attachment_id: UUID) -> bool:
        return await self._query_service.attachment_exists(attachment_id)

    async def list_attachments_for_visit(self, visit_id: UUID) -> list[AttachmentSummaryDTO]:
        return await self._query_service.list_attachments_for_visit(visit_id)
