"""
Hierarchy level definitions for trading MCTS.

Implements the three-level trading hierarchy:
1. Strategic: Portfolio allocation (days/weeks horizon)
2. Tactical: Asset selection and timing (hours/days horizon)
3. Execution: Order execution and trade primitives (seconds/minutes horizon)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import timedelta
from enum import Enum, auto
from typing import TYPE_CHECKING, Any

import numpy as np
from numpy.typing import NDArray
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

if TYPE_CHECKING:
    from reasoning_trading.core.actions import TradingAction
    from reasoning_trading.core.state import TradingState


class HierarchyLevelType(str, Enum):
    """Types of hierarchy levels in trading."""

    STRATEGIC = "strategic"
    TACTICAL = "tactical"
    EXECUTION = "execution"


class HierarchyLevelConfig(BaseSettings):
    """Configuration for hierarchy levels."""

    model_config = SettingsConfigDict(
        env_prefix="HIERARCHY_",
        case_sensitive=False,
        extra="ignore",
    )

    # Strategic level
    strategic_simulations: int = Field(
        default=800,
        ge=100,
        le=10000,
        description="MCTS simulations for strategic level",
    )
    strategic_horizon_days: int = Field(
        default=30,
        ge=1,
        le=365,
        description="Planning horizon for strategic level",
    )

    # Tactical level
    tactical_simulations: int = Field(
        default=200,
        ge=50,
        le=5000,
        description="MCTS simulations for tactical level",
    )
    tactical_horizon_hours: int = Field(
        default=24,
        ge=1,
        le=168,
        description="Planning horizon for tactical level",
    )

    # Execution level
    execution_simulations: int = Field(
        default=50,
        ge=10,
        le=1000,
        description="MCTS simulations for execution level",
    )
    execution_horizon_minutes: int = Field(
        default=30,
        ge=1,
        le=480,
        description="Planning horizon for execution level",
    )

    # State abstraction dimensions
    strategic_state_dim: int = Field(
        default=50,
        ge=10,
        le=500,
        description="Compressed state dimension for strategic level",
    )
    tactical_state_dim: int = Field(
        default=200,
        ge=50,
        le=1000,
        description="State dimension for tactical level",
    )
    execution_state_dim: int = Field(
        default=500,
        ge=100,
        le=2000,
        description="State dimension for execution level",
    )


@dataclass
class LevelAction:
    """Action at a specific hierarchy level."""

    level: HierarchyLevelType
    action_type: str
    parameters: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.5
    subtask_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "level": self.level.value,
            "action_type": self.action_type,
            "parameters": self.parameters,
            "confidence": self.confidence,
            "subtask_id": self.subtask_id,
        }


@dataclass
class LevelState:
    """State representation at a specific hierarchy level."""

    level: HierarchyLevelType
    features: NDArray[np.float64]
    raw_state: TradingState | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def dimension(self) -> int:
        """Get state dimension."""
        return len(self.features)


class HierarchyLevel(ABC):
    """
    Abstract base class for hierarchy levels.

    Each level defines:
    - State abstraction function
    - Action space for that level
    - Transition model
    - Reward function
    """

    def __init__(self, config: HierarchyLevelConfig | None = None):
        """Initialize hierarchy level."""
        self.config = config or HierarchyLevelConfig()

    @property
    @abstractmethod
    def level_type(self) -> HierarchyLevelType:
        """Get the level type."""
        pass

    @property
    @abstractmethod
    def time_horizon(self) -> timedelta:
        """Get the planning time horizon for this level."""
        pass

    @property
    @abstractmethod
    def simulation_budget(self) -> int:
        """Get the MCTS simulation budget for this level."""
        pass

    @property
    @abstractmethod
    def action_types(self) -> list[str]:
        """Get available action types at this level."""
        pass

    @abstractmethod
    def abstract_state(self, state: TradingState) -> LevelState:
        """
        Abstract the trading state for this level.

        Higher levels see more compressed representations.
        """
        pass

    @abstractmethod
    def get_subtasks(self, action: LevelAction, state: LevelState) -> list[LevelAction]:
        """
        Get subtasks for a given action.

        Returns list of actions at the next level down.
        """
        pass

    @abstractmethod
    def is_terminal(self, action: LevelAction) -> bool:
        """Check if action is a primitive (no subtasks)."""
        pass

    @abstractmethod
    def reward(self, state: LevelState, action: LevelAction, next_state: LevelState) -> float:
        """Calculate immediate reward for action at this level."""
        pass


class StrategicLevel(HierarchyLevel):
    """
    Strategic level: Portfolio allocation decisions.

    Time horizon: Days to weeks
    State: Asset class correlations, macro indicators, portfolio risk metrics
    Actions: Portfolio configurations, sector allocations, risk adjustments
    """

    @property
    def level_type(self) -> HierarchyLevelType:
        return HierarchyLevelType.STRATEGIC

    @property
    def time_horizon(self) -> timedelta:
        return timedelta(days=self.config.strategic_horizon_days)

    @property
    def simulation_budget(self) -> int:
        return self.config.strategic_simulations

    @property
    def action_types(self) -> list[str]:
        return [
            "increase_equity_allocation",
            "decrease_equity_allocation",
            "increase_fixed_income",
            "decrease_fixed_income",
            "increase_cash",
            "rebalance_sectors",
            "adjust_risk_level",
            "maintain_allocation",
        ]

    def abstract_state(self, state: TradingState) -> LevelState:
        """Compress state to strategic features."""
        # Portfolio-level features
        portfolio_features = np.array([
            state.portfolio.portfolio_value / max(state.portfolio.cash_balance, 1),
            state.portfolio.current_drawdown,
            state.portfolio.max_drawdown,
            state.portfolio.largest_position_pct,
            state.portfolio.position_count / 20.0,  # Normalize by typical max
        ])

        # Market regime features (one-hot)
        from reasoning_trading.core.state import MarketRegime
        regime_map = {
            MarketRegime.TRENDING_UP: 0,
            MarketRegime.TRENDING_DOWN: 1,
            MarketRegime.MEAN_REVERTING: 2,
            MarketRegime.VOLATILE: 3,
            MarketRegime.LOW_VOLATILITY: 4,
            MarketRegime.UNKNOWN: 5,
        }
        regime_features = np.zeros(6)
        regime_features[regime_map[state.market_regime]] = 1.0

        # Analyst consensus features
        analyst_features = np.array([
            state.analyst_signals.weighted_consensus(),
            state.analyst_signals.debate_confidence,
        ])

        # Technical summary (aggregated)
        tech_features = state.technical_indicators.to_feature_vector()

        # Combine and pad/truncate to target dimension
        combined = np.concatenate([
            portfolio_features,
            regime_features,
            analyst_features,
            tech_features,
        ])

        # Pad or truncate to strategic state dimension
        target_dim = self.config.strategic_state_dim
        if len(combined) < target_dim:
            combined = np.pad(combined, (0, target_dim - len(combined)))
        else:
            combined = combined[:target_dim]

        return LevelState(
            level=self.level_type,
            features=combined,
            raw_state=state,
            metadata={"abstraction": "strategic"},
        )

    def get_subtasks(self, action: LevelAction, state: LevelState) -> list[LevelAction]:
        """Get tactical subtasks for strategic action."""
        subtasks = []

        if action.action_type in ["increase_equity_allocation", "rebalance_sectors"]:
            # Need to identify which assets to buy
            subtasks.append(LevelAction(
                level=HierarchyLevelType.TACTICAL,
                action_type="identify_buy_candidates",
                parameters={"allocation_target": action.parameters.get("target", 0.1)},
                subtask_id=f"tactical_{action.action_type}",
            ))

        elif action.action_type in ["decrease_equity_allocation"]:
            subtasks.append(LevelAction(
                level=HierarchyLevelType.TACTICAL,
                action_type="identify_sell_candidates",
                parameters={"reduction_target": action.parameters.get("target", 0.1)},
                subtask_id=f"tactical_{action.action_type}",
            ))

        elif action.action_type == "adjust_risk_level":
            subtasks.append(LevelAction(
                level=HierarchyLevelType.TACTICAL,
                action_type="rebalance_positions",
                parameters={"risk_adjustment": action.parameters.get("adjustment", 0)},
                subtask_id=f"tactical_{action.action_type}",
            ))

        elif action.action_type == "maintain_allocation":
            # No subtasks needed
            pass

        return subtasks

    def is_terminal(self, action: LevelAction) -> bool:
        """Strategic actions are never primitive."""
        return action.action_type == "maintain_allocation"

    def reward(self, state: LevelState, action: LevelAction, next_state: LevelState) -> float:
        """Calculate strategic reward based on portfolio metrics."""
        if state.raw_state is None or next_state.raw_state is None:
            return 0.0

        # Portfolio value change
        value_change = (
            next_state.raw_state.portfolio.portfolio_value
            - state.raw_state.portfolio.portfolio_value
        ) / max(state.raw_state.portfolio.portfolio_value, 1)

        # Drawdown penalty
        drawdown_penalty = -next_state.raw_state.portfolio.current_drawdown * 0.5

        # Concentration penalty
        concentration_penalty = -next_state.raw_state.portfolio.largest_position_pct * 0.2

        return value_change + drawdown_penalty + concentration_penalty


class TacticalLevel(HierarchyLevel):
    """
    Tactical level: Asset selection and timing decisions.

    Time horizon: Hours to days
    State: Security momentum, relative strength, position-level risk
    Actions: Position adjustments, entry/exit timing, sector rotation
    """

    @property
    def level_type(self) -> HierarchyLevelType:
        return HierarchyLevelType.TACTICAL

    @property
    def time_horizon(self) -> timedelta:
        return timedelta(hours=self.config.tactical_horizon_hours)

    @property
    def simulation_budget(self) -> int:
        return self.config.tactical_simulations

    @property
    def action_types(self) -> list[str]:
        return [
            "enter_long_position",
            "exit_long_position",
            "enter_short_position",
            "exit_short_position",
            "scale_in_position",
            "scale_out_position",
            "wait_for_entry",
            "wait_for_exit",
            "hold_position",
        ]

    def abstract_state(self, state: TradingState) -> LevelState:
        """Extract tactical-level state features."""
        # Technical indicators (more detailed than strategic)
        tech_features = state.technical_indicators.to_feature_vector()

        # Analyst signals (all of them)
        signal_features = state.analyst_signals.to_feature_vector()

        # Position-specific features
        position_pct = state.portfolio.get_position_pct(state.symbol)
        position_features = np.array([
            position_pct,
            state.portfolio.unrealized_pnl / max(state.portfolio.portfolio_value, 1),
            state.portfolio.current_drawdown,
        ])

        # Price features from OHLCV
        if state.ohlcv_history is not None and len(state.ohlcv_history) > 0:
            recent_prices = state.ohlcv_history[-20:, 3]  # Close prices
            if len(recent_prices) > 1:
                returns = np.diff(recent_prices) / recent_prices[:-1]
                price_features = np.array([
                    np.mean(returns),
                    np.std(returns),
                    np.min(returns),
                    np.max(returns),
                    (state.current_price - recent_prices[0]) / recent_prices[0],
                ])
            else:
                price_features = np.zeros(5)
        else:
            price_features = np.zeros(5)

        # Combine features
        combined = np.concatenate([
            tech_features,
            signal_features,
            position_features,
            price_features,
        ])

        # Pad or truncate to tactical state dimension
        target_dim = self.config.tactical_state_dim
        if len(combined) < target_dim:
            combined = np.pad(combined, (0, target_dim - len(combined)))
        else:
            combined = combined[:target_dim]

        return LevelState(
            level=self.level_type,
            features=combined,
            raw_state=state,
            metadata={"abstraction": "tactical", "symbol": state.symbol},
        )

    def get_subtasks(self, action: LevelAction, state: LevelState) -> list[LevelAction]:
        """Get execution subtasks for tactical action."""
        subtasks = []

        if action.action_type in ["enter_long_position", "enter_short_position"]:
            direction = "buy" if "long" in action.action_type else "sell"
            subtasks.append(LevelAction(
                level=HierarchyLevelType.EXECUTION,
                action_type="execute_market_order",
                parameters={
                    "direction": direction,
                    "size": action.parameters.get("size", 0.1),
                },
                subtask_id=f"exec_{action.action_type}",
            ))

        elif action.action_type in ["exit_long_position", "exit_short_position"]:
            direction = "sell" if "long" in action.action_type else "buy"
            subtasks.append(LevelAction(
                level=HierarchyLevelType.EXECUTION,
                action_type="close_position",
                parameters={"direction": direction},
                subtask_id=f"exec_{action.action_type}",
            ))

        elif action.action_type in ["scale_in_position", "scale_out_position"]:
            subtasks.append(LevelAction(
                level=HierarchyLevelType.EXECUTION,
                action_type="execute_partial_order",
                parameters={
                    "scale_type": "in" if "in" in action.action_type else "out",
                    "fraction": action.parameters.get("fraction", 0.25),
                },
                subtask_id=f"exec_{action.action_type}",
            ))

        return subtasks

    def is_terminal(self, action: LevelAction) -> bool:
        """Wait and hold actions are terminal at tactical level."""
        return action.action_type in ["wait_for_entry", "wait_for_exit", "hold_position"]

    def reward(self, state: LevelState, action: LevelAction, next_state: LevelState) -> float:
        """Calculate tactical reward based on position performance."""
        if state.raw_state is None or next_state.raw_state is None:
            return 0.0

        # Position P&L change
        symbol = state.metadata.get("symbol", "")
        prev_pnl = state.raw_state.portfolio.unrealized_pnl
        next_pnl = next_state.raw_state.portfolio.unrealized_pnl
        pnl_change = (next_pnl - prev_pnl) / max(state.raw_state.portfolio.portfolio_value, 1)

        # Timing reward (did we enter/exit at good prices?)
        # Positive if price moved in our favor after entry
        timing_reward = 0.0

        return pnl_change + timing_reward


class ExecutionLevel(HierarchyLevel):
    """
    Execution level: Order execution and trade primitives.

    Time horizon: Seconds to minutes
    State: Order book depth, spread, trade flow, queue position
    Actions: Market orders, limit orders, order sizing, price levels
    """

    @property
    def level_type(self) -> HierarchyLevelType:
        return HierarchyLevelType.EXECUTION

    @property
    def time_horizon(self) -> timedelta:
        return timedelta(minutes=self.config.execution_horizon_minutes)

    @property
    def simulation_budget(self) -> int:
        return self.config.execution_simulations

    @property
    def action_types(self) -> list[str]:
        return [
            "execute_market_order",
            "place_limit_order",
            "cancel_order",
            "modify_order",
            "close_position",
            "execute_partial_order",
            "set_stop_loss",
            "set_take_profit",
        ]

    def abstract_state(self, state: TradingState) -> LevelState:
        """Extract execution-level state features."""
        # Price and volume features
        if state.ohlcv_history is not None and len(state.ohlcv_history) > 0:
            recent_data = state.ohlcv_history[-10:]  # Last 10 bars

            # Price features
            closes = recent_data[:, 3]
            volumes = recent_data[:, 4]

            price_features = np.array([
                state.current_price,
                np.mean(closes) if len(closes) > 0 else state.current_price,
                np.std(closes) if len(closes) > 1 else 0,
                np.mean(volumes) if len(volumes) > 0 else 0,
                np.std(volumes) if len(volumes) > 1 else 0,
            ])

            # Microstructure features (simulated for now)
            spread_estimate = 0.001  # 0.1% spread
            depth_estimate = np.mean(volumes) * 0.1 if len(volumes) > 0 else 0

            micro_features = np.array([
                spread_estimate,
                depth_estimate,
                np.random.uniform(0.4, 0.6),  # Order imbalance (simulated)
            ])
        else:
            price_features = np.array([state.current_price, state.current_price, 0, 0, 0])
            micro_features = np.array([0.001, 0, 0.5])

        # Position features
        position_qty = state.portfolio.get_position_size(state.symbol)
        position_features = np.array([
            position_qty,
            position_qty * state.current_price,
            state.portfolio.cash_balance,
        ])

        # Technical indicators subset (short-term)
        tech_features = np.array([
            state.technical_indicators.rsi_14 or 50,
            state.technical_indicators.macd_histogram or 0,
            state.technical_indicators.stochastic_k or 50,
        ]) / 100.0

        # Combine all features
        combined = np.concatenate([
            price_features,
            micro_features,
            position_features,
            tech_features,
        ])

        # Pad or truncate to execution state dimension
        target_dim = self.config.execution_state_dim
        if len(combined) < target_dim:
            combined = np.pad(combined, (0, target_dim - len(combined)))
        else:
            combined = combined[:target_dim]

        return LevelState(
            level=self.level_type,
            features=combined,
            raw_state=state,
            metadata={"abstraction": "execution", "symbol": state.symbol},
        )

    def get_subtasks(self, action: LevelAction, state: LevelState) -> list[LevelAction]:
        """Execution actions are primitive - no subtasks."""
        return []

    def is_terminal(self, action: LevelAction) -> bool:
        """All execution actions are primitive (terminal)."""
        return True

    def reward(self, state: LevelState, action: LevelAction, next_state: LevelState) -> float:
        """Calculate execution reward based on trade quality."""
        if state.raw_state is None or next_state.raw_state is None:
            return 0.0

        # Slippage penalty (difference from expected execution)
        expected_price = state.raw_state.current_price
        actual_price = next_state.raw_state.current_price
        slippage = abs(actual_price - expected_price) / expected_price
        slippage_penalty = -slippage * 10  # Penalize slippage heavily

        # Speed reward (faster execution is better)
        speed_reward = 0.1  # Base reward for completing execution

        return slippage_penalty + speed_reward


def create_hierarchy_level(level_type: HierarchyLevelType, config: HierarchyLevelConfig | None = None) -> HierarchyLevel:
    """Factory function to create hierarchy levels."""
    level_classes = {
        HierarchyLevelType.STRATEGIC: StrategicLevel,
        HierarchyLevelType.TACTICAL: TacticalLevel,
        HierarchyLevelType.EXECUTION: ExecutionLevel,
    }

    if level_type not in level_classes:
        raise ValueError(f"Unknown hierarchy level type: {level_type}")

    return level_classes[level_type](config)
