"""`MockEmbeddingProvider` — deterministic, zero-I/O `EmbeddingProviderPort`
implementation, mirroring `infrastructure/llm/mock_provider.py::
MockAIProvider`'s role for embeddings.

Vectors are derived from each input text via a stable hash, not random —
the same text always embeds to the same vector, which is what makes this
usable for deterministic tests of anything downstream that does
similarity comparison (e.g. "the embedding of X should be closer to X
than to Y") without a real embedding model.
"""

import hashlib

from app.modules.ai.application.dto import EmbeddingRequest, EmbeddingResponse
from app.modules.ai.application.ports import EmbeddingProviderPort
from app.modules.ai.domain.enums import AIProviderType
from app.modules.ai.domain.value_objects import TokenUsage

_DIMENSIONS = 16


def _embed_text(text: str) -> tuple[float, ...]:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return tuple((digest[i % len(digest)] / 255.0) * 2 - 1 for i in range(_DIMENSIONS))


class MockEmbeddingProvider(EmbeddingProviderPort):
    @property
    def provider_type(self) -> AIProviderType:
        return AIProviderType.MOCK

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        embeddings = tuple(_embed_text(text) for text in request.input_texts)
        token_estimate = sum(max(1, len(text) // 4) for text in request.input_texts)
        return EmbeddingResponse(
            embeddings=embeddings,
            model=request.model,
            provider=AIProviderType.MOCK,
            usage=TokenUsage(
                prompt_tokens=token_estimate, completion_tokens=0, total_tokens=token_estimate
            ),
        )
