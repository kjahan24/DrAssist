"""Data Transfer Objects for the AI module's application layer.

`ChatCompletionRequest`/`Response` and `EmbeddingRequest`/`Response` are
the envelope every `AIProviderPort`/`EmbeddingProviderPort` implementation
speaks (`application/ports.py`) — distinct from the domain value objects
they're built from (`AIMessage`, `AIModel`, `TokenUsage`): a request/
response pair has no invariant of its own beyond "bundle these domain
values together for one call", which is exactly what a DTO is for, per
this module's own `container.py` and every other module's `application
/dto.py` (e.g. `app.modules.family_access.application.dto`).
"""

from collections.abc import Mapping
from dataclasses import dataclass, field

from app.modules.ai.domain.enums import AIFinishReason, AIProviderType
from app.modules.ai.domain.value_objects import AIMessage, AIModel, TokenUsage

# --- Chat completion ---------------------------------------------------


@dataclass(frozen=True, slots=True)
class ChatCompletionRequest:
    messages: tuple[AIMessage, ...]
    model: AIModel
    temperature: float = 0.7
    max_output_tokens: int | None = None
    top_p: float | None = None
    stop_sequences: tuple[str, ...] = ()
    response_format: str = "text"
    """`"text"` or `"json"` — a hint adapters pass to the provider's own
    structured-output mode when it supports one; callers that need
    strict JSON should still parse the reply through
    `infrastructure/parsers/json_parser.py::JSONResponseParser` rather
    than trusting the provider never deviates."""


@dataclass(frozen=True, slots=True)
class ChatCompletionResponse:
    message: AIMessage
    model: AIModel
    provider: AIProviderType
    usage: TokenUsage
    finish_reason: AIFinishReason
    latency_ms: float
    raw_response_id: str | None = None


@dataclass(frozen=True, slots=True)
class StreamChunk:
    """One increment of a streamed chat completion —
    `AIProviderPort.stream_complete` yields these, per-token or
    per-provider-batch depending on how granularly the provider streams."""

    delta: str
    finish_reason: AIFinishReason | None = None
    is_final: bool = False


# --- Embeddings ----------------------------------------------------------


@dataclass(frozen=True, slots=True)
class EmbeddingRequest:
    input_texts: tuple[str, ...]
    model: AIModel

    def __post_init__(self) -> None:
        if not self.input_texts:
            raise ValueError("EmbeddingRequest.input_texts must not be empty")


@dataclass(frozen=True, slots=True)
class EmbeddingResponse:
    embeddings: tuple[tuple[float, ...], ...]
    model: AIModel
    provider: AIProviderType
    usage: TokenUsage = field(default_factory=TokenUsage.zero)


# --- Prompt rendering ----------------------------------------------------


class PromptVariables:
    """The substitution values `infrastructure/prompts/renderer.py::
    PromptRenderer` fills a `PromptTemplate.template_string`'s
    `{{ name }}` placeholders with. Lives here, not in
    `infrastructure/prompts/`, specifically so
    `public/interfaces.py::AIGatewayPort.render_prompt` can accept it as a
    parameter type without forcing callers in other modules to import
    from this module's `infrastructure/` package — every other module may
    only ever import from `app.modules.ai.public`
    (`11_standards_and_conventions.md`).

    Every value is coerced to `str` at construction (not left as
    arbitrary `object`) — a template placeholder is always substituted
    into plain text, so a caller passing an `int`/`date`/`Decimal` gets a
    predictable `str(value)` rendering rather than the renderer needing
    to guess a formatting rule per type.
    """

    def __init__(self, values: Mapping[str, object] | None = None) -> None:
        self._values: dict[str, str] = {k: str(v) for k, v in (values or {}).items()}

    def __contains__(self, name: str) -> bool:
        return name in self._values

    def __getitem__(self, name: str) -> str:
        return self._values[name]

    def get(self, name: str, default: str | None = None) -> str | None:
        return self._values.get(name, default)

    def as_dict(self) -> dict[str, str]:
        return dict(self._values)

    @classmethod
    def empty(cls) -> "PromptVariables":
        return cls()
