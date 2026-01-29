"""
Redis connection management for caching.
"""

from typing import Optional, Any
import json
import redis.asyncio as redis

from core.config import settings
from core.logging import get_logger

logger = get_logger(__name__)

_redis_client: Optional[redis.Redis] = None


async def init_redis() -> bool:
    """Initialize Redis connection. Returns True if successful."""
    global _redis_client
    
    try:
        _redis_client = redis.from_url(
            settings.redis_url,
            password=settings.redis_password,
            encoding="utf-8",
            decode_responses=True
        )
        # Test connection
        await _redis_client.ping()
        logger.info("Redis connection initialized")
        return True
    except Exception as e:
        logger.warning(f"Could not connect to Redis: {e}")
        _redis_client = None
        return False


async def close_redis() -> None:
    """Close Redis connection."""
    global _redis_client
    
    if _redis_client:
        await _redis_client.close()
        logger.info("Redis connection closed")


def get_redis() -> Optional[redis.Redis]:
    """Get the Redis client instance."""
    return _redis_client


async def cache_get(key: str) -> Optional[Any]:
    """Get a value from cache."""
    if not _redis_client:
        return None
    
    try:
        value = await _redis_client.get(key)
        return json.loads(value) if value else None
    except Exception as e:
        logger.error(f"Cache get error: {e}")
        return None


async def cache_set(key: str, value: Any, ttl: int = 300) -> bool:
    """Set a value in cache with TTL (default 5 minutes)."""
    if not _redis_client:
        return False
    
    try:
        await _redis_client.setex(key, ttl, json.dumps(value))
        return True
    except Exception as e:
        logger.error(f"Cache set error: {e}")
        return False


async def cache_delete(key: str) -> bool:
    """Delete a key from cache."""
    if not _redis_client:
        return False
    
    try:
        await _redis_client.delete(key)
        return True
    except Exception as e:
        logger.error(f"Cache delete error: {e}")
        return False


async def cache_delete_pattern(pattern: str) -> int:
    """Delete all keys matching a pattern."""
    if not _redis_client:
        return 0
    
    try:
        keys = []
        async for key in _redis_client.scan_iter(match=pattern):
            keys.append(key)
        
        if keys:
            await _redis_client.delete(*keys)
        return len(keys)
    except Exception as e:
        logger.error(f"Cache delete pattern error: {e}")
        return 0


async def rate_limit_check(user_id: str, limit: int = None) -> tuple[bool, int]:
    """
    Check rate limit for a user.
    Returns (allowed, remaining_requests).
    """
    if not _redis_client:
        return True, limit or settings.rate_limit_per_minute
    
    limit = limit or settings.rate_limit_per_minute
    key = f"rate_limit:{user_id}"
    
    try:
        current = await _redis_client.get(key)
        if current is None:
            await _redis_client.setex(key, 60, 1)
            return True, limit - 1
        
        count = int(current)
        if count >= limit:
            return False, 0
        
        await _redis_client.incr(key)
        return True, limit - count - 1
    except Exception as e:
        logger.error(f"Rate limit check error: {e}")
        return True, limit
