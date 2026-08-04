"""`StructlogMedicalReasoningAuditLogger` — the one concrete
`MedicalReasoningAuditLoggerPort` implementation this task ships, per
"AUDIT — provider, model, latency, token usage, reasoning status".
Mirrors `app.modules.differential_diagnosis_ai.infrastructure.audit
.audit_logger.StructlogDifferentialDiagnosisAuditLogger` exactly
(structured `structlog` line via `app.core.logging.get_logger`, IDs/
enums/numbers only, never clinical content —
`06_configuration_logging_exceptions.md`'s "PHI is never logged, at any
layer" rule — evidence/reasoning text is never logged here for the same
reason).
"""

from uuid import UUID

from app.core.logging import get_logger
from app.modules.medical_reasoning_ai.application.ports import MedicalReasoningAuditLoggerPort
from app.modules.medical_reasoning_ai.domain.value_objects import GenerationSession

logger = get_logger(__name__)


class StructlogMedicalReasoningAuditLogger(MedicalReasoningAuditLoggerPort):
    async def log_generation(
        self, session: GenerationSession, *, organization_id: UUID, patient_id: UUID
    ) -> None:
        logger.info(
            "medical_reasoning_generation",
            generation_id=str(session.generation_id),
            organization_id=str(organization_id),
            patient_id=str(patient_id),
            provider=session.provider,
            model=session.model,
            reasoning_setting=session.reasoning_setting,
            language=session.language,
            status=session.status.value,
            latency_ms=round(session.latency_ms, 2),
            prompt_tokens=session.prompt_tokens,
            completion_tokens=session.completion_tokens,
            total_tokens=session.total_tokens,
            estimated_cost_usd=round(session.estimated_cost_usd, 6),
        )

    async def log_failure(
        self,
        *,
        generation_id: UUID,
        organization_id: UUID,
        patient_id: UUID,
        stage: str,
        error_code: str,
        message: str,
    ) -> None:
        logger.warning(
            "medical_reasoning_generation_failed",
            generation_id=str(generation_id),
            organization_id=str(organization_id),
            patient_id=str(patient_id),
            stage=stage,
            error_code=error_code,
            message=message,
        )
