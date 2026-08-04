"""OpenAI embedding adapter (`EmbeddingProviderPort`).

`client` is duck-typed to `openai.AsyncOpenAI`'s `.embeddings.create(...)`
surface — see `infrastructure/llm/openai_provider.py`'s module docstring
for why this stays `Any`-typed with a lazy default-client import.
"""

from typing import Any

from app.modules.ai.application.dto import EmbeddingRequest, EmbeddingResponse
from app.modules.ai.application.ports import EmbeddingProviderPort
from app.modules.ai.domain.enums import AIProviderType
from app.modules.ai.domain.exceptions import AIProviderAuthenticationError
from app.modules.ai.domain.value_objects import TokenUsage
from app.modules.ai.infrastructure.providers.exception_mapping import classify_provider_exception


class OpenAIEmbeddingProvider(EmbeddingProviderPort):
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

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        client = self._get_client()
        try:
            response = await client.embeddings.create(
                model=request.model.name, input=list(request.input_texts)
            )
        except Exception as exc:
            raise classify_provider_exception(exc, provider=AIProviderType.OPENAI) from exc

        embeddings = tuple(tuple(item.embedding) for item in response.data)
        usage = response.usage
        prompt_tokens = usage.prompt_tokens if usage else 0
        total_tokens = usage.total_tokens if usage else prompt_tokens
        return EmbeddingResponse(
            embeddings=embeddings,
            model=request.model,
            provider=AIProviderType.OPENAI,
            usage=TokenUsage(
                prompt_tokens=prompt_tokens, completion_tokens=0, total_tokens=total_tokens
            ),
        )
