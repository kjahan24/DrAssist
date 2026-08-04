"""`StaticTablePricingCostCalculator` — the one concrete
`CostCalculatorPort` implementation this task ships: a static, in-code USD-
per-1000-token pricing table, keyed by `(provider, model name)`.

A static table, not a live pricing API — provider prices change
infrequently enough (and a wrong estimate here is a cost dashboard being
briefly stale, never a billing-correctness issue, since the provider's own
invoice is the real source of truth) that an external I/O dependency for
this would violate `09_ai_gateway_and_storage.md`'s framing of cost
tracking as passive instrumentation, not a call the request path should
ever be able to fail on. An unknown `(provider, model)` combination
returns a zero estimate rather than raising, for the same reason.
"""

from app.modules.ai.application.ports import CostCalculatorPort
from app.modules.ai.domain.enums import AIProviderType
from app.modules.ai.domain.value_objects import AIModel, CostEstimate, TokenUsage

# USD per 1,000 tokens: (input_price, output_price). Update as providers
# change list prices — this table has no other code dependency.
_PRICING_TABLE: dict[tuple[AIProviderType, str], tuple[float, float]] = {
    (AIProviderType.OPENAI, "gpt-4o-mini"): (0.00015, 0.00060),
    (AIProviderType.OPENAI, "gpt-4o"): (0.0025, 0.0100),
    (AIProviderType.OPENAI, "text-embedding-3-small"): (0.00002, 0.0),
    (AIProviderType.GEMINI, "gemini-2.5-pro"): (0.00125, 0.0050),
    (AIProviderType.GEMINI, "gemini-2.5-flash"): (0.000075, 0.00030),
    (AIProviderType.CLAUDE, "claude-3-5-sonnet-latest"): (0.0030, 0.0150),
    (AIProviderType.CLAUDE, "claude-3-5-haiku-latest"): (0.0008, 0.0040),
}


class StaticTablePricingCostCalculator(CostCalculatorPort):
    def __init__(
        self,
        pricing_table: dict[tuple[AIProviderType, str], tuple[float, float]] | None = None,
    ) -> None:
        self._pricing_table = pricing_table or _PRICING_TABLE

    def estimate_cost(self, *, usage: TokenUsage, model: AIModel) -> CostEstimate:
        prices = self._pricing_table.get((model.provider, model.name))
        if prices is None:
            return CostEstimate(input_cost_usd=0.0, output_cost_usd=0.0)
        input_price_per_1k, output_price_per_1k = prices
        return CostEstimate(
            input_cost_usd=(usage.prompt_tokens / 1000) * input_price_per_1k,
            output_cost_usd=(usage.completion_tokens / 1000) * output_price_per_1k,
        )
