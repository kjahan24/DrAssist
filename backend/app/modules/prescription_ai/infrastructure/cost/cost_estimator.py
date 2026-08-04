"""`CostEstimator` — a small, independent USD-per-1000-token pricing
table, keyed by `(provider, model name)` string pair. Mirrors
`app.modules.icd10_ai.infrastructure.cost.cost_estimator.CostEstimator`
exactly, duplicated locally rather than imported — that class lives in a
peer module's `.infrastructure`, not its `.public`, so it cannot be
imported from here (module-independence rule); it also cannot move into
`app.shared.infrastructure.text_processing` alongside the genuinely-
shared parser/validator utilities, since it needs AI Foundation's
provider/model vocabulary conceptually (even though it's typed as plain
`str` here) and this exact pricing-table shape is small enough that the
"each module defines its own copy" precedent (`app.modules.documents`/
`app.modules.attachments`'s own `Sha256Checksum`, duplicated twice
already, and now `clinical_note_ai`/`soap_note_ai`/`icd10_ai`'s own
`CostEstimator` copies) is the more consistent choice than inventing a
new shared abstraction for a fifth module's identical need.
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
