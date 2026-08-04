"""`ResilientAIProvider` / `ResilientEmbeddingProvider` — the resilience
decorator every concrete provider adapter is wrapped in before
`AIProviderFactory`/`EmbeddingProviderFactory` hands it out
(`infrastructure/providers/factory.py`).

Composes retry (`retry.py`), timeout (`timeout.py`), audit logging
(`AIAuditLoggerPort`), cost estimation (`CostCalculatorPort`), and running
usage totals (`TokenUsageCollector`) around an inner
`AIProviderPort`/`EmbeddingProviderPort` — exactly the "this wrapping
lives entirely in `modules/ai/infrastructure/`" design
`09_ai_gateway_and_storage.md` calls for, so a use case (or a future
clinical module calling through `public/facade.py`) only ever sees
"succeeded" or "raised `AIProviderError`", never retry/timeout mechanics.

`stream_complete` is deliberately **not** retried — a partially-streamed
response has already been handed to the caller chunk by chunk; retrying
after a mid-stream failure would silently duplicate output rather than
cleanly restart, so a streaming failure is reported once (audit-logged,
then re-raised) and retrying is left to the caller, who can decide whether
"start a fresh completion" is safe for their use.
"""

from collections.abc import AsyncIterator
from time import perf_counter

from app.modules.ai.application.dto import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    EmbeddingRequest,
    EmbeddingResponse,
    StreamChunk,
)
from app.modules.ai.application.ports import (
    AIAuditLoggerPort,
    AIProviderPort,
    CostCalculatorPort,
    EmbeddingProviderPort,
)
from app.modules.ai.application.services.token_usage_collector import TokenUsageCollector
from app.modules.ai.domain.enums import AIProviderType
from app.modules.ai.domain.exceptions import AIProviderError
from app.modules.ai.domain.value_objects import TokenUsage
from app.modules.ai.infrastructure.providers.retry import RetryPolicy, call_with_retry
from app.modules.ai.infrastructure.providers.timeout import call_with_timeout


class ResilientAIProvider(AIProviderPort):
    def __init__(
        self,
        *,
        inner: AIProviderPort,
        retry_policy: RetryPolicy,
        timeout_seconds: float,
        audit_logger: AIAuditLoggerPort | None = None,
        cost_calculator: CostCalculatorPort | None = None,
        usage_collector: TokenUsageCollector | None = None,
    ) -> None:
        self._inner = inner
        self._retry_policy = retry_policy
        self._timeout_seconds = timeout_seconds
        self._audit_logger = audit_logger
        self._cost_calculator = cost_calculator
        self._usage_collector = usage_collector

    @property
    def provider_type(self) -> AIProviderType:
        return self._inner.provider_type

    async def complete(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        start = perf_counter()
        try:
            response = await call_with_retry(
                lambda: call_with_timeout(
                    lambda: self._inner.complete(request),
                    seconds=self._timeout_seconds,
                    provider=self._inner.provider_type,
                ),
                policy=self._retry_policy,
            )
        except AIProviderError as exc:
            await self._audit_failure(
                operation="complete",
                model=request.model.name,
                duration_ms=(perf_counter() - start) * 1000,
                exc=exc,
            )
            raise

        duration_ms = (perf_counter() - start) * 1000
        if self._usage_collector is not None:
            self._usage_collector.record(response.usage, model=request.model.name)
        cost = (
            self._cost_calculator.estimate_cost(usage=response.usage, model=response.model)
            if self._cost_calculator is not None
            else None
        )
        if self._audit_logger is not None:
            await self._audit_logger.log_call(
                provider=self._inner.provider_type,
                model=request.model.name,
                operation="complete",
                usage=response.usage,
                cost=cost,
                duration_ms=duration_ms,
                success=True,
            )
        return response

    async def stream_complete(self, request: ChatCompletionRequest) -> AsyncIterator[StreamChunk]:
        start = perf_counter()
        try:
            async for chunk in self._inner.stream_complete(request):
                yield chunk
        except AIProviderError as exc:
            await self._audit_failure(
                operation="stream_complete",
                model=request.model.name,
                duration_ms=(perf_counter() - start) * 1000,
                exc=exc,
            )
            raise
        else:
            if self._audit_logger is not None:
                await self._audit_logger.log_call(
                    provider=self._inner.provider_type,
                    model=request.model.name,
                    operation="stream_complete",
                    usage=TokenUsage.zero(),
                    cost=None,
                    duration_ms=(perf_counter() - start) * 1000,
                    success=True,
                )

    async def _audit_failure(
        self, *, operation: str, model: str, duration_ms: float, exc: AIProviderError
    ) -> None:
        if self._audit_logger is not None:
            await self._audit_logger.log_call(
                provider=self._inner.provider_type,
                model=model,
                operation=operation,
                usage=TokenUsage.zero(),
                cost=None,
                duration_ms=duration_ms,
                success=False,
                error_code=type(exc).__name__,
            )


class ResilientEmbeddingProvider(EmbeddingProviderPort):
    def __init__(
        self,
        *,
        inner: EmbeddingProviderPort,
        retry_policy: RetryPolicy,
        timeout_seconds: float,
        audit_logger: AIAuditLoggerPort | None = None,
        cost_calculator: CostCalculatorPort | None = None,
        usage_collector: TokenUsageCollector | None = None,
    ) -> None:
        self._inner = inner
        self._retry_policy = retry_policy
        self._timeout_seconds = timeout_seconds
        self._audit_logger = audit_logger
        self._cost_calculator = cost_calculator
        self._usage_collector = usage_collector

    @property
    def provider_type(self) -> AIProviderType:
        return self._inner.provider_type

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        start = perf_counter()
        try:
            response = await call_with_retry(
                lambda: call_with_timeout(
                    lambda: self._inner.embed(request),
                    seconds=self._timeout_seconds,
                    provider=self._inner.provider_type,
                ),
                policy=self._retry_policy,
            )
        except AIProviderError as exc:
            if self._audit_logger is not None:
                await self._audit_logger.log_call(
                    provider=self._inner.provider_type,
                    model=request.model.name,
                    operation="embed",
                    usage=TokenUsage.zero(),
                    cost=None,
                    duration_ms=(perf_counter() - start) * 1000,
                    success=False,
                    error_code=type(exc).__name__,
                )
            raise

        duration_ms = (perf_counter() - start) * 1000
        if self._usage_collector is not None:
            self._usage_collector.record(response.usage, model=request.model.name)
        cost = (
            self._cost_calculator.estimate_cost(usage=response.usage, model=response.model)
            if self._cost_calculator is not None
            else None
        )
        if self._audit_logger is not None:
            await self._audit_logger.log_call(
                provider=self._inner.provider_type,
                model=request.model.name,
                operation="embed",
                usage=response.usage,
                cost=cost,
                duration_ms=duration_ms,
                success=True,
            )
        return response
