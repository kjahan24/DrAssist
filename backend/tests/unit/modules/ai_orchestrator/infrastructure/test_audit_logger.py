"""Unit tests for `StructlogWorkflowOrchestrationAuditLogger` — verifies
it logs without raising for both the success and failure paths."""

from uuid import uuid4

from app.modules.ai_orchestrator.domain.enums import WorkflowModule, WorkflowStatus
from app.modules.ai_orchestrator.domain.value_objects import WorkflowExecutionSession
from app.modules.ai_orchestrator.infrastructure.audit.audit_logger import (
    StructlogWorkflowOrchestrationAuditLogger,
)


def _session() -> WorkflowExecutionSession:
    return WorkflowExecutionSession(
        execution_id=uuid4(),
        workflow_name="test-workflow",
        execution_order=(WorkflowModule.CLINICAL_NOTE,),
        total_latency_ms=10.0,
        module_timings={WorkflowModule.CLINICAL_NOTE: 10.0},
        failure_count=0,
        retry_count=0,
        status=WorkflowStatus.COMPLETED,
    )


class TestStructlogWorkflowOrchestrationAuditLogger:
    async def test_log_execution_does_not_raise(self) -> None:
        logger = StructlogWorkflowOrchestrationAuditLogger()
        await logger.log_execution(_session(), organization_id=uuid4(), patient_id=uuid4())

    async def test_log_failure_does_not_raise(self) -> None:
        logger = StructlogWorkflowOrchestrationAuditLogger()
        await logger.log_failure(
            execution_id=uuid4(),
            organization_id=uuid4(),
            patient_id=uuid4(),
            stage="validate_graph",
            error_code="DuplicateModuleExecutionError",
            message="module 'clinical_note' is listed more than once",
        )
