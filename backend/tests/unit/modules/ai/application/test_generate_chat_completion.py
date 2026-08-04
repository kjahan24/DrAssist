"""Unit tests for the `GenerateChatCompletion` use case."""

import pytest

from app.modules.ai.application.dto import ChatCompletionRequest
from app.modules.ai.application.use_cases.generate_chat_completion import GenerateChatCompletion
from app.modules.ai.domain.enums import AIMessageRole, AIProviderType
from app.modules.ai.domain.exceptions import AIProviderUnavailableError
from app.modules.ai.domain.value_objects import AIMessage, AIModel
from tests.unit.modules.ai.application.fakes import FakeAIProviderPort


def _request() -> ChatCompletionRequest:
    return ChatCompletionRequest(
        messages=(AIMessage(role=AIMessageRole.USER, content="hi"),),
        model=AIModel(provider=AIProviderType.MOCK, name="mock-model"),
    )


class TestGenerateChatCompletion:
    async def test_delegates_to_the_injected_provider(self) -> None:
        provider = FakeAIProviderPort()
        use_case = GenerateChatCompletion(provider=provider)

        response = await use_case.execute(_request())

        assert response.message.content == "fake reply"
        assert len(provider.received_requests) == 1

    async def test_propagates_provider_errors(self) -> None:
        provider = FakeAIProviderPort(
            error=AIProviderUnavailableError(provider="mock", message="down")
        )
        use_case = GenerateChatCompletion(provider=provider)

        with pytest.raises(AIProviderUnavailableError):
            await use_case.execute(_request())

    async def test_passes_the_exact_request_through_unmodified(self) -> None:
        provider = FakeAIProviderPort()
        use_case = GenerateChatCompletion(provider=provider)
        request = _request()

        await use_case.execute(request)

        assert provider.received_requests[0] is request
