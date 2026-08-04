"""Unit tests for `StaticTablePricingCostCalculator`."""

from app.modules.ai.domain.enums import AIProviderType
from app.modules.ai.domain.value_objects import AIModel, TokenUsage
from app.modules.ai.infrastructure.providers.cost_calculator import (
    StaticTablePricingCostCalculator,
)


class TestStaticTablePricingCostCalculator:
    def test_computes_cost_for_a_known_model(self) -> None:
        calculator = StaticTablePricingCostCalculator(
            {(AIProviderType.OPENAI, "gpt-4o-mini"): (0.001, 0.002)}
        )
        model = AIModel(provider=AIProviderType.OPENAI, name="gpt-4o-mini")
        usage = TokenUsage(prompt_tokens=1000, completion_tokens=500, total_tokens=1500)

        estimate = calculator.estimate_cost(usage=usage, model=model)

        assert estimate.input_cost_usd == 0.001
        assert estimate.output_cost_usd == 0.001
        assert estimate.total_cost_usd == 0.002

    def test_unknown_model_returns_zero_cost(self) -> None:
        calculator = StaticTablePricingCostCalculator({})
        model = AIModel(provider=AIProviderType.OPENAI, name="never-priced")
        usage = TokenUsage(prompt_tokens=1000, completion_tokens=500, total_tokens=1500)

        estimate = calculator.estimate_cost(usage=usage, model=model)

        assert estimate.total_cost_usd == 0.0

    def test_zero_usage_is_zero_cost(self) -> None:
        calculator = StaticTablePricingCostCalculator(
            {(AIProviderType.OPENAI, "gpt-4o-mini"): (0.001, 0.002)}
        )
        model = AIModel(provider=AIProviderType.OPENAI, name="gpt-4o-mini")

        estimate = calculator.estimate_cost(usage=TokenUsage.zero(), model=model)

        assert estimate.total_cost_usd == 0.0

    def test_default_pricing_table_covers_common_models(self) -> None:
        calculator = StaticTablePricingCostCalculator()
        model = AIModel(provider=AIProviderType.OPENAI, name="gpt-4o-mini")
        usage = TokenUsage(prompt_tokens=1000, completion_tokens=1000, total_tokens=2000)

        estimate = calculator.estimate_cost(usage=usage, model=model)

        assert estimate.total_cost_usd > 0.0
