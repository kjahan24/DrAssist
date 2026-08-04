"""Unit tests for `container.py` — verifies the module's composition root
wires end to end with the zero-configuration `mock` defaults
(`AI_DEFAULT_PROVIDER=mock`/`AI_DEFAULT_EMBEDDING_PROVIDER=mock`, set by
`tests/conftest.py`), without needing any real provider API key."""

from app.core.config import get_settings
from app.modules.ai.container import (
    get_ai_gateway_facade,
    get_ai_provider_factory,
    get_cost_calculator,
    get_embedding_provider_factory,
    get_prompt_registry,
    get_token_usage_collector,
)
from app.modules.ai.domain.enums import AIMessageRole, AIProviderType
from app.modules.ai.domain.value_objects import AIMessage, AIModel
from app.modules.ai.public.dto import ChatCompletionRequest
from app.modules.ai.public.facade import AIGatewayFacade


class TestGetAiProviderFactory:
    def test_every_provider_type_is_registered(self) -> None:
        factory = get_ai_provider_factory()
        assert set(factory.available_providers()) == set(AIProviderType)

    def test_mock_provider_can_be_created_with_zero_configuration(self) -> None:
        provider = get_ai_provider_factory().create(AIProviderType.MOCK)
        assert provider.provider_type is AIProviderType.MOCK

    def test_returns_the_same_singleton_across_calls(self) -> None:
        assert get_ai_provider_factory() is get_ai_provider_factory()


class TestGetEmbeddingProviderFactory:
    def test_mock_embedding_provider_can_be_created(self) -> None:
        provider = get_embedding_provider_factory().create(AIProviderType.MOCK)
        assert provider.provider_type is AIProviderType.MOCK


class TestGetAiGatewayFacade:
    async def test_defaults_to_the_mock_provider_and_answers_a_request(self) -> None:
        settings = get_settings()
        assert settings.ai.default_provider == "mock"

        facade = get_ai_gateway_facade()
        assert isinstance(facade, AIGatewayFacade)

        response = await facade.generate_chat_completion(
            ChatCompletionRequest(
                messages=(AIMessage(role=AIMessageRole.USER, content="hi"),),
                model=AIModel(provider=AIProviderType.MOCK, name="mock-model"),
            )
        )
        assert response.message.content


class TestSingletonHelpers:
    def test_token_usage_collector_is_a_singleton(self) -> None:
        assert get_token_usage_collector() is get_token_usage_collector()

    def test_cost_calculator_is_a_singleton(self) -> None:
        assert get_cost_calculator() is get_cost_calculator()

    def test_prompt_registry_is_a_singleton(self) -> None:
        assert get_prompt_registry() is get_prompt_registry()
