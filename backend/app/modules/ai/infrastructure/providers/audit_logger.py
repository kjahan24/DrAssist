"""`StructlogAIAuditLogger` — the one concrete `AIAuditLoggerPort`
implementation this task ships: writes a structured `structlog` line per
provider call, via `app.core.logging.get_logger`
(`06_configuration_logging_exceptions.md`'s "Infrastructure logs technical
events" convention).

Never logs `AIMessage` content or embedding vectors — only IDs, enums, and
numbers, per that same document's "PHI is never logged, at any layer"
rule. A future durable-audit-trail requirement (e.g. compliance needing to
query AI usage per patient) should add a second `AIAuditLoggerPort`
implementation that also calls the Audit module's public command port —
this task does not add that cross-module dependency itself, since nothing
here calls this port with patient-identifying context yet (see
`container.py`'s scope note).
"""

from app.core.logging import get_logger
from app.modules.ai.application.ports import AIAuditLoggerPort
from app.modules.ai.domain.enums import AIProviderType
from app.modules.ai.domain.value_objects import CostEstimate, TokenUsage

logger = get_logger(__name__)


class StructlogAIAuditLogger(AIAuditLoggerPort):
    async def log_call(
        self,
        *,
        provider: AIProviderType,
        model: str,
        operation: str,
        usage: TokenUsage,
        cost: CostEstimate | None,
        duration_ms: float,
        success: bool,
        error_code: str | None = None,
    ) -> None:
        logger.info(
            "ai_provider_call",
            provider=provider.value,
            model=model,
            operation=operation,
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
            total_tokens=usage.total_tokens,
            cost_usd=cost.total_cost_usd if cost is not None else None,
            duration_ms=round(duration_ms, 2),
            success=success,
            error_code=error_code,
        )
