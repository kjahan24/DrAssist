"""Unit tests for `GeminiEmbeddingProvider`, using a fake client duck-typed
to `_DefaultGeminiEmbeddingClient`'s one method:
`embed_content_async(model=, contents=)`."""

from typing import Any

import pytest

from app.modules.ai.application.dto import EmbeddingRequest
from app.modules.ai.domain.enums import AIProviderType
from app.modules.ai.domain.exceptions import AIProviderAuthenticationError
from app.modules.ai.domain.value_objects import AIModel
from app.modules.ai.infrastructure.embeddings.gemini_embedding_provider import (
    GeminiEmbeddingProvider,
)


class _FakeGeminiEmbeddingClient:
    def __init__(
        self, *, vectors: list[list[float]] | None = None, error: Exception | None = None
    ) -> None:
        self._vectors = vectors or []
        self._error = error
        self.received_kwargs: dict[str, Any] | None = None

    async def embed_content_async(self, *, model: str, contents: list[str]) -> list[list[float]]:
        self.received_kwargs = {"model": model, "contents": contents}
        if self._error is not None:
            raise self._error
        return self._vectors


def _request(*texts: str) -> EmbeddingRequest:
    return EmbeddingRequest(
        input_texts=texts, model=AIModel(provider=AIProviderType.GEMINI, name="text-embedding-004")
    )


class TestGeminiEmbeddingProvider:
    def test_provider_type_is_gemini(self) -> None:
        assert GeminiEmbeddingProvider(api_key="key").provider_type is AIProviderType.GEMINI

    async def test_maps_response_vectors(self) -> None:
        client = _FakeGeminiEmbeddingClient(vectors=[[0.1, 0.2], [0.3, 0.4]])
        provider = GeminiEmbeddingProvider(api_key="key", client=client)

        result = await provider.embed(_request("a", "b"))

        assert result.embeddings == ((0.1, 0.2), (0.3, 0.4))

    async def test_missing_api_key_raises_authentication_error(self) -> None:
        provider = GeminiEmbeddingProvider(api_key=None)
        with pytest.raises(AIProviderAuthenticationError):
            await provider.embed(_request("a"))

    async def test_sends_model_and_contents(self) -> None:
        client = _FakeGeminiEmbeddingClient(vectors=[[0.0]])
        provider = GeminiEmbeddingProvider(api_key="key", client=client)

        await provider.embed(_request("hello"))

        received_kwargs = client.received_kwargs
        assert received_kwargs is not None
        assert received_kwargs["model"] == "text-embedding-004"
        assert received_kwargs["contents"] == ["hello"]
