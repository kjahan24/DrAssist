"""Application-layer ports for the AI module.

Distinct from the pre-existing, narrower `app.shared.application
.ai_provider_port` (`TextGenerationPort`/`SpeechToTextPort`/`OCRPort`,
implemented by `app/infrastructure/ai/`'s Gemini/Whisper/PaddleOCR
adapters) — those remain untouched and serve their own existing callers.
The ports below are this task's own, richer, provider-agnostic chat-
completion/embedding abstraction (`AIProviderType.OPENAI/GEMINI/CLAUDE/
OLLAMA/MOCK`, `09_ai_gateway_and_storage.md`'s "Strategy + Factory"
design), scoped to `app.modules.ai` only.

A use case depends on these interfaces, never on a concrete adapter
(`infrastructure/llm/openai_provider.py` etc.) directly — the Dependency
Inversion Principle every other module's `domain/repositories.py` /
`public/interfaces.py` already applies here for `application/`.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Protocol

from app.modules.ai.application.dto import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    EmbeddingRequest,
    EmbeddingResponse,
    PromptVariables,
    StreamChunk,
)
from app.modules.ai.domain.enums import AIProviderType
from app.modules.ai.domain.value_objects import AIModel, CostEstimate, TokenUsage


class AIProviderPort(ABC):
    @property
    @abstractmethod
    def provider_type(self) -> AIProviderType: ...

    @abstractmethod
    async def complete(self, request: ChatCompletionRequest) -> ChatCompletionResponse: ...

    @abstractmethod
    def stream_complete(self, request: ChatCompletionRequest) -> AsyncIterator[StreamChunk]:
        """Declared as a plain (non-`async def`) method returning
        `AsyncIterator[StreamChunk]` rather than an `async def` generator
        — an abstract method's body is never executed, and this signature
        is what lets every concrete adapter implement it as either an
        `async def ... : yield ...` generator function or a regular method
        returning an async-iterable object, both of which satisfy the same
        type."""
        ...


class EmbeddingProviderPort(ABC):
    @property
    @abstractmethod
    def provider_type(self) -> AIProviderType: ...

    @abstractmethod
    async def embed(self, request: EmbeddingRequest) -> EmbeddingResponse: ...


class TokenizerPort(ABC):
    @abstractmethod
    def count_tokens(self, *, text: str, model: AIModel) -> int: ...


class StructuredResponseParserPort(ABC):
    @abstractmethod
    def parse(self, raw_text: str) -> object:
        """Returns whatever JSON-decodes to — a `dict`/`list`/scalar, per
        `json.loads`'s own return type. Raises
        `AIProviderResponseParsingError` (domain) when `raw_text` cannot
        be decoded, even after the adapter's own cleanup heuristics."""
        ...


class CostCalculatorPort(ABC):
    @abstractmethod
    def estimate_cost(self, *, usage: TokenUsage, model: AIModel) -> CostEstimate: ...


class PromptRenderingPort(Protocol):
    """A `typing.Protocol`, not an `ABC` — structural, not nominal,
    typing. `infrastructure/prompts/registry.py::PromptRegistry` already
    exposes a `render(name, variables, version=...)` method with this
    exact shape and satisfies this protocol without inheriting from it,
    which is what lets `public/facade.py::AIGatewayFacade` depend on this
    application-layer type (never on `infrastructure/prompts/` directly,
    per the module-boundary rule in `11_standards_and_conventions.md`)
    while `container.py` still injects the real `PromptRegistry`."""

    async def render(
        self, name: str, variables: PromptVariables, *, version: int | None = None
    ) -> str: ...


class AIAuditLoggerPort(ABC):
    """Every provider call is logged through here (see
    `infrastructure/providers/resilient_provider.py`) — never PHI, only
    IDs/enums/numbers, per `06_configuration_logging_exceptions.md`'s
    "PHI is never logged, at any layer" rule; callers must not pass
    prompt/response *content* to `log_call`, only metadata about the call."""

    @abstractmethod
    async def log_call(
        self,
        *,
        provider: AIProviderType,
        model: str,
        operation: str,
        usage: TokenUsage,
        cost: CostEstimate | None,
        duration_ms: float,
        success: bool,
        error_code: str | None = None,
    ) -> None: ...
