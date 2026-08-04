"""`StructlogPrescriptionAuditLogger` — the one concrete
`PrescriptionAuditLoggerPort` implementation this task ships, per
"AUDIT — Record provider, model, latency, token usage, generation
status". Mirrors `app.modules.icd10_ai.infrastructure.audit.audit_logger
.StructlogICD10AuditLogger` exactly (structured `structlog` line via
`app.core.logging.get_logger`, IDs/enums/numbers only, never clinical
content — `06_configuration_logging_exceptions.md`'s "PHI is never
logged, at any layer" rule — medication names/dosages are never logged
here for the same reason).
"""

from uuid import UUID

from app.core.logging import get_logger
from app.modules.prescription_ai.application.ports import PrescriptionAuditLoggerPort
from app.modules.prescription_ai.domain.value_objects import GenerationSession

logger = get_logger(__name__)


class StructlogPrescriptionAuditLogger(PrescriptionAuditLoggerPort):
    async def log_generation(
        self, session: GenerationSession, *, organization_id: UUID, patient_id: UUID
    ) -> None:
        logger.info(
            "prescription_suggestion_generation",
            generation_id=str(session.generation_id),
            organization_id=str(organization_id),
            patient_id=str(patient_id),
            provider=session.provider,
            model=session.model,
            prescribing_setting=session.prescribing_setting,
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
            "prescription_suggestion_generation_failed",
            generation_id=str(generation_id),
            organization_id=str(organization_id),
            patient_id=str(patient_id),
            stage=stage,
            error_code=error_code,
            message=message,
        )
