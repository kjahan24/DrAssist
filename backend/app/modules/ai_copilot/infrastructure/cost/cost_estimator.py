"""`CostEstimator` — a small, independent USD-per-1000-token pricing
table, keyed by `(provider, model name)` string pair.

See `domain/value_objects.py::AISession`'s own docstring for why this
module computes its own estimate rather than reading one from AI
Foundation: `ChatCompletionResponse` (AI Foundation's public response
shape) carries token usage but no cost figure — cost estimation happens
inside that module's own `infrastructure/providers/resilient_provider.py`
decorator, which is not part of its `public/` surface. This is a plain
concrete class, not an `ABC` with multiple implementations — this task
did not ask for a second, separately-swappable cost-calculator
abstraction the way it did for AI Foundation itself in the prior task.
`application/ports.py::CostEstimatorPort` (a structural `Protocol`, not a
nominal `ABC`) is what `ClinicalCopilotService` actually depends on, so a
test double can satisfy that type without subclassing this concrete
class — see that Protocol's own docstring.
"""

_DEFAULT_PRICING_TABLE: dict[tuple[str, str], tuple[float, float]] = {
    ("openai", "gpt-4o-mini"): (0.00015, 0.00060),
    ("openai", "gpt-4o"): (0.0025, 0.0100),
    ("gemini", "gemini-2.5-pro"): (0.00125, 0.0050),
    ("gemini", "gemini-2.5-flash"): (0.000075, 0.00030),
    ("claude", "claude-3-5-sonnet-latest"): (0.0030, 0.0150),
    ("claude", "claude-3-5-haiku-latest"): (0.0008, 0.0040),
}


class CostEstimator:
    def __init__(
        self, pricing_table: dict[tuple[str, str], tuple[float, float]] | None = None
    ) -> None:
        self._pricing_table = pricing_table or _DEFAULT_PRICING_TABLE

    def estimate(
        self, *, provider: str, model: str, prompt_tokens: int, completion_tokens: int
    ) -> float:
        prices = self._pricing_table.get((provider, model))
        if prices is None:
            return 0.0
        input_price_per_1k, output_price_per_1k = prices
        return (prompt_tokens / 1000) * input_price_per_1k + (
            completion_tokens / 1000
        ) * output_price_per_1k
