import json
import logging

import redis

from app.config import settings

logger = logging.getLogger(__name__)

_redis_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    return _redis_client


def cache_get(key: str) -> dict | list | None:
    try:
        data = get_redis().get(key)
        return json.loads(data) if data else None
    except Exception as e:
        logger.warning("Redis cache get failed: %s", e)
        return None


def cache_set(key: str, value: dict | list, ttl: int = 300) -> None:
    try:
        get_redis().setex(key, ttl, json.dumps(value, default=str))
    except Exception as e:
        logger.warning("Redis cache set failed: %s", e)


def check_redis_health() -> str:
    try:
        get_redis().ping()
        return "connected"
    except Exception:
        return "disconnected"
