"""`MockAIProvider` — a deterministic, zero-I/O `AIProviderPort`
implementation. The default provider for local development/CI
(`AISettings.default_provider`) and for any test that needs a real
`AIProviderPort` instance without injecting a fake by hand.

Deterministic by design: `complete()` echoes a fixed, predictable reply
built from the request (never a random string) so a caller's test
assertions stay stable across runs, and token usage is derived from text
length via the same heuristic `HeuristicTokenizer` uses, so usage/cost
plumbing has *something* realistic to compute against in dev without a
real provider configured.
"""

from collections.abc import AsyncIterator
from time import perf_counter

from app.modules.ai.application.dto import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    StreamChunk,
)
from app.modules.ai.application.ports import AIProviderPort
from app.modules.ai.domain.enums import AIFinishReason, AIMessageRole, AIProviderType
from app.modules.ai.domain.value_objects import AIMessage, TokenUsage

_CHARS_PER_TOKEN = 4


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // _CHARS_PER_TOKEN)


class MockAIProvider(AIProviderPort):
    def __init__(self, *, canned_reply: str | None = None) -> None:
        self._canned_reply = canned_reply

    @property
    def provider_type(self) -> AIProviderType:
        return AIProviderType.MOCK

    async def complete(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        start = perf_counter()
        last_user_message = next(
            (m.content for m in reversed(request.messages) if m.role == AIMessageRole.USER),
            "",
        )
        reply_text = self._canned_reply or f"Mock response to: {last_user_message[:200]}"
        prompt_tokens = sum(_estimate_tokens(m.content) for m in request.messages)
        completion_tokens = _estimate_tokens(reply_text)
        latency_ms = (perf_counter() - start) * 1000
        return ChatCompletionResponse(
            message=AIMessage(role=AIMessageRole.ASSISTANT, content=reply_text),
            model=request.model,
            provider=AIProviderType.MOCK,
            usage=TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
            ),
            finish_reason=AIFinishReason.STOP,
            latency_ms=latency_ms,
        )

    async def stream_complete(self, request: ChatCompletionRequest) -> AsyncIterator[StreamChunk]:
        response = await self.complete(request)
        words = response.message.content.split(" ")
        for index, word in enumerate(words):
            is_final = index == len(words) - 1
            yield StreamChunk(
                delta=word if index == 0 else f" {word}",
                finish_reason=AIFinishReason.STOP if is_final else None,
                is_final=is_final,
            )
