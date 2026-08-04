"""Retry-with-backoff, built on `tenacity` (already a base dependency —
`requirements/base.txt`, and the library `09_ai_gateway_and_storage.md`
names explicitly for this purpose).

Only `AIProviderError` subclasses whose `retryable` class attribute is
`True` are retried (`AIProviderRateLimitError`, `AIProviderTimeoutError`,
`AIProviderUnavailableError`) — a 4xx-shaped
`AIProviderInvalidRequestError`/`AIProviderAuthenticationError` fails
fast, per this codebase's own "retry transient errors only" rule.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TypeVar

from tenacity import AsyncRetrying, retry_if_exception, stop_after_attempt, wait_exponential

from app.modules.ai.domain.exceptions import AIProviderError

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    max_attempts: int = 3
    initial_backoff_seconds: float = 0.5
    max_backoff_seconds: float = 8.0

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if self.initial_backoff_seconds < 0 or self.max_backoff_seconds < 0:
            raise ValueError("backoff seconds cannot be negative")


def _is_retryable(exc: BaseException) -> bool:
    return isinstance(exc, AIProviderError) and exc.retryable


async def call_with_retry(func: Callable[[], Awaitable[T]], *, policy: RetryPolicy) -> T:
    async for attempt in AsyncRetrying(
        stop=stop_after_attempt(policy.max_attempts),
        wait=wait_exponential(
            multiplier=policy.initial_backoff_seconds, max=policy.max_backoff_seconds
        ),
        retry=retry_if_exception(_is_retryable),
        reraise=True,
    ):
        with attempt:
            return await func()
    # AsyncRetrying either returns from inside the `with attempt:` block
    # above or re-raises (`reraise=True`) once attempts are exhausted —
    # this line exists only to satisfy the type checker that the function
    # always returns or raises.
    raise AssertionError("unreachable")  # pragma: no cover
