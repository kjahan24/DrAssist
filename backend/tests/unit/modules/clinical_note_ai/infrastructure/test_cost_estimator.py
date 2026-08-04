"""Unit tests for `CostEstimator`."""

from app.modules.clinical_note_ai.infrastructure.cost.cost_estimator import CostEstimator


class TestCostEstimator:
    def test_computes_cost_for_a_known_model(self) -> None:
        estimator = CostEstimator({("openai", "gpt-4o-mini"): (0.001, 0.002)})

        cost = estimator.estimate(
            provider="openai", model="gpt-4o-mini", prompt_tokens=1000, completion_tokens=500
        )

        assert cost == 0.001 + 0.001

    def test_unknown_model_returns_zero(self) -> None:
        estimator = CostEstimator({})

        cost = estimator.estimate(
            provider="openai", model="never-priced", prompt_tokens=1000, completion_tokens=500
        )

        assert cost == 0.0

    def test_zero_tokens_is_zero_cost(self) -> None:
        estimator = CostEstimator({("openai", "gpt-4o-mini"): (0.001, 0.002)})

        cost = estimator.estimate(
            provider="openai", model="gpt-4o-mini", prompt_tokens=0, completion_tokens=0
        )

        assert cost == 0.0

    def test_default_pricing_table_covers_common_models(self) -> None:
        estimator = CostEstimator()

        cost = estimator.estimate(
            provider="openai", model="gpt-4o-mini", prompt_tokens=1000, completion_tokens=1000
        )

        assert cost > 0.0
