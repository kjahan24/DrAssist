"""Unit tests for `GeminiChatProvider`, using a fake client duck-typed to
the one method `_DefaultGeminiClient` exposes:
`generate_content_async(model=, contents=, generation_config=)`."""

from types import SimpleNamespace
from typing import Any

import pytest

from app.modules.ai.application.dto import ChatCompletionRequest
from app.modules.ai.domain.enums import AIFinishReason, AIMessageRole, AIProviderType
from app.modules.ai.domain.exceptions import AIProviderAuthenticationError
from app.modules.ai.domain.value_objects import AIMessage, AIModel
from app.modules.ai.infrastructure.llm.gemini_provider import GeminiChatProvider


class _FakeGeminiClient:
    def __init__(
        self, *, response: SimpleNamespace | None = None, error: Exception | None = None
    ) -> None:
        self._response = response
        self._error = error
        self.received_kwargs: dict[str, Any] | None = None

    async def generate_content_async(
        self, *, model: str, contents: list[dict[str, Any]], generation_config: dict[str, Any]
    ) -> SimpleNamespace:
        self.received_kwargs = {
            "model": model,
            "contents": contents,
            "generation_config": generation_config,
        }
        if self._error is not None:
            raise self._error
        assert self._response is not None
        return self._response


def _response(text: str = "hi there", finish_reason_name: str = "STOP") -> SimpleNamespace:
    return SimpleNamespace(
        text=text,
        candidates=[SimpleNamespace(finish_reason=SimpleNamespace(name=finish_reason_name))],
        usage_metadata=SimpleNamespace(
            prompt_token_count=5, candidates_token_count=3, total_token_count=8
        ),
    )


def _request() -> ChatCompletionRequest:
    return ChatCompletionRequest(
        messages=(AIMessage(role=AIMessageRole.USER, content="hi"),),
        model=AIModel(provider=AIProviderType.GEMINI, name="gemini-2.5-flash"),
    )


class TestGeminiChatProvider:
    def test_provider_type_is_gemini(self) -> None:
        assert GeminiChatProvider(api_key="key").provider_type is AIProviderType.GEMINI

    async def test_complete_maps_a_successful_response(self) -> None:
        client = _FakeGeminiClient(response=_response())
        provider = GeminiChatProvider(api_key="key", client=client)

        result = await provider.complete(_request())

        assert result.message.content == "hi there"
        assert result.finish_reason is AIFinishReason.STOP
        assert result.usage.total_tokens == 8
        assert result.latency_ms >= 0

    async def test_max_tokens_finish_reason_maps_to_length(self) -> None:
        client = _FakeGeminiClient(response=_response(finish_reason_name="MAX_TOKENS"))
        provider = GeminiChatProvider(api_key="key", client=client)

        result = await provider.complete(_request())

        assert result.finish_reason is AIFinishReason.LENGTH

    async def test_user_role_maps_to_gemini_user_and_assistant_to_model(self) -> None:
        client = _FakeGeminiClient(response=_response())
        provider = GeminiChatProvider(api_key="key", client=client)
        request = ChatCompletionRequest(
            messages=(
                AIMessage(role=AIMessageRole.USER, content="hi"),
                AIMessage(role=AIMessageRole.ASSISTANT, content="hello"),
            ),
            model=AIModel(provider=AIProviderType.GEMINI, name="gemini-2.5-flash"),
        )

        await provider.complete(request)

        received_kwargs = client.received_kwargs
        assert received_kwargs is not None
        contents = received_kwargs["contents"]
        assert contents[0]["role"] == "user"
        assert contents[1]["role"] == "model"

    async def test_missing_api_key_raises_authentication_error(self) -> None:
        provider = GeminiChatProvider(api_key=None)
        with pytest.raises(AIProviderAuthenticationError):
            await provider.complete(_request())

    async def test_stream_complete_yields_a_single_final_chunk(self) -> None:
        client = _FakeGeminiClient(response=_response(text="whole reply"))
        provider = GeminiChatProvider(api_key="key", client=client)

        received = [chunk async for chunk in provider.stream_complete(_request())]

        assert len(received) == 1
        assert received[0].delta == "whole reply"
        assert received[0].is_final is True
