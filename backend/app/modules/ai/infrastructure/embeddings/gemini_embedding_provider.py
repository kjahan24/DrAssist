"""Google Gemini embedding adapter (`EmbeddingProviderPort`).

`client` is duck-typed to one async method, `embed_content_async(*, model,
contents) -> list[list[float]]` — `_DefaultGeminiEmbeddingClient` wraps
`google.generativeai`'s synchronous `genai.embed_content` (this SDK
version has no native async embedding call) via `asyncio.to_thread`, so a
real call never blocks the event loop; a test double only needs to
implement that one async method, matching the same shape
`infrastructure/llm/gemini_provider.py::_DefaultGeminiClient` establishes
for chat completions.
"""

import asyncio
from typing import Any

from app.modules.ai.application.dto import EmbeddingRequest, EmbeddingResponse
from app.modules.ai.application.ports import EmbeddingProviderPort
from app.modules.ai.domain.enums import AIProviderType
from app.modules.ai.domain.exceptions import AIProviderAuthenticationError
from app.modules.ai.domain.value_objects import TokenUsage
from app.modules.ai.infrastructure.providers.exception_mapping import classify_provider_exception


class _DefaultGeminiEmbeddingClient:
    def __init__(self, api_key: str) -> None:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        self._genai = genai

    async def embed_content_async(self, *, model: str, contents: list[str]) -> list[list[float]]:
        def _call() -> list[list[float]]:
            result = self._genai.embed_content(model=model, content=contents)
            return list(result["embedding"])

        return await asyncio.to_thread(_call)


class GeminiEmbeddingProvider(EmbeddingProviderPort):
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
        self._client = _DefaultGeminiEmbeddingClient(self._api_key)
        return self._client

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        client = self._get_client()
        try:
            raw_embeddings = await client.embed_content_async(
                model=request.model.name, contents=list(request.input_texts)
            )
        except Exception as exc:
            raise classify_provider_exception(exc, provider=AIProviderType.GEMINI) from exc

        embeddings = tuple(tuple(vector) for vector in raw_embeddings)
        token_estimate = sum(max(1, len(text) // 4) for text in request.input_texts)
        return EmbeddingResponse(
            embeddings=embeddings,
            model=request.model,
            provider=AIProviderType.GEMINI,
            usage=TokenUsage(
                prompt_tokens=token_estimate, completion_tokens=0, total_tokens=token_estimate
            ),
        )
