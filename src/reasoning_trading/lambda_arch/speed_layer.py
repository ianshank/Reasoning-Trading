"""
Speed Layer for Lambda Architecture.

Provides sub-100ms tactical/execution decisions:
- Fast policy network inference
- Real-time regime detection
- Heuristic fallback when cache misses
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

import numpy as np
from numpy.typing import NDArray
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

if TYPE_CHECKING:
    from reasoning_trading.core.state import TradingState
    from reasoning_trading.hierarchical.levels import LevelAction
    from reasoning_trading.policy.network import PolicyNetwork


class DecisionSource(str, Enum):
    """Source of a realtime decision."""

    POLICY_NETWORK = "policy_network"
    CACHE_HIT = "cache_hit"
    HEURISTIC = "heuristic"
    MCTS_LITE = "mcts_lite"


class SpeedLayerConfig(BaseSettings):
    """Configuration for speed layer."""

    model_config = SettingsConfigDict(
        env_prefix="SPEED_",
        case_sensitive=False,
        extra="ignore",
    )

    # Latency targets
    target_latency_ms: float = Field(
        default=10.0,
        ge=1.0,
        le=1000.0,
        description="Target decision latency in ms",
    )
    max_latency_ms: float = Field(
        default=100.0,
        ge=10.0,
        le=5000.0,
        description="Maximum acceptable latency",
    )

    # Policy network settings
    policy_inference_timeout_ms: float = Field(
        default=5.0,
        ge=1.0,
        le=50.0,
        description="Policy network inference timeout",
    )
    use_batched_inference: bool = Field(
        default=True,
        description="Enable batched inference",
    )
    max_batch_size: int = Field(
        default=32,
        ge=1,
        le=256,
        description="Maximum batch size for inference",
    )
    batch_wait_timeout_ms: float = Field(
        default=2.0,
        ge=0.5,
        le=20.0,
        description="Wait time for batch accumulation",
    )

    # MCTS lite settings
    lite_simulations: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Simulations for lite MCTS",
    )
    lite_timeout_ms: float = Field(
        default=20.0,
        ge=5.0,
        le=100.0,
        description="Timeout for lite MCTS",
    )

    # Fallback settings
    enable_heuristic_fallback: bool = Field(
        default=True,
        description="Enable heuristic fallback",
    )
    cache_miss_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Similarity threshold for cache hit",
    )


@dataclass
class RealtimeDecision:
    """Result of a realtime decision."""

    # Action recommendation
    action_type: str
    action_params: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0

    # Source and timing
    source: DecisionSource = DecisionSource.HEURISTIC
    latency_ms: float = 0.0

    # Alternative actions
    alternatives: list[tuple[str, float]] = field(default_factory=list)

    # Metadata
    state_hash: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    regime: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "action_type": self.action_type,
            "action_params": self.action_params,
            "confidence": self.confidence,
            "source": self.source.value,
            "latency_ms": self.latency_ms,
            "alternatives": self.alternatives,
            "state_hash": self.state_hash,
            "timestamp": self.timestamp.isoformat(),
            "regime": self.regime,
        }


@dataclass
class SpeedLayerMetrics:
    """Metrics for speed layer performance."""

    # Latency statistics
    avg_latency_ms: float = 0.0
    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    max_latency_ms: float = 0.0

    # Decision source breakdown
    policy_network_pct: float = 0.0
    cache_hit_pct: float = 0.0
    heuristic_pct: float = 0.0
    mcts_lite_pct: float = 0.0

    # Volume
    total_decisions: int = 0
    decisions_per_second: float = 0.0

    # Quality
    avg_confidence: float = 0.0

    # Time range
    start_time: datetime = field(default_factory=datetime.now)
    end_time: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "avg_latency_ms": self.avg_latency_ms,
            "p50_latency_ms": self.p50_latency_ms,
            "p95_latency_ms": self.p95_latency_ms,
            "p99_latency_ms": self.p99_latency_ms,
            "max_latency_ms": self.max_latency_ms,
            "policy_network_pct": self.policy_network_pct,
            "cache_hit_pct": self.cache_hit_pct,
            "heuristic_pct": self.heuristic_pct,
            "mcts_lite_pct": self.mcts_lite_pct,
            "total_decisions": self.total_decisions,
            "decisions_per_second": self.decisions_per_second,
            "avg_confidence": self.avg_confidence,
        }


class SpeedLayer:
    """
    Speed Layer for realtime trading decisions.

    Provides sub-100ms decisions using:
    1. Fast policy network inference (primary)
    2. Policy cache lookup (fastest)
    3. Lite MCTS (when high confidence needed)
    4. Heuristic fallback (guaranteed fast)
    """

    def __init__(
        self,
        config: SpeedLayerConfig | None = None,
        policy_network: PolicyNetwork | None = None,
        cache: Any | None = None,  # PolicyCache from serving_layer
    ):
        """Initialize speed layer."""
        self.config = config or SpeedLayerConfig()
        self.policy_network = policy_network
        self.cache = cache

        # Metrics tracking
        self._latencies: list[float] = []
        self._sources: list[DecisionSource] = []
        self._confidences: list[float] = []
        self._start_time = datetime.now()

        # Batching
        self._pending_requests: list[tuple[NDArray, asyncio.Future]] = []
        self._batch_task: asyncio.Task | None = None

    async def decide(
        self,
        state: TradingState,
        level: str = "tactical",
    ) -> RealtimeDecision:
        """
        Make a realtime decision for the given state.

        Args:
            state: Current trading state
            level: Decision level (tactical, execution)

        Returns:
            RealtimeDecision with action and metadata
        """
        start_time = time.perf_counter()

        # Compute state features and hash
        state_features = state.to_feature_vector()
        state_hash = self._compute_state_hash(state_features)

        # Try cache first (fastest)
        if self.cache is not None:
            cached = await self.cache.get(state_hash)
            if cached is not None:
                latency = (time.perf_counter() - start_time) * 1000
                decision = RealtimeDecision(
                    action_type=cached.get("action_type", "hold"),
                    action_params=cached.get("params", {}),
                    confidence=cached.get("confidence", 0.8),
                    source=DecisionSource.CACHE_HIT,
                    latency_ms=latency,
                    state_hash=state_hash,
                    regime=cached.get("regime"),
                )
                self._record_decision(decision)
                return decision

        # Try policy network
        if self.policy_network is not None:
            try:
                async with asyncio.timeout(self.config.policy_inference_timeout_ms / 1000):
                    output = self.policy_network.predict(state_features)

                    best_action = output.best_action
                    if best_action:
                        latency = (time.perf_counter() - start_time) * 1000

                        decision = RealtimeDecision(
                            action_type=best_action,
                            confidence=output.max_prob,
                            source=DecisionSource.POLICY_NETWORK,
                            latency_ms=latency,
                            alternatives=output.get_top_k_actions(5),
                            state_hash=state_hash,
                        )
                        self._record_decision(decision)
                        return decision

            except asyncio.TimeoutError:
                pass  # Fall through to heuristic
            except Exception:
                pass  # Fall through to heuristic

        # Heuristic fallback
        if self.config.enable_heuristic_fallback:
            decision = self._heuristic_decision(state, level)
            decision.latency_ms = (time.perf_counter() - start_time) * 1000
            decision.state_hash = state_hash
            self._record_decision(decision)
            return decision

        # Default: hold
        latency = (time.perf_counter() - start_time) * 1000
        decision = RealtimeDecision(
            action_type="hold_position",
            confidence=0.5,
            source=DecisionSource.HEURISTIC,
            latency_ms=latency,
            state_hash=state_hash,
        )
        self._record_decision(decision)
        return decision

    async def decide_batch(
        self,
        states: list[TradingState],
        level: str = "tactical",
    ) -> list[RealtimeDecision]:
        """
        Make realtime decisions for multiple states.

        Args:
            states: List of trading states
            level: Decision level

        Returns:
            List of RealtimeDecision objects
        """
        if not states:
            return []

        start_time = time.perf_counter()

        # Prepare batch
        state_features = [s.to_feature_vector() for s in states]
        state_hashes = [self._compute_state_hash(f) for f in state_features]

        decisions: list[RealtimeDecision] = []

        # Try batch policy inference
        if self.policy_network is not None:
            try:
                async with asyncio.timeout(self.config.policy_inference_timeout_ms / 1000):
                    outputs = await self.policy_network.predict_batch(state_features)

                    for i, output in enumerate(outputs):
                        best_action = output.best_action
                        if best_action:
                            decisions.append(RealtimeDecision(
                                action_type=best_action,
                                confidence=output.max_prob,
                                source=DecisionSource.POLICY_NETWORK,
                                alternatives=output.get_top_k_actions(3),
                                state_hash=state_hashes[i],
                            ))
                        else:
                            # Heuristic for this state
                            decisions.append(self._heuristic_decision(states[i], level))
                            decisions[-1].state_hash = state_hashes[i]

            except (asyncio.TimeoutError, Exception):
                # Fall back to individual heuristics
                decisions = [
                    self._heuristic_decision(s, level)
                    for s in states
                ]
                for i, d in enumerate(decisions):
                    d.state_hash = state_hashes[i]

        else:
            # Heuristic for all
            decisions = [self._heuristic_decision(s, level) for s in states]
            for i, d in enumerate(decisions):
                d.state_hash = state_hashes[i]

        # Record timing
        total_latency = (time.perf_counter() - start_time) * 1000
        per_decision_latency = total_latency / len(states)

        for decision in decisions:
            decision.latency_ms = per_decision_latency
            self._record_decision(decision)

        return decisions

    def _heuristic_decision(
        self,
        state: TradingState,
        level: str,
    ) -> RealtimeDecision:
        """
        Make a heuristic decision based on technical indicators.

        Args:
            state: Trading state
            level: Decision level

        Returns:
            RealtimeDecision from heuristic
        """
        # Get signals
        rsi = state.technical_indicators.rsi_14 or 50
        consensus = state.analyst_signals.weighted_consensus()
        position_pct = state.portfolio.get_position_pct(state.symbol)

        from reasoning_trading.core.state import MarketRegime

        # Determine action based on signals
        if level == "execution":
            # Execution level: order type decisions
            if rsi > 70 and position_pct > 0:
                action_type = "close_position"
                confidence = (rsi - 70) / 30 * 0.5 + 0.5
            elif rsi < 30 and position_pct < 0.2:
                action_type = "execute_market_order"
                confidence = (30 - rsi) / 30 * 0.5 + 0.5
            else:
                action_type = "wait_for_entry"
                confidence = 0.5 + abs(rsi - 50) / 100

        else:
            # Tactical level: position decisions
            if consensus > 0.3 and rsi < 70:
                if position_pct < 0.1:
                    action_type = "enter_long_position"
                else:
                    action_type = "scale_in_position"
                confidence = consensus * 0.5 + 0.5

            elif consensus < -0.3 and rsi > 30:
                if position_pct > 0:
                    action_type = "exit_long_position"
                else:
                    action_type = "wait_for_entry"
                confidence = abs(consensus) * 0.5 + 0.5

            elif state.market_regime == MarketRegime.VOLATILE:
                action_type = "hold_position"
                confidence = 0.6

            else:
                action_type = "hold_position"
                confidence = 0.5

        return RealtimeDecision(
            action_type=action_type,
            confidence=confidence,
            source=DecisionSource.HEURISTIC,
            regime=state.market_regime.value,
        )

    def _compute_state_hash(self, features: NDArray[np.float64]) -> str:
        """Compute hash for state lookup."""
        import hashlib

        discretized = np.round(features, 2)
        return hashlib.md5(discretized.tobytes()).hexdigest()[:16]

    def _record_decision(self, decision: RealtimeDecision) -> None:
        """Record decision for metrics."""
        self._latencies.append(decision.latency_ms)
        self._sources.append(decision.source)
        self._confidences.append(decision.confidence)

        # Keep last 10000 decisions
        max_history = 10000
        if len(self._latencies) > max_history:
            self._latencies = self._latencies[-max_history:]
            self._sources = self._sources[-max_history:]
            self._confidences = self._confidences[-max_history:]

    def get_metrics(self) -> SpeedLayerMetrics:
        """Get current performance metrics."""
        if not self._latencies:
            return SpeedLayerMetrics()

        latencies = np.array(self._latencies)

        # Source breakdown
        source_counts = {s: 0 for s in DecisionSource}
        for source in self._sources:
            source_counts[source] += 1
        total = len(self._sources)

        # Time range
        elapsed = (datetime.now() - self._start_time).total_seconds()

        return SpeedLayerMetrics(
            avg_latency_ms=float(np.mean(latencies)),
            p50_latency_ms=float(np.percentile(latencies, 50)),
            p95_latency_ms=float(np.percentile(latencies, 95)),
            p99_latency_ms=float(np.percentile(latencies, 99)),
            max_latency_ms=float(np.max(latencies)),
            policy_network_pct=source_counts[DecisionSource.POLICY_NETWORK] / total * 100,
            cache_hit_pct=source_counts[DecisionSource.CACHE_HIT] / total * 100,
            heuristic_pct=source_counts[DecisionSource.HEURISTIC] / total * 100,
            mcts_lite_pct=source_counts[DecisionSource.MCTS_LITE] / total * 100,
            total_decisions=total,
            decisions_per_second=total / max(elapsed, 1),
            avg_confidence=float(np.mean(self._confidences)),
            start_time=self._start_time,
            end_time=datetime.now(),
        )

    def reset_metrics(self) -> None:
        """Reset metrics tracking."""
        self._latencies.clear()
        self._sources.clear()
        self._confidences.clear()
        self._start_time = datetime.now()
