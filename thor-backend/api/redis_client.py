from __future__ import annotations

import redis
from django.conf import settings

_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _client


# Key conventions
def latest_key(symbol: str) -> str:
    return f"quotes:latest:{symbol}"


def unified_stream_key() -> str:
    return "quotes:stream:unified"
