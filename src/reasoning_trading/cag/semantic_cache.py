"""
Semantic Decision Cache for trading decisions.

Provides semantic similarity-based caching for trading decisions,
allowing cache hits on similar market states even without exact matches.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

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
    from reasoning_trading.core.actions import TradingAction
    from reasoning_trading.core.state import TradingState


class SemanticCacheConfig(BaseSettings):
    """Configuration specific to semantic decision cache."""

    model_config = SettingsConfigDict(
        env_prefix="SEMANTIC_CACHE_",
        case_sensitive=False,
        extra="ignore",
    )

    # State encoding settings
    include_price_features: bool = Field(
        default=True,
        description="Include price features in state encoding",
    )
    include_technical_features: bool = Field(
        default=True,
        description="Include technical indicators in state encoding",
    )
    include_analyst_features: bool = Field(
        default=True,
        description="Include analyst signals in state encoding",
    )
    include_portfolio_features: bool = Field(
        default=True,
        description="Include portfolio state in state encoding",
    )
    include_regime_features: bool = Field(
        default=True,
        description="Include market regime in state encoding",
    )

    # Feature discretization
    price_precision: int = Field(
        default=2,
        ge=0,
        le=6,
        description="Decimal precision for price features",
    )
    indicator_precision: int = Field(
        default=1,
        ge=0,
        le=4,
        description="Decimal precision for indicator features",
    )

    # Partitioning
    partition_by_symbol: bool = Field(
        default=True,
        description="Partition cache by trading symbol",
    )
    partition_by_regime: bool = Field(
        default=True,
        description="Partition cache by market regime",
    )

    # Confidence thresholds
    min_confidence_to_cache: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="Minimum decision confidence to cache",
    )
    confidence_decay_factor: float = Field(
        default=0.95,
        ge=0.5,
        le=1.0,
        description="Confidence decay factor for cached decisions",
    )


@dataclass
class CachedDecision:
    """A cached trading decision with metadata."""

    action_dict: dict[str, Any]
    confidence: float
    reasoning: str
    state_features: list[float]
    embedding: NDArray[np.float64] | None = None
    symbol: str = ""
    regime: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    hit_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "action_dict": self.action_dict,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "state_features": self.state_features,
            "symbol": self.symbol,
            "regime": self.regime,
            "created_at": self.created_at.isoformat(),
            "hit_count": self.hit_count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CachedDecision:
        """Create from dictionary."""
        return cls(
            action_dict=data["action_dict"],
            confidence=data["confidence"],
            reasoning=data.get("reasoning", ""),
            state_features=data.get("state_features", []),
            symbol=data.get("symbol", ""),
            regime=data.get("regime", ""),
            created_at=datetime.fromisoformat(
                data.get("created_at", datetime.now().isoformat())
            ),
            hit_count=data.get("hit_count", 0),
        )

    def to_trading_action(self) -> TradingAction:
        """Convert back to TradingAction."""
        from reasoning_trading.core.actions import TradingAction

        return TradingAction.from_dict(self.action_dict)


class SemanticDecisionCache(BaseCAG[CachedDecision]):
    """
    Semantic cache for trading decisions.

    Provides multi-level caching:
    - L1: Exact hash match (sub-millisecond)
    - L2: Semantic embedding similarity (few milliseconds)

    Cache keys are derived from trading state features.
    """

    def __init__(
        self,
        cag_config: CAGConfig | None = None,
        semantic_config: SemanticCacheConfig | None = None,
    ):
        super().__init__(config=cag_config)
        self.semantic_config = semantic_config or SemanticCacheConfig()

        # L2 semantic cache: symbol/regime -> list of (embedding, entry)
        self._l2_cache: dict[str, list[tuple[NDArray[np.float64], CacheEntry]]] = {}

        # Embedding provider (lazy loaded)
        self._embedding_provider = None

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
        # In-memory backend doesn't need setup
        # Redis backend would connect here
        if self.config.backend.value == "redis":
            # Would initialize Redis connection
            pass

    async def _clear_backend(self) -> None:
        """Clear backend cache."""
        self._l2_cache.clear()

    def _encode_state(self, state: TradingState) -> str:
        """
        Encode trading state to semantic text representation.

        Args:
            state: Trading state to encode

        Returns:
            Text representation for embedding
        """
        parts = []

        if self.semantic_config.include_price_features:
            price = round(state.current_price, self.semantic_config.price_precision)
            parts.append(f"Price: ${price}")

        if self.semantic_config.include_technical_features:
            ind = state.technical_indicators
            precision = self.semantic_config.indicator_precision

            if ind.rsi_14 is not None:
                parts.append(f"RSI: {round(ind.rsi_14, precision)}")
            if ind.macd is not None:
                macd_sign = "+" if ind.macd > 0 else ""
                parts.append(f"MACD: {macd_sign}{round(ind.macd, precision)}")
            if ind.adx_14 is not None:
                parts.append(f"ADX: {round(ind.adx_14, precision)}")
            if ind.volatility_20 is not None:
                parts.append(f"Vol: {round(ind.volatility_20 * 100, precision)}%")

        if self.semantic_config.include_analyst_features:
            signals = state.analyst_signals
            precision = self.semantic_config.indicator_precision

            consensus = round(signals.weighted_consensus(), precision)
            consensus_sign = "+" if consensus > 0 else ""
            parts.append(f"Consensus: {consensus_sign}{consensus}")

            debate_conf = round(signals.debate_confidence, precision)
            parts.append(f"Debate confidence: {debate_conf}")

        if self.semantic_config.include_portfolio_features:
            portfolio = state.portfolio
            precision = self.semantic_config.indicator_precision

            position_pct = round(portfolio.get_position_pct(state.symbol) * 100, precision)
            parts.append(f"Position: {position_pct}%")

            if portfolio.current_drawdown > 0:
                drawdown = round(portfolio.current_drawdown * 100, precision)
                parts.append(f"Drawdown: {drawdown}%")

        if self.semantic_config.include_regime_features:
            parts.append(f"Regime: {state.market_regime.value}")

        return " | ".join(parts)

    def _get_partition_key(self, state: TradingState) -> str:
        """Get partition key for cache lookup."""
        parts = []

        if self.semantic_config.partition_by_symbol:
            parts.append(state.symbol)

        if self.semantic_config.partition_by_regime:
            parts.append(state.market_regime.value)

        return ":".join(parts) if parts else "default"

    def _compute_state_hash(self, state: TradingState) -> str:
        """Compute hash of state for exact match."""
        # Use feature vector for hash
        features = state.to_feature_vector()
        # Discretize to reduce sensitivity
        discretized = np.round(features, self.semantic_config.indicator_precision)
        return hashlib.md5(discretized.tobytes()).hexdigest()

    async def get(
        self,
        key: str,
        context: dict[str, Any] | None = None,
    ) -> CacheHit:
        """
        Look up cached decision.

        For SemanticDecisionCache, the key is the state hash and
        context should contain the TradingState for semantic matching.

        Args:
            key: State hash or identifier
            context: Should contain 'state' with TradingState

        Returns:
            CacheHit result
        """
        start_time = time.perf_counter()

        # Get state from context
        state = context.get("state") if context else None
        if state is None:
            return CacheHit(
                found=False,
                lookup_time_ms=(time.perf_counter() - start_time) * 1000,
            )

        # L1: Exact hash match
        state_hash = self._compute_state_hash(state)
        l1_entry = self._l1_get(state_hash)

        if l1_entry is not None:
            latency = (time.perf_counter() - start_time) * 1000
            self._record_hit(CacheLevel.L1_EXACT, latency)
            return CacheHit(
                found=True,
                level=CacheLevel.L1_EXACT,
                entry=l1_entry,
                similarity=1.0,
                lookup_time_ms=latency,
                query_hash=state_hash,
            )

        # L2: Semantic similarity match
        partition_key = self._get_partition_key(state)
        l2_entries = self._l2_cache.get(partition_key, [])

        if l2_entries:
            # Encode state to text and get embedding
            state_text = self._encode_state(state)
            query_embedding = self.embedding_provider.encode_single(state_text)

            best_match = None
            best_similarity = 0.0

            for stored_embedding, entry in l2_entries:
                if entry.is_expired:
                    continue

                similarity = self._compute_similarity(query_embedding, stored_embedding)

                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = entry

            if best_match is not None and best_similarity >= self.config.l2_semantic_threshold:
                # Apply confidence decay for semantic matches
                cached_decision = best_match.value
                if isinstance(cached_decision, dict):
                    cached_decision = CachedDecision.from_dict(cached_decision)

                # Decay confidence based on similarity
                decay = self.semantic_config.confidence_decay_factor * best_similarity
                cached_decision.confidence *= decay
                cached_decision.hit_count += 1

                latency = (time.perf_counter() - start_time) * 1000
                self._record_hit(CacheLevel.L2_SEMANTIC, latency)

                return CacheHit(
                    found=True,
                    level=CacheLevel.L2_SEMANTIC,
                    entry=best_match,
                    similarity=best_similarity,
                    lookup_time_ms=latency,
                    entries_searched=len(l2_entries),
                    query_hash=state_hash,
                )

        # Cache miss
        latency = (time.perf_counter() - start_time) * 1000
        self._record_miss(latency)

        return CacheHit(
            found=False,
            lookup_time_ms=latency,
            entries_searched=len(l2_entries),
            query_hash=state_hash,
        )

    def _compute_similarity(
        self,
        query_embedding: NDArray[np.float64],
        doc_embedding: NDArray[np.float64],
    ) -> float:
        """Compute cosine similarity between embeddings."""
        norm_q = np.linalg.norm(query_embedding)
        norm_d = np.linalg.norm(doc_embedding)
        if norm_q == 0 or norm_d == 0:
            return 0.0
        return float(np.dot(query_embedding, doc_embedding) / (norm_q * norm_d))

    async def get_cached_decision(
        self,
        state: TradingState,
    ) -> tuple[TradingAction | None, float]:
        """
        Get cached decision for a trading state.

        Convenience method that returns the TradingAction directly.

        Args:
            state: Trading state to look up

        Returns:
            Tuple of (TradingAction or None, similarity score)
        """
        state_hash = self._compute_state_hash(state)
        result = await self.get(state_hash, context={"state": state})

        if result.is_hit and result.entry is not None:
            cached = result.entry.value
            if isinstance(cached, dict):
                cached = CachedDecision.from_dict(cached)
            return cached.to_trading_action(), result.similarity

        return None, 0.0

    async def put(
        self,
        key: str,
        value: CachedDecision,
        context: dict[str, Any] | None = None,
        ttl_seconds: int | None = None,
    ) -> str:
        """
        Store a decision in the cache.

        Args:
            key: Cache key (typically state hash)
            value: CachedDecision to store
            context: Should contain 'state' for semantic indexing
            ttl_seconds: Custom TTL

        Returns:
            Entry ID
        """
        state = context.get("state") if context else None
        ttl = ttl_seconds or self.config.l2_ttl_seconds

        # Create cache entry
        entry = CacheEntry(
            key=key,
            value=value.to_dict() if isinstance(value, CachedDecision) else value,
            metadata={
                "symbol": value.symbol,
                "regime": value.regime,
                "confidence": value.confidence,
            },
            ttl_seconds=ttl,
        )

        # Store in L1 (exact match)
        self._l1_put(key, entry)

        # Store in L2 (semantic)
        if state is not None:
            state_text = self._encode_state(state)
            embedding = self.embedding_provider.encode_single(state_text)
            entry.embedding = embedding

            partition_key = self._get_partition_key(state)
            if partition_key not in self._l2_cache:
                self._l2_cache[partition_key] = []

            # Check capacity and evict if needed
            if len(self._l2_cache[partition_key]) >= self.config.max_l2_entries:
                self._l2_evict(partition_key)

            self._l2_cache[partition_key].append((embedding, entry))

        return key

    async def cache_decision(
        self,
        state: TradingState,
        action: TradingAction,
        reasoning: str = "",
    ) -> str:
        """
        Cache a trading decision.

        Convenience method for caching decisions.

        Args:
            state: Trading state
            action: Trading action taken
            reasoning: Reasoning for the decision

        Returns:
            Cache entry ID
        """
        # Check minimum confidence
        if action.confidence < self.semantic_config.min_confidence_to_cache:
            return ""

        state_hash = self._compute_state_hash(state)
        state_features = state.to_feature_vector().tolist()

        cached_decision = CachedDecision(
            action_dict=action.to_dict(),
            confidence=action.confidence,
            reasoning=reasoning or action.reasoning,
            state_features=state_features,
            symbol=state.symbol,
            regime=state.market_regime.value,
        )

        return await self.put(
            state_hash,
            cached_decision,
            context={"state": state},
        )

    def _l2_evict(self, partition_key: str) -> None:
        """Evict entries from L2 partition."""
        entries = self._l2_cache.get(partition_key, [])
        if not entries:
            return

        # Remove expired entries first
        entries = [(e, entry) for e, entry in entries if not entry.is_expired]

        # If still over capacity, evict by LRU
        if len(entries) >= self.config.max_l2_entries:
            entries.sort(key=lambda x: x[1].accessed_at)
            entries = entries[self.config.eviction_batch_size :]

        self._l2_cache[partition_key] = entries

    async def delete(self, key: str) -> bool:
        """Delete a cached decision."""
        # Remove from L1
        if key in self._l1_cache:
            del self._l1_cache[key]

        # Remove from all L2 partitions
        for partition_key in list(self._l2_cache.keys()):
            self._l2_cache[partition_key] = [
                (e, entry)
                for e, entry in self._l2_cache[partition_key]
                if entry.key != key
            ]

        return True

    async def get_similar_decisions(
        self,
        state: TradingState,
        top_k: int = 5,
    ) -> list[tuple[CachedDecision, float]]:
        """
        Get top-k similar cached decisions.

        Args:
            state: Trading state
            top_k: Number of results

        Returns:
            List of (CachedDecision, similarity) tuples
        """
        partition_key = self._get_partition_key(state)
        l2_entries = self._l2_cache.get(partition_key, [])

        if not l2_entries:
            return []

        state_text = self._encode_state(state)
        query_embedding = self.embedding_provider.encode_single(state_text)

        results = []
        for stored_embedding, entry in l2_entries:
            if entry.is_expired:
                continue

            similarity = self._compute_similarity(query_embedding, stored_embedding)
            cached = entry.value
            if isinstance(cached, dict):
                cached = CachedDecision.from_dict(cached)

            results.append((cached, similarity))

        # Sort by similarity descending
        results.sort(key=lambda x: x[1], reverse=True)

        return results[:top_k]

    async def get_partition_stats(self) -> dict[str, dict[str, Any]]:
        """Get statistics per partition."""
        stats = {}

        for partition_key, entries in self._l2_cache.items():
            valid_entries = [e for _, e in entries if not e.is_expired]
            stats[partition_key] = {
                "total_entries": len(entries),
                "valid_entries": len(valid_entries),
                "expired_entries": len(entries) - len(valid_entries),
            }

        return stats
