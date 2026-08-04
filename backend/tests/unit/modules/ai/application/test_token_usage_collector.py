"""Unit tests for `TokenUsageCollector`."""

from app.modules.ai.application.services.token_usage_collector import TokenUsageCollector
from app.modules.ai.domain.value_objects import TokenUsage


class TestTokenUsageCollector:
    def test_starts_at_zero(self) -> None:
        collector = TokenUsageCollector()
        assert collector.total_usage() == TokenUsage.zero()

    def test_record_accumulates_the_running_total(self) -> None:
        collector = TokenUsageCollector()
        collector.record(
            TokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15), model="gpt-4o-mini"
        )
        collector.record(
            TokenUsage(prompt_tokens=3, completion_tokens=2, total_tokens=5), model="gpt-4o-mini"
        )
        assert collector.total_usage() == TokenUsage(
            prompt_tokens=13, completion_tokens=7, total_tokens=20
        )

    def test_usage_is_broken_down_per_model(self) -> None:
        collector = TokenUsageCollector()
        collector.record(
            TokenUsage(prompt_tokens=10, completion_tokens=0, total_tokens=10), model="gpt-4o-mini"
        )
        collector.record(
            TokenUsage(prompt_tokens=5, completion_tokens=0, total_tokens=5),
            model="claude-3-5-sonnet",
        )
        assert collector.usage_for_model("gpt-4o-mini").total_tokens == 10
        assert collector.usage_for_model("claude-3-5-sonnet").total_tokens == 5
        assert set(collector.usage_by_model().keys()) == {"gpt-4o-mini", "claude-3-5-sonnet"}

    def test_usage_for_unknown_model_is_zero(self) -> None:
        collector = TokenUsageCollector()
        assert collector.usage_for_model("never-called") == TokenUsage.zero()

    def test_reset_clears_everything(self) -> None:
        collector = TokenUsageCollector()
        collector.record(
            TokenUsage(prompt_tokens=10, completion_tokens=0, total_tokens=10), model="gpt-4o-mini"
        )
        collector.reset()
        assert collector.total_usage() == TokenUsage.zero()
        assert collector.usage_by_model() == {}
