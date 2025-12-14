"""
Analyst Response CAG for caching LLM analyst responses.

Provides semantic caching for multi-agent analyst responses,
significantly reducing LLM API calls and costs.
"""

from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

logger = logging.getLogger(__name__)

import numpy as np
from numpy.typing import NDArray
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from reasoning_trading.cag.base import (
    BaseCAG,
    CacheEntry,
    CacheHit,
    CacheLevel,
    CAGConfig,
)

if TYPE_CHECKING:
    from reasoning_trading.core.state import TradingState


class AnalystType(str, Enum):
    """Types of analysts."""

    MARKET = "market"
    NEWS = "news"
    SENTIMENT = "sentiment"
    FUNDAMENTAL = "fundamental"
    MACRO = "macro"


class AnalystCacheConfig(BaseSettings):
    """Configuration specific to analyst response cache."""

    model_config = SettingsConfigDict(
        env_prefix="ANALYST_CACHE_",
        case_sensitive=False,
        extra="ignore",
    )

    # Cache TTL per analyst type (in seconds)
    market_ttl_seconds: int = Field(
        default=300,  # 5 minutes - market conditions change fast
        ge=60,
        le=7200,
        description="TTL for market analyst cache",
    )
    news_ttl_seconds: int = Field(
        default=1800,  # 30 minutes - news is somewhat stable
        ge=300,
        le=14400,
        description="TTL for news analyst cache",
    )
    sentiment_ttl_seconds: int = Field(
        default=900,  # 15 minutes
        ge=300,
        le=7200,
        description="TTL for sentiment analyst cache",
    )
    fundamental_ttl_seconds: int = Field(
        default=3600,  # 1 hour - fundamentals change slowly
        ge=600,
        le=86400,
        description="TTL for fundamental analyst cache",
    )
    macro_ttl_seconds: int = Field(
        default=7200,  # 2 hours - macro is very stable
        ge=1800,
        le=86400,
        description="TTL for macro analyst cache",
    )

    # Similarity thresholds per analyst
    market_similarity_threshold: float = Field(
        default=0.88,
        ge=0.5,
        le=1.0,
        description="Similarity threshold for market analyst",
    )
    news_similarity_threshold: float = Field(
        default=0.85,
        ge=0.5,
        le=1.0,
        description="Similarity threshold for news analyst",
    )
    sentiment_similarity_threshold: float = Field(
        default=0.85,
        ge=0.5,
        le=1.0,
        description="Similarity threshold for sentiment analyst",
    )
    fundamental_similarity_threshold: float = Field(
        default=0.90,
        ge=0.5,
        le=1.0,
        description="Similarity threshold for fundamental analyst",
    )
    macro_similarity_threshold: float = Field(
        default=0.92,
        ge=0.5,
        le=1.0,
        description="Similarity threshold for macro analyst",
    )

    # Context encoding settings
    include_price_context: bool = Field(
        default=True,
        description="Include price in context encoding",
    )
    include_volume_context: bool = Field(
        default=True,
        description="Include volume in context encoding",
    )
    price_bucket_size: float = Field(
        default=0.02,  # 2% price buckets
        ge=0.001,
        le=0.10,
        description="Price bucket size for discretization",
    )

    # Storage settings
    max_entries_per_analyst: int = Field(
        default=1000,
        ge=100,
        le=100000,
        description="Maximum cache entries per analyst per symbol",
    )


@dataclass
class CachedAnalystResponse:
    """A cached analyst response."""

    analyst_type: AnalystType
    symbol: str
    response: str
    score: float  # -1 to 1
    confidence: float  # 0 to 1
    reasoning: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)
    context_hash: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    hit_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "analyst_type": self.analyst_type.value,
            "symbol": self.symbol,
            "response": self.response,
            "score": self.score,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "evidence": self.evidence,
            "context_hash": self.context_hash,
            "created_at": self.created_at.isoformat(),
            "hit_count": self.hit_count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CachedAnalystResponse:
        """Create from dictionary."""
        return cls(
            analyst_type=AnalystType(data["analyst_type"]),
            symbol=data["symbol"],
            response=data.get("response", ""),
            score=data.get("score", 0.0),
            confidence=data.get("confidence", 0.5),
            reasoning=data.get("reasoning", ""),
            evidence=data.get("evidence", {}),
            context_hash=data.get("context_hash", ""),
            created_at=datetime.fromisoformat(
                data.get("created_at", datetime.now().isoformat())
            ),
            hit_count=data.get("hit_count", 0),
        )


