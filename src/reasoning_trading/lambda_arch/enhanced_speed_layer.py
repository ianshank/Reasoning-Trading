"""
Enhanced Speed Layer with RAG/CAG integration.

Extends the base speed layer with hierarchical caching
and retrieval-augmented decision making.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

import numpy as np
from numpy.typing import NDArray
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from reasoning_trading.cag.hierarchical_cache import (
    DecisionLevel,
    HierarchicalCAG,
    HierarchicalCAGConfig,
    HierarchicalDecision,
)
from reasoning_trading.lambda_arch.speed_layer import (
    DecisionSource,
    RealtimeDecision,
    SpeedLayer,
    SpeedLayerConfig,
    SpeedLayerMetrics,
)

if TYPE_CHECKING:
    from reasoning_trading.core.state import TradingState
    from reasoning_trading.policy.network import PolicyNetwork


class EnhancedSpeedLayerConfig(BaseSettings):
    """Configuration for enhanced speed layer."""

    model_config = SettingsConfigDict(
        env_prefix="ENHANCED_SPEED_",
        case_sensitive=False,
        extra="ignore",
    )

    # RAG/CAG integration
    enable_hierarchical_cag: bool = Field(
        default=True,
        description="Enable hierarchical CAG for decisions",
    )
    enable_pattern_rag: bool = Field(
        default=True,
        description="Enable pattern RAG retrieval",
    )
    enable_strategy_rag: bool = Field(
        default=True,
        description="Enable strategy RAG retrieval",
    )

    # Decision routing thresholds
    cag_confidence_threshold: float = Field(
        default=0.75,
        ge=0.5,
        le=1.0,
        description="Minimum CAG confidence to use cached decision",
    )
    rag_confidence_threshold: float = Field(
        default=0.65,
        ge=0.4,
        le=1.0,
        description="Minimum RAG confidence to use retrieved decision",
    )

    # Latency budgets
    cag_budget_ms: float = Field(
        default=20.0,
        ge=5.0,
        le=100.0,
        description="Budget for CAG lookup",
    )
    rag_budget_ms: float = Field(
        default=50.0,
        ge=10.0,
        le=200.0,
        description="Budget for RAG retrieval",
    )
    total_enhanced_budget_ms: float = Field(
        default=100.0,
        ge=20.0,
        le=500.0,
        description="Total budget for enhanced decision",
    )

    # Fallback behavior
    fallback_to_heuristic: bool = Field(
        default=True,
        description="Fall back to heuristics if all else fails",
    )
    fallback_to_policy: bool = Field(
        default=True,
        description="Fall back to policy network if cache miss",
    )


class EnhancedDecisionSource(DecisionSource):
    """Extended decision sources including RAG/CAG."""

    CAG_L1 = "cag_l1"
    CAG_L2 = "cag_l2"
    CAG_L3 = "cag_l3"
    RAG_PATTERN = "rag_pattern"
    RAG_STRATEGY = "rag_strategy"
    ENSEMBLE = "ensemble"


@dataclass
class EnhancedRealtimeDecision(RealtimeDecision):
    """Extended decision with RAG/CAG metadata."""

    # RAG/CAG info
    cag_level: str = ""
    ensemble_agreement: float = 0.0
    ensemble_sources: list[str] = field(default_factory=list)

    # RAG context
    rag_patterns_used: int = 0
    rag_strategies_used: int = 0
    rag_context_summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        base_dict = super().to_dict()
        base_dict.update(
            {
                "cag_level": self.cag_level,
                "ensemble_agreement": self.ensemble_agreement,
                "ensemble_sources": self.ensemble_sources,
                "rag_patterns_used": self.rag_patterns_used,
                "rag_strategies_used": self.rag_strategies_used,
                "rag_context_summary": self.rag_context_summary,
            }
        )
        return base_dict


class EnhancedSpeedLayer(SpeedLayer):
    """
    Speed Layer enhanced with RAG/CAG capabilities.

    Decision hierarchy:
    1. CAG L1 (exact match) - <1ms target
    2. CAG L2 (semantic) - <10ms target
    3. CAG L3/RAG (retrieval) - <50ms target
    4. Policy network - <5ms target
    5. Heuristic fallback - <1ms target
    """

    def __init__(
        self,
        base_config: SpeedLayerConfig | None = None,
        enhanced_config: EnhancedSpeedLayerConfig | None = None,
        hierarchical_cag: HierarchicalCAG | None = None,
        policy_network: PolicyNetwork | None = None,
    ):
        super().__init__(config=base_config, policy_network=policy_network)
        self.enhanced_config = enhanced_config or EnhancedSpeedLayerConfig()

        # Hierarchical CAG (lazy loaded)
        self._hierarchical_cag = hierarchical_cag

        # Enhanced metrics
        self._cag_hits = 0
        self._rag_hits = 0
        self._ensemble_decisions = 0

    @property
    def hierarchical_cag(self) -> HierarchicalCAG:
        """Lazy load hierarchical CAG."""
        if self._hierarchical_cag is None:
            self._hierarchical_cag = HierarchicalCAG()
        return self._hierarchical_cag

    async def decide(
        self,
        state: TradingState,
        level: str = "tactical",
    ) -> EnhancedRealtimeDecision:
        """
        Make a realtime decision with RAG/CAG enhancement.

        Args:
            state: Current trading state
            level: Decision level (tactical, execution)

        Returns:
            EnhancedRealtimeDecision with action and metadata
        """
        start_time = time.perf_counter()
        decision_level = DecisionLevel(level)

        # Compute state features and hash
        state_features = state.to_feature_vector()
        state_hash = self._compute_state_hash(state_features)

        # Step 1: Try hierarchical CAG
        if self.enhanced_config.enable_hierarchical_cag:
            cag_result = await self._try_hierarchical_cag(state, decision_level)

            if cag_result is not None:
                cag_result.latency_ms = (time.perf_counter() - start_time) * 1000
                cag_result.state_hash = state_hash
                self._record_decision(cag_result)
                return cag_result

        # Step 2: Try policy network with RAG context
        elapsed = (time.perf_counter() - start_time) * 1000
        remaining_budget = self.enhanced_config.total_enhanced_budget_ms - elapsed

        if (
            self.policy_network is not None
            and self.enhanced_config.fallback_to_policy
            and remaining_budget > self.config.policy_inference_timeout_ms
        ):
            policy_result = await self._try_policy_with_rag(state, remaining_budget)

            if policy_result is not None:
                policy_result.latency_ms = (time.perf_counter() - start_time) * 1000
                policy_result.state_hash = state_hash
                self._record_decision(policy_result)
                return policy_result

        # Step 3: Heuristic fallback
        if self.enhanced_config.fallback_to_heuristic:
            heuristic_decision = self._heuristic_decision(state, level)
            result = EnhancedRealtimeDecision(
                action_type=heuristic_decision.action_type,
                action_params=heuristic_decision.action_params,
                confidence=heuristic_decision.confidence,
                source=DecisionSource.HEURISTIC,
                latency_ms=(time.perf_counter() - start_time) * 1000,
                state_hash=state_hash,
                regime=heuristic_decision.regime,
            )
            self._record_decision(result)
            return result

        # Default: hold
        return EnhancedRealtimeDecision(
            action_type="hold_position",
            confidence=0.5,
            source=DecisionSource.HEURISTIC,
            latency_ms=(time.perf_counter() - start_time) * 1000,
            state_hash=state_hash,
        )

    async def _try_hierarchical_cag(
        self,
        state: TradingState,
        level: DecisionLevel,
    ) -> EnhancedRealtimeDecision | None:
        """Try to get decision from hierarchical CAG."""
        try:
            async with asyncio.timeout(self.enhanced_config.cag_budget_ms / 1000):
                hier_decision = await self.hierarchical_cag.get_decision(state, level)

                if not hier_decision.found:
                    return None

                # Check confidence threshold
                if hier_decision.confidence < self.enhanced_config.cag_confidence_threshold:
                    # Low confidence - might use but with caution
                    pass

                self._cag_hits += 1
                if len(hier_decision.ensemble_sources) > 1:
                    self._ensemble_decisions += 1

                # Map cache level to source
                source = self._map_cache_level_to_source(hier_decision.cache_level)

                return EnhancedRealtimeDecision(
                    action_type=self._map_direction_to_action(hier_decision.action_direction),
                    action_params=hier_decision.action_params,
                    confidence=hier_decision.confidence,
                    source=source,
                    alternatives=self._extract_alternatives(hier_decision),
                    regime=state.market_regime.value,
                    cag_level=hier_decision.cache_level.value,
                    ensemble_agreement=hier_decision.ensemble_agreement,
                    ensemble_sources=[s.source_name for s in hier_decision.ensemble_sources],
                    rag_patterns_used=sum(
                        1
                        for s in hier_decision.ensemble_sources
                        if "pattern" in s.source_name
                    ),
                    rag_strategies_used=sum(
                        1
                        for s in hier_decision.ensemble_sources
                        if "strategy" in s.source_name
                    ),
                    rag_context_summary=hier_decision.reasoning[:200],
                )

        except asyncio.TimeoutError:
            return None
        except Exception:
            return None

    async def _try_policy_with_rag(
        self,
        state: TradingState,
        budget_ms: float,
    ) -> EnhancedRealtimeDecision | None:
        """Try policy network with RAG context."""
        try:
            async with asyncio.timeout(budget_ms / 1000):
                # Get RAG context if enabled
                rag_context = []

                if self.enhanced_config.enable_pattern_rag:
                    patterns = await self.hierarchical_cag.pattern_rag.retrieve_similar_patterns(
                        state, top_k=2, successful_only=True
                    )
                    rag_context.extend(
                        [
                            f"Similar pattern: {p.action_direction} (Sharpe={p.outcome_sharpe:.2f})"
                            for p, _ in patterns
                        ]
                    )

                if self.enhanced_config.enable_strategy_rag:
                    strategies = (
                        await self.hierarchical_cag.strategy_rag.retrieve_similar_strategies(
                            state, min_sharpe=0.5, top_k=2
                        )
                    )
                    rag_context.extend(
                        [
                            f"Similar strategy: {s.best_action} (Sharpe={s.outcome_sharpe:.2f})"
                            for s, _ in strategies
                        ]
                    )

                # Run policy network
                state_features = state.to_feature_vector()
                output = self.policy_network.predict(state_features)

                best_action = output.best_action
                if best_action:
                    return EnhancedRealtimeDecision(
                        action_type=best_action,
                        confidence=output.max_prob,
                        source=DecisionSource.POLICY_NETWORK,
                        alternatives=output.get_top_k_actions(3),
                        regime=state.market_regime.value,
                        rag_context_summary="; ".join(rag_context) if rag_context else "",
                        rag_patterns_used=len(
                            [c for c in rag_context if "pattern" in c.lower()]
                        ),
                        rag_strategies_used=len(
                            [c for c in rag_context if "strategy" in c.lower()]
                        ),
                    )

        except asyncio.TimeoutError:
            return None
        except Exception:
            return None

        return None

    def _map_cache_level_to_source(self, level) -> DecisionSource:
        """Map cache level to decision source."""
        from reasoning_trading.cag.base import CacheLevel

        mapping = {
            CacheLevel.L1_EXACT: DecisionSource.CACHE_HIT,
            CacheLevel.L2_SEMANTIC: DecisionSource.CACHE_HIT,
            CacheLevel.L3_RAG: DecisionSource.CACHE_HIT,
        }
        return mapping.get(level, DecisionSource.CACHE_HIT)

    def _map_direction_to_action(self, direction: str) -> str:
        """Map action direction to action type."""
        mapping = {
            "buy": "enter_long_position",
            "sell": "exit_long_position",
            "hold": "hold_position",
            "short": "enter_short_position",
            "cover": "exit_short_position",
        }
        return mapping.get(direction.lower(), "hold_position")

    def _extract_alternatives(
        self,
        decision: HierarchicalDecision,
    ) -> list[tuple[str, float]]:
        """Extract alternative actions from ensemble sources."""
        alternatives = []
        seen_actions = {decision.action_direction}

        for source in decision.ensemble_sources:
            if source.action_direction not in seen_actions:
                alternatives.append(
                    (
                        self._map_direction_to_action(source.action_direction),
                        source.confidence,
                    )
                )
                seen_actions.add(source.action_direction)

        return alternatives[:3]

    def get_enhanced_metrics(self) -> dict[str, Any]:
        """Get enhanced metrics including RAG/CAG stats."""
        base_metrics = self.get_metrics().to_dict()

        total = base_metrics.get("total_decisions", 0) or 1

        base_metrics.update(
            {
                "cag_hits": self._cag_hits,
                "cag_hit_rate": self._cag_hits / total,
                "rag_hits": self._rag_hits,
                "rag_hit_rate": self._rag_hits / total,
                "ensemble_decisions": self._ensemble_decisions,
                "ensemble_rate": self._ensemble_decisions / total,
            }
        )

        # Add CAG stats if available
        if self._hierarchical_cag is not None:
            base_metrics["cag_stats"] = self.hierarchical_cag.get_ensemble_stats()

        return base_metrics

    def reset_enhanced_metrics(self) -> None:
        """Reset enhanced metrics."""
        self.reset_metrics()
        self._cag_hits = 0
        self._rag_hits = 0
        self._ensemble_decisions = 0

    async def cache_outcome(
        self,
        state: TradingState,
        action,  # TradingAction
        outcome: dict[str, float],
        reasoning: str = "",
    ) -> None:
        """
        Cache a decision outcome for future use.

        Args:
            state: Trading state at decision time
            action: Action taken
            outcome: Outcome metrics (returns, sharpe, etc.)
            reasoning: Reasoning text
        """
        await self.hierarchical_cag.cache_decision_outcome(state, action, outcome, reasoning)

        # Update adaptive weights if applicable
        success = outcome.get("sharpe", 0) >= 0.5
        if hasattr(self.hierarchical_cag, "update_adaptive_weights"):
            # Update based on which source was used
            self.hierarchical_cag.update_adaptive_weights("decision_cache", success)
