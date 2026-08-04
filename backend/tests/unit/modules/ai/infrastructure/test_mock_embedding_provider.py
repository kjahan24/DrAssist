"""Unit tests for `MockEmbeddingProvider`."""

from app.modules.ai.application.dto import EmbeddingRequest
from app.modules.ai.domain.enums import AIProviderType
from app.modules.ai.domain.value_objects import AIModel
from app.modules.ai.infrastructure.embeddings.mock_embedding_provider import MockEmbeddingProvider


def _request(*texts: str) -> EmbeddingRequest:
    return EmbeddingRequest(
        input_texts=texts, model=AIModel(provider=AIProviderType.MOCK, name="mock-embedding")
    )


class TestMockEmbeddingProvider:
    def test_provider_type_is_mock(self) -> None:
        assert MockEmbeddingProvider().provider_type is AIProviderType.MOCK

    async def test_returns_one_vector_per_input_text(self) -> None:
        response = await MockEmbeddingProvider().embed(_request("a", "b", "c"))
        assert len(response.embeddings) == 3

    async def test_embeddings_are_deterministic(self) -> None:
        provider = MockEmbeddingProvider()
        first = await provider.embed(_request("same text"))
        second = await provider.embed(_request("same text"))
        assert first.embeddings == second.embeddings

    async def test_different_text_produces_different_vectors(self) -> None:
        provider = MockEmbeddingProvider()
        response = await provider.embed(_request("alpha", "omega"))
        assert response.embeddings[0] != response.embeddings[1]

    async def test_vectors_are_bounded_in_unit_range(self) -> None:
        response = await MockEmbeddingProvider().embed(_request("hello"))
        assert all(-1.0 <= value <= 1.0 for value in response.embeddings[0])
