from __future__ import annotations
from typing import Optional
from redis.asyncio import Redis as AsyncRedis

client: Optional[AsyncRedis] = None


async def initialize(redis_url: str | None = None) -> AsyncRedis:
    global client
    if client is None:
        if redis_url is None:
            from src.core.config import get_redis_settings

            redis_url = str(get_redis_settings().redis_url)
        client = AsyncRedis.from_url(redis_url)
    return client


async def close() -> None:
    global client
    if client is not None:
        await client.aclose()
        client = None

