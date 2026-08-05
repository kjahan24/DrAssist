"""`StructlogWorkflowOrchestrationAuditLogger` — the one concrete
`WorkflowOrchestrationAuditLoggerPort` implementation this task ships,
per "AUDIT — workflow, execution order, latency, module timings,
failures, retry count". Mirrors every prior AI module's own audit
logger exactly (structured `structlog` line via `app.core.logging
.get_logger`, IDs/enums/numbers only, never clinical content —
`06_configuration_logging_exceptions.md`'s "PHI is never logged, at any
layer" rule — no step's own `summary` text is ever logged here for the
same reason).
"""

from uuid import UUID

from app.core.logging import get_logger
from app.modules.ai_orchestrator.application.ports import WorkflowOrchestrationAuditLoggerPort
from app.modules.ai_orchestrator.domain.value_objects import WorkflowExecutionSession

logger = get_logger(__name__)


class StructlogWorkflowOrchestrationAuditLogger(WorkflowOrchestrationAuditLoggerPort):
    async def log_execution(
        self, session: WorkflowExecutionSession, *, organization_id: UUID, patient_id: UUID
    ) -> None:
        logger.info(
            "workflow_execution",
            execution_id=str(session.execution_id),
            organization_id=str(organization_id),
            patient_id=str(patient_id),
            workflow_name=session.workflow_name,
            execution_order=[module.value for module in session.execution_order],
            total_latency_ms=round(session.total_latency_ms, 2),
            module_timings={
                module.value: round(latency_ms, 2)
                for module, latency_ms in session.module_timings.items()
            },
            failure_count=session.failure_count,
            retry_count=session.retry_count,
            status=session.status.value,
        )

    async def log_failure(
        self,
        *,
        execution_id: UUID,
        organization_id: UUID,
        patient_id: UUID,
        stage: str,
        error_code: str,
        message: str,
    ) -> None:
        logger.warning(
            "workflow_execution_failed",
            execution_id=str(execution_id),
            organization_id=str(organization_id),
            patient_id=str(patient_id),
            stage=stage,
            error_code=error_code,
            message=message,
        )
