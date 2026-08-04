"""Unit tests for `ResilientAIProvider`/`ResilientEmbeddingProvider` — the
retry/timeout/audit/cost/usage-collection decorator every real provider
adapter is wrapped in by `container.py`."""

from collections.abc import AsyncIterator
from typing import Any

import pytest

from app.modules.ai.application.dto import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    EmbeddingRequest,
    StreamChunk,
)
from app.modules.ai.application.ports import AIAuditLoggerPort, CostCalculatorPort
from app.modules.ai.application.services.token_usage_collector import TokenUsageCollector
from app.modules.ai.domain.enums import AIMessageRole, AIProviderType
from app.modules.ai.domain.exceptions import (
    AIProviderInvalidRequestError,
    AIProviderUnavailableError,
)
from app.modules.ai.domain.value_objects import AIMessage, AIModel, CostEstimate, TokenUsage
from app.modules.ai.infrastructure.providers.resilient_provider import (
    ResilientAIProvider,
    ResilientEmbeddingProvider,
)
from app.modules.ai.infrastructure.providers.retry import RetryPolicy
from tests.unit.modules.ai.application.fakes import FakeAIProviderPort, FakeEmbeddingProviderPort


class _RecordingAuditLogger(AIAuditLoggerPort):
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def log_call(
        self,
        *,
        provider: AIProviderType,
        model: str,
        operation: str,
        usage: TokenUsage,
        cost: CostEstimate | None,
        duration_ms: float,
        success: bool,
        error_code: str | None = None,
    ) -> None:
        self.calls.append(
            {
                "provider": provider,
                "model": model,
                "operation": operation,
                "usage": usage,
                "cost": cost,
                "duration_ms": duration_ms,
                "success": success,
                "error_code": error_code,
            }
        )


class _FixedCostCalculator(CostCalculatorPort):
    def estimate_cost(self, *, usage: TokenUsage, model: AIModel) -> CostEstimate:
        return CostEstimate(input_cost_usd=0.01, output_cost_usd=0.02)


