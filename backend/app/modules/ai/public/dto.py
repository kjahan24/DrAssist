"""Public DTOs — the only data shapes another module may depend on.

Re-exported from the application/domain layers, not redefined, so there is
exactly one definition of each shape (the same "re-exported... not
redefined" precedent `app.modules.family_access.public.dto` establishes).
`AIMessage`/`AIModel`/`TokenUsage`/`CostEstimate` and the three enums are
pure value types with no behavior — the same "peer domain value types are
safe to depend on directly" allowance every other module's public DTOs
already rely on for their own enums (e.g. `AccessLevel` in
`family_access.public.dto`), extended here to the handful of value objects
a caller needs in order to actually construct a `ChatCompletionRequest`/
`EmbeddingRequest`.
"""

from app.modules.ai.application.dto import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    EmbeddingRequest,
    EmbeddingResponse,
    PromptVariables,
    StreamChunk,
)
from app.modules.ai.domain.enums import AIFinishReason, AIMessageRole, AIProviderType
from app.modules.ai.domain.value_objects import AIMessage, AIModel, CostEstimate, TokenUsage

__all__ = [
    "AIFinishReason",
    "AIMessage",
    "AIMessageRole",
    "AIModel",
    "AIProviderType",
    "ChatCompletionRequest",
    "ChatCompletionResponse",
    "CostEstimate",
    "EmbeddingRequest",
    "EmbeddingResponse",
    "PromptVariables",
    "StreamChunk",
    "TokenUsage",
]
