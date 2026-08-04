"""Unit tests for `AIProviderFactory`/`EmbeddingProviderFactory`."""

import pytest

from app.modules.ai.domain.enums import AIProviderType
from app.modules.ai.domain.exceptions import UnsupportedAIProviderError
from app.modules.ai.infrastructure.embeddings.mock_embedding_provider import MockEmbeddingProvider
from app.modules.ai.infrastructure.llm.mock_provider import MockAIProvider
from app.modules.ai.infrastructure.providers.factory import (
    AIProviderFactory,
    EmbeddingProviderFactory,
)


class TestAIProviderFactory:
    def test_create_invokes_the_registered_builder(self) -> None:
        factory = AIProviderFactory()
        factory.register(AIProviderType.MOCK, lambda: MockAIProvider())

        provider = factory.create(AIProviderType.MOCK)

        assert isinstance(provider, MockAIProvider)

    def test_create_raises_for_an_unregistered_provider(self) -> None:
        factory = AIProviderFactory()
        with pytest.raises(UnsupportedAIProviderError):
            factory.create(AIProviderType.OPENAI)

    def test_create_builds_a_fresh_instance_each_call(self) -> None:
        factory = AIProviderFactory()
        factory.register(AIProviderType.MOCK, lambda: MockAIProvider())

        first = factory.create(AIProviderType.MOCK)
        second = factory.create(AIProviderType.MOCK)

        assert first is not second

    def test_available_providers_lists_only_registered_types(self) -> None:
        factory = AIProviderFactory()
        factory.register(AIProviderType.MOCK, lambda: MockAIProvider())

        assert factory.available_providers() == [AIProviderType.MOCK]


class TestEmbeddingProviderFactory:
    def test_create_invokes_the_registered_builder(self) -> None:
        factory = EmbeddingProviderFactory()
        factory.register(AIProviderType.MOCK, lambda: MockEmbeddingProvider())

        provider = factory.create(AIProviderType.MOCK)

        assert isinstance(provider, MockEmbeddingProvider)

    def test_create_raises_for_an_unregistered_provider(self) -> None:
        factory = EmbeddingProviderFactory()
        with pytest.raises(UnsupportedAIProviderError):
            factory.create(AIProviderType.GEMINI)
