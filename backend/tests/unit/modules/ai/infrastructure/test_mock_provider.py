"""Unit tests for `MockAIProvider`."""

from app.modules.ai.application.dto import ChatCompletionRequest
from app.modules.ai.domain.enums import AIFinishReason, AIMessageRole, AIProviderType
from app.modules.ai.domain.value_objects import AIMessage, AIModel
from app.modules.ai.infrastructure.llm.mock_provider import MockAIProvider


def _request(content: str = "hello there") -> ChatCompletionRequest:
    return ChatCompletionRequest(
        messages=(AIMessage(role=AIMessageRole.USER, content=content),),
        model=AIModel(provider=AIProviderType.MOCK, name="mock-model"),
    )


class TestMockAIProvider:
    def test_provider_type_is_mock(self) -> None:
        assert MockAIProvider().provider_type is AIProviderType.MOCK

    async def test_complete_echoes_the_last_user_message(self) -> None:
        provider = MockAIProvider()
        response = await provider.complete(_request("what is the weather"))
        assert "what is the weather" in response.message.content
        assert response.finish_reason is AIFinishReason.STOP
        assert response.provider is AIProviderType.MOCK

    async def test_complete_uses_a_canned_reply_when_configured(self) -> None:
        provider = MockAIProvider(canned_reply="fixed reply")
        response = await provider.complete(_request())
        assert response.message.content == "fixed reply"

    async def test_complete_is_deterministic(self) -> None:
        provider = MockAIProvider()
        first = await provider.complete(_request("same input"))
        second = await provider.complete(_request("same input"))
        assert first.message.content == second.message.content

    async def test_usage_scales_with_input_length(self) -> None:
        provider = MockAIProvider()
        short_response = await provider.complete(_request("hi"))
        long_response = await provider.complete(_request("hi " * 200))
        assert long_response.usage.prompt_tokens > short_response.usage.prompt_tokens

    async def test_stream_complete_yields_the_full_reply_across_chunks(self) -> None:
        provider = MockAIProvider(canned_reply="one two three")
        chunks = [chunk async for chunk in provider.stream_complete(_request())]
        assert "".join(c.delta for c in chunks).strip() == "one two three"
        assert chunks[-1].is_final is True
        assert all(not c.is_final for c in chunks[:-1])
