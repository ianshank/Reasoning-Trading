"""
Cache service for Redis-based caching with TTL management.

Provides a high-level abstraction over Redis for caching trading data,
MCTS results, and other expensive computations.
"""

import json
import pickle
from datetime import timedelta
from typing import Any, Optional

import structlog
from redis.asyncio import Redis

from .exceptions import CacheServiceException

logger = structlog.get_logger(__name__)


class CacheService:
    """
    Redis-based caching service with TTL management.

    Provides methods for:
    - Key-value storage with automatic expiration
    - JSON and pickle serialization
    - Cache invalidation patterns
    - Statistics tracking
    """

    def __init__(
        self,
        redis_client: Redis,
        default_ttl: int = 3600,
        key_prefix: str = "reasoning_trading",
    ):
        """
        Initialize cache service.

        Args:
            redis_client: Async Redis client
            default_ttl: Default TTL in seconds
            key_prefix: Prefix for all cache keys
        """
        self.redis = redis_client
        self.default_ttl = default_ttl
        self.key_prefix = key_prefix

        # Statistics
        self._hits = 0
        self._misses = 0
        self._errors = 0

    def _make_key(self, key: str) -> str:
        """Create prefixed cache key."""
        return f"{self.key_prefix}:{key}"

    async def get(self, key: str, use_pickle: bool = False) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key
            use_pickle: Use pickle instead of JSON for deserialization

        Returns:
            Cached value or None if not found

        Raises:
            CacheServiceException: On cache errors
        """
        try:
            full_key = self._make_key(key)
            value = await self.redis.get(full_key)

            if value is None:
                self._misses += 1
                logger.debug("cache_miss", key=key)
                return None

            self._hits += 1
            logger.debug("cache_hit", key=key)

            # Deserialize
            if use_pickle:
                return pickle.loads(value)
            else:
                return json.loads(value)

        except (json.JSONDecodeError, pickle.PickleError) as e:
            self._errors += 1
            logger.error("cache_deserialization_error", key=key, error=str(e))
            # Return None for deserialization errors, don't raise
            return None
        except Exception as e:
            self._errors += 1
            logger.error("cache_get_error", key=key, error=str(e))
            raise CacheServiceException(f"Failed to get cache key '{key}'", {"error": str(e)})

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        use_pickle: bool = False,
    ) -> bool:
        """
        Set value in cache with TTL.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (uses default if None)
            use_pickle: Use pickle instead of JSON for serialization

        Returns:
            True if successful

        Raises:
            CacheServiceException: On cache errors
        """
        try:
            full_key = self._make_key(key)
            ttl = ttl or self.default_ttl

            # Serialize
            if use_pickle:
                serialized = pickle.dumps(value)
            else:
                serialized = json.dumps(value)

            # Set with expiration
            await self.redis.setex(full_key, ttl, serialized)

            logger.debug("cache_set", key=key, ttl=ttl)
            return True

        except (json.JSONDecodeError, pickle.PickleError) as e:
            self._errors += 1
            logger.error("cache_serialization_error", key=key, error=str(e))
            raise CacheServiceException(
                f"Failed to serialize value for key '{key}'",
                {"error": str(e)},
            )
        except Exception as e:
            self._errors += 1
            logger.error("cache_set_error", key=key, error=str(e))
            raise CacheServiceException(f"Failed to set cache key '{key}'", {"error": str(e)})

    async def delete(self, key: str) -> bool:
        """
        Delete key from cache.

        Args:
            key: Cache key

        Returns:
            True if key was deleted, False if key didn't exist

        Raises:
            CacheServiceException: On cache errors
        """
        try:
            full_key = self._make_key(key)
            result = await self.redis.delete(full_key)
            logger.debug("cache_delete", key=key, existed=bool(result))
            return bool(result)
        except Exception as e:
            self._errors += 1
            logger.error("cache_delete_error", key=key, error=str(e))
            raise CacheServiceException(f"Failed to delete cache key '{key}'", {"error": str(e)})

    async def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.

        Args:
            key: Cache key

        Returns:
            True if key exists

        Raises:
            CacheServiceException: On cache errors
        """
        try:
            full_key = self._make_key(key)
            result = await self.redis.exists(full_key)
            return bool(result)
        except Exception as e:
            self._errors += 1
            logger.error("cache_exists_error", key=key, error=str(e))
            raise CacheServiceException(f"Failed to check cache key '{key}'", {"error": str(e)})

    async def clear_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching pattern.

        Args:
            pattern: Redis pattern (e.g., "mcts:*")

        Returns:
            Number of keys deleted

        Raises:
            CacheServiceException: On cache errors
        """
        try:
            full_pattern = self._make_key(pattern)
            cursor = 0
            deleted = 0

            while True:
                cursor, keys = await self.redis.scan(cursor, match=full_pattern, count=100)
                if keys:
                    deleted += await self.redis.delete(*keys)
                if cursor == 0:
                    break

            logger.info("cache_pattern_cleared", pattern=pattern, deleted=deleted)
            return deleted

        except Exception as e:
            self._errors += 1
            logger.error("cache_clear_pattern_error", pattern=pattern, error=str(e))
            raise CacheServiceException(
                f"Failed to clear cache pattern '{pattern}'",
                {"error": str(e)},
            )

    async def clear(self) -> bool:
        """
        Clear all cache entries with this service's prefix.

        Returns:
            True if successful

        Raises:
            CacheServiceException: On cache errors
        """
        try:
            deleted = await self.clear_pattern("*")
            logger.info("cache_cleared", deleted=deleted)
            return True
        except Exception as e:
            self._errors += 1
            logger.error("cache_clear_error", error=str(e))
            raise CacheServiceException("Failed to clear cache", {"error": str(e)})

    async def get_ttl(self, key: str) -> Optional[int]:
        """
        Get remaining TTL for a key.

        Args:
            key: Cache key

        Returns:
            TTL in seconds, or None if key doesn't exist

        Raises:
            CacheServiceException: On cache errors
        """
        try:
            full_key = self._make_key(key)
            ttl = await self.redis.ttl(full_key)
            return ttl if ttl > 0 else None
        except Exception as e:
            self._errors += 1
            logger.error("cache_ttl_error", key=key, error=str(e))
            raise CacheServiceException(f"Failed to get TTL for key '{key}'", {"error": str(e)})

    async def extend_ttl(self, key: str, additional_seconds: int) -> bool:
        """
        Extend TTL for an existing key.

        Args:
            key: Cache key
            additional_seconds: Seconds to add to current TTL

        Returns:
            True if successful

        Raises:
            CacheServiceException: On cache errors
        """
        try:
            full_key = self._make_key(key)
            current_ttl = await self.redis.ttl(full_key)

            if current_ttl > 0:
                new_ttl = current_ttl + additional_seconds
                await self.redis.expire(full_key, new_ttl)
                logger.debug("cache_ttl_extended", key=key, new_ttl=new_ttl)
                return True

            return False

        except Exception as e:
            self._errors += 1
            logger.error("cache_extend_ttl_error", key=key, error=str(e))
            raise CacheServiceException(f"Failed to extend TTL for key '{key}'", {"error": str(e)})

    async def get_or_compute(
        self,
        key: str,
        compute_fn: Any,
        ttl: Optional[int] = None,
        use_pickle: bool = False,
    ) -> Any:
        """
        Get value from cache or compute and store it.

        Args:
            key: Cache key
            compute_fn: Async function to compute value if not cached
            ttl: TTL in seconds
            use_pickle: Use pickle serialization

        Returns:
            Cached or computed value

        Raises:
            CacheServiceException: On cache errors
        """
        # Try to get from cache
        value = await self.get(key, use_pickle=use_pickle)
        if value is not None:
            return value

        # Compute value
        try:
            value = await compute_fn()
        except Exception as e:
            logger.error("cache_compute_error", key=key, error=str(e))
            raise CacheServiceException(
                f"Failed to compute value for key '{key}'",
                {"error": str(e)},
            )

        # Store in cache
        await self.set(key, value, ttl=ttl, use_pickle=use_pickle)

        return value

    def get_statistics(self) -> dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache metrics
        """
        total_requests = self._hits + self._misses
        hit_rate = self._hits / total_requests if total_requests > 0 else 0.0

        return {
            "hits": self._hits,
            "misses": self._misses,
            "errors": self._errors,
            "total_requests": total_requests,
            "hit_rate": hit_rate,
            "miss_rate": 1.0 - hit_rate,
        }

    def reset_statistics(self) -> None:
        """Reset cache statistics."""
        self._hits = 0
        self._misses = 0
        self._errors = 0
        logger.info("cache_statistics_reset")
