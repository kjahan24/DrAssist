"""OpenAI chat-completion adapter (`AIProviderPort`).

`client` is duck-typed to `openai.AsyncOpenAI`'s
`.chat.completions.create(...)` surface (typed `Any` — no `openai`-specific
stub is imported at module scope, so importing this module never requires
the `openai` package to be installed; see `_get_client` for the one place
it's imported, lazily, only when a real call is actually made without an
injected test double). Unit tests construct this adapter with a small fake
object exposing that one method — see
`tests/unit/modules/ai/infrastructure/test_openai_provider.py`.
"""

from collections.abc import AsyncIterator
from time import perf_counter
from typing import Any

from app.modules.ai.application.dto import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    StreamChunk,
)
from app.modules.ai.application.ports import AIProviderPort
from app.modules.ai.domain.enums import AIFinishReason, AIMessageRole, AIProviderType
from app.modules.ai.domain.exceptions import AIProviderAuthenticationError
from app.modules.ai.domain.value_objects import AIMessage, TokenUsage
from app.modules.ai.infrastructure.providers.exception_mapping import classify_provider_exception

_FINISH_REASON_MAP = {
    "stop": AIFinishReason.STOP,
    "length": AIFinishReason.LENGTH,
    "content_filter": AIFinishReason.CONTENT_FILTER,
    "tool_calls": AIFinishReason.TOOL_CALLS,
}


def _to_openai_message(message: AIMessage) -> dict[str, str]:
    payload = {"role": message.role.value, "content": message.content}
    if message.name is not None:
        payload["name"] = message.name
    return payload


class OpenAIProvider(AIProviderPort):
    def __init__(self, *, api_key: str | None, client: Any | None = None) -> None:
        self._api_key = api_key
        self._client = client

    @property
    def provider_type(self) -> AIProviderType:
        return AIProviderType.OPENAI

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        if not self._api_key:
            raise AIProviderAuthenticationError(
                provider=AIProviderType.OPENAI.value, message="OPENAI_API_KEY is not configured"
            )
        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(api_key=self._api_key)
        return self._client

    async def complete(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        client = self._get_client()
        start = perf_counter()
        try:
            response = await client.chat.completions.create(
                model=request.model.name,
                messages=[_to_openai_message(m) for m in request.messages],
                temperature=request.temperature,
                max_tokens=request.max_output_tokens,
                top_p=request.top_p,
                stop=list(request.stop_sequences) or None,
            )
        except Exception as exc:
            raise classify_provider_exception(exc, provider=AIProviderType.OPENAI) from exc
        latency_ms = (perf_counter() - start) * 1000

        choice = response.choices[0]
        usage = response.usage
        return ChatCompletionResponse(
            message=AIMessage(role=AIMessageRole.ASSISTANT, content=choice.message.content or ""),
            model=request.model,
            provider=AIProviderType.OPENAI,
            usage=TokenUsage(
                prompt_tokens=usage.prompt_tokens if usage else 0,
                completion_tokens=usage.completion_tokens if usage else 0,
                total_tokens=usage.total_tokens if usage else 0,
            ),
            finish_reason=_FINISH_REASON_MAP.get(choice.finish_reason, AIFinishReason.STOP),
            latency_ms=latency_ms,
            raw_response_id=getattr(response, "id", None),
        )

    async def stream_complete(self, request: ChatCompletionRequest) -> AsyncIterator[StreamChunk]:
        client = self._get_client()
        try:
            stream = await client.chat.completions.create(
                model=request.model.name,
                messages=[_to_openai_message(m) for m in request.messages],
                temperature=request.temperature,
                max_tokens=request.max_output_tokens,
                stream=True,
            )
        except Exception as exc:
            raise classify_provider_exception(exc, provider=AIProviderType.OPENAI) from exc

        async for chunk in stream:
            choice = chunk.choices[0]
            delta_content = choice.delta.content or ""
            raw_finish_reason = choice.finish_reason
            finish_reason = (
                _FINISH_REASON_MAP.get(raw_finish_reason, AIFinishReason.STOP)
                if raw_finish_reason
                else None
            )
            yield StreamChunk(
                delta=delta_content,
                finish_reason=finish_reason,
                is_final=raw_finish_reason is not None,
            )
