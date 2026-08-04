"""Value objects for the AI module's domain.

Every provider adapter (`infrastructure/llm/`, `infrastructure/embeddings/`)
constructs and returns these same shapes regardless of which SDK it wraps —
this is what makes `AIProviderPort`/`EmbeddingProviderPort` genuinely
provider-agnostic (`docs/backend-architecture/09_ai_gateway_and_storage.md`).
"""

from dataclasses import dataclass

from app.modules.ai.domain.enums import AIMessageRole, AIProviderType
from app.modules.ai.domain.exceptions import InvalidPromptTemplateError
from app.shared.domain.value_object import ValueObject


@dataclass(frozen=True, slots=True)
class TokenUsage(ValueObject):
    """`total_tokens` is stored, not derived, because some providers report
    it directly and may round/adjust it independently of
    `prompt_tokens + completion_tokens` (e.g. cached-token discounts) —
    trusting the provider's own total avoids this value object silently
    disagreeing with what the provider bills for."""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

    def __post_init__(self) -> None:
        if self.prompt_tokens < 0 or self.completion_tokens < 0 or self.total_tokens < 0:
            raise ValueError("token counts cannot be negative")

    def __add__(self, other: "TokenUsage") -> "TokenUsage":
        """Lets `application/services/token_usage_collector.py` accumulate
        a running total with plain `+=` rather than reimplementing
        field-by-field addition at every call site."""
        if not isinstance(other, TokenUsage):
            return NotImplemented
        return TokenUsage(
            prompt_tokens=self.prompt_tokens + other.prompt_tokens,
            completion_tokens=self.completion_tokens + other.completion_tokens,
            total_tokens=self.total_tokens + other.total_tokens,
        )

    @classmethod
    def zero(cls) -> "TokenUsage":
        return cls(prompt_tokens=0, completion_tokens=0, total_tokens=0)


@dataclass(frozen=True, slots=True)
class AIModel(ValueObject):
    """Identifies a specific model offered by a specific provider —
    `provider` is part of the value's identity (`gpt-4o-mini` from
    `AIProviderType.OPENAI` is a different `AIModel` than a same-named
    model from a future custom-endpoint provider), so equality/hashing
    naturally scope by both fields together."""

    provider: AIProviderType
    name: str
    context_window: int | None = None
    max_output_tokens: int | None = None
    supports_streaming: bool = False
    supports_embeddings: bool = False

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("AIModel.name must not be blank")
        if self.context_window is not None and self.context_window <= 0:
            raise ValueError("context_window must be positive when given")
        if self.max_output_tokens is not None and self.max_output_tokens <= 0:
            raise ValueError("max_output_tokens must be positive when given")


@dataclass(frozen=True, slots=True)
class AIMessage(ValueObject):
    """One turn in a chat-completion conversation. `name` is the optional
    per-provider "who specifically" tag (OpenAI/Anthropic both support a
    named participant distinct from `role`) — most callers leave it unset."""

    role: AIMessageRole
    content: str
    name: str | None = None


@dataclass(frozen=True, slots=True)
class CostEstimate(ValueObject):
    """USD estimate for one provider call, split by input/output so a
    caller can see which side of a request drove the cost (useful for
    prompts with a large fixed system-message prefix)."""

    input_cost_usd: float
    output_cost_usd: float

    def __post_init__(self) -> None:
        if self.input_cost_usd < 0 or self.output_cost_usd < 0:
            raise ValueError("cost components cannot be negative")

    @property
    def total_cost_usd(self) -> float:
        return self.input_cost_usd + self.output_cost_usd


@dataclass(frozen=True, slots=True)
class PromptTemplate(ValueObject):
    """A single, immutable version of a named prompt. `(name, version)` is
    the composite business key `domain/repositories.py::
    PromptTemplateRepository` looks templates up by — versioning exists so
    a future prompt-tuning change can be rolled out (and rolled back)
    without editing a template callers already depend on out from under
    them; `infrastructure/prompts/registry.py::PromptRegistry` is what
    resolves "latest" vs. a pinned version.

    `variable_names` is declared explicitly by whoever registers the
    template (not parsed from `template_string` by this value object,
    which — per `04_repository_and_service_patterns.md`'s Tier 3
    validation guidance — only validates its own fields' shape) so a typo
    inside `{{ }}` markup is still caught by
    `infrastructure/prompts/renderer.py::PromptRenderer` cross-checking
    the two, rather than silently rendering as a literal `{{typo}}` string.
    """

    name: str
    version: int
    template_string: str
    variable_names: frozenset[str] = frozenset()
    description: str = ""

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise InvalidPromptTemplateError("name must not be blank")
        if self.version < 1:
            raise InvalidPromptTemplateError("version must be >= 1")
        if not self.template_string.strip():
            raise InvalidPromptTemplateError("template_string must not be blank")
