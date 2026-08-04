"""Unit tests for `StructlogAIAuditLogger` — verifies it logs without
raising and never receives/leaks message content, which callers must
uphold since this port's contract only ever passes IDs/enums/numbers."""

from app.modules.ai.domain.enums import AIProviderType
from app.modules.ai.domain.value_objects import CostEstimate, TokenUsage
from app.modules.ai.infrastructure.providers.audit_logger import StructlogAIAuditLogger


class TestStructlogAIAuditLogger:
    async def test_log_call_does_not_raise_on_success(self) -> None:
        logger = StructlogAIAuditLogger()
        await logger.log_call(
            provider=AIProviderType.MOCK,
            model="mock-model",
            operation="complete",
            usage=TokenUsage(prompt_tokens=1, completion_tokens=1, total_tokens=2),
            cost=CostEstimate(input_cost_usd=0.0, output_cost_usd=0.0),
            duration_ms=12.3,
            success=True,
        )

    async def test_log_call_does_not_raise_on_failure_without_cost(self) -> None:
        logger = StructlogAIAuditLogger()
        await logger.log_call(
            provider=AIProviderType.MOCK,
            model="mock-model",
            operation="complete",
            usage=TokenUsage.zero(),
            cost=None,
            duration_ms=5.0,
            success=False,
            error_code="AIProviderTimeoutError",
        )
