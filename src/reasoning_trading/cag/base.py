"""
Base abstractions for CAG (Cache-Augmented Generation) systems.

Provides configurable, extensible base classes for semantic caching
with no hardcoded values.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Generic, TypeVar

import numpy as np
from numpy.typing import NDArray
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Type variable for cached content
T = TypeVar("T")


class CacheBackend(str, Enum):
    """Supported cache backend types."""

    REDIS = "redis"
    IN_MEMORY = "in_memory"
    HYBRID = "hybrid"  # In-memory L1 + Redis L2


class CacheLevel(str, Enum):
    """Cache hierarchy levels."""

    L1_EXACT = "l1_exact"  # Hash-based exact match
    L2_SEMANTIC = "l2_semantic"  # Embedding similarity
    L3_RAG = "l3_rag"  # Full RAG retrieval


class CAGConfig(BaseSettings):
    """
    Configuration for CAG systems.

    All values are configurable via environment variables with CAG_ prefix.
    """

    model_config = SettingsConfigDict(
        env_prefix="CAG_",
        case_sensitive=False,
        extra="ignore",
    )

    # Backend settings
    backend: CacheBackend = Field(
        default=CacheBackend.IN_MEMORY,
        description="Cache backend type",
    )
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL",
    )

    # TTL settings (all in seconds)
    l1_ttl_seconds: int = Field(
        default=300,
        ge=1,
        le=86400,
        description="L1 cache TTL in seconds",
    )
    l2_ttl_seconds: int = Field(
        default=3600,
        ge=60,
        le=604800,
        description="L2 cache TTL in seconds",
    )
    l3_ttl_seconds: int = Field(
        default=7200,
        ge=300,
        le=604800,
        description="L3 cache TTL in seconds",
    )

    # Similarity thresholds
    l1_exact_threshold: float = Field(
        default=1.0,
        ge=0.9,
        le=1.0,
        description="Threshold for L1 exact match",
    )
    l2_semantic_threshold: float = Field(
        default=0.92,
        ge=0.5,
        le=1.0,
        description="Threshold for L2 semantic match",
    )
    l3_rag_threshold: float = Field(
        default=0.85,
        ge=0.3,
        le=1.0,
        description="Threshold for L3 RAG match",
    )

    # Capacity settings
    max_l1_entries: int = Field(
        default=10000,
        ge=100,
        le=1000000,
        description="Maximum L1 cache entries",
    )
    max_l2_entries: int = Field(
        default=50000,
        ge=1000,
        le=10000000,
        description="Maximum L2 cache entries per collection",
    )

    # Embedding settings
    embedding_dimension: int = Field(
        default=384,
        ge=64,
        le=4096,
        description="Embedding vector dimension",
    )
    use_quantized_embeddings: bool = Field(
        default=False,
        description="Use INT8 quantized embeddings to save memory",
    )

    # Performance settings
    batch_size: int = Field(
        default=32,
        ge=1,
        le=256,
        description="Batch size for cache operations",
    )
    max_concurrent_lookups: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum concurrent cache lookups",
    )

    # Eviction settings
    eviction_policy: str = Field(
        default="lru",
        description="Cache eviction policy (lru, lfu, ttl)",
    )
    eviction_batch_size: int = Field(
        default=100,
        ge=10,
        le=1000,
        description="Number of entries to evict at once",
    )


@dataclass
class CacheEntry:
    """An entry in the cache."""

    key: str
    value: Any
    embedding: NDArray[np.float64] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    accessed_at: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    ttl_seconds: int = 3600

    @property
    def is_expired(self) -> bool:
        """Check if entry is expired."""
        age = (datetime.now() - self.created_at).total_seconds()
        return age > self.ttl_seconds

    def touch(self) -> None:
        """Update access time and count."""
        self.accessed_at = datetime.now()
        self.access_count += 1

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "key": self.key,
            "value": self.value,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "accessed_at": self.accessed_at.isoformat(),
            "access_count": self.access_count,
            "ttl_seconds": self.ttl_seconds,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CacheEntry:
        """Create from dictionary."""
        return cls(
            key=data["key"],
            value=data["value"],
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data.get("created_at", datetime.now().isoformat())),
            accessed_at=datetime.fromisoformat(data.get("accessed_at", datetime.now().isoformat())),
            access_count=data.get("access_count", 0),
            ttl_seconds=data.get("ttl_seconds", 3600),
        )


@dataclass
class CacheHit:
    """Result from a cache lookup."""

    # Hit information
    found: bool = False
    level: CacheLevel = CacheLevel.L1_EXACT
    entry: CacheEntry | None = None

    # Similarity info
    similarity: float = 0.0
    distance: float = 0.0

    # Performance
    lookup_time_ms: float = 0.0

    # Debug info
    entries_searched: int = 0
    query_hash: str = ""

    @property
    def is_hit(self) -> bool:
        """Check if this was a cache hit."""
        return self.found and self.entry is not None

    @property
    def value(self) -> Any:
        """Get cached value if hit."""
        return self.entry.value if self.entry else None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "found": self.found,
            "level": self.level.value,
            "similarity": self.similarity,
            "lookup_time_ms": self.lookup_time_ms,
            "entries_searched": self.entries_searched,
            "value": self.entry.value if self.entry else None,
        }


@dataclass
class CacheStats:
    """Statistics for cache performance."""

    # Hit rates
    total_queries: int = 0
    l1_hits: int = 0
    l2_hits: int = 0
    l3_hits: int = 0
    misses: int = 0

    # Latency
    avg_l1_latency_ms: float = 0.0
    avg_l2_latency_ms: float = 0.0
    avg_l3_latency_ms: float = 0.0
    avg_miss_latency_ms: float = 0.0

    # Storage
    l1_entries: int = 0
    l2_entries: int = 0
    memory_usage_mb: float = 0.0

    # Time range
    start_time: datetime = field(default_factory=datetime.now)
    end_time: datetime = field(default_factory=datetime.now)

    @property
    def hit_rate(self) -> float:
        """Overall cache hit rate."""
        if self.total_queries == 0:
            return 0.0
        return (self.l1_hits + self.l2_hits + self.l3_hits) / self.total_queries

    @property
    def l1_hit_rate(self) -> float:
        """L1 cache hit rate."""
        if self.total_queries == 0:
            return 0.0
        return self.l1_hits / self.total_queries

    @property
    def l2_hit_rate(self) -> float:
        """L2 cache hit rate."""
        if self.total_queries == 0:
            return 0.0
        return self.l2_hits / self.total_queries

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_queries": self.total_queries,
            "hit_rate": self.hit_rate,
            "l1_hit_rate": self.l1_hit_rate,
            "l2_hit_rate": self.l2_hit_rate,
            "l1_hits": self.l1_hits,
            "l2_hits": self.l2_hits,
            "l3_hits": self.l3_hits,
            "misses": self.misses,
            "avg_l1_latency_ms": self.avg_l1_latency_ms,
            "avg_l2_latency_ms": self.avg_l2_latency_ms,
            "l1_entries": self.l1_entries,
            "l2_entries": self.l2_entries,
            "memory_usage_mb": self.memory_usage_mb,
        }


class BaseCAG(ABC, Generic[T]):
    """
    Abstract base class for CAG implementations.

    Provides common functionality for:
    - Semantic cache lookup
    - Cache entry management
    - Statistics tracking
    """

    def __init__(
        self,
        config: CAGConfig | None = None,
    ):
        self.config = config or CAGConfig()
        self._initialized = False
        self._stats = CacheStats()

        # L1 in-memory cache
        self._l1_cache: dict[str, CacheEntry] = {}

        # Latency tracking
        self._l1_latencies: list[float] = []
        self._l2_latencies: list[float] = []
        self._l3_latencies: list[float] = []
        self._miss_latencies: list[float] = []

    @abstractmethod
    async def get(self, key: str, context: dict[str, Any] | None = None) -> CacheHit:
        """
        Look up a value in the cache.

        Args:
            key: Cache key or query
            context: Additional context for semantic matching

        Returns:
            CacheHit with result
        """
        pass

    @abstractmethod
    async def put(
        self,
        key: str,
        value: T,
        context: dict[str, Any] | None = None,
        ttl_seconds: int | None = None,
    ) -> str:
        """
        Store a value in the cache.

        Args:
            key: Cache key
            value: Value to cache
            context: Additional context for semantic key
            ttl_seconds: Custom TTL

        Returns:
            Cache entry ID
        """
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """
        Delete an entry from the cache.

        Args:
            key: Cache key

        Returns:
            True if deleted
        """
        pass

    async def initialize(self) -> None:
        """Initialize the cache system."""
        if self._initialized:
            return
        await self._setup_backend()
        self._initialized = True

    @abstractmethod
    async def _setup_backend(self) -> None:
        """Setup cache backend."""
        pass

    def _compute_key_hash(self, key: str) -> str:
        """Compute hash for exact match lookup."""
        import hashlib

        return hashlib.md5(key.encode()).hexdigest()

    def _l1_get(self, key_hash: str) -> CacheEntry | None:
        """Get from L1 cache."""
        entry = self._l1_cache.get(key_hash)
        if entry is not None and not entry.is_expired:
            entry.touch()
            return entry
        elif entry is not None:
            # Expired, remove it
            del self._l1_cache[key_hash]
        return None

    def _l1_put(self, key_hash: str, entry: CacheEntry) -> None:
        """Put to L1 cache."""
        # Evict if at capacity
        if len(self._l1_cache) >= self.config.max_l1_entries:
            self._l1_evict()
        self._l1_cache[key_hash] = entry

    def _l1_evict(self) -> None:
        """Evict entries from L1 cache."""
        if not self._l1_cache:
            return

        # Evict based on policy
        if self.config.eviction_policy == "lru":
            # Sort by access time, evict oldest
            sorted_entries = sorted(
                self._l1_cache.items(),
                key=lambda x: x[1].accessed_at,
            )
        elif self.config.eviction_policy == "lfu":
            # Sort by access count, evict least used
            sorted_entries = sorted(
                self._l1_cache.items(),
                key=lambda x: x[1].access_count,
            )
        else:
            # TTL-based: evict expired first, then oldest
            sorted_entries = sorted(
                self._l1_cache.items(),
                key=lambda x: (not x[1].is_expired, x[1].created_at),
            )

        # Evict batch
        to_evict = sorted_entries[: self.config.eviction_batch_size]
        for key, _ in to_evict:
            del self._l1_cache[key]

    def _record_hit(self, level: CacheLevel, latency_ms: float) -> None:
        """Record a cache hit."""
        self._stats.total_queries += 1

        if level == CacheLevel.L1_EXACT:
            self._stats.l1_hits += 1
            self._l1_latencies.append(latency_ms)
        elif level == CacheLevel.L2_SEMANTIC:
            self._stats.l2_hits += 1
            self._l2_latencies.append(latency_ms)
        elif level == CacheLevel.L3_RAG:
            self._stats.l3_hits += 1
            self._l3_latencies.append(latency_ms)

        self._update_latency_stats()

    def _record_miss(self, latency_ms: float) -> None:
        """Record a cache miss."""
        self._stats.total_queries += 1
        self._stats.misses += 1
        self._miss_latencies.append(latency_ms)
        self._update_latency_stats()

    def _update_latency_stats(self) -> None:
        """Update latency statistics."""
        max_samples = 10000

        if self._l1_latencies:
            self._stats.avg_l1_latency_ms = np.mean(self._l1_latencies[-max_samples:])
        if self._l2_latencies:
            self._stats.avg_l2_latency_ms = np.mean(self._l2_latencies[-max_samples:])
        if self._l3_latencies:
            self._stats.avg_l3_latency_ms = np.mean(self._l3_latencies[-max_samples:])
        if self._miss_latencies:
            self._stats.avg_miss_latency_ms = np.mean(self._miss_latencies[-max_samples:])

        self._stats.l1_entries = len(self._l1_cache)
        self._stats.end_time = datetime.now()

    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        self._update_latency_stats()
        return self._stats

    def reset_stats(self) -> None:
        """Reset statistics."""
        self._stats = CacheStats()
        self._l1_latencies.clear()
        self._l2_latencies.clear()
        self._l3_latencies.clear()
        self._miss_latencies.clear()

    async def clear(self) -> None:
        """Clear all cache entries."""
        self._l1_cache.clear()
        await self._clear_backend()

    @abstractmethod
    async def _clear_backend(self) -> None:
        """Clear backend cache."""
        pass
