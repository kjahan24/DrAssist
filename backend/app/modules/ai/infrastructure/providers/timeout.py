"""Timeout handling — bounds how long a single provider call may run, so a
hung request can't hold a worker/request slot indefinitely
(`09_ai_gateway_and_storage.md`)."""

import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

from app.modules.ai.domain.enums import AIProviderType
from app.modules.ai.domain.exceptions import AIProviderTimeoutError

T = TypeVar("T")


async def call_with_timeout(
    func: Callable[[], Awaitable[T]], *, seconds: float, provider: AIProviderType
) -> T:
    try:
        return await asyncio.wait_for(func(), timeout=seconds)
    except TimeoutError as exc:
        raise AIProviderTimeoutError(
            provider=provider.value, message=f"call exceeded {seconds}s timeout"
        ) from exc
