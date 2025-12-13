"""
Lambda Architecture Coordinator.

Orchestrates batch and speed layers with regime-triggered recomputation:
- Monitors market regime changes
- Triggers batch recomputation when regime shifts
- Routes decisions to appropriate layer
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable

import numpy as np
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from reasoning_trading.lambda_arch.batch_layer import BatchLayer, BatchLayerConfig, BatchResult
from reasoning_trading.lambda_arch.speed_layer import SpeedLayer, SpeedLayerConfig, RealtimeDecision
from reasoning_trading.lambda_arch.serving_layer import ServingLayer, ServingLayerConfig

if TYPE_CHECKING:
    from reasoning_trading.core.state import TradingState, MarketRegime
    from reasoning_trading.hierarchical.tree import HierarchicalMCTSTree
    from reasoning_trading.policy.network import PolicyNetwork


class RegimeChangeAction(str, Enum):
    """Action to take on regime change."""

    TRIGGER_BATCH = "trigger_batch"
    INVALIDATE_CACHE = "invalidate_cache"
    UPDATE_POLICIES = "update_policies"
    ALERT_ONLY = "alert_only"


class LambdaConfig(BaseSettings):
    """Configuration for Lambda coordinator."""

    model_config = SettingsConfigDict(
        env_prefix="LAMBDA_",
        case_sensitive=False,
        extra="ignore",
    )

    # Regime detection
    regime_change_threshold: float = Field(
        default=0.7,
        ge=0.5,
        le=0.95,
        description="Confidence threshold for regime change",
    )
    regime_check_interval_seconds: int = Field(
        default=60,
        ge=10,
        le=3600,
        description="Interval between regime checks",
    )
    min_regime_duration_seconds: int = Field(
        default=300,
        ge=60,
        le=3600,
        description="Minimum time before regime can change",
    )

    # Layer preferences
    prefer_speed_layer: bool = Field(
        default=True,
        description="Prefer speed layer when possible",
    )
    fallback_to_batch: bool = Field(
        default=True,
        description="Fall back to batch results if speed layer fails",
    )

    # Recomputation triggers
    volatile_triggers_recompute: bool = Field(
        default=True,
        description="Trigger batch recompute on volatile regime",
    )
    significant_move_pct: float = Field(
        default=0.03,
        ge=0.01,
        le=0.20,
        description="Percent move that triggers recomputation",
    )


@dataclass
class RegimeTrigger:
    """Information about a regime change trigger."""

    previous_regime: str
    new_regime: str
    confidence: float
    action: RegimeChangeAction

    triggered_at: datetime = field(default_factory=datetime.now)
    batch_job_id: str | None = None
    completed: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "previous_regime": self.previous_regime,
            "new_regime": self.new_regime,
            "confidence": self.confidence,
            "action": self.action.value,
            "triggered_at": self.triggered_at.isoformat(),
            "batch_job_id": self.batch_job_id,
            "completed": self.completed,
        }


class LambdaCoordinator:
    """
    Coordinator for Lambda Architecture.

    Orchestrates:
    - Batch layer: Strategic overnight planning
    - Speed layer: Real-time tactical decisions
    - Serving layer: Policy caching
    - Regime detection: Triggers between layers
    """

    def __init__(
        self,
        config: LambdaConfig | None = None,
        batch_config: BatchLayerConfig | None = None,
        speed_config: SpeedLayerConfig | None = None,
        serving_config: ServingLayerConfig | None = None,
        mcts_tree: HierarchicalMCTSTree | None = None,
        policy_network: PolicyNetwork | None = None,
        regime_detector: Callable[[TradingState], tuple[str, float]] | None = None,
    ):
        """Initialize Lambda coordinator."""
        self.config = config or LambdaConfig()

        # Initialize layers
        self.batch_layer = BatchLayer(batch_config, mcts_tree)
        self.serving_layer = ServingLayer(serving_config)
        self.speed_layer = SpeedLayer(
            speed_config,
            policy_network,
            self.serving_layer.cache,
        )

        # Regime detection
        self.regime_detector = regime_detector or self._default_regime_detector
        self._current_regime: str = "unknown"
        self._regime_confidence: float = 0.0
        self._regime_since: datetime = datetime.now()

        # Trigger history
        self._triggers: list[RegimeTrigger] = []

        # Background task
        self._monitor_task: asyncio.Task | None = None
        self._is_running = False

    async def decide(
        self,
        state: TradingState,
        level: str = "tactical",
    ) -> RealtimeDecision:
        """
        Make a trading decision for the given state.

        Routes to appropriate layer based on configuration and regime.

        Args:
            state: Current trading state
            level: Decision level

        Returns:
            RealtimeDecision from the appropriate layer
        """
        # Check regime
        await self._check_regime(state)

        # Try speed layer first if preferred
        if self.config.prefer_speed_layer:
            decision = await self.speed_layer.decide(state, level)

            # Check if we should supplement with batch results
            if decision.confidence < 0.5 and self.config.fallback_to_batch:
                batch_result = self.batch_layer.get_latest_result()
                if batch_result is not None:
                    symbol = state.symbol
                    if symbol in batch_result.strategic_policies:
                        policy = batch_result.strategic_policies[symbol]
                        if policy:
                            best_action = max(policy.items(), key=lambda x: x[1])
                            decision.alternatives.insert(
                                0,
                                (f"batch:{best_action[0]}", best_action[1]),
                            )

            return decision

        # Use batch layer results directly
        batch_result = self.batch_layer.get_latest_result()
        if batch_result is not None:
            symbol = state.symbol
            if symbol in batch_result.strategic_policies:
                policy = batch_result.strategic_policies[symbol]
                if policy:
                    best_action = max(policy.items(), key=lambda x: x[1])
                    return RealtimeDecision(
                        action_type=best_action[0],
                        confidence=best_action[1],
                        source="batch",
                    )

        # Fallback to speed layer
        return await self.speed_layer.decide(state, level)

    async def decide_batch(
        self,
        states: list[TradingState],
        level: str = "tactical",
    ) -> list[RealtimeDecision]:
        """
        Make decisions for multiple states.

        Args:
            states: List of trading states
            level: Decision level

        Returns:
            List of RealtimeDecision objects
        """
        return await self.speed_layer.decide_batch(states, level)

    async def trigger_batch_recompute(
        self,
        states: dict[str, TradingState],
        reason: str = "manual",
    ) -> str:
        """
        Trigger batch layer recomputation.

        Args:
            states: States to recompute
            reason: Reason for recomputation

        Returns:
            Job ID
        """
        from reasoning_trading.lambda_arch.batch_layer import BatchJob, BatchJobType

        job = BatchJob(
            job_type=BatchJobType.STRATEGIC_MCTS,
            symbols=list(states.keys()),
            parameters={"reason": reason},
        )

        job_id = await self.batch_layer.submit_job(job)

        # Run the job
        result = await self.batch_layer.run_strategic_mcts(states)

        # Update serving layer cache
        for symbol, policy in result.strategic_policies.items():
            if symbol in states:
                state = states[symbol]
                state_features = state.to_feature_vector()
                state_hash = self._compute_state_hash(state_features)

                await self.serving_layer.store_policy(
                    state_hash=state_hash,
                    policy={
                        "action_type": max(policy.items(), key=lambda x: x[1])[0] if policy else "hold",
                        "probs": policy,
                        "value": result.strategic_values.get(symbol, 0),
                        "confidence": max(policy.values()) if policy else 0.5,
                    },
                    state_features=state_features,
                    regime=self._current_regime,
                )

        return job_id

    async def _check_regime(self, state: TradingState) -> None:
        """Check and update market regime."""
        new_regime, confidence = self.regime_detector(state)

        # Check if regime changed
        if new_regime != self._current_regime:
            # Check confidence threshold
            if confidence >= self.config.regime_change_threshold:
                # Check minimum duration
                time_in_regime = (datetime.now() - self._regime_since).total_seconds()
                if time_in_regime >= self.config.min_regime_duration_seconds:
                    await self._handle_regime_change(
                        self._current_regime,
                        new_regime,
                        confidence,
                    )

        self._regime_confidence = confidence

    async def _handle_regime_change(
        self,
        old_regime: str,
        new_regime: str,
        confidence: float,
    ) -> None:
        """Handle a regime change event."""
        # Determine action
        if new_regime in ["volatile", "high_volatility"]:
            if self.config.volatile_triggers_recompute:
                action = RegimeChangeAction.TRIGGER_BATCH
            else:
                action = RegimeChangeAction.INVALIDATE_CACHE
        elif old_regime in ["volatile", "high_volatility"]:
            action = RegimeChangeAction.UPDATE_POLICIES
        else:
            action = RegimeChangeAction.INVALIDATE_CACHE

        # Create trigger
        trigger = RegimeTrigger(
            previous_regime=old_regime,
            new_regime=new_regime,
            confidence=confidence,
            action=action,
        )

        self._triggers.append(trigger)

        # Execute action
        if action == RegimeChangeAction.TRIGGER_BATCH:
            # Would need states to recompute
            pass
        elif action == RegimeChangeAction.INVALIDATE_CACHE:
            await self.serving_layer.cache.clear()
        elif action == RegimeChangeAction.UPDATE_POLICIES:
            # Policies will be updated on next batch run
            pass

        trigger.completed = True

        # Update state
        self._current_regime = new_regime
        self._regime_since = datetime.now()

    def _default_regime_detector(
        self,
        state: TradingState,
    ) -> tuple[str, float]:
        """
        Default regime detection based on technical indicators.

        Args:
            state: Trading state

        Returns:
            Tuple of (regime_name, confidence)
        """
        from reasoning_trading.core.state import MarketRegime

        # Use existing regime from state
        regime = state.market_regime

        # Estimate confidence from indicators
        tech = state.technical_indicators
        adx = tech.adx_14 or 25
        volatility = tech.volatility_20 or 0.02

        if volatility > 0.03:
            return "volatile", min(volatility / 0.05, 1.0)
        elif adx > 30:
            if (tech.sma_20 or 0) > (tech.sma_50 or 0):
                return "trending_up", adx / 100
            else:
                return "trending_down", adx / 100
        elif adx < 20:
            return "mean_reverting", (25 - adx) / 25
        else:
            return regime.value, 0.5

    def _compute_state_hash(self, features: np.ndarray) -> str:
        """Compute hash for state."""
        import hashlib

        discretized = np.round(features, 2)
        return hashlib.md5(discretized.tobytes()).hexdigest()[:16]

    async def start_monitoring(self) -> None:
        """Start background regime monitoring."""
        if self._is_running:
            return

        self._is_running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())

    async def stop_monitoring(self) -> None:
        """Stop background monitoring."""
        self._is_running = False
        if self._monitor_task is not None:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

    async def _monitor_loop(self) -> None:
        """Background monitoring loop."""
        while self._is_running:
            await asyncio.sleep(self.config.regime_check_interval_seconds)
            # Would check regime here if we had a state source

    def get_statistics(self) -> dict[str, Any]:
        """Get coordinator statistics."""
        return {
            "current_regime": self._current_regime,
            "regime_confidence": self._regime_confidence,
            "regime_since": self._regime_since.isoformat(),
            "total_triggers": len(self._triggers),
            "recent_triggers": [t.to_dict() for t in self._triggers[-10:]],
            "batch_layer": self.batch_layer.get_statistics(),
            "speed_layer": self.speed_layer.get_metrics().to_dict(),
            "serving_layer": self.serving_layer.get_statistics(),
        }

    def get_regime_history(self) -> list[dict[str, Any]]:
        """Get history of regime changes."""
        return [t.to_dict() for t in self._triggers]
