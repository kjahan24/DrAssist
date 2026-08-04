"""Unit tests for the `GenerateEmbedding` use case."""

import pytest

from app.modules.ai.application.dto import EmbeddingRequest
from app.modules.ai.application.use_cases.generate_embedding import GenerateEmbedding
from app.modules.ai.domain.enums import AIProviderType
from app.modules.ai.domain.exceptions import AIProviderInvalidRequestError
from app.modules.ai.domain.value_objects import AIModel
from tests.unit.modules.ai.application.fakes import FakeEmbeddingProviderPort


def _request() -> EmbeddingRequest:
    return EmbeddingRequest(
        input_texts=("hello", "world"),
        model=AIModel(provider=AIProviderType.MOCK, name="mock-embedding"),
    )


class TestGenerateEmbedding:
    async def test_delegates_to_the_injected_provider(self) -> None:
        provider = FakeEmbeddingProviderPort()
        use_case = GenerateEmbedding(provider=provider)

        response = await use_case.execute(_request())

        assert len(response.embeddings) == 2

    async def test_propagates_provider_errors(self) -> None:
        provider = FakeEmbeddingProviderPort(
            error=AIProviderInvalidRequestError(provider="mock", message="bad input")
        )
        use_case = GenerateEmbedding(provider=provider)

        with pytest.raises(AIProviderInvalidRequestError):
            await use_case.execute(_request())
