"""Enums owned by the AI module's domain.

The AI module is a **generic** gateway (`docs/backend-architecture
/03_module_architecture.md #10`) — these enums describe the shape of a
chat-completion/embedding call in provider-agnostic terms, never a
clinical concept (no `SoapSection`, no `DiagnosisConfidence`, ...); those
belong to whichever future clinical module consumes this gateway.
"""

from enum import StrEnum


class AIProviderType(StrEnum):
    """The five provider identities the AI Foundation's `AIProviderFactory`
    (`infrastructure/providers/factory.py`) knows how to build an adapter
    for. Adding a sixth provider means adding one new value here plus one
    new `infrastructure/llm/` adapter — no other file in this enum's
    dependents needs to change (Open/Closed, per
    `09_ai_gateway_and_storage.md`)."""

    OPENAI = "openai"
    GEMINI = "gemini"
    CLAUDE = "claude"
    OLLAMA = "ollama"
    MOCK = "mock"


class AIMessageRole(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class AIFinishReason(StrEnum):
    """Normalized across every provider's own vocabulary (OpenAI's
    `stop`/`length`/`content_filter`, Anthropic's `end_turn`/`max_tokens`,
    Gemini's `STOP`/`MAX_TOKENS`, ...) — each `infrastructure/llm/` adapter
    is responsible for mapping its provider's raw value onto one of these,
    so no caller of `AIProviderPort` needs to know any provider's own
    vocabulary."""

    STOP = "stop"
    LENGTH = "length"
    CONTENT_FILTER = "content_filter"
    TOOL_CALLS = "tool_calls"
    ERROR = "error"
