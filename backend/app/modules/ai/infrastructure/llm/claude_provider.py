"""Anthropic Claude chat-completion adapter (`AIProviderPort`).

`client` is duck-typed to `anthropic.AsyncAnthropic`'s `.messages.create(...)`
surface — see `openai_provider.py`'s module docstring for why this stays
`Any`-typed and lazily imports the real SDK only when no test double is
injected.

Anthropic's Messages API separates the system prompt from the turn-by-turn
`messages` list (unlike OpenAI/Gemini, which fold it in as just another
role) — `_split_system_prompt` extracts every leading/embedded
`AIMessageRole.SYSTEM` message from `request.messages` and joins them into
the single `system=` parameter Anthropic expects, since `AIMessage` itself
is provider-agnostic and always represents a system prompt as a normal
message with that role.
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
    "end_turn": AIFinishReason.STOP,
    "stop_sequence": AIFinishReason.STOP,
    "max_tokens": AIFinishReason.LENGTH,
    "tool_use": AIFinishReason.TOOL_CALLS,
}
_DEFAULT_MAX_TOKENS = 4096


def _split_system_prompt(
    messages: tuple[AIMessage, ...],
) -> tuple[str | None, list[dict[str, str]]]:
    system_parts = [m.content for m in messages if m.role == AIMessageRole.SYSTEM]
    turns = [
        {"role": m.role.value, "content": m.content}
        for m in messages
        if m.role != AIMessageRole.SYSTEM
    ]
    system_prompt = "\n\n".join(system_parts) if system_parts else None
    return system_prompt, turns


class ClaudeProvider(AIProviderPort):
    def __init__(self, *, api_key: str | None, client: Any | None = None) -> None:
        self._api_key = api_key
        self._client = client

    @property
    def provider_type(self) -> AIProviderType:
        return AIProviderType.CLAUDE

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        if not self._api_key:
            raise AIProviderAuthenticationError(
                provider=AIProviderType.CLAUDE.value,
                message="ANTHROPIC_API_KEY is not configured",
            )
        from anthropic import AsyncAnthropic

        self._client = AsyncAnthropic(api_key=self._api_key)
        return self._client

    async def complete(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        client = self._get_client()
        system_prompt, turns = _split_system_prompt(request.messages)
        start = perf_counter()
        try:
            kwargs: dict[str, Any] = {
                "model": request.model.name,
                "messages": turns,
                "max_tokens": request.max_output_tokens or _DEFAULT_MAX_TOKENS,
                "temperature": request.temperature,
            }
            if system_prompt is not None:
                kwargs["system"] = system_prompt
            if request.stop_sequences:
                kwargs["stop_sequences"] = list(request.stop_sequences)
            response = await client.messages.create(**kwargs)
        except Exception as exc:
            raise classify_provider_exception(exc, provider=AIProviderType.CLAUDE) from exc
        latency_ms = (perf_counter() - start) * 1000

        text = "".join(block.text for block in response.content if hasattr(block, "text"))
        usage = response.usage
        return ChatCompletionResponse(
            message=AIMessage(role=AIMessageRole.ASSISTANT, content=text),
            model=request.model,
            provider=AIProviderType.CLAUDE,
            usage=TokenUsage(
                prompt_tokens=usage.input_tokens,
                completion_tokens=usage.output_tokens,
                total_tokens=usage.input_tokens + usage.output_tokens,
            ),
            finish_reason=_FINISH_REASON_MAP.get(response.stop_reason, AIFinishReason.STOP),
            latency_ms=latency_ms,
            raw_response_id=getattr(response, "id", None),
        )

    async def stream_complete(self, request: ChatCompletionRequest) -> AsyncIterator[StreamChunk]:
        """Consumes a sequence of Anthropic streaming events (each exposing
        `.type` and, for content deltas, `.delta.text`; the final
        `message_delta` event carries `.delta.stop_reason`) — the shape
        `client.messages.create(..., stream=True)` yields."""
        client = self._get_client()
        system_prompt, turns = _split_system_prompt(request.messages)
        try:
            kwargs: dict[str, Any] = {
                "model": request.model.name,
                "messages": turns,
                "max_tokens": request.max_output_tokens or _DEFAULT_MAX_TOKENS,
                "temperature": request.temperature,
                "stream": True,
            }
            if system_prompt is not None:
                kwargs["system"] = system_prompt
            stream = await client.messages.create(**kwargs)
        except Exception as exc:
            raise classify_provider_exception(exc, provider=AIProviderType.CLAUDE) from exc

        async for event in stream:
            event_type = getattr(event, "type", None)
            if event_type == "content_block_delta":
                delta_text = getattr(event.delta, "text", "") or ""
                yield StreamChunk(delta=delta_text, finish_reason=None, is_final=False)
            elif event_type == "message_delta":
                raw_stop_reason = getattr(event.delta, "stop_reason", None)
                stop_reason_key = str(raw_stop_reason) if raw_stop_reason is not None else ""
                yield StreamChunk(
                    delta="",
                    finish_reason=_FINISH_REASON_MAP.get(stop_reason_key, AIFinishReason.STOP),
                    is_final=True,
                )
