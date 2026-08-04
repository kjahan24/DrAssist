"""Unit tests for `StructlogCopilotAuditLogger` — verifies it logs without
raising for both the success and failure paths."""

from uuid import uuid4

from app.modules.ai_copilot.domain.value_objects import AISession
from app.modules.ai_copilot.infrastructure.audit.audit_logger import StructlogCopilotAuditLogger


class TestStructlogCopilotAuditLogger:
    async def test_log_session_does_not_raise(self) -> None:
        logger = StructlogCopilotAuditLogger()
        session = AISession(
            request_id=uuid4(),
            provider="mock",
            model="mock-model",
            prompt_name="generic",
            prompt_version=1,
            latency_ms=1.0,
            prompt_tokens=1,
            completion_tokens=1,
            total_tokens=2,
            estimated_cost_usd=0.0,
        )
        await logger.log_session(session, request_type="generic", patient_id=uuid4())

    async def test_log_failure_does_not_raise(self) -> None:
        logger = StructlogCopilotAuditLogger()
        await logger.log_failure(
            request_id=uuid4(),
            request_type="generic",
            patient_id=uuid4(),
            stage="context_assembly",
            error_code="PatientNotFoundError",
            message="no patient found",
        )
