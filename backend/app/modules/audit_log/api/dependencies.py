"""Module-specific FastAPI dependency provider.

New — this module had no `api/` package before the REST APIs task (see
`container.py`'s scope note). Read-only: only a query service provider is
needed here — there is no use-case provider, since this router exposes no
write endpoint (see `api/schemas.py`'s own docstring for why).
"""

from typing import Annotated

from fastapi import Depends

from app.api.deps import DbSession
from app.modules.audit_log.application.services.audit_log_query_service import (
    AuditLogQueryService,
)
from app.modules.audit_log.domain.repositories import AuditLogRepository
from app.modules.audit_log.infrastructure.repositories import SqlAlchemyAuditLogRepository


def get_audit_log_repository(session: DbSession) -> AuditLogRepository:
    return SqlAlchemyAuditLogRepository(session)


AuditLogRepo = Annotated[AuditLogRepository, Depends(get_audit_log_repository)]


def get_audit_log_query_service(audit_log_repository: AuditLogRepo) -> AuditLogQueryService:
    return AuditLogQueryService(audit_log_repository=audit_log_repository)
