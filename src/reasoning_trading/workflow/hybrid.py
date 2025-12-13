"""
Hybrid batch/realtime trading architecture.

Implements the Lambda architecture pattern combining:
- Batch layer: Full MCTS exploration overnight
- Speed layer: Fast policy lookup for real-time decisions
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

import structlog

try:
    import redis.asyncio as aioredis
except ImportError:
    aioredis = None

from reasoning_trading.config import Settings, get_settings
from reasoning_trading.core.actions import ActionSpace, TradingAction, TradingDirection
from reasoning_trading.core.state import TradingState
from reasoning_trading.mcts.tree import MCTSConfig, MCTSResult, MCTSTree
from reasoning_trading.services.adapter import TradingServiceAdapter

logger = structlog.get_logger(__name__)


@dataclass
class PolicyEntry:
    """Cached policy entry from batch planning."""

    action: TradingAction
    value: float
    confidence: float
    computed_at: datetime
    expires_at: datetime
    state_hash: str

    def is_expired(self) -> bool:
        """Check if this entry has expired."""
        return datetime.now() > self.expires_at

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "action": self.action.to_dict(),
            "value": self.value,
            "confidence": self.confidence,
            "computed_at": self.computed_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "state_hash": self.state_hash,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PolicyEntry:
        """Deserialize from dictionary."""
        return cls(
            action=TradingAction.from_dict(data["action"]),
            value=data["value"],
            confidence=data["confidence"],
            computed_at=datetime.fromisoformat(data["computed_at"]),
            expires_at=datetime.fromisoformat(data["expires_at"]),
            state_hash=data["state_hash"],
        )


@dataclass
class HybridTradingArchitecture:
    """
    Lambda architecture for MCTS-enhanced trading.

    Combines batch planning (overnight full MCTS) with real-time
    policy lookup for low-latency trading decisions.

    Batch Layer:
    - Runs overnight or on schedule
    - Full MCTS exploration (thousands of simulations)
    - Pre-computes optimal actions for discretized states
    - Caches results in Redis

    Speed Layer:
    - Serves real-time trading requests
    - Looks up cached policy first
    - Falls back to quick MCTS if cache miss
    - Strict time budget for decisions
    """

    settings: Settings = field(default_factory=get_settings)
    trading_adapter: TradingServiceAdapter | None = None
    action_space: ActionSpace | None = None

    # Batch layer config
    batch_simulations: int = 10000
    batch_rollout_horizon: int = 30

    # Speed layer config
    realtime_simulations: int = 100
    realtime_timeout_ms: int = 500

    # Cache config
    cache_ttl_hours: int = 24
    state_discretization_bins: int = 10

    _redis: Any = None
    _local_cache: dict[str, PolicyEntry] = field(default_factory=dict)

    async def initialize(self) -> None:
        """Initialize connections and adapters."""
        if self.trading_adapter is None:
            self.trading_adapter = TradingServiceAdapter(
                mode=self.settings.trading.trading_mode,
                settings=self.settings,
            )
            await self.trading_adapter._initialize()

        if self.action_space is None:
            self.action_space = ActionSpace(
                allow_shorts=self.settings.features.allow_shorts,
                max_position_size=self.settings.risk.max_position_size_fraction,
            )

        # Initialize Redis connection
        if aioredis is not None:
            try:
                self._redis = await aioredis.from_url(
                    self.settings.cache.redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                )
                await self._redis.ping()
                logger.info("Redis connected", url=self.settings.cache.redis_url)
            except Exception as e:
                logger.warning("Redis connection failed, using local cache", error=str(e))
                self._redis = None

    async def cleanup(self) -> None:
        """Cleanup connections."""
        if self._redis is not None:
            await self._redis.close()

        if self.trading_adapter is not None:
            await self.trading_adapter._cleanup()

    async def nightly_planning(
        self,
        symbols: list[str],
        progress_callback: Any = None,
    ) -> dict[str, MCTSResult]:
        """
        Run batch MCTS planning for all symbols.

        This should be scheduled to run overnight when markets are closed.

        Args:
            symbols: List of symbols to plan for
            progress_callback: Optional callback for progress updates

        Returns:
            Dictionary of symbol -> MCTSResult
        """
        logger.info("Starting nightly planning", symbols=symbols)

        results = {}

        for i, symbol in enumerate(symbols):
            try:
                result = await self._full_mcts_search(symbol)
                results[symbol] = result

                # Cache the policy
                await self._cache_policy(symbol, result)

                if progress_callback:
                    progress_callback(symbol, i + 1, len(symbols))

                logger.info(
                    "Completed planning",
                    symbol=symbol,
                    best_action=result.best_action.direction.value if result.best_action else "none",
                    simulations=result.total_simulations,
                )

            except Exception as e:
                logger.error("Planning failed for symbol", symbol=symbol, error=str(e))
                results[symbol] = MCTSResult(best_action=TradingAction.hold())

        logger.info(
            "Nightly planning completed",
            total_symbols=len(symbols),
            successful=len([r for r in results.values() if r.best_action]),
        )

        return results

    async def realtime_decision(
        self,
        symbol: str,
        market_state: dict[str, Any] | None = None,
    ) -> TradingAction:
        """
        Make a real-time trading decision.

        First checks cached policy, then falls back to quick MCTS.

        Args:
            symbol: Trading symbol
            market_state: Current market state (optional)

        Returns:
            Trading action to execute
        """
        # Build or use provided state
        if market_state is None:
            trading_state = await self.trading_adapter.build_trading_state(symbol)
        else:
            trading_state = self._build_state_from_dict(symbol, market_state)

        state_hash = self._compute_state_hash(trading_state)

        # Try cache lookup
        cached = await self._get_cached_policy(symbol, state_hash)
        if cached is not None and not cached.is_expired():
            logger.debug(
                "Using cached policy",
                symbol=symbol,
                confidence=cached.confidence,
            )
            return cached.action

        # Cache miss - run quick MCTS
        logger.debug("Cache miss, running quick MCTS", symbol=symbol)
        return await self._quick_mcts_search(trading_state)

    async def _full_mcts_search(self, symbol: str) -> MCTSResult:
        """Run full MCTS exploration for batch planning."""
        trading_state = await self.trading_adapter.build_trading_state(symbol)

        config = MCTSConfig(
            max_simulations=self.batch_simulations,
            rollout_horizon=self.batch_rollout_horizon,
            exploration_weight=self.settings.mcts.exploration_weight,
            discount_factor=self.settings.mcts.discount_factor,
        )

        tree = MCTSTree(config=config)
        result = await tree.search(trading_state, self.action_space)

        return result

    async def _quick_mcts_search(self, trading_state: TradingState) -> TradingAction:
        """Run quick MCTS with strict time budget."""
        config = MCTSConfig(
            max_simulations=self.realtime_simulations,
            time_budget_ms=self.realtime_timeout_ms,
            rollout_horizon=min(self.batch_rollout_horizon, 10),
            exploration_weight=self.settings.mcts.exploration_weight,
        )

        tree = MCTSTree(config=config)

        try:
            result = await tree.search(trading_state, self.action_space)
            if result.best_action:
                return result.best_action
        except asyncio.TimeoutError:
            logger.warning("Quick MCTS timeout")
        except Exception as e:
            logger.error("Quick MCTS failed", error=str(e))

        # Fallback to simple heuristic
        return self._heuristic_action(trading_state)

    def _heuristic_action(self, state: TradingState) -> TradingAction:
        """Simple heuristic fallback when MCTS fails."""
        consensus = state.analyst_signals.weighted_consensus()

        if consensus > 0.3:
            direction = TradingDirection.BUY
            size = min(0.1, abs(consensus) * 0.2)
        elif consensus < -0.3:
            direction = TradingDirection.SELL
            size = min(0.1, abs(consensus) * 0.2)
        else:
            direction = TradingDirection.HOLD
            size = 0.0

        from reasoning_trading.core.actions import (
            PositionSizeAction,
            StopLossAction,
            TimeHorizon,
        )

        return TradingAction(
            direction=direction,
            position_size=PositionSizeAction(size_fraction=size),
            stop_loss=StopLossAction(stop_loss_pct=self.settings.risk.default_stop_loss_percent),
            time_horizon=TimeHorizon.INTRADAY,
            confidence=abs(consensus),
            reasoning="Heuristic fallback",
        )

    async def _cache_policy(self, symbol: str, result: MCTSResult) -> None:
        """Cache MCTS result as policy."""
        if result.best_action is None:
            return

        state_hash = (
            self._compute_state_hash(result.best_node.state)
            if result.best_node and result.best_node.state
            else "default"
        )

        entry = PolicyEntry(
            action=result.best_action,
            value=result.best_value,
            confidence=result.best_visits / max(result.total_simulations, 1),
            computed_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=self.cache_ttl_hours),
            state_hash=state_hash,
        )

        cache_key = f"policy:{symbol}:{state_hash}"

        # Cache in Redis if available
        if self._redis is not None:
            try:
                await self._redis.setex(
                    cache_key,
                    self.cache_ttl_hours * 3600,
                    json.dumps(entry.to_dict()),
                )
            except Exception as e:
                logger.warning("Redis cache write failed", error=str(e))

        # Also cache locally
        self._local_cache[cache_key] = entry

    async def _get_cached_policy(
        self, symbol: str, state_hash: str
    ) -> PolicyEntry | None:
        """Retrieve cached policy."""
        cache_key = f"policy:{symbol}:{state_hash}"

        # Try local cache first
        if cache_key in self._local_cache:
            return self._local_cache[cache_key]

        # Try Redis
        if self._redis is not None:
            try:
                data = await self._redis.get(cache_key)
                if data:
                    entry = PolicyEntry.from_dict(json.loads(data))
                    self._local_cache[cache_key] = entry
                    return entry
            except Exception as e:
                logger.warning("Redis cache read failed", error=str(e))

        # Try default key (without state hash)
        default_key = f"policy:{symbol}:default"
        if default_key in self._local_cache:
            return self._local_cache[default_key]

        if self._redis is not None:
            try:
                data = await self._redis.get(default_key)
                if data:
                    return PolicyEntry.from_dict(json.loads(data))
            except Exception:
                pass

        return None

    def _compute_state_hash(self, state: TradingState) -> str:
        """
        Compute hash for state lookup.

        Discretizes continuous values to enable cache hits for
        similar states.
        """
        # Discretize key state features
        def discretize(value: float, bins: int = 10) -> int:
            return int(value * bins)

        features = [
            discretize(state.analyst_signals.weighted_consensus() + 1, self.state_discretization_bins),
            discretize(state.technical_indicators.rsi_14 / 100 if state.technical_indicators.rsi_14 else 0.5),
            discretize(state.portfolio.get_position_pct(state.symbol) + 0.5),
            state.market_regime.value,
            state.risk_profile,
        ]

        feature_str = "|".join(str(f) for f in features)
        return hashlib.md5(feature_str.encode()).hexdigest()[:16]

    def _build_state_from_dict(
        self, symbol: str, market_state: dict[str, Any]
    ) -> TradingState:
        """Build TradingState from dictionary."""
        from reasoning_trading.core.state import (
            AnalystSignals,
            PortfolioState,
            TechnicalIndicators,
        )

        return TradingState(
            symbol=symbol,
            timestamp=datetime.now(),
            current_price=market_state.get("current_price", 0.0),
            technical_indicators=TechnicalIndicators(
                **market_state.get("indicators", {})
            ),
            portfolio=PortfolioState(**market_state.get("portfolio", {})),
            analyst_signals=AnalystSignals(**market_state.get("signals", {})),
            risk_profile=market_state.get("risk_profile", "moderate"),
        )

    async def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        stats = {
            "local_cache_size": len(self._local_cache),
            "redis_connected": self._redis is not None,
        }

        if self._redis is not None:
            try:
                info = await self._redis.info("memory")
                stats["redis_memory_used"] = info.get("used_memory_human", "unknown")
            except Exception:
                pass

        return stats

    async def clear_cache(self, symbol: str | None = None) -> int:
        """
        Clear cached policies.

        Args:
            symbol: Clear only for this symbol (all if None)

        Returns:
            Number of entries cleared
        """
        cleared = 0

        if symbol:
            pattern = f"policy:{symbol}:*"
        else:
            pattern = "policy:*"

        # Clear local cache
        keys_to_remove = [k for k in self._local_cache.keys() if k.startswith(pattern.replace("*", ""))]
        for key in keys_to_remove:
            del self._local_cache[key]
            cleared += 1

        # Clear Redis
        if self._redis is not None:
            try:
                async for key in self._redis.scan_iter(pattern):
                    await self._redis.delete(key)
                    cleared += 1
            except Exception as e:
                logger.warning("Redis cache clear failed", error=str(e))

        return cleared
