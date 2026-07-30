"""`AuditLogFacade` — the one concrete implementation of
`AuditLogQueryPort`. Constructed per-request (or per future background
task) by `app.modules.audit_log.container.build_audit_log_facade`, bound
to that caller's `AsyncSession`.
"""

from uuid import UUID

from app.modules.audit_log.application.services.audit_log_query_service import (
    AuditLogQueryService,
)
from app.modules.audit_log.public.dto import AuditLogSummaryDTO
from app.modules.audit_log.public.interfaces import AuditLogQueryPort


class AuditLogFacade(AuditLogQueryPort):
    def __init__(self, *, query_service: AuditLogQueryService) -> None:
        self._query_service = query_service

    async def get_by_id(self, audit_log_id: UUID) -> AuditLogSummaryDTO | None:
        return await self._query_service.get_by_id(audit_log_id)

    async def list_for_entity(
        self, *, entity_type: str, entity_id: UUID
    ) -> list[AuditLogSummaryDTO]:
        return await self._query_service.list_for_entity(
            entity_type=entity_type, entity_id=entity_id
        )

    async def list_for_organization(
        self, organization_id: UUID, *, offset: int = 0, limit: int = 50
    ) -> list[AuditLogSummaryDTO]:
        return await self._query_service.list_for_organization(
            organization_id, offset=offset, limit=limit
        )

    async def list_for_actor(self, actor_user_id: UUID) -> list[AuditLogSummaryDTO]:
        return await self._query_service.list_for_actor(actor_user_id)
