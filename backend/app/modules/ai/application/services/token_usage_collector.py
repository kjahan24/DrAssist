"""`TokenUsageCollector` — an in-process running total of token usage,
broken down by model name.

Deliberately **not** where cost tracking happens per call (that's
`infrastructure/providers/resilient_provider.py`, per
`09_ai_gateway_and_storage.md`'s "infrastructure-layer instrumentation,
not a decision any individual use case makes" rule) — this is a plain
aggregator a caller (the resilient provider wrapper, a future scheduled
report, a debug endpoint) can `record()` into and read back from. It holds
no lock/persistence: one instance is process-lifetime-scoped via
`container.py::get_token_usage_collector` (an `lru_cache`d singleton, the
same pattern `app.core.container.get_event_bus` already establishes), not
request-scoped, so it can report the running total across many requests.
"""

from app.modules.ai.domain.value_objects import TokenUsage


class TokenUsageCollector:
    def __init__(self) -> None:
        self._total = TokenUsage.zero()
        self._by_model: dict[str, TokenUsage] = {}

    def record(self, usage: TokenUsage, *, model: str) -> None:
        self._total = self._total + usage
        self._by_model[model] = self._by_model.get(model, TokenUsage.zero()) + usage

    def total_usage(self) -> TokenUsage:
        return self._total

    def usage_for_model(self, model: str) -> TokenUsage:
        return self._by_model.get(model, TokenUsage.zero())

    def usage_by_model(self) -> dict[str, TokenUsage]:
        return dict(self._by_model)

    def reset(self) -> None:
        self._total = TokenUsage.zero()
        self._by_model.clear()
