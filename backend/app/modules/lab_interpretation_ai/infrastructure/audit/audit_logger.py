"""`StructlogLabInterpretationAuditLogger` — the one concrete
`LabInterpretationAuditLoggerPort` implementation this task ships, per
"AUDIT — provider, model, latency, token usage, interpretation status".
Mirrors every prior AI module's own audit logger exactly (structured
`structlog` line via `app.core.logging.get_logger`, IDs/enums/numbers
only, never clinical content — `06_configuration_logging_exceptions.md`'s
"PHI is never logged, at any layer" rule — lab values/interpretation text
are never logged here for the same reason).
"""

from uuid import UUID

from app.core.logging import get_logger
from app.modules.lab_interpretation_ai.application.ports import LabInterpretationAuditLoggerPort
from app.modules.lab_interpretation_ai.domain.value_objects import GenerationSession

logger = get_logger(__name__)


class StructlogLabInterpretationAuditLogger(LabInterpretationAuditLoggerPort):
    async def log_generation(
        self, session: GenerationSession, *, organization_id: UUID, patient_id: UUID
    ) -> None:
        logger.info(
            "lab_interpretation_generation",
            generation_id=str(session.generation_id),
            organization_id=str(organization_id),
            patient_id=str(patient_id),
            provider=session.provider,
            model=session.model,
            lab_setting=session.lab_setting,
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
            "lab_interpretation_generation_failed",
            generation_id=str(generation_id),
            organization_id=str(organization_id),
            patient_id=str(patient_id),
            stage=stage,
            error_code=error_code,
            message=message,
        )