class AnalystResponseCAG(BaseCAG[CachedAnalystResponse]):
    """
    Cache for LLM analyst responses.

    Provides per-analyst semantic caching with configurable
    TTL and similarity thresholds to maximize cache hits
    while ensuring response relevance.
    """

    def __init__(
        self,
        cag_config: CAGConfig | None = None,
        analyst_config: AnalystCacheConfig | None = None,
    ):
        super().__init__(config=cag_config)
        self.analyst_config = analyst_config or AnalystCacheConfig()

        # Per-analyst L2 cache: (analyst_type, symbol) -> list of (embedding, entry)
        self._analyst_cache: dict[
            tuple[AnalystType, str],
            list[tuple[NDArray[np.float64], CacheEntry]],
        ] = {}

        # Embedding provider (lazy loaded)
        self._embedding_provider = None

        # Per-analyst stats
        self._analyst_stats: dict[AnalystType, dict[str, int]] = {
            analyst: {"queries": 0, "hits": 0, "misses": 0}
            for analyst in AnalystType
        }

    @property
    def embedding_provider(self):
        """Lazy load embedding provider."""
        if self._embedding_provider is None:
            from reasoning_trading.rag.base import DefaultEmbeddingProvider, RAGConfig

            rag_config = RAGConfig(embedding_dimension=self.config.embedding_dimension)
            self._embedding_provider = DefaultEmbeddingProvider(rag_config)
        return self._embedding_provider

    async def _setup_backend(self) -> None:
        """Setup cache backend."""
        pass

    async def _clear_backend(self) -> None:
        """Clear backend cache."""
        self._analyst_cache.clear()

    def _get_analyst_ttl(self, analyst_type: AnalystType) -> int:
        """Get TTL for analyst type."""
        ttl_map = {
            AnalystType.MARKET: self.analyst_config.market_ttl_seconds,
            AnalystType.NEWS: self.analyst_config.news_ttl_seconds,
            AnalystType.SENTIMENT: self.analyst_config.sentiment_ttl_seconds,
            AnalystType.FUNDAMENTAL: self.analyst_config.fundamental_ttl_seconds,
            AnalystType.MACRO: self.analyst_config.macro_ttl_seconds,
        }
        return ttl_map.get(analyst_type, self.config.l2_ttl_seconds)

    def _get_analyst_threshold(self, analyst_type: AnalystType) -> float:
        """Get similarity threshold for analyst type."""
        threshold_map = {
            AnalystType.MARKET: self.analyst_config.market_similarity_threshold,
            AnalystType.NEWS: self.analyst_config.news_similarity_threshold,
            AnalystType.SENTIMENT: self.analyst_config.sentiment_similarity_threshold,
            AnalystType.FUNDAMENTAL: self.analyst_config.fundamental_similarity_threshold,
            AnalystType.MACRO: self.analyst_config.macro_similarity_threshold,
        }
        return threshold_map.get(analyst_type, self.config.l2_semantic_threshold)

    def _encode_context(
        self,
        analyst_type: AnalystType,
        symbol: str,
        context: dict[str, Any],
    ) -> str:
        """
        Encode analysis context to semantic text.

        Different analysts have different context requirements.
        """
        parts = [f"Symbol: {symbol}"]

        # All analysts use technical indicators
        if "state" in context:
            state = context["state"]
            ind = state.technical_indicators

            if ind.rsi_14 is not None:
                parts.append(f"RSI: {round(ind.rsi_14, 0)}")
            if ind.macd_histogram is not None:
                sign = "+" if ind.macd_histogram > 0 else ""
                parts.append(f"MACD: {sign}{round(ind.macd_histogram, 2)}")

            # Price context (discretized)
            if self.analyst_config.include_price_context:
                price = state.current_price
                bucket_size = self.analyst_config.price_bucket_size
                price_bucket = round(price / bucket_size) * bucket_size
                parts.append(f"Price bucket: ${price_bucket:.2f}")

            # Regime
            parts.append(f"Regime: {state.market_regime.value}")

        # Analyst-specific context
        if analyst_type == AnalystType.MARKET:
            # Market analyst focuses on technical
            if "state" in context:
                state = context["state"]
                ind = state.technical_indicators
                if ind.adx_14 is not None:
                    parts.append(f"ADX: {round(ind.adx_14, 0)}")
                if ind.volatility_20 is not None:
                    parts.append(f"Vol: {round(ind.volatility_20 * 100, 1)}%")

        elif analyst_type == AnalystType.NEWS:
            # News analyst includes recent news context
            if "news_summary" in context:
                parts.append(f"News: {context['news_summary'][:200]}")
            if "event_type" in context:
                parts.append(f"Event: {context['event_type']}")

        elif analyst_type == AnalystType.SENTIMENT:
            # Sentiment includes social signals
            if "social_sentiment" in context:
                parts.append(f"Social: {context['social_sentiment']}")
            if "mention_volume" in context:
                parts.append(f"Mentions: {context['mention_volume']}")

        elif analyst_type == AnalystType.FUNDAMENTAL:
            # Fundamental includes financial metrics
            if "pe_ratio" in context:
                parts.append(f"P/E: {context['pe_ratio']:.1f}")
            if "revenue_growth" in context:
                parts.append(f"Revenue growth: {context['revenue_growth']:.1%}")

        elif analyst_type == AnalystType.MACRO:
            # Macro includes economic indicators
            if "fed_rate" in context:
                parts.append(f"Fed rate: {context['fed_rate']:.2%}")
            if "vix" in context:
                parts.append(f"VIX: {context['vix']:.1f}")

        return " | ".join(parts)

    def _compute_context_hash(
        self,
        analyst_type: AnalystType,
        symbol: str,
        context: dict[str, Any],
    ) -> str:
        """Compute hash of context for exact match."""
        encoded = self._encode_context(analyst_type, symbol, context)
        return hashlib.md5(encoded.encode()).hexdigest()

    def _compute_similarity(
        self,
        query_embedding: NDArray[np.float64],
        doc_embedding: NDArray[np.float64],
    ) -> float:
        """Compute cosine similarity."""
        norm_q = np.linalg.norm(query_embedding)
        norm_d = np.linalg.norm(doc_embedding)
        if norm_q == 0 or norm_d == 0:
            return 0.0
        return float(np.dot(query_embedding, doc_embedding) / (norm_q * norm_d))

    async def get(
        self,
        key: str,
        context: dict[str, Any] | None = None,
    ) -> CacheHit:
        """
        Look up cached analyst response.

        Args:
            key: Context hash
            context: Should contain 'analyst_type', 'symbol', and analysis context

        Returns:
            CacheHit result
        """
        start_time = time.perf_counter()

        if context is None:
            return CacheHit(
                found=False,
                lookup_time_ms=(time.perf_counter() - start_time) * 1000,
            )

        analyst_type = context.get("analyst_type")
        symbol = context.get("symbol", "")

        if analyst_type is None:
            return CacheHit(
                found=False,
                lookup_time_ms=(time.perf_counter() - start_time) * 1000,
            )

        if isinstance(analyst_type, str):
            analyst_type = AnalystType(analyst_type)

        self._analyst_stats[analyst_type]["queries"] += 1

        # L1: Exact hash match
        context_hash = self._compute_context_hash(analyst_type, symbol, context)
        l1_entry = self._l1_get(f"{analyst_type.value}:{symbol}:{context_hash}")

        if l1_entry is not None:
            self._analyst_stats[analyst_type]["hits"] += 1
            latency = (time.perf_counter() - start_time) * 1000
            self._record_hit(CacheLevel.L1_EXACT, latency)
            return CacheHit(
                found=True,
                level=CacheLevel.L1_EXACT,
                entry=l1_entry,
                similarity=1.0,
                lookup_time_ms=latency,
                query_hash=context_hash,
            )

        # L2: Semantic similarity match
        cache_key = (analyst_type, symbol)
        l2_entries = self._analyst_cache.get(cache_key, [])

        if l2_entries:
            context_text = self._encode_context(analyst_type, symbol, context)
            try:
                query_embedding = self.embedding_provider.encode_single(context_text)
            except Exception as e:
                logger.warning("Embedding provider failed for analyst cache lookup: %s", e)
                self._analyst_stats[analyst_type]["misses"] += 1
                latency = (time.perf_counter() - start_time) * 1000
                self._record_miss(latency)
                return CacheHit(
                    found=False,
                    lookup_time_ms=latency,
                    query_hash=context_hash,
                )
            threshold = self._get_analyst_threshold(analyst_type)

            best_match = None
            best_similarity = 0.0

            for stored_embedding, entry in l2_entries:
                if entry.is_expired:
                    continue

                similarity = self._compute_similarity(query_embedding, stored_embedding)

                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = entry

            if best_match is not None and best_similarity >= threshold:
                self._analyst_stats[analyst_type]["hits"] += 1
                latency = (time.perf_counter() - start_time) * 1000
                self._record_hit(CacheLevel.L2_SEMANTIC, latency)

                return CacheHit(
                    found=True,
                    level=CacheLevel.L2_SEMANTIC,
                    entry=best_match,
                    similarity=best_similarity,
                    lookup_time_ms=latency,
                    entries_searched=len(l2_entries),
                    query_hash=context_hash,
                )

        # Cache miss
        self._analyst_stats[analyst_type]["misses"] += 1
        latency = (time.perf_counter() - start_time) * 1000
        self._record_miss(latency)

        return CacheHit(
            found=False,
            lookup_time_ms=latency,
            entries_searched=len(l2_entries),
            query_hash=context_hash,
        )

    async def get_analyst_response(
        self,
        analyst_type: AnalystType | str,
        symbol: str,
        context: dict[str, Any],
        similarity_threshold: float | None = None,
    ) -> CachedAnalystResponse | None:
        """
        Get cached analyst response.

        Convenience method for analyst response lookup.

        Args:
            analyst_type: Type of analyst
            symbol: Trading symbol
            context: Analysis context (state, news, etc.)
            similarity_threshold: Override default threshold

        Returns:
            CachedAnalystResponse or None if no cache hit
        """
        if isinstance(analyst_type, str):
            analyst_type = AnalystType(analyst_type)

        full_context = {
            "analyst_type": analyst_type,
            "symbol": symbol,
            **context,
        }

        result = await self.get("", context=full_context)

        if result.is_hit and result.entry is not None:
            cached = result.entry.value
            if isinstance(cached, dict):
                cached = CachedAnalystResponse.from_dict(cached)

            # Check custom threshold if provided
            if similarity_threshold is not None and result.similarity < similarity_threshold:
                return None

            cached.hit_count += 1
            return cached

        return None

    async def put(
        self,
        key: str,
        value: CachedAnalystResponse,
        context: dict[str, Any] | None = None,
        ttl_seconds: int | None = None,
    ) -> str:
        """
        Store an analyst response.

        Args:
            key: Cache key
            value: CachedAnalystResponse to store
            context: Analysis context
            ttl_seconds: Custom TTL

        Returns:
            Entry ID
        """
        analyst_type = value.analyst_type
        symbol = value.symbol
        ttl = ttl_seconds or self._get_analyst_ttl(analyst_type)

        # Compute context hash
        context_hash = value.context_hash
        if not context_hash and context:
            context_hash = self._compute_context_hash(analyst_type, symbol, context)
            value.context_hash = context_hash

        # Create cache entry
        entry_key = f"{analyst_type.value}:{symbol}:{context_hash}"
        entry = CacheEntry(
            key=entry_key,
            value=value.to_dict() if isinstance(value, CachedAnalystResponse) else value,
            metadata={
                "analyst_type": analyst_type.value,
                "symbol": symbol,
                "score": value.score,
                "confidence": value.confidence,
            },
            ttl_seconds=ttl,
        )

        # Store in L1
        self._l1_put(entry_key, entry)

        # Store in L2
        if context:
            context_text = self._encode_context(analyst_type, symbol, context)
            try:
                embedding = self.embedding_provider.encode_single(context_text)
                entry.embedding = embedding
            except Exception as e:
                logger.warning("Embedding provider failed for analyst cache store: %s", e)
                # Continue without L2 storage - L1 will still work
                return entry_key

            cache_key = (analyst_type, symbol)
            if cache_key not in self._analyst_cache:
                self._analyst_cache[cache_key] = []

            # Check capacity
            max_entries = self.analyst_config.max_entries_per_analyst
            if len(self._analyst_cache[cache_key]) >= max_entries:
                self._evict_analyst_entries(cache_key)

            self._analyst_cache[cache_key].append((embedding, entry))

        return entry_key

    async def cache_analyst_response(
        self,
        analyst_type: AnalystType | str,
        symbol: str,
        response: str,
        score: float,
        confidence: float,
        reasoning: str = "",
        evidence: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
    ) -> str:
        """
        Cache an analyst's LLM response.

        Convenience method for caching analyst responses.

        Args:
            analyst_type: Type of analyst
            symbol: Trading symbol
            response: LLM response text
            score: Analysis score (-1 to 1)
            confidence: Confidence level (0 to 1)
            reasoning: Reasoning text
            evidence: Supporting evidence
            context: Analysis context

        Returns:
            Cache entry ID
        """
        if isinstance(analyst_type, str):
            analyst_type = AnalystType(analyst_type)

        context = context or {}
        context_hash = self._compute_context_hash(analyst_type, symbol, context)

        cached_response = CachedAnalystResponse(
            analyst_type=analyst_type,
            symbol=symbol,
            response=response,
            score=score,
            confidence=confidence,
            reasoning=reasoning,
            evidence=evidence or {},
            context_hash=context_hash,
        )

        return await self.put(
            context_hash,
            cached_response,
            context={
                "analyst_type": analyst_type,
                "symbol": symbol,
                **context,
            },
        )

    def _evict_analyst_entries(
        self,
        cache_key: tuple[AnalystType, str],
    ) -> None:
        """Evict entries for an analyst/symbol pair."""
        entries = self._analyst_cache.get(cache_key, [])
        if not entries:
            return

        # Remove expired first
        entries = [(e, entry) for e, entry in entries if not entry.is_expired]

        # LRU eviction
        if len(entries) >= self.analyst_config.max_entries_per_analyst:
            entries.sort(key=lambda x: x[1].accessed_at)
            entries = entries[self.config.eviction_batch_size :]

        self._analyst_cache[cache_key] = entries

    async def delete(self, key: str) -> bool:
        """Delete a cached response."""
        # Remove from L1
        if key in self._l1_cache:
            del self._l1_cache[key]

        # Remove from L2
        for cache_key in list(self._analyst_cache.keys()):
            self._analyst_cache[cache_key] = [
                (e, entry)
                for e, entry in self._analyst_cache[cache_key]
                if entry.key != key
            ]

        return True

    def get_analyst_stats(self) -> dict[str, dict[str, Any]]:
        """Get per-analyst cache statistics."""
        stats = {}

        for analyst_type, counts in self._analyst_stats.items():
            total = counts["queries"]
            hits = counts["hits"]
            hit_rate = hits / max(total, 1)

            # Count entries
            entry_count = sum(
                len(entries)
                for (at, _), entries in self._analyst_cache.items()
                if at == analyst_type
            )

            stats[analyst_type.value] = {
                "queries": total,
                "hits": hits,
                "misses": counts["misses"],
                "hit_rate": hit_rate,
                "entries": entry_count,
                "ttl_seconds": self._get_analyst_ttl(analyst_type),
                "threshold": self._get_analyst_threshold(analyst_type),
            }

        return stats

    def reset_analyst_stats(self) -> None:
        """Reset per-analyst statistics."""
        for analyst in AnalystType:
            self._analyst_stats[analyst] = {"queries": 0, "hits": 0, "misses": 0}
