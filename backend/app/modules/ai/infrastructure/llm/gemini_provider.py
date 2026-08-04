"""Google Gemini chat-completion adapter (`AIProviderPort`).

Distinct from the pre-existing `app.infrastructure.ai.gemini_client
.GeminiClient` (implements the older, narrower `TextGenerationPort` —
see `application/ports.py`'s module docstring for why that file is left
untouched). This adapter implements the richer `AIProviderPort` this
task's Foundation layer defines.

`google.generativeai`'s `GenerativeModel` is constructed per model name
(unlike OpenAI's/Anthropic's client, which take a model name per call) —
`_DefaultGeminiClient` below absorbs that quirk behind a model-per-call
method (`generate_content_async(model=..., contents=..., generation_config=...)`),
so `GeminiChatProvider.complete()` itself stays symmetric with the other
three adapters, and a test double only needs to implement that one method.
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
    "STOP": AIFinishReason.STOP,
    "MAX_TOKENS": AIFinishReason.LENGTH,
    "SAFETY": AIFinishReason.CONTENT_FILTER,
    "RECITATION": AIFinishReason.CONTENT_FILTER,
}
_ROLE_MAP = {
    AIMessageRole.USER: "user",
    AIMessageRole.ASSISTANT: "model",
    AIMessageRole.SYSTEM: "user",
    AIMessageRole.TOOL: "function",
}


def _to_gemini_contents(messages: tuple[AIMessage, ...]) -> list[dict[str, Any]]:
    return [{"role": _ROLE_MAP[m.role], "parts": [m.content]} for m in messages]


class _DefaultGeminiClient:
    def __init__(self, api_key: str) -> None:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        self._genai = genai
        self._models: dict[str, Any] = {}

    def _model_for(self, model_name: str) -> Any:
        if model_name not in self._models:
            self._models[model_name] = self._genai.GenerativeModel(model_name)
        return self._models[model_name]

    async def generate_content_async(
        self, *, model: str, contents: list[dict[str, Any]], generation_config: dict[str, Any]
    ) -> Any:
        return await self._model_for(model).generate_content_async(
            contents, generation_config=generation_config
        )


class GeminiChatProvider(AIProviderPort):
    def __init__(self, *, api_key: str | None, client: Any | None = None) -> None:
        self._api_key = api_key
        self._client = client

    @property
    def provider_type(self) -> AIProviderType:
        return AIProviderType.GEMINI

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        if not self._api_key:
            raise AIProviderAuthenticationError(
                provider=AIProviderType.GEMINI.value, message="GEMINI_API_KEY is not configured"
            )
        self._client = _DefaultGeminiClient(self._api_key)
        return self._client

    async def complete(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        client = self._get_client()
        generation_config: dict[str, Any] = {"temperature": request.temperature}
        if request.max_output_tokens is not None:
            generation_config["max_output_tokens"] = request.max_output_tokens
        if request.top_p is not None:
            generation_config["top_p"] = request.top_p
        if request.stop_sequences:
            generation_config["stop_sequences"] = list(request.stop_sequences)

        start = perf_counter()
        try:
            response = await client.generate_content_async(
                model=request.model.name,
                contents=_to_gemini_contents(request.messages),
                generation_config=generation_config,
            )
        except Exception as exc:
            raise classify_provider_exception(exc, provider=AIProviderType.GEMINI) from exc
        latency_ms = (perf_counter() - start) * 1000

        candidate = response.candidates[0]
        raw_finish_reason = getattr(candidate, "finish_reason", None)
        finish_reason_value = getattr(raw_finish_reason, "name", raw_finish_reason)
        finish_reason_name = str(finish_reason_value) if finish_reason_value is not None else "STOP"
        usage_metadata = getattr(response, "usage_metadata", None)
        prompt_tokens = getattr(usage_metadata, "prompt_token_count", 0) if usage_metadata else 0
        completion_tokens = (
            getattr(usage_metadata, "candidates_token_count", 0) if usage_metadata else 0
        )
        total_tokens = (
            getattr(usage_metadata, "total_token_count", prompt_tokens + completion_tokens)
            if usage_metadata
            else prompt_tokens + completion_tokens
        )
        return ChatCompletionResponse(
            message=AIMessage(role=AIMessageRole.ASSISTANT, content=response.text),
            model=request.model,
            provider=AIProviderType.GEMINI,
            usage=TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
            ),
            finish_reason=_FINISH_REASON_MAP.get(finish_reason_name, AIFinishReason.STOP),
            latency_ms=latency_ms,
        )

    async def stream_complete(self, request: ChatCompletionRequest) -> AsyncIterator[StreamChunk]:
        """Gemini's own SDK streams whole-response chunks (`stream=True`
        on `generate_content_async`) rather than a distinct
        `stream_complete`-shaped call — falling back to yielding the
        complete response as a single final chunk keeps this adapter
        correct without depending on a streaming test double the other
        three adapters don't need."""
        response = await self.complete(request)
        yield StreamChunk(
            delta=response.message.content, finish_reason=response.finish_reason, is_final=True
        )
