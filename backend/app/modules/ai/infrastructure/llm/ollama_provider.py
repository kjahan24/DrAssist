"""Ollama (local model server) chat-completion adapter (`AIProviderPort`).

Unlike the other three adapters, Ollama needs no SDK at all — it's a
plain local HTTP server (`OLLAMA_BASE_URL`, default
`http://localhost:11434`) with a JSON REST API, so this adapter talks to
it directly over `httpx` (already a base dependency), making it the one
adapter in this module that is fully exercisable in unit tests against a
real (mocked-transport) HTTP client rather than a hand-rolled fake SDK
object — see `httpx.MockTransport` usage in
`tests/unit/modules/ai/infrastructure/test_ollama_provider.py`.
"""

import json
from collections.abc import AsyncIterator
from time import perf_counter
from typing import Any

import httpx

from app.modules.ai.application.dto import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    StreamChunk,
)
from app.modules.ai.application.ports import AIProviderPort
from app.modules.ai.domain.enums import AIFinishReason, AIMessageRole, AIProviderType
from app.modules.ai.domain.value_objects import AIMessage, TokenUsage
from app.modules.ai.infrastructure.providers.exception_mapping import classify_provider_exception

_FINISH_REASON_MAP = {"stop": AIFinishReason.STOP, "length": AIFinishReason.LENGTH}


def _to_ollama_messages(messages: tuple[AIMessage, ...]) -> list[dict[str, str]]:
    return [{"role": m.role.value, "content": m.content} for m in messages]


class OllamaProvider(AIProviderPort):
    def __init__(self, *, base_url: str, client: httpx.AsyncClient | None = None) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = client

    @property
    def provider_type(self) -> AIProviderType:
        return AIProviderType.OLLAMA

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(base_url=self._base_url, timeout=60.0)
        return self._client

    async def complete(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        client = self._get_client()
        payload: dict[str, Any] = {
            "model": request.model.name,
            "messages": _to_ollama_messages(request.messages),
            "stream": False,
            "options": {"temperature": request.temperature},
        }
        start = perf_counter()
        try:
            http_response = await client.post("/api/chat", json=payload)
            http_response.raise_for_status()
        except httpx.HTTPError as exc:
            raise classify_provider_exception(exc, provider=AIProviderType.OLLAMA) from exc
        latency_ms = (perf_counter() - start) * 1000

        body = http_response.json()
        prompt_tokens = body.get("prompt_eval_count", 0)
        completion_tokens = body.get("eval_count", 0)
        done_reason = body.get("done_reason", "stop")
        return ChatCompletionResponse(
            message=AIMessage(role=AIMessageRole.ASSISTANT, content=body["message"]["content"]),
            model=request.model,
            provider=AIProviderType.OLLAMA,
            usage=TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
            ),
            finish_reason=_FINISH_REASON_MAP.get(done_reason, AIFinishReason.STOP),
            latency_ms=latency_ms,
        )

    async def stream_complete(self, request: ChatCompletionRequest) -> AsyncIterator[StreamChunk]:
        client = self._get_client()
        payload: dict[str, Any] = {
            "model": request.model.name,
            "messages": _to_ollama_messages(request.messages),
            "stream": True,
            "options": {"temperature": request.temperature},
        }
        try:
            async with client.stream("POST", "/api/chat", json=payload) as http_response:
                http_response.raise_for_status()
                async for line in http_response.aiter_lines():
                    if not line.strip():
                        continue
                    chunk = json.loads(line)
                    is_final = bool(chunk.get("done", False))
                    chunk_done_reason = chunk.get("done_reason", "stop")
                    yield StreamChunk(
                        delta=chunk.get("message", {}).get("content", ""),
                        finish_reason=(
                            _FINISH_REASON_MAP.get(chunk_done_reason, AIFinishReason.STOP)
                            if is_final
                            else None
                        ),
                        is_final=is_final,
                    )
        except httpx.HTTPError as exc:
            raise classify_provider_exception(exc, provider=AIProviderType.OLLAMA) from exc
