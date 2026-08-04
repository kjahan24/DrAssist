"""Unit tests for `OllamaProvider`, using `httpx.MockTransport` — Ollama
needs no SDK, so this is the one adapter exercisable against a real
(mocked-transport) HTTP client rather than a hand-rolled fake object."""

import json
from collections.abc import Callable
from typing import Any

import httpx
import pytest

from app.modules.ai.application.dto import ChatCompletionRequest
from app.modules.ai.domain.enums import AIFinishReason, AIMessageRole, AIProviderType
from app.modules.ai.domain.exceptions import (
    AIProviderAuthenticationError,
    AIProviderInvalidRequestError,
    AIProviderRateLimitError,
)
from app.modules.ai.domain.value_objects import AIMessage, AIModel
from app.modules.ai.infrastructure.llm.ollama_provider import OllamaProvider


def _client(handler: Callable[[httpx.Request], httpx.Response]) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="http://localhost:11434"
    )


def _request() -> ChatCompletionRequest:
    return ChatCompletionRequest(
        messages=(AIMessage(role=AIMessageRole.USER, content="hi"),),
        model=AIModel(provider=AIProviderType.OLLAMA, name="llama3.1"),
    )


class TestOllamaProviderComplete:
    def test_provider_type_is_ollama(self) -> None:
        provider = OllamaProvider(base_url="http://localhost:11434")
        assert provider.provider_type is AIProviderType.OLLAMA

    async def test_maps_a_successful_response(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "message": {"role": "assistant", "content": "hi there"},
                    "done_reason": "stop",
                    "prompt_eval_count": 5,
                    "eval_count": 3,
                },
            )

        provider = OllamaProvider(base_url="http://localhost:11434", client=_client(handler))

        result = await provider.complete(_request())

        assert result.message.content == "hi there"
        assert result.finish_reason is AIFinishReason.STOP
        assert result.usage.prompt_tokens == 5
        assert result.usage.completion_tokens == 3

    async def test_sends_the_model_and_message_payload(self) -> None:
        captured: dict[str, Any] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["body"] = json.loads(request.content)
            return httpx.Response(200, json={"message": {"content": "ok"}, "done_reason": "stop"})

        provider = OllamaProvider(base_url="http://localhost:11434", client=_client(handler))

        await provider.complete(_request())

        assert captured["body"]["model"] == "llama3.1"
        assert captured["body"]["messages"] == [{"role": "user", "content": "hi"}]
        assert captured["body"]["stream"] is False

    async def test_401_response_raises_authentication_error(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(401, text="unauthorized")

        provider = OllamaProvider(base_url="http://localhost:11434", client=_client(handler))

        with pytest.raises(AIProviderAuthenticationError):
            await provider.complete(_request())

    async def test_429_response_raises_rate_limit_error(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(429, text="too many requests")

        provider = OllamaProvider(base_url="http://localhost:11434", client=_client(handler))

        with pytest.raises(AIProviderRateLimitError):
            await provider.complete(_request())

    async def test_400_response_raises_invalid_request_error(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(400, text="bad request")

        provider = OllamaProvider(base_url="http://localhost:11434", client=_client(handler))

        with pytest.raises(AIProviderInvalidRequestError):
            await provider.complete(_request())


class TestOllamaProviderStream:
    async def test_stream_complete_yields_mapped_chunks(self) -> None:
        lines = [
            {"message": {"content": "Hel"}, "done": False},
            {"message": {"content": "lo"}, "done": False},
            {"message": {"content": ""}, "done": True, "done_reason": "stop"},
        ]

        def handler(request: httpx.Request) -> httpx.Response:
            body = "\n".join(json.dumps(line) for line in lines).encode()
            return httpx.Response(200, content=body)

        provider = OllamaProvider(base_url="http://localhost:11434", client=_client(handler))

        received = [chunk async for chunk in provider.stream_complete(_request())]

        assert "".join(c.delta for c in received) == "Hello"
        assert received[-1].is_final is True
        assert received[-1].finish_reason is AIFinishReason.STOP
