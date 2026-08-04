"""Unit tests for `OpenAIEmbeddingProvider`, using a fake client duck-typed
to `openai.AsyncOpenAI`'s `.embeddings.create(...)` surface."""

from types import SimpleNamespace
from typing import Any

import pytest

from app.modules.ai.application.dto import EmbeddingRequest
from app.modules.ai.domain.enums import AIProviderType
from app.modules.ai.domain.exceptions import AIProviderAuthenticationError
from app.modules.ai.domain.value_objects import AIModel
from app.modules.ai.infrastructure.embeddings.openai_embedding_provider import (
    OpenAIEmbeddingProvider,
)


class _FakeEmbeddings:
    def __init__(
        self, *, response: SimpleNamespace | None = None, error: Exception | None = None
    ) -> None:
        self._response = response
        self._error = error
        self.received_kwargs: dict[str, Any] | None = None

    async def create(self, **kwargs: Any) -> SimpleNamespace:
        self.received_kwargs = kwargs
        if self._error is not None:
            raise self._error
        assert self._response is not None
        return self._response


class _FakeOpenAIClient:
    def __init__(
        self, *, response: SimpleNamespace | None = None, error: Exception | None = None
    ) -> None:
        self.embeddings = _FakeEmbeddings(response=response, error=error)


def _response(vectors: list[list[float]]) -> SimpleNamespace:
    return SimpleNamespace(
        data=[SimpleNamespace(embedding=v) for v in vectors],
        usage=SimpleNamespace(prompt_tokens=4, total_tokens=4),
    )


def _request(*texts: str) -> EmbeddingRequest:
    return EmbeddingRequest(
        input_texts=texts,
        model=AIModel(provider=AIProviderType.OPENAI, name="text-embedding-3-small"),
    )


class TestOpenAIEmbeddingProvider:
    def test_provider_type_is_openai(self) -> None:
        assert OpenAIEmbeddingProvider(api_key="key").provider_type is AIProviderType.OPENAI

    async def test_maps_response_vectors(self) -> None:
        client = _FakeOpenAIClient(response=_response([[0.1, 0.2], [0.3, 0.4]]))
        provider = OpenAIEmbeddingProvider(api_key="key", client=client)

        result = await provider.embed(_request("a", "b"))

        assert result.embeddings == ((0.1, 0.2), (0.3, 0.4))
        assert result.usage.total_tokens == 4

    async def test_missing_api_key_raises_authentication_error(self) -> None:
        provider = OpenAIEmbeddingProvider(api_key=None)
        with pytest.raises(AIProviderAuthenticationError):
            await provider.embed(_request("a"))

    async def test_sends_model_and_input_texts(self) -> None:
        client = _FakeOpenAIClient(response=_response([[0.0]]))
        provider = OpenAIEmbeddingProvider(api_key="key", client=client)

        await provider.embed(_request("hello"))

        received_kwargs = client.embeddings.received_kwargs
        assert received_kwargs is not None
        assert received_kwargs["model"] == "text-embedding-3-small"
        assert received_kwargs["input"] == ["hello"]
