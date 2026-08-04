"""In-memory test doubles for the AI module's application-layer ports —
per `docs/backend-architecture/12_testing_architecture.md` ("fakes over
mocks as the default"), each implements the exact same interface its real
adapter does.
"""

from collections.abc import AsyncIterator

from app.modules.ai.application.dto import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    EmbeddingRequest,
    EmbeddingResponse,
    StreamChunk,
)
from app.modules.ai.application.ports import AIProviderPort, EmbeddingProviderPort
from app.modules.ai.domain.enums import AIFinishReason, AIMessageRole, AIProviderType
from app.modules.ai.domain.value_objects import AIMessage, TokenUsage


class FakeAIProviderPort(AIProviderPort):
    def __init__(
        self,
        *,
        provider_type: AIProviderType = AIProviderType.MOCK,
        response: ChatCompletionResponse | None = None,
        error: Exception | None = None,
    ) -> None:
        self._provider_type = provider_type
        self._response = response
        self._error = error
        self.received_requests: list[ChatCompletionRequest] = []

    @property
    def provider_type(self) -> AIProviderType:
        return self._provider_type

    async def complete(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        self.received_requests.append(request)
        if self._error is not None:
            raise self._error
        if self._response is not None:
            return self._response
        return ChatCompletionResponse(
            message=AIMessage(role=AIMessageRole.ASSISTANT, content="fake reply"),
            model=request.model,
            provider=self._provider_type,
            usage=TokenUsage(prompt_tokens=1, completion_tokens=1, total_tokens=2),
            finish_reason=AIFinishReason.STOP,
            latency_ms=1.0,
        )

    async def stream_complete(self, request: ChatCompletionRequest) -> AsyncIterator[StreamChunk]:
        self.received_requests.append(request)
        yield StreamChunk(delta="fake", finish_reason=AIFinishReason.STOP, is_final=True)


class FakeEmbeddingProviderPort(EmbeddingProviderPort):
    def __init__(
        self,
        *,
        provider_type: AIProviderType = AIProviderType.MOCK,
        response: EmbeddingResponse | None = None,
        error: Exception | None = None,
    ) -> None:
        self._provider_type = provider_type
        self._response = response
        self._error = error
        self.received_requests: list[EmbeddingRequest] = []

    @property
    def provider_type(self) -> AIProviderType:
        return self._provider_type

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        self.received_requests.append(request)
        if self._error is not None:
            raise self._error
        if self._response is not None:
            return self._response
        return EmbeddingResponse(
            embeddings=tuple((0.0, 0.0) for _ in request.input_texts),
            model=request.model,
            provider=self._provider_type,
            usage=TokenUsage(prompt_tokens=1, completion_tokens=0, total_tokens=1),
        )
