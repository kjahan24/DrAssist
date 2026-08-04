"""`StructlogCopilotAuditLogger` — the one concrete `CopilotAuditLoggerPort`
implementation this task ships, mirroring AI Foundation's own
`infrastructure/providers/audit_logger.py::StructlogAIAuditLogger` exactly
(structured `structlog` line via `app.core.logging.get_logger`, IDs/enums/
numbers only, never message content) — see `application/ports.py`'s
module docstring for why this is a *separate*, copilot-scoped audit
record rather than a reuse of AI Foundation's own.
"""

from uuid import UUID

from app.core.logging import get_logger
from app.modules.ai_copilot.application.ports import CopilotAuditLoggerPort
from app.modules.ai_copilot.domain.value_objects import AISession

logger = get_logger(__name__)


class StructlogCopilotAuditLogger(CopilotAuditLoggerPort):
    async def log_session(self, session: AISession, *, request_type: str, patient_id: UUID) -> None:
        logger.info(
            "ai_copilot_session",
            request_id=str(session.request_id),
            request_type=request_type,
            patient_id=str(patient_id),
            provider=session.provider,
            model=session.model,
            prompt_name=session.prompt_name,
            prompt_version=session.prompt_version,
            latency_ms=round(session.latency_ms, 2),
            prompt_tokens=session.prompt_tokens,
            completion_tokens=session.completion_tokens,
            total_tokens=session.total_tokens,
            estimated_cost_usd=round(session.estimated_cost_usd, 6),
        )

    async def log_failure(
        self,
        *,
        request_id: UUID,
        request_type: str,
        patient_id: UUID,
        stage: str,
        error_code: str,
        message: str,
    ) -> None:
        logger.warning(
            "ai_copilot_session_failed",
            request_id=str(request_id),
            request_type=request_type,
            patient_id=str(patient_id),
            stage=stage,
            error_code=error_code,
            message=message,
        )
