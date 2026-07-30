"""`RecordAuditLog` — validates the actor's organization (when an actor
is given) via `AuditLogConsistencyService.validate_actor_organization()`,
then persists an immutable `AuditLog` row.

Named `RecordAuditLog`, not `CreateAuditLog` — matching `AuditLog.record()`
itself; see that factory's own docstring for why `Create<X>` would be
ambiguous here (`AuditAction.CREATE` is a distinct concept: the *kind* of
event being recorded, not this use case's own action).
"""

from app.modules.audit_log.application.dto import RecordAuditLogInput, RecordAuditLogOutput
from app.modules.audit_log.application.services.audit_log_consistency_service import (
    AuditLogConsistencyService,
)
from app.modules.audit_log.domain.entities import AuditLog
from app.modules.audit_log.domain.repositories import AuditLogRepository
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class RecordAuditLog(UseCase[RecordAuditLogInput, RecordAuditLogOutput]):
    def __init__(
        self,
        *,
        audit_log_repository: AuditLogRepository,
        consistency_service: AuditLogConsistencyService,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._audit_logs = audit_log_repository
        self._consistency = consistency_service
        self._uow = unit_of_work

    async def execute(self, input_dto: RecordAuditLogInput) -> RecordAuditLogOutput:
        await self._consistency.validate_actor_organization(
            actor_user_id=input_dto.actor_user_id, organization_id=input_dto.organization_id
        )

        audit_log = AuditLog.record(
            organization_id=input_dto.organization_id,
            entity_type=input_dto.entity_type,
            entity_id=input_dto.entity_id,
            action=input_dto.action,
            source=input_dto.source,
            actor_user_id=input_dto.actor_user_id,
            old_values=input_dto.old_values,
            new_values=input_dto.new_values,
            ip_address=input_dto.ip_address,
            user_agent=input_dto.user_agent,
            request_id=input_dto.request_id,
            correlation_id=input_dto.correlation_id,
        )
        await self._audit_logs.add(audit_log)
        await self._uow.commit()

        return RecordAuditLogOutput(audit_log_id=audit_log.id, created_at=audit_log.created_at)
