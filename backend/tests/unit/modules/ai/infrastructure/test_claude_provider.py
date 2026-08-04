"""Unit tests for `ClaudeProvider`, using a fake client duck-typed to
`anthropic.AsyncAnthropic`'s `.messages.create(...)` surface."""

from collections.abc import AsyncIterator
from types import SimpleNamespace
from typing import Any

import pytest

from app.modules.ai.application.dto import ChatCompletionRequest
from app.modules.ai.domain.enums import AIFinishReason, AIMessageRole, AIProviderType
from app.modules.ai.domain.exceptions import AIProviderAuthenticationError
from app.modules.ai.domain.value_objects import AIMessage, AIModel
from app.modules.ai.infrastructure.llm.claude_provider import ClaudeProvider


class _FakeMessages:
    def __init__(
        self,
        *,
        response: SimpleNamespace | None = None,
        stream_events: list[SimpleNamespace] | None = None,
        error: Exception | None = None,
    ) -> None:
        self._response = response
        self._stream_events = stream_events or []
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
        for event in self._stream_events:
            yield event


class _FakeAnthropicClient:
    def __init__(
        self,
        *,
        response: SimpleNamespace | None = None,
        stream_events: list[SimpleNamespace] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.messages = _FakeMessages(response=response, stream_events=stream_events, error=error)


def _response(text: str = "hi there", stop_reason: str = "end_turn") -> SimpleNamespace:
    return SimpleNamespace(
        id="msg-1",
        content=[SimpleNamespace(text=text)],
        stop_reason=stop_reason,
        usage=SimpleNamespace(input_tokens=6, output_tokens=4),
    )


def _request(*, with_system: bool = False) -> ChatCompletionRequest:
    messages = []
    if with_system:
        messages.append(AIMessage(role=AIMessageRole.SYSTEM, content="be concise"))
    messages.append(AIMessage(role=AIMessageRole.USER, content="hi"))
    return ChatCompletionRequest(
        messages=tuple(messages),
        model=AIModel(provider=AIProviderType.CLAUDE, name="claude-3-5-sonnet-latest"),
    )


class TestClaudeProvider:
    def test_provider_type_is_claude(self) -> None:
        assert ClaudeProvider(api_key="key").provider_type is AIProviderType.CLAUDE

    async def test_complete_maps_a_successful_response(self) -> None:
        client = _FakeAnthropicClient(response=_response())
        provider = ClaudeProvider(api_key="key", client=client)

        result = await provider.complete(_request())

        assert result.message.content == "hi there"
        assert result.finish_reason is AIFinishReason.STOP
        assert result.usage.prompt_tokens == 6
        assert result.usage.completion_tokens == 4
        assert result.usage.total_tokens == 10

    async def test_max_tokens_finish_reason_maps_to_length(self) -> None:
        client = _FakeAnthropicClient(response=_response(stop_reason="max_tokens"))
        provider = ClaudeProvider(api_key="key", client=client)

        result = await provider.complete(_request())

        assert result.finish_reason is AIFinishReason.LENGTH

    async def test_system_messages_are_extracted_into_the_system_parameter(self) -> None:
        client = _FakeAnthropicClient(response=_response())
        provider = ClaudeProvider(api_key="key", client=client)

        await provider.complete(_request(with_system=True))

        kwargs = client.messages.received_kwargs
        assert kwargs is not None
        assert kwargs["system"] == "be concise"
        assert kwargs["messages"] == [{"role": "user", "content": "hi"}]

    async def test_missing_api_key_raises_authentication_error(self) -> None:
        provider = ClaudeProvider(api_key=None)
        with pytest.raises(AIProviderAuthenticationError):
            await provider.complete(_request())

    async def test_stream_complete_yields_content_deltas_then_a_final_chunk(self) -> None:
        events = [
            SimpleNamespace(type="content_block_delta", delta=SimpleNamespace(text="Hel")),
            SimpleNamespace(type="content_block_delta", delta=SimpleNamespace(text="lo")),
            SimpleNamespace(type="message_delta", delta=SimpleNamespace(stop_reason="end_turn")),
        ]
        client = _FakeAnthropicClient(stream_events=events)
        provider = ClaudeProvider(api_key="key", client=client)

        received = [chunk async for chunk in provider.stream_complete(_request())]

        assert "".join(c.delta for c in received) == "Hello"
        assert received[-1].is_final is True
        assert received[-1].finish_reason is AIFinishReason.STOP