class _FlakyAIProvider(FakeAIProviderPort):
    """Fails `fail_times` times with a retryable error, then succeeds."""

    def __init__(self, *, fail_times: int) -> None:
        super().__init__()
        self._fail_times = fail_times
        self.attempts = 0

    async def complete(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        self.attempts += 1
        if self.attempts <= self._fail_times:
            raise AIProviderUnavailableError(provider="mock", message="temporarily down")
        return await super().complete(request)


def _request() -> ChatCompletionRequest:
    return ChatCompletionRequest(
        messages=(AIMessage(role=AIMessageRole.USER, content="hi"),),
        model=AIModel(provider=AIProviderType.MOCK, name="mock-model"),
    )


def _embedding_request() -> EmbeddingRequest:
    return EmbeddingRequest(
        input_texts=("hi",), model=AIModel(provider=AIProviderType.MOCK, name="mock-embedding")
    )


class TestResilientAIProviderComplete:
    async def test_success_records_usage_audit_and_cost(self) -> None:
        inner = FakeAIProviderPort()
        audit_logger = _RecordingAuditLogger()
        usage_collector = TokenUsageCollector()
        provider = ResilientAIProvider(
            inner=inner,
            retry_policy=RetryPolicy(max_attempts=3, initial_backoff_seconds=0),
            timeout_seconds=5.0,
            audit_logger=audit_logger,
            cost_calculator=_FixedCostCalculator(),
            usage_collector=usage_collector,
        )

        response = await provider.complete(_request())

        assert response.message.content == "fake reply"
        assert usage_collector.total_usage().total_tokens > 0
        assert len(audit_logger.calls) == 1
        assert audit_logger.calls[0]["success"] is True
        assert audit_logger.calls[0]["cost"].total_cost_usd == pytest.approx(0.03)

    async def test_provider_type_delegates_to_inner(self) -> None:
        inner = FakeAIProviderPort(provider_type=AIProviderType.OPENAI)
        provider = ResilientAIProvider(
            inner=inner, retry_policy=RetryPolicy(max_attempts=1), timeout_seconds=5.0
        )
        assert provider.provider_type is AIProviderType.OPENAI

    async def test_retries_a_transient_failure_then_succeeds(self) -> None:
        inner = _FlakyAIProvider(fail_times=2)
        provider = ResilientAIProvider(
            inner=inner,
            retry_policy=RetryPolicy(max_attempts=5, initial_backoff_seconds=0),
            timeout_seconds=5.0,
        )

        response = await provider.complete(_request())

        assert response.message.content == "fake reply"
        assert inner.attempts == 3

    async def test_non_retryable_failure_is_recorded_and_reraised_without_retry(self) -> None:
        inner = FakeAIProviderPort(
            error=AIProviderInvalidRequestError(provider="mock", message="bad input")
        )
        audit_logger = _RecordingAuditLogger()
        provider = ResilientAIProvider(
            inner=inner,
            retry_policy=RetryPolicy(max_attempts=5, initial_backoff_seconds=0),
            timeout_seconds=5.0,
            audit_logger=audit_logger,
        )

        with pytest.raises(AIProviderInvalidRequestError):
            await provider.complete(_request())

        assert len(inner.received_requests) == 1
        assert audit_logger.calls[0]["success"] is False
        assert audit_logger.calls[0]["error_code"] == "AIProviderInvalidRequestError"

    async def test_works_with_no_audit_logger_cost_calculator_or_collector(self) -> None:
        provider = ResilientAIProvider(
            inner=FakeAIProviderPort(),
            retry_policy=RetryPolicy(max_attempts=1),
            timeout_seconds=5.0,
        )
        response = await provider.complete(_request())
        assert response.message.content == "fake reply"


class TestResilientAIProviderStream:
    async def test_success_yields_every_chunk_and_audits_once(self) -> None:
        inner = FakeAIProviderPort()
        audit_logger = _RecordingAuditLogger()
        provider = ResilientAIProvider(
            inner=inner,
            retry_policy=RetryPolicy(max_attempts=3, initial_backoff_seconds=0),
            timeout_seconds=5.0,
            audit_logger=audit_logger,
        )

        chunks = [chunk async for chunk in provider.stream_complete(_request())]

        assert len(chunks) == 1
        assert len(audit_logger.calls) == 1
        assert audit_logger.calls[0]["success"] is True

    async def test_failure_partway_through_is_audited_and_reraised(self) -> None:
        class _FailingStreamProvider(FakeAIProviderPort):
            async def stream_complete(
                self, request: ChatCompletionRequest
            ) -> AsyncIterator[StreamChunk]:
                yield StreamChunk(delta="partial", is_final=False)
                raise AIProviderUnavailableError(provider="mock", message="dropped connection")

        audit_logger = _RecordingAuditLogger()
        provider = ResilientAIProvider(
            inner=_FailingStreamProvider(),
            retry_policy=RetryPolicy(max_attempts=5, initial_backoff_seconds=0),
            timeout_seconds=5.0,
            audit_logger=audit_logger,
        )

        received = []
        with pytest.raises(AIProviderUnavailableError):
            async for chunk in provider.stream_complete(_request()):
                received.append(chunk)

        assert len(received) == 1
        assert audit_logger.calls[0]["success"] is False


class TestResilientEmbeddingProvider:
    async def test_success_records_usage_and_cost(self) -> None:
        inner = FakeEmbeddingProviderPort()
        usage_collector = TokenUsageCollector()
        audit_logger = _RecordingAuditLogger()
        provider = ResilientEmbeddingProvider(
            inner=inner,
            retry_policy=RetryPolicy(max_attempts=3, initial_backoff_seconds=0),
            timeout_seconds=5.0,
            audit_logger=audit_logger,
            cost_calculator=_FixedCostCalculator(),
            usage_collector=usage_collector,
        )

        response = await provider.embed(_embedding_request())

        assert len(response.embeddings) == 1
        assert usage_collector.total_usage().total_tokens > 0
        assert audit_logger.calls[0]["success"] is True

    async def test_failure_is_audited_and_reraised(self) -> None:
        inner = FakeEmbeddingProviderPort(
            error=AIProviderInvalidRequestError(provider="mock", message="bad input")
        )
        audit_logger = _RecordingAuditLogger()
        provider = ResilientEmbeddingProvider(
            inner=inner,
            retry_policy=RetryPolicy(max_attempts=3, initial_backoff_seconds=0),
            timeout_seconds=5.0,
            audit_logger=audit_logger,
        )

        with pytest.raises(AIProviderInvalidRequestError):
            await provider.embed(_embedding_request())

        assert audit_logger.calls[0]["success"] is False
