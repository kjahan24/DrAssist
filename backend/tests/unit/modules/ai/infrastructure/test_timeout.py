"""Unit tests for `call_with_timeout`."""

import asyncio

import pytest

from app.modules.ai.domain.enums import AIProviderType
from app.modules.ai.domain.exceptions import AIProviderTimeoutError
from app.modules.ai.infrastructure.providers.timeout import call_with_timeout


class TestCallWithTimeout:
    async def test_returns_the_result_when_within_budget(self) -> None:
        async def func() -> str:
            return "done"

        result = await call_with_timeout(func, seconds=1.0, provider=AIProviderType.MOCK)

        assert result == "done"

    async def test_raises_normalized_timeout_error_when_exceeded(self) -> None:
        async def func() -> str:
            await asyncio.sleep(10)
            return "too slow"

        with pytest.raises(AIProviderTimeoutError):
            await call_with_timeout(func, seconds=0.01, provider=AIProviderType.MOCK)

    async def test_error_carries_the_provider(self) -> None:
        async def func() -> str:
            await asyncio.sleep(10)
            return "too slow"

        with pytest.raises(AIProviderTimeoutError) as exc_info:
            await call_with_timeout(func, seconds=0.01, provider=AIProviderType.CLAUDE)

        assert exc_info.value.provider == "claude"
