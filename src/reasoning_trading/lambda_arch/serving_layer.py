"""
Serving Layer for Lambda Architecture.

Provides policy caching and serving infrastructure:
- Redis-based distributed cache
- Semantic similarity for approximate cache hits
- TTL management based on regime
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

import numpy as np
from numpy.typing import NDArray
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class CacheBackend(str, Enum):
    """Cache backend types."""

    MEMORY = "memory"
    REDIS = "redis"


class ServingLayerConfig(BaseSettings):
    """Configuration for serving layer."""

    model_config = SettingsConfigDict(
        env_prefix="SERVING_",
        case_sensitive=False,
        extra="ignore",
    )

    # Cache backend
    backend: CacheBackend = Field(
        default=CacheBackend.MEMORY,
        description="Cache backend type",
    )
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL",
    )

    # TTL settings
    default_ttl_seconds: int = Field(
        default=3600,
        ge=60,
        le=86400,
        description="Default cache TTL",
    )
    volatile_regime_ttl_seconds: int = Field(
        default=600,
        ge=60,
        le=3600,
        description="TTL for volatile regime policies",
    )
    stable_regime_ttl_seconds: int = Field(
        default=7200,
        ge=600,
        le=86400,
        description="TTL for stable regime policies",
    )

    # Cache size limits
    max_entries: int = Field(
        default=100000,
        ge=1000,
        le=10000000,
        description="Maximum cache entries",
    )
    max_memory_mb: int = Field(
        default=500,
        ge=10,
        le=10000,
        description="Maximum memory usage in MB",
    )

    # Semantic similarity
    enable_semantic_lookup: bool = Field(
        default=True,
        description="Enable semantic similarity for cache lookup",
    )
    similarity_threshold: float = Field(
        default=0.95,
        ge=0.5,
        le=1.0,
        description="Cosine similarity threshold for cache hit",
    )
    semantic_index_size: int = Field(
        default=10000,
        ge=100,
        le=1000000,
        description="Size of semantic similarity index",
    )


@dataclass
class CacheEntry:
    """Entry in the policy cache."""

    key: str
    state_hash: str

    # Policy data
    action_type: str
    action_params: dict[str, Any] = field(default_factory=dict)
    action_probs: dict[str, float] = field(default_factory=dict)
    value: float = 0.0
    confidence: float = 0.0

    # Metadata
    regime: str | None = None
    level: str = "tactical"
    source: str = "batch"

    # State features for semantic similarity
    state_features: NDArray[np.float64] | None = None

    # Timing
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: datetime | None = None
    accessed_at: datetime = field(default_factory=datetime.now)
    access_count: int = 0

    @property
    def is_expired(self) -> bool:
        """Check if entry is expired."""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at

    @property
    def ttl_seconds(self) -> float:
        """Get remaining TTL in seconds."""
        if self.expires_at is None:
            return float("inf")
        remaining = (self.expires_at - datetime.now()).total_seconds()
        return max(0, remaining)

    def record_access(self) -> None:
        """Record an access to this entry."""
        self.accessed_at = datetime.now()
        self.access_count += 1

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "key": self.key,
            "state_hash": self.state_hash,
            "action_type": self.action_type,
            "action_params": self.action_params,
            "action_probs": self.action_probs,
            "value": self.value,
            "confidence": self.confidence,
            "regime": self.regime,
            "level": self.level,
            "source": self.source,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "access_count": self.access_count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CacheEntry:
        """Create from dictionary."""
        entry = cls(
            key=data["key"],
            state_hash=data["state_hash"],
            action_type=data["action_type"],
            action_params=data.get("action_params", {}),
            action_probs=data.get("action_probs", {}),
            value=data.get("value", 0.0),
            confidence=data.get("confidence", 0.0),
            regime=data.get("regime"),
            level=data.get("level", "tactical"),
            source=data.get("source", "batch"),
        )

        if "expires_at" in data and data["expires_at"]:
            entry.expires_at = datetime.fromisoformat(data["expires_at"])

        return entry


class PolicyCache:
    """
    Policy cache for fast lookup.

    Provides:
    - Exact hash-based lookup
    - Optional semantic similarity lookup
    - TTL management
    - LRU eviction
    """

    def __init__(self, config: ServingLayerConfig | None = None):
        """Initialize policy cache."""
        self.config = config or ServingLayerConfig()

        # In-memory cache
        self._cache: dict[str, CacheEntry] = {}

        # Semantic index (state_hash -> features)
        self._semantic_index: dict[str, NDArray[np.float64]] = {}
        self._index_keys: list[str] = []

        # Redis client (lazy initialized)
        self._redis: Any = None

    async def get(
        self,
        state_hash: str,
        state_features: NDArray[np.float64] | None = None,
    ) -> dict[str, Any] | None:
        """
        Get policy from cache.

        Args:
            state_hash: Hash of state features
            state_features: Optional features for semantic lookup

        Returns:
            Cached policy data or None
        """
        # Try exact match first
        key = f"policy:{state_hash}"

        if self.config.backend == CacheBackend.REDIS:
            entry = await self._redis_get(key)
        else:
            entry = self._memory_get(key)

        if entry is not None and not entry.is_expired:
            entry.record_access()
            return {
                "action_type": entry.action_type,
                "params": entry.action_params,
                "probs": entry.action_probs,
                "value": entry.value,
                "confidence": entry.confidence,
                "regime": entry.regime,
            }

        # Try semantic similarity if enabled
        if (
            self.config.enable_semantic_lookup
            and state_features is not None
            and self._semantic_index
        ):
            similar_entry = self._find_similar(state_features)
            if similar_entry is not None and not similar_entry.is_expired:
                similar_entry.record_access()
                return {
                    "action_type": similar_entry.action_type,
                    "params": similar_entry.action_params,
                    "probs": similar_entry.action_probs,
                    "value": similar_entry.value,
                    "confidence": similar_entry.confidence * 0.9,  # Discount for semantic match
                    "regime": similar_entry.regime,
                }

        return None

    async def set(
        self,
        state_hash: str,
        policy: dict[str, Any],
        state_features: NDArray[np.float64] | None = None,
        regime: str | None = None,
        level: str = "tactical",
        ttl_seconds: int | None = None,
    ) -> None:
        """
        Set policy in cache.

        Args:
            state_hash: Hash of state features
            policy: Policy data to cache
            state_features: Optional features for semantic index
            regime: Market regime for TTL selection
            level: Decision level
            ttl_seconds: Optional explicit TTL
        """
        # Determine TTL
        if ttl_seconds is None:
            if regime in ["volatile", "high_volatility"]:
                ttl_seconds = self.config.volatile_regime_ttl_seconds
            elif regime in ["trending_up", "trending_down", "mean_reverting"]:
                ttl_seconds = self.config.stable_regime_ttl_seconds
            else:
                ttl_seconds = self.config.default_ttl_seconds

        key = f"policy:{state_hash}"
        expires_at = datetime.now() + timedelta(seconds=ttl_seconds)

        entry = CacheEntry(
            key=key,
            state_hash=state_hash,
            action_type=policy.get("action_type", "hold"),
            action_params=policy.get("params", {}),
            action_probs=policy.get("probs", {}),
            value=policy.get("value", 0.0),
            confidence=policy.get("confidence", 0.5),
            regime=regime,
            level=level,
            state_features=state_features,
            expires_at=expires_at,
        )

        if self.config.backend == CacheBackend.REDIS:
            await self._redis_set(key, entry, ttl_seconds)
        else:
            self._memory_set(key, entry)

        # Add to semantic index
        if state_features is not None and self.config.enable_semantic_lookup:
            self._add_to_semantic_index(state_hash, state_features)

    async def delete(self, state_hash: str) -> bool:
        """Delete entry from cache."""
        key = f"policy:{state_hash}"

        if self.config.backend == CacheBackend.REDIS:
            return await self._redis_delete(key)
        else:
            return self._memory_delete(key)

    async def clear(self) -> None:
        """Clear entire cache."""
        self._cache.clear()
        self._semantic_index.clear()
        self._index_keys.clear()

        if self._redis is not None:
            await self._redis.flushdb()

    def _memory_get(self, key: str) -> CacheEntry | None:
        """Get from in-memory cache."""
        return self._cache.get(key)

    def _memory_set(self, key: str, entry: CacheEntry) -> None:
        """Set in in-memory cache."""
        # Evict if at capacity
        if len(self._cache) >= self.config.max_entries:
            self._evict_lru()

        self._cache[key] = entry

    def _memory_delete(self, key: str) -> bool:
        """Delete from in-memory cache."""
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def _evict_lru(self) -> None:
        """Evict least recently used entries."""
        if not self._cache:
            return

        # Sort by access time, evict oldest 10%
        sorted_entries = sorted(
            self._cache.items(),
            key=lambda x: x[1].accessed_at,
        )

        evict_count = max(1, len(self._cache) // 10)
        for key, _ in sorted_entries[:evict_count]:
            del self._cache[key]

    async def _redis_get(self, key: str) -> CacheEntry | None:
        """Get from Redis cache."""
        if self._redis is None:
            await self._init_redis()

        try:
            data = await self._redis.get(key)
            if data is None:
                return None
            return CacheEntry.from_dict(json.loads(data))
        except Exception:
            return None

    async def _redis_set(
        self,
        key: str,
        entry: CacheEntry,
        ttl_seconds: int,
    ) -> None:
        """Set in Redis cache."""
        if self._redis is None:
            await self._init_redis()

        try:
            data = json.dumps(entry.to_dict())
            await self._redis.setex(key, ttl_seconds, data)
        except Exception:
            pass

    async def _redis_delete(self, key: str) -> bool:
        """Delete from Redis cache."""
        if self._redis is None:
            await self._init_redis()

        try:
            result = await self._redis.delete(key)
            return result > 0
        except Exception:
            return False

    async def _init_redis(self) -> None:
        """Initialize Redis connection."""
        try:
            import aioredis

            self._redis = await aioredis.from_url(self.config.redis_url)
        except ImportError:
            # aioredis not available, use memory backend
            self.config.backend = CacheBackend.MEMORY

    def _add_to_semantic_index(
        self,
        state_hash: str,
        features: NDArray[np.float64],
    ) -> None:
        """Add features to semantic similarity index."""
        # Normalize features
        norm = np.linalg.norm(features)
        if norm > 0:
            normalized = features / norm
        else:
            normalized = features

        self._semantic_index[state_hash] = normalized
        self._index_keys.append(state_hash)

        # Limit index size
        if len(self._index_keys) > self.config.semantic_index_size:
            # Remove oldest entries
            old_keys = self._index_keys[: len(self._index_keys) - self.config.semantic_index_size]
            for key in old_keys:
                self._semantic_index.pop(key, None)
            self._index_keys = self._index_keys[-self.config.semantic_index_size:]

    def _find_similar(
        self,
        features: NDArray[np.float64],
    ) -> CacheEntry | None:
        """Find semantically similar cached entry."""
        if not self._semantic_index:
            return None

        # Normalize query
        norm = np.linalg.norm(features)
        if norm > 0:
            query = features / norm
        else:
            return None

        # Compute similarities
        best_similarity = -1.0
        best_hash = None

        for state_hash, indexed_features in self._semantic_index.items():
            similarity = float(np.dot(query, indexed_features))
            if similarity > best_similarity:
                best_similarity = similarity
                best_hash = state_hash

        # Check threshold
        if best_similarity >= self.config.similarity_threshold and best_hash is not None:
            key = f"policy:{best_hash}"
            return self._cache.get(key)

        return None

    def get_statistics(self) -> dict[str, Any]:
        """Get cache statistics."""
        total_entries = len(self._cache)
        expired_entries = sum(1 for e in self._cache.values() if e.is_expired)
        total_accesses = sum(e.access_count for e in self._cache.values())

        return {
            "backend": self.config.backend.value,
            "total_entries": total_entries,
            "active_entries": total_entries - expired_entries,
            "expired_entries": expired_entries,
            "semantic_index_size": len(self._semantic_index),
            "total_accesses": total_accesses,
            "max_entries": self.config.max_entries,
        }


class ServingLayer:
    """
    Serving Layer for Lambda Architecture.

    Combines caching with policy serving infrastructure.
    """

    def __init__(self, config: ServingLayerConfig | None = None):
        """Initialize serving layer."""
        self.config = config or ServingLayerConfig()
        self.cache = PolicyCache(config)

    async def serve_policy(
        self,
        state_hash: str,
        state_features: NDArray[np.float64] | None = None,
    ) -> dict[str, Any] | None:
        """Serve a policy from cache."""
        return await self.cache.get(state_hash, state_features)

    async def store_policy(
        self,
        state_hash: str,
        policy: dict[str, Any],
        state_features: NDArray[np.float64] | None = None,
        regime: str | None = None,
    ) -> None:
        """Store a policy in cache."""
        await self.cache.set(
            state_hash=state_hash,
            policy=policy,
            state_features=state_features,
            regime=regime,
        )

    async def bulk_store(
        self,
        policies: list[tuple[str, dict[str, Any], NDArray[np.float64] | None]],
        regime: str | None = None,
    ) -> int:
        """
        Store multiple policies.

        Args:
            policies: List of (state_hash, policy, features) tuples
            regime: Market regime

        Returns:
            Number of policies stored
        """
        count = 0
        for state_hash, policy, features in policies:
            try:
                await self.cache.set(
                    state_hash=state_hash,
                    policy=policy,
                    state_features=features,
                    regime=regime,
                )
                count += 1
            except Exception:
                continue
        return count

    def get_statistics(self) -> dict[str, Any]:
        """Get serving layer statistics."""
        return self.cache.get_statistics()
