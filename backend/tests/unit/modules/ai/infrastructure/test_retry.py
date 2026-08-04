"""Unit tests for `call_with_retry`/`RetryPolicy`."""

import pytest

from app.modules.ai.domain.exceptions import (
    AIProviderInvalidRequestError,
    AIProviderUnavailableError,
)
from app.modules.ai.infrastructure.providers.retry import RetryPolicy, call_with_retry


class TestRetryPolicy:
    def test_rejects_zero_max_attempts(self) -> None:
        with pytest.raises(ValueError, match="max_attempts"):
            RetryPolicy(max_attempts=0)

    def test_rejects_negative_backoff(self) -> None:
        with pytest.raises(ValueError, match="backoff"):
            RetryPolicy(initial_backoff_seconds=-1)


class TestCallWithRetry:
    async def test_succeeds_without_retrying_on_first_success(self) -> None:
        calls = 0

        async def func() -> str:
            nonlocal calls
            calls += 1
            return "ok"

        result = await call_with_retry(
            func, policy=RetryPolicy(max_attempts=3, initial_backoff_seconds=0)
        )

        assert result == "ok"
        assert calls == 1

    async def test_retries_a_transient_error_until_it_succeeds(self) -> None:
        calls = 0

        async def func() -> str:
            nonlocal calls
            calls += 1
            if calls < 3:
                raise AIProviderUnavailableError(provider="mock", message="down")
            return "recovered"

        result = await call_with_retry(
            func, policy=RetryPolicy(max_attempts=5, initial_backoff_seconds=0)
        )

        assert result == "recovered"
        assert calls == 3

    async def test_gives_up_after_max_attempts(self) -> None:
        calls = 0

        async def func() -> str:
            nonlocal calls
            calls += 1
            raise AIProviderUnavailableError(provider="mock", message="down")

        with pytest.raises(AIProviderUnavailableError):
            await call_with_retry(
                func, policy=RetryPolicy(max_attempts=3, initial_backoff_seconds=0)
            )

        assert calls == 3

    async def test_does_not_retry_a_non_retryable_error(self) -> None:
        calls = 0

        async def func() -> str:
            nonlocal calls
            calls += 1
            raise AIProviderInvalidRequestError(provider="mock", message="bad input")

        with pytest.raises(AIProviderInvalidRequestError):
            await call_with_retry(
                func, policy=RetryPolicy(max_attempts=5, initial_backoff_seconds=0)
            )

        assert calls == 1
