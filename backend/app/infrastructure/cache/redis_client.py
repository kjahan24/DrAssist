"""Shared async Redis client factory.

A single connection pool is created lazily and reused process-wide;
import `get_redis_client()` rather than instantiating `redis.Redis`
elsewhere.
"""

from functools import lru_cache

from redis.asyncio import Redis

from app.core.config import get_settings


@lru_cache
def get_redis_client() -> Redis:
    settings = get_settings()
    return Redis.from_url(str(settings.redis.url), decode_responses=True)
