import os
import json
from typing import Any, Optional

from dotenv import load_dotenv
from redis.asyncio import Redis

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "60"))

redis: Optional[Redis] = None


async def init_redis() -> None:
    global redis
    if redis is None:
        redis = Redis.from_url(REDIS_URL, decode_responses=True)
        await redis.ping()
        print("✅ Redis connected:", REDIS_URL)


async def close_redis() -> None:
    global redis
    if redis is not None:
        await redis.close()
        redis = None
        print("❌ Redis disconnected")


def _dumps(value: Any) -> str:
    return json.dumps(value, default=str)


def _loads(value: str) -> Any:
    return json.loads(value)


async def cache_get(key: str):
    if redis is None:
        return None
    val = await redis.get(key)
    return None if val is None else _loads(val)


async def cache_set(key: str, value: Any, ttl: int = CACHE_TTL_SECONDS):
    if redis is None:
        return
    await redis.set(key, _dumps(value), ex=ttl)


async def cache_del(*keys: str):
    if redis is None or not keys:
        return
    await redis.delete(*keys)

async def redis_get_str(key: str) -> str | None:
    if redis is None:
        return None
    return await redis.get(key)


async def redis_set_str(key: str, value: str, ttl: int = CACHE_TTL_SECONDS) -> None:
    if redis is None:
        return
    await redis.set(key, value, ex=ttl)


async def redis_incr(key: str, ttl: int = CACHE_TTL_SECONDS) -> int:
    """
    Increment integer key in Redis.
    If key is new, it will also get TTL so it auto-expires.
    """
    if redis is None:
        return 0

    val = await redis.incr(key)
    # Ensure expiry exists
    if await redis.ttl(key) == -1:
        await redis.expire(key, ttl)
    return int(val)


async def redis_del(*keys: str) -> None:
    if redis is None or not keys:
        return
    await redis.delete(*keys)
