"""
Hierarchical CAG with ensemble coordination.

Provides multi-level caching with RAG fallback and ensemble
weighting across all sub-agents for optimal decision retrieval.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

import numpy as np
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from reasoning_trading.cag.base import (
    BaseCAG,
    CacheEntry,
    CacheHit,
    CacheLevel,
    CacheStats,
    CAGConfig,
)
from reasoning_trading.cag.analyst_cache import AnalystResponseCAG, AnalystType
from reasoning_trading.cag.semantic_cache import SemanticDecisionCache

if TYPE_CHECKING:
    from reasoning_trading.core.actions import TradingAction
    from reasoning_trading.core.state import TradingState
    from reasoning_trading.rag.mcts_strategies import MCTSStrategyRAG
    from reasoning_trading.rag.trading_patterns import TradingPatternRAG


class EnsembleStrategy(str, Enum):
    """Ensemble weighting strategies."""

    UNIFORM = "uniform"  # Equal weights
    CONFIDENCE_WEIGHTED = "confidence_weighted"  # Weight by confidence
    RECENCY_WEIGHTED = "recency_weighted"  # Weight by recency
    PERFORMANCE_WEIGHTED = "performance_weighted"  # Weight by historical performance
    ADAPTIVE = "adaptive"  # Learn weights from outcomes


class DecisionLevel(str, Enum):
    """Decision hierarchy levels."""

    STRATEGIC = "strategic"  # Portfolio-level decisions
    TACTICAL = "tactical"  # Position-level decisions
    EXECUTION = "execution"  # Order-level decisions


class HierarchicalCAGConfig(BaseSettings):
    """Configuration for hierarchical CAG."""

    model_config = SettingsConfigDict(
        env_prefix="HIER_CAG_",
        case_sensitive=False,
        extra="ignore",
    )

    # Level-specific settings
    strategic_cache_ttl: int = Field(
        default=7200,  # 2 hours
        ge=600,
        le=86400,
        description="TTL for strategic level cache",
    )
    tactical_cache_ttl: int = Field(
        default=1800,  # 30 minutes
        ge=300,
        le=14400,
        description="TTL for tactical level cache",
    )
    execution_cache_ttl: int = Field(
        default=300,  # 5 minutes
        ge=60,
        le=3600,
        description="TTL for execution level cache",
    )

    # Latency budgets (ms)
    l1_budget_ms: float = Field(
        default=1.0,
        ge=0.1,
        le=10.0,
        description="L1 cache lookup budget",
    )
    l2_budget_ms: float = Field(
        default=10.0,
        ge=1.0,
        le=50.0,
        description="L2 semantic cache budget",
    )
    l3_budget_ms: float = Field(
        default=50.0,
        ge=10.0,
        le=200.0,
        description="L3 RAG retrieval budget",
    )
    total_budget_ms: float = Field(
        default=100.0,
        ge=20.0,
        le=500.0,
        description="Total decision budget",
    )

    # Ensemble settings
    ensemble_strategy: EnsembleStrategy = Field(
        default=EnsembleStrategy.CONFIDENCE_WEIGHTED,
        description="Ensemble weighting strategy",
    )
    min_ensemble_sources: int = Field(
        default=2,
        ge=1,
        le=5,
        description="Minimum sources for ensemble decision",
    )
    ensemble_agreement_threshold: float = Field(
        default=0.6,
        ge=0.3,
        le=1.0,
        description="Minimum agreement for ensemble consensus",
    )

    # Sub-agent weights (must sum to 1.0 when normalized)
    decision_cache_weight: float = Field(
        default=0.35,
        ge=0.0,
        le=1.0,
        description="Weight for decision cache",
    )
    pattern_rag_weight: float = Field(
        default=0.25,
        ge=0.0,
        le=1.0,
        description="Weight for pattern RAG",
    )
    strategy_rag_weight: float = Field(
        default=0.25,
        ge=0.0,
        le=1.0,
        description="Weight for strategy RAG",
    )
    analyst_cache_weight: float = Field(
        default=0.15,
        ge=0.0,
        le=1.0,
        description="Weight for analyst cache",
    )

    # Fallback settings
    enable_rag_fallback: bool = Field(
        default=True,
        description="Enable RAG fallback on cache miss",
    )
    min_confidence_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Minimum confidence to use cached result",
    )

    # RAG confidence settings
    max_rag_confidence: float = Field(
        default=0.85,
        ge=0.5,
        le=1.0,
        description="Maximum confidence cap for RAG-based decisions",
    )

    # Analyst signal thresholds
    bullish_signal_threshold: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description="Threshold above which signals are considered bullish",
    )
    bearish_signal_threshold: float = Field(
        default=-0.2,
        ge=-1.0,
        le=0.0,
        description="Threshold below which signals are considered bearish",
    )

    # Adaptive learning settings
    adaptive_learning_rate: float = Field(
        default=0.05,
        ge=0.001,
        le=0.5,
        description="Learning rate for adaptive weight updates",
    )
    adaptive_weight_min: float = Field(
        default=0.05,
        ge=0.01,
        le=0.2,
        description="Minimum weight for any source in adaptive mode",
    )
    adaptive_weight_max: float = Field(
        default=0.5,
        ge=0.3,
        le=0.9,
        description="Maximum weight for any source in adaptive mode",
    )


@dataclass
class EnsembleSource:
    """A source contributing to ensemble decision."""

    source_name: str
    level: CacheLevel
    action_direction: str
    confidence: float
    similarity: float = 0.0
    weight: float = 0.0
    latency_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class HierarchicalDecision:
    """Result from hierarchical cache lookup."""

    # Decision info
    found: bool = False
    decision_level: DecisionLevel = DecisionLevel.TACTICAL
    action_direction: str = ""
    action_params: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0

    # Source info
    primary_source: str = ""
    cache_level: CacheLevel = CacheLevel.L1_EXACT
    similarity: float = 0.0

    # Ensemble info
    ensemble_sources: list[EnsembleSource] = field(default_factory=list)
    ensemble_agreement: float = 0.0
    ensemble_confidence: float = 0.0

    # Performance
    total_latency_ms: float = 0.0
    level_latencies: dict[str, float] = field(default_factory=dict)

    # Debug
    query_hash: str = ""
    reasoning: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "found": self.found,
            "decision_level": self.decision_level.value,
            "action_direction": self.action_direction,
            "action_params": self.action_params,
            "confidence": self.confidence,
            "primary_source": self.primary_source,
            "cache_level": self.cache_level.value,
            "similarity": self.similarity,
            "ensemble_agreement": self.ensemble_agreement,
            "ensemble_confidence": self.ensemble_confidence,
            "total_latency_ms": self.total_latency_ms,
            "reasoning": self.reasoning,
        }


class HierarchicalCAG(BaseCAG[HierarchicalDecision]):
    """
    Hierarchical CAG with ensemble coordination.

    Provides multi-level caching:
    - L1: Exact hash match (sub-millisecond)
    - L2: Semantic similarity (few milliseconds)
    - L3: RAG retrieval fallback (tens of milliseconds)

    Coordinates multiple sub-agents:
    - SemanticDecisionCache: Cached trading decisions
    - TradingPatternRAG: Historical trading patterns
    - MCTSStrategyRAG: Successful MCTS strategies
    - AnalystResponseCAG: Cached analyst responses
    """

    def __init__(
        self,
        cag_config: CAGConfig | None = None,
        hier_config: HierarchicalCAGConfig | None = None,
        decision_cache: SemanticDecisionCache | None = None,
        pattern_rag: TradingPatternRAG | None = None,
        strategy_rag: MCTSStrategyRAG | None = None,
        analyst_cache: AnalystResponseCAG | None = None,
    ):
        super().__init__(config=cag_config)
        self.hier_config = hier_config or HierarchicalCAGConfig()

        # Sub-agents (lazy loaded if not provided)
        self._decision_cache = decision_cache
        self._pattern_rag = pattern_rag
        self._strategy_rag = strategy_rag
        self._analyst_cache = analyst_cache

        # Per-level stats
        self._level_stats: dict[DecisionLevel, CacheStats] = {
            level: CacheStats() for level in DecisionLevel
        }

        # Adaptive weights (for ADAPTIVE strategy)
        self._adaptive_weights: dict[str, float] = {
            "decision_cache": self.hier_config.decision_cache_weight,
            "pattern_rag": self.hier_config.pattern_rag_weight,
            "strategy_rag": self.hier_config.strategy_rag_weight,
            "analyst_cache": self.hier_config.analyst_cache_weight,
        }

    @property
    def decision_cache(self) -> SemanticDecisionCache:
        """Lazy load decision cache."""
        if self._decision_cache is None:
            self._decision_cache = SemanticDecisionCache(cag_config=self.config)
        return self._decision_cache

    @property
    def pattern_rag(self) -> TradingPatternRAG:
        """Lazy load pattern RAG."""
        if self._pattern_rag is None:
            from reasoning_trading.rag.trading_patterns import TradingPatternRAG

            self._pattern_rag = TradingPatternRAG()
        return self._pattern_rag

    @property
    def strategy_rag(self) -> MCTSStrategyRAG:
        """Lazy load strategy RAG."""
        if self._strategy_rag is None:
            from reasoning_trading.rag.mcts_strategies import MCTSStrategyRAG

            self._strategy_rag = MCTSStrategyRAG()
        return self._strategy_rag

    @property
    def analyst_cache(self) -> AnalystResponseCAG:
        """Lazy load analyst cache."""
        if self._analyst_cache is None:
            self._analyst_cache = AnalystResponseCAG(cag_config=self.config)
        return self._analyst_cache

    async def _setup_backend(self) -> None:
        """Setup cache backends."""
        await asyncio.gather(
            self.decision_cache.initialize(),
            self.pattern_rag.initialize(),
            self.strategy_rag.initialize(),
            self.analyst_cache.initialize(),
        )

    async def _clear_backend(self) -> None:
        """Clear all backends."""
        await asyncio.gather(
            self.decision_cache.clear(),
            self.analyst_cache.clear(),
        )

    def _get_level_ttl(self, level: DecisionLevel) -> int:
        """Get TTL for decision level."""
        ttl_map = {
            DecisionLevel.STRATEGIC: self.hier_config.strategic_cache_ttl,
            DecisionLevel.TACTICAL: self.hier_config.tactical_cache_ttl,
            DecisionLevel.EXECUTION: self.hier_config.execution_cache_ttl,
        }
        return ttl_map.get(level, self.config.l2_ttl_seconds)

    def _get_source_weight(self, source_name: str) -> float:
        """Get weight for a source."""
        if self.hier_config.ensemble_strategy == EnsembleStrategy.ADAPTIVE:
            return self._adaptive_weights.get(source_name, 0.25)

        weight_map = {
            "decision_cache": self.hier_config.decision_cache_weight,
            "pattern_rag": self.hier_config.pattern_rag_weight,
            "strategy_rag": self.hier_config.strategy_rag_weight,
            "analyst_cache": self.hier_config.analyst_cache_weight,
        }
        return weight_map.get(source_name, 0.25)

    async def get(
        self,
        key: str,
        context: dict[str, Any] | None = None,
    ) -> CacheHit:
        """
        Hierarchical cache lookup.

        Args:
            key: Cache key
            context: Should contain 'state' and optional 'level'

        Returns:
            CacheHit result
        """
        start_time = time.perf_counter()

        if context is None:
            return CacheHit(
                found=False,
                lookup_time_ms=(time.perf_counter() - start_time) * 1000,
            )

        state = context.get("state")
        level = context.get("level", DecisionLevel.TACTICAL)

        if isinstance(level, str):
            level = DecisionLevel(level)

        # Get hierarchical decision
        decision = await self.get_decision(state, level)

        latency = (time.perf_counter() - start_time) * 1000

        if decision.found:
            # Create cache entry from decision
            entry = CacheEntry(
                key=key,
                value=decision.to_dict(),
                metadata={
                    "level": level.value,
                    "primary_source": decision.primary_source,
                },
            )

            self._record_hit(decision.cache_level, latency)

            return CacheHit(
                found=True,
                level=decision.cache_level,
                entry=entry,
                similarity=decision.similarity,
                lookup_time_ms=latency,
                query_hash=decision.query_hash,
            )

        self._record_miss(latency)
        return CacheHit(
            found=False,
            lookup_time_ms=latency,
        )

    async def get_decision(
        self,
        state: TradingState,
        level: DecisionLevel = DecisionLevel.TACTICAL,
    ) -> HierarchicalDecision:
        """
        Get decision from hierarchical cache with ensemble.

        This is the main entry point for decision retrieval.

        Args:
            state: Current trading state
            level: Decision level

        Returns:
            HierarchicalDecision with ensemble result
        """
        start_time = time.perf_counter()
        level_latencies = {}
        ensemble_sources: list[EnsembleSource] = []

        # L1: Check decision cache (fastest)
        l1_start = time.perf_counter()
        decision_result = await self.decision_cache.get_cached_decision(state)
        l1_latency = (time.perf_counter() - l1_start) * 1000
        level_latencies["l1_decision_cache"] = l1_latency

        if decision_result[0] is not None:
            action, similarity = decision_result
            ensemble_sources.append(
                EnsembleSource(
                    source_name="decision_cache",
                    level=CacheLevel.L2_SEMANTIC if similarity < 1.0 else CacheLevel.L1_EXACT,
                    action_direction=action.direction.value,
                    confidence=action.confidence,
                    similarity=similarity,
                    weight=self._get_source_weight("decision_cache"),
                    latency_ms=l1_latency,
                )
            )

            # If high confidence exact match, return early
            if similarity >= 0.98 and action.confidence >= self.hier_config.min_confidence_threshold:
                return HierarchicalDecision(
                    found=True,
                    decision_level=level,
                    action_direction=action.direction.value,
                    action_params=action.to_dict(),
                    confidence=action.confidence,
                    primary_source="decision_cache",
                    cache_level=CacheLevel.L1_EXACT,
                    similarity=similarity,
                    ensemble_sources=ensemble_sources,
                    ensemble_agreement=1.0,
                    ensemble_confidence=action.confidence,
                    total_latency_ms=(time.perf_counter() - start_time) * 1000,
                    level_latencies=level_latencies,
                    reasoning=action.reasoning,
                )

        # L2/L3: Query other sources in parallel if budget allows
        elapsed = (time.perf_counter() - start_time) * 1000
        remaining_budget = self.hier_config.total_budget_ms - elapsed

        if remaining_budget > self.hier_config.l2_budget_ms and self.hier_config.enable_rag_fallback:
            # Query pattern RAG and strategy RAG in parallel
            l2_results = await asyncio.gather(
                self._query_pattern_rag(state),
                self._query_strategy_rag(state),
                self._query_analyst_signals(state),
                return_exceptions=True,
            )

            # Process pattern RAG result
            if isinstance(l2_results[0], tuple):
                patterns, pattern_latency = l2_results[0]
                level_latencies["l2_pattern_rag"] = pattern_latency

                if patterns:
                    best_pattern, similarity = patterns[0]
                    ensemble_sources.append(
                        EnsembleSource(
                            source_name="pattern_rag",
                            level=CacheLevel.L3_RAG,
                            action_direction=best_pattern.action_direction,
                            confidence=min(similarity, self.hier_config.max_rag_confidence),
                            similarity=similarity,
                            weight=self._get_source_weight("pattern_rag"),
                            latency_ms=pattern_latency,
                            metadata={"sharpe": best_pattern.outcome_sharpe},
                        )
                    )

            # Process strategy RAG result
            if isinstance(l2_results[1], tuple):
                strategies, strategy_latency = l2_results[1]
                level_latencies["l2_strategy_rag"] = strategy_latency

                if strategies:
                    best_strategy, similarity = strategies[0]
                    ensemble_sources.append(
                        EnsembleSource(
                            source_name="strategy_rag",
                            level=CacheLevel.L3_RAG,
                            action_direction=best_strategy.best_action,
                            confidence=min(
                                similarity * best_strategy.best_action_confidence,
                                self.hier_config.max_rag_confidence,
                            ),
                            similarity=similarity,
                            weight=self._get_source_weight("strategy_rag"),
                            latency_ms=strategy_latency,
                            metadata={"sharpe": best_strategy.outcome_sharpe},
                        )
                    )

            # Process analyst signals
            if isinstance(l2_results[2], tuple):
                analyst_direction, analyst_confidence, analyst_latency = l2_results[2]
                level_latencies["l2_analyst_cache"] = analyst_latency

                if analyst_direction:
                    ensemble_sources.append(
                        EnsembleSource(
                            source_name="analyst_cache",
                            level=CacheLevel.L2_SEMANTIC,
                            action_direction=analyst_direction,
                            confidence=analyst_confidence,
                            similarity=analyst_confidence,
                            weight=self._get_source_weight("analyst_cache"),
                            latency_ms=analyst_latency,
                        )
                    )

        # Compute ensemble decision
        if ensemble_sources:
            ensemble_result = self._compute_ensemble(ensemble_sources)

            return HierarchicalDecision(
                found=True,
                decision_level=level,
                action_direction=ensemble_result["direction"],
                action_params=ensemble_result.get("params", {}),
                confidence=ensemble_result["confidence"],
                primary_source=ensemble_result["primary_source"],
                cache_level=ensemble_result["cache_level"],
                similarity=ensemble_result["similarity"],
                ensemble_sources=ensemble_sources,
                ensemble_agreement=ensemble_result["agreement"],
                ensemble_confidence=ensemble_result["confidence"],
                total_latency_ms=(time.perf_counter() - start_time) * 1000,
                level_latencies=level_latencies,
                reasoning=ensemble_result.get("reasoning", ""),
            )

        # No results found
        return HierarchicalDecision(
            found=False,
            decision_level=level,
            total_latency_ms=(time.perf_counter() - start_time) * 1000,
            level_latencies=level_latencies,
        )

    async def _query_pattern_rag(
        self,
        state: TradingState,
    ) -> tuple[list[tuple[Any, float]], float]:
        """Query pattern RAG."""
        start = time.perf_counter()
        try:
            patterns = await self.pattern_rag.retrieve_similar_patterns(
                state,
                top_k=3,
                successful_only=True,
            )
            return patterns, (time.perf_counter() - start) * 1000
        except Exception:
            return [], (time.perf_counter() - start) * 1000

    async def _query_strategy_rag(
        self,
        state: TradingState,
    ) -> tuple[list[tuple[Any, float]], float]:
        """Query strategy RAG."""
        start = time.perf_counter()
        try:
            strategies = await self.strategy_rag.retrieve_similar_strategies(
                state,
                min_sharpe=0.5,
                top_k=3,
            )
            return strategies, (time.perf_counter() - start) * 1000
        except Exception:
            return [], (time.perf_counter() - start) * 1000

    async def _query_analyst_signals(
        self,
        state: TradingState,
    ) -> tuple[str, float, float]:
        """Query analyst cache for consensus direction."""
        start = time.perf_counter()
        try:
            # Get cached responses for each analyst
            scores = []
            context = {"state": state}

            for analyst_type in [
                AnalystType.MARKET,
                AnalystType.FUNDAMENTAL,
                AnalystType.MACRO,
            ]:
                response = await self.analyst_cache.get_analyst_response(
                    analyst_type,
                    state.symbol,
                    context,
                )
                if response:
                    scores.append((response.score, response.confidence))

            if scores:
                # Weighted average of scores
                total_weight = sum(c for _, c in scores)
                if total_weight > 0:
                    weighted_score = sum(s * c for s, c in scores) / total_weight
                    avg_confidence = np.mean([c for _, c in scores])

                    # Determine direction using configurable thresholds
                    if weighted_score > self.hier_config.bullish_signal_threshold:
                        direction = "buy"
                    elif weighted_score < self.hier_config.bearish_signal_threshold:
                        direction = "sell"
                    else:
                        direction = "hold"

                    return direction, avg_confidence, (time.perf_counter() - start) * 1000

            return "", 0.0, (time.perf_counter() - start) * 1000
        except Exception:
            return "", 0.0, (time.perf_counter() - start) * 1000

    def _compute_ensemble(
        self,
        sources: list[EnsembleSource],
    ) -> dict[str, Any]:
        """
        Compute ensemble decision from multiple sources.

        Uses configured ensemble strategy to weight and combine sources.
        """
        if not sources:
            return {
                "direction": "hold",
                "confidence": 0.0,
                "primary_source": "",
                "cache_level": CacheLevel.L1_EXACT,
                "similarity": 0.0,
                "agreement": 0.0,
            }

        # Compute weights based on strategy
        if self.hier_config.ensemble_strategy == EnsembleStrategy.UNIFORM:
            for source in sources:
                source.weight = 1.0 / len(sources)

        elif self.hier_config.ensemble_strategy == EnsembleStrategy.CONFIDENCE_WEIGHTED:
            total_conf = sum(s.confidence for s in sources)
            if total_conf > 0:
                for source in sources:
                    source.weight = (source.confidence / total_conf) * self._get_source_weight(
                        source.source_name
                    )

        elif self.hier_config.ensemble_strategy == EnsembleStrategy.PERFORMANCE_WEIGHTED:
            # Weight by historical Sharpe in metadata
            total_perf = sum(s.metadata.get("sharpe", 0.5) + 1 for s in sources)
            if total_perf > 0:
                for source in sources:
                    perf = source.metadata.get("sharpe", 0.5) + 1
                    source.weight = perf / total_perf

        # Normalize weights
        total_weight = sum(s.weight for s in sources)
        if total_weight > 0:
            for source in sources:
                source.weight /= total_weight

        # Aggregate votes by direction
        direction_weights: dict[str, float] = {}
        direction_confidences: dict[str, list[float]] = {}

        for source in sources:
            direction = source.action_direction
            if direction not in direction_weights:
                direction_weights[direction] = 0.0
                direction_confidences[direction] = []

            direction_weights[direction] += source.weight
            direction_confidences[direction].append(source.confidence)

        # Find winning direction
        best_direction = max(direction_weights, key=direction_weights.get)
        agreement = direction_weights[best_direction]

        # Compute ensemble confidence
        conf_list = direction_confidences[best_direction]
        ensemble_confidence = np.mean(conf_list) if conf_list else 0.0

        # Find primary source (highest weight for winning direction)
        primary_source = max(
            [s for s in sources if s.action_direction == best_direction],
            key=lambda s: s.weight,
        )

        # Build reasoning
        reasoning_parts = [f"Ensemble decision: {best_direction}"]
        reasoning_parts.append(f"Agreement: {agreement:.0%}")
        reasoning_parts.append("Sources:")
        for source in sorted(sources, key=lambda s: s.weight, reverse=True):
            reasoning_parts.append(
                f"  - {source.source_name}: {source.action_direction} "
                f"(weight={source.weight:.2f}, conf={source.confidence:.2f})"
            )

        return {
            "direction": best_direction,
            "confidence": ensemble_confidence * agreement,  # Scale by agreement
            "primary_source": primary_source.source_name,
            "cache_level": primary_source.level,
            "similarity": primary_source.similarity,
            "agreement": agreement,
            "reasoning": "\n".join(reasoning_parts),
        }

    async def put(
        self,
        key: str,
        value: HierarchicalDecision,
        context: dict[str, Any] | None = None,
        ttl_seconds: int | None = None,
    ) -> str:
        """
        Store a decision in the cache.

        Stores in appropriate sub-caches based on decision level.
        """
        # This would store in the decision cache
        # The hierarchical cache primarily acts as a read coordinator
        return key

    async def delete(self, key: str) -> bool:
        """Delete from all sub-caches."""
        results = await asyncio.gather(
            self.decision_cache.delete(key),
            return_exceptions=True,
        )
        return any(r is True for r in results if isinstance(r, bool))

    async def cache_decision_outcome(
        self,
        state: TradingState,
        action: TradingAction,
        outcome: dict[str, float],
        reasoning: str = "",
    ) -> None:
        """
        Cache a decision with its outcome.

        Stores in both decision cache and pattern RAG for future retrieval.

        Args:
            state: Trading state at decision time
            action: Action taken
            outcome: Outcome metrics
            reasoning: Reasoning text
        """
        # Cache in decision cache
        await self.decision_cache.cache_decision(state, action, reasoning)

        # Store pattern in RAG
        if self.hier_config.enable_rag_fallback:
            await self.pattern_rag.store_pattern(state, action, outcome, reasoning)

    def get_ensemble_stats(self) -> dict[str, Any]:
        """Get ensemble and sub-agent statistics."""
        return {
            "decision_cache": self.decision_cache.get_stats().to_dict(),
            "analyst_cache": self.analyst_cache.get_analyst_stats(),
            "adaptive_weights": self._adaptive_weights,
            "config": {
                "ensemble_strategy": self.hier_config.ensemble_strategy.value,
                "min_ensemble_sources": self.hier_config.min_ensemble_sources,
                "total_budget_ms": self.hier_config.total_budget_ms,
            },
        }

    def update_adaptive_weights(self, source_name: str, success: bool) -> None:
        """
        Update adaptive weights based on outcome.

        For ADAPTIVE ensemble strategy.
        """
        if self.hier_config.ensemble_strategy != EnsembleStrategy.ADAPTIVE:
            return

        learning_rate = self.hier_config.adaptive_learning_rate
        current_weight = self._adaptive_weights.get(source_name, 0.25)

        if success:
            # Increase weight for successful source
            new_weight = current_weight + learning_rate * (1 - current_weight)
        else:
            # Decrease weight for unsuccessful source
            new_weight = current_weight - learning_rate * current_weight

        # Clamp to configurable range
        new_weight = max(
            self.hier_config.adaptive_weight_min,
            min(self.hier_config.adaptive_weight_max, new_weight),
        )
        self._adaptive_weights[source_name] = new_weight

        # Renormalize all weights
        total = sum(self._adaptive_weights.values())
        for key in self._adaptive_weights:
            self._adaptive_weights[key] /= total
