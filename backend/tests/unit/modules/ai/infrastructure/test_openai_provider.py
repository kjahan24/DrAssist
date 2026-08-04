"""Unit tests for `OpenAIProvider`, using a fake client duck-typed to
`openai.AsyncOpenAI`'s `.chat.completions.create(...)` surface — no real
`openai` package interaction is required (see that module's own docstring
for why)."""

from collections.abc import AsyncIterator
from types import SimpleNamespace
from typing import Any

import pytest

from app.modules.ai.application.dto import ChatCompletionRequest
from app.modules.ai.domain.enums import AIFinishReason, AIMessageRole, AIProviderType
from app.modules.ai.domain.exceptions import AIProviderAuthenticationError, AIProviderRateLimitError
from app.modules.ai.domain.value_objects import AIMessage, AIModel
from app.modules.ai.infrastructure.llm.openai_provider import OpenAIProvider


class _FakeCompletions:
    def __init__(
        self,
        *,
        response: SimpleNamespace | None = None,
        stream_chunks: list[SimpleNamespace] | None = None,
        error: Exception | None = None,
    ) -> None:
        self._response = response
        self._stream_chunks = stream_chunks or []
        self._error = error
        self.received_kwargs: dict[str, Any] | None = None

    async def create(self, **kwargs: Any) -> SimpleNamespace | AsyncIterator[SimpleNamespace]:
        self.received_kwargs = kwargs
        if self._error is not None:
            raise self._error
        if kwargs.get("stream"):
            return self._stream()
        assert self._response is not None
        return self._response

    async def _stream(self) -> AsyncIterator[SimpleNamespace]:
        for chunk in self._stream_chunks:
            yield chunk


class _FakeOpenAIClient:
    def __init__(
        self,
        *,
        response: SimpleNamespace | None = None,
        stream_chunks: list[SimpleNamespace] | None = None,
        error: Exception | None = None,
    ) -> None:
        completions = _FakeCompletions(response=response, stream_chunks=stream_chunks, error=error)
        self.chat = SimpleNamespace(completions=completions)


def _response(
    content: str = "hi there", finish_reason: str = "stop", response_id: str = "resp-1"
) -> SimpleNamespace:
    message = SimpleNamespace(content=content)
    return SimpleNamespace(
        id=response_id,
        choices=[SimpleNamespace(message=message, finish_reason=finish_reason)],
        usage=SimpleNamespace(prompt_tokens=5, completion_tokens=3, total_tokens=8),
    )


def _request() -> ChatCompletionRequest:
    return ChatCompletionRequest(
        messages=(AIMessage(role=AIMessageRole.USER, content="hi"),),
        model=AIModel(provider=AIProviderType.OPENAI, name="gpt-4o-mini"),
    )


class TestOpenAIProvider:
    def test_provider_type_is_openai(self) -> None:
        assert OpenAIProvider(api_key="key").provider_type is AIProviderType.OPENAI

    async def test_complete_maps_a_successful_response(self) -> None:
        client = _FakeOpenAIClient(response=_response())
        provider = OpenAIProvider(api_key="key", client=client)

        result = await provider.complete(_request())

        assert result.message.content == "hi there"
        assert result.message.role is AIMessageRole.ASSISTANT
        assert result.finish_reason is AIFinishReason.STOP
        assert result.usage.total_tokens == 8
        assert result.provider is AIProviderType.OPENAI
        assert result.raw_response_id == "resp-1"

    async def test_complete_maps_length_finish_reason(self) -> None:
        client = _FakeOpenAIClient(response=_response(finish_reason="length"))
        provider = OpenAIProvider(api_key="key", client=client)

        result = await provider.complete(_request())

        assert result.finish_reason is AIFinishReason.LENGTH

    async def test_complete_sends_model_name_and_messages(self) -> None:
        client = _FakeOpenAIClient(response=_response())
        provider = OpenAIProvider(api_key="key", client=client)

        await provider.complete(_request())

        kwargs = client.chat.completions.received_kwargs
        assert kwargs is not None
        assert kwargs["model"] == "gpt-4o-mini"
        assert kwargs["messages"] == [{"role": "user", "content": "hi"}]

    async def test_missing_api_key_and_no_client_raises_authentication_error(self) -> None:
        provider = OpenAIProvider(api_key=None)
        with pytest.raises(AIProviderAuthenticationError):
            await provider.complete(_request())

    async def test_sdk_exception_is_classified_into_normalized_error(self) -> None:
        class RateLimitError(Exception):
            pass

        client = _FakeOpenAIClient(error=RateLimitError("slow down"))
        provider = OpenAIProvider(api_key="key", client=client)

        with pytest.raises(AIProviderRateLimitError):
            await provider.complete(_request())

    async def test_stream_complete_yields_mapped_chunks(self) -> None:
        chunks = [
            SimpleNamespace(
                choices=[SimpleNamespace(delta=SimpleNamespace(content="Hel"), finish_reason=None)]
            ),
            SimpleNamespace(
                choices=[SimpleNamespace(delta=SimpleNamespace(content="lo"), finish_reason=None)]
            ),
            SimpleNamespace(
                choices=[SimpleNamespace(delta=SimpleNamespace(content=""), finish_reason="stop")]
            ),
        ]
        client = _FakeOpenAIClient(stream_chunks=chunks)
        provider = OpenAIProvider(api_key="key", client=client)

        received = [chunk async for chunk in provider.stream_complete(_request())]

        assert "".join(c.delta for c in received) == "Hello"
        assert received[-1].is_final is True
        assert received[-1].finish_reason is AIFinishReason.STOP
