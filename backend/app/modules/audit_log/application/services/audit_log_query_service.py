"""Read-only queries against `AuditLog`.

Backs the module's public `AuditLogQueryPort` — the one implementation,
per `docs/backend-architecture/04_repository_and_service_patterns.md`'s
service-interface guidance (a formal interface earns its place at the
`public/` boundary; this internal service doesn't need a second one).

`list_for_entity`/`list_for_organization`/`list_for_actor` are the three
natural read axes `docs/database/06_audit_and_activity.md` itself
identifies for this table: "show me the history of this row", an
organization-wide activity feed, and "show this user's activity" — the
same three the doc's own index strategy is built around (see
`infrastructure/models.py`).
"""

from collections.abc import Sequence
from datetime import datetime
from typing import Literal
from uuid import UUID

from app.modules.audit_log.application.dto import AuditLogSummaryDTO
from app.modules.audit_log.domain.entities import AuditLog
from app.modules.audit_log.domain.enums import AuditAction, AuditSource
from app.modules.audit_log.domain.repositories import AuditLogRepository


class AuditLogQueryService:
    def __init__(self, *, audit_log_repository: AuditLogRepository) -> None:
        self._audit_logs = audit_log_repository

    async def get_by_id(self, audit_log_id: UUID) -> AuditLogSummaryDTO | None:
        audit_log = await self._audit_logs.get_by_id(audit_log_id)
        return _to_summary(audit_log) if audit_log is not None else None

    async def list_for_entity(
        self, *, entity_type: str, entity_id: UUID
    ) -> list[AuditLogSummaryDTO]:
        audit_logs = await self._audit_logs.list_for_entity(
            entity_type=entity_type, entity_id=entity_id
        )
        return [_to_summary(audit_log) for audit_log in audit_logs]

    async def list_for_organization(
        self, organization_id: UUID, *, offset: int = 0, limit: int = 50
    ) -> list[AuditLogSummaryDTO]:
        audit_logs = await self._audit_logs.list_for_organization(
            organization_id, offset=offset, limit=limit
        )
        return [_to_summary(audit_log) for audit_log in audit_logs]

    async def list_for_actor(self, actor_user_id: UUID) -> list[AuditLogSummaryDTO]:
        audit_logs = await self._audit_logs.list_for_actor(actor_user_id)
        return [_to_summary(audit_log) for audit_log in audit_logs]

    async def search(
        self,
        *,
        organization_id: UUID,
        query: str | None = None,
        actions: Sequence[AuditAction] | None = None,
        sources: Sequence[AuditSource] | None = None,
        entity_type: str | None = None,
        entity_id: UUID | None = None,
        actor_user_id: UUID | None = None,
        correlation_id: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        sort_by: str = "created_at",
        sort_order: Literal["asc", "desc"] = "desc",
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[AuditLogSummaryDTO], int]:
        """Search & Filtering module — see `AuditLogRepository.search`'s
        docstring for filter/sort/pagination semantics."""
        audit_logs, total = await self._audit_logs.search(
            organization_id=organization_id,
            query=query,
            actions=actions,
            sources=sources,
            entity_type=entity_type,
            entity_id=entity_id,
            actor_user_id=actor_user_id,
            correlation_id=correlation_id,
            created_from=created_from,
            created_to=created_to,
            sort_by=sort_by,
            sort_order=sort_order,
            offset=offset,
            limit=limit,
        )
        return [_to_summary(audit_log) for audit_log in audit_logs], total


def _to_summary(audit_log: AuditLog) -> AuditLogSummaryDTO:
    return AuditLogSummaryDTO(
        audit_log_id=audit_log.id,
        organization_id=audit_log.organization_id,
        actor_user_id=audit_log.actor_user_id,
        entity_type=audit_log.entity_type,
        entity_id=audit_log.entity_id,
        action=audit_log.action,
        source=audit_log.source,
        old_values=audit_log.old_values,
        new_values=audit_log.new_values,
        ip_address=audit_log.ip_address,
        user_agent=audit_log.user_agent,
        request_id=audit_log.request_id,
        correlation_id=audit_log.correlation_id,
        created_at=audit_log.created_at,
    )
