"""
Trading action representations for MCTS.

This module defines the action space for trading decisions, including
direction, position sizing, stop-loss, and time horizons. It supports
both discrete and continuous action spaces with progressive widening.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np
from numpy.typing import NDArray
from pydantic import BaseModel, Field


class TradingDirection(str, Enum):
    """Trading direction enum."""

    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    SHORT = "short"
    COVER = "cover"  # Cover short position

    def is_entry(self) -> bool:
        """Check if this is an entry action."""
        return self in (TradingDirection.BUY, TradingDirection.SHORT)

    def is_exit(self) -> bool:
        """Check if this is an exit action."""
        return self in (TradingDirection.SELL, TradingDirection.COVER)

    def opposite(self) -> TradingDirection:
        """Get the opposite direction for closing positions."""
        opposites = {
            TradingDirection.BUY: TradingDirection.SELL,
            TradingDirection.SELL: TradingDirection.BUY,
            TradingDirection.SHORT: TradingDirection.COVER,
            TradingDirection.COVER: TradingDirection.SHORT,
            TradingDirection.HOLD: TradingDirection.HOLD,
        }
        return opposites[self]


class TimeHorizon(str, Enum):
    """Trading time horizon for position management."""

    SCALP = "1H"  # 1 hour
    INTRADAY = "4H"  # 4 hours
    SWING = "1D"  # 1 day
    POSITION = "1W"  # 1 week
    INVESTMENT = "1M"  # 1 month

    def to_hours(self) -> int:
        """Convert horizon to hours."""
        mapping = {
            TimeHorizon.SCALP: 1,
            TimeHorizon.INTRADAY: 4,
            TimeHorizon.SWING: 24,
            TimeHorizon.POSITION: 168,
            TimeHorizon.INVESTMENT: 720,
        }
        return mapping[self]

    def to_trading_days(self) -> float:
        """Convert horizon to trading days (6.5 hours per day)."""
        return self.to_hours() / 6.5


class PositionSizeAction(BaseModel):
    """Continuous position size action with Kelly Criterion reference."""

    # Size as fraction of portfolio (0 to max_position_size)
    size_fraction: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Position size as fraction of portfolio"
    )

    # Kelly fraction multiplier (0 = no position, 1 = full Kelly)
    kelly_fraction: float = Field(
        default=0.5, ge=0.0, le=2.0, description="Fraction of Kelly optimal size"
    )

    @classmethod
    def from_kelly_optimal(
        cls,
        win_probability: float,
        win_loss_ratio: float,
        kelly_multiplier: float = 0.5,
        max_size: float = 0.25,
    ) -> PositionSizeAction:
        """
        Calculate position size using Kelly Criterion.

        Args:
            win_probability: Probability of winning trade (0-1)
            win_loss_ratio: Ratio of average win to average loss
            kelly_multiplier: Fraction of Kelly to use (0.5 = half Kelly)
            max_size: Maximum allowed position size

        Returns:
            PositionSizeAction with calculated size
        """
        if win_probability <= 0 or win_loss_ratio <= 0:
            return cls(size_fraction=0.0, kelly_fraction=kelly_multiplier)

        # Kelly formula: f* = (bp - q) / b
        # where b = win/loss ratio, p = win probability, q = loss probability
        b = win_loss_ratio
        p = win_probability
        q = 1 - p

        kelly_optimal = (b * p - q) / b

        # Apply multiplier and cap at max
        size = min(max(kelly_optimal * kelly_multiplier, 0.0), max_size)

        return cls(size_fraction=size, kelly_fraction=kelly_multiplier)


class StopLossAction(BaseModel):
    """Stop-loss configuration for risk management."""

    # Stop-loss as percentage below entry (0 to 0.5)
    stop_loss_pct: float = Field(
        default=0.05, ge=0.0, le=0.50, description="Stop-loss percentage"
    )

    # Take-profit as percentage above entry (0 to 1.0)
    take_profit_pct: float | None = Field(
        default=None, ge=0.0, le=1.0, description="Take-profit percentage"
    )

    # Trailing stop parameters
    trailing_stop: bool = Field(default=False, description="Enable trailing stop")
    trailing_distance_pct: float = Field(
        default=0.03, ge=0.0, le=0.20, description="Trailing stop distance"
    )

    def risk_reward_ratio(self) -> float | None:
        """Calculate risk/reward ratio if take-profit is set."""
        if self.take_profit_pct is None or self.stop_loss_pct == 0:
            return None
        return self.take_profit_pct / self.stop_loss_pct


@dataclass
class TradingAction:
    """
    Complete trading action representation.

    Combines direction, sizing, stop-loss, and timing into a single
    action that can be executed or used in MCTS tree expansion.
    """

    direction: TradingDirection
    position_size: PositionSizeAction
    stop_loss: StopLossAction
    time_horizon: TimeHorizon

    # Execution parameters
    order_type: str = "market"  # market, limit, stop
    limit_price: float | None = None

    # Confidence and reasoning
    confidence: float = 0.5  # 0-1 confidence in this action
    reasoning: str = ""  # LLM-generated reasoning

    # MCTS metadata
    visit_count: int = 0
    value_sum: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "direction": self.direction.value,
            "position_size": self.position_size.model_dump(),
            "stop_loss": self.stop_loss.model_dump(),
            "time_horizon": self.time_horizon.value,
            "order_type": self.order_type,
            "limit_price": self.limit_price,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TradingAction:
        """Create from dictionary."""
        return cls(
            direction=TradingDirection(data["direction"]),
            position_size=PositionSizeAction(**data["position_size"]),
            stop_loss=StopLossAction(**data["stop_loss"]),
            time_horizon=TimeHorizon(data["time_horizon"]),
            order_type=data.get("order_type", "market"),
            limit_price=data.get("limit_price"),
            confidence=data.get("confidence", 0.5),
            reasoning=data.get("reasoning", ""),
        )

    @classmethod
    def hold(cls) -> TradingAction:
        """Create a HOLD action (do nothing)."""
        return cls(
            direction=TradingDirection.HOLD,
            position_size=PositionSizeAction(size_fraction=0.0),
            stop_loss=StopLossAction(),
            time_horizon=TimeHorizon.INTRADAY,
            confidence=1.0,
            reasoning="No action taken",
        )

    def __hash__(self) -> int:
        """Hash for tree node lookup."""
        return hash(
            (
                self.direction,
                round(self.position_size.size_fraction, 3),
                round(self.stop_loss.stop_loss_pct, 3),
                self.time_horizon,
            )
        )


class ActionSpace:
    """
    Defines the action space for MCTS exploration.

    Supports both discrete actions (direction, time horizon) and
    continuous actions (position size, stop-loss) with progressive
    widening for continuous spaces.
    """

    def __init__(
        self,
        allow_shorts: bool = False,
        max_position_size: float = 0.25,
        min_position_size: float = 0.01,
        stop_loss_range: tuple[float, float] = (0.01, 0.10),
        progressive_widening_alpha: float = 0.5,
    ):
        """
        Initialize action space.

        Args:
            allow_shorts: Whether short selling is allowed
            max_position_size: Maximum position size as fraction of portfolio
            min_position_size: Minimum position size
            stop_loss_range: (min, max) stop-loss percentages
            progressive_widening_alpha: Alpha parameter for progressive widening
        """
        self.allow_shorts = allow_shorts
        self.max_position_size = max_position_size
        self.min_position_size = min_position_size
        self.stop_loss_min, self.stop_loss_max = stop_loss_range
        self.progressive_widening_alpha = progressive_widening_alpha

        # Build discrete action components
        self._directions = [TradingDirection.BUY, TradingDirection.HOLD, TradingDirection.SELL]
        if allow_shorts:
            self._directions.extend([TradingDirection.SHORT, TradingDirection.COVER])

        self._time_horizons = list(TimeHorizon)

    @property
    def directions(self) -> list[TradingDirection]:
        """Available trading directions."""
        return self._directions.copy()

    @property
    def time_horizons(self) -> list[TimeHorizon]:
        """Available time horizons."""
        return self._time_horizons.copy()

    def sample_position_size(
        self, current_price: float = 1.0, noise_scale: float = 0.1
    ) -> PositionSizeAction:
        """
        Sample a position size using Ornstein-Uhlenbeck noise.

        Args:
            current_price: Current asset price (for context)
            noise_scale: Scale of random perturbation

        Returns:
            Sampled PositionSizeAction
        """
        # Sample kelly fraction from reasonable range with OU noise
        base_kelly = np.random.uniform(0.25, 0.75)
        noise = np.random.normal(0, noise_scale)
        kelly_fraction = np.clip(base_kelly + noise, 0.1, 1.0)

        # Map to actual position size
        size_fraction = np.random.uniform(self.min_position_size, self.max_position_size)

        return PositionSizeAction(size_fraction=size_fraction, kelly_fraction=kelly_fraction)

    def sample_stop_loss(self, volatility: float = 0.02) -> StopLossAction:
        """
        Sample stop-loss parameters based on volatility.

        Args:
            volatility: Current market volatility estimate

        Returns:
            Sampled StopLossAction
        """
        # Stop-loss typically 1.5-3x daily volatility
        vol_multiplier = np.random.uniform(1.5, 3.0)
        stop_loss_pct = np.clip(
            volatility * vol_multiplier, self.stop_loss_min, self.stop_loss_max
        )

        # Take-profit typically 2-4x stop-loss (risk/reward 1:2 to 1:4)
        rr_ratio = np.random.uniform(2.0, 4.0)
        take_profit_pct = min(stop_loss_pct * rr_ratio, 0.50)

        # Sometimes use trailing stop
        use_trailing = np.random.random() < 0.3

        return StopLossAction(
            stop_loss_pct=stop_loss_pct,
            take_profit_pct=take_profit_pct,
            trailing_stop=use_trailing,
            trailing_distance_pct=stop_loss_pct * 0.75,
        )

    def sample_action(self, volatility: float = 0.02) -> TradingAction:
        """
        Sample a complete trading action.

        Args:
            volatility: Current market volatility for sizing

        Returns:
            Sampled TradingAction
        """
        return TradingAction(
            direction=np.random.choice(self._directions),
            position_size=self.sample_position_size(),
            stop_loss=self.sample_stop_loss(volatility),
            time_horizon=np.random.choice(self._time_horizons),
            confidence=np.random.uniform(0.3, 0.8),
        )

    def get_candidate_actions(
        self, visit_count: int, existing_actions: list[TradingAction] | None = None
    ) -> list[TradingAction]:
        """
        Get candidate actions for expansion using progressive widening.

        The number of allowed children grows as visit_count^alpha.

        Args:
            visit_count: Current node visit count
            existing_actions: Actions already expanded at this node

        Returns:
            List of candidate actions to consider
        """
        existing = existing_actions or []
        existing_set = set(existing)

        # Progressive widening: allow more actions as visits increase
        max_children = max(1, int(visit_count**self.progressive_widening_alpha))

        if len(existing) >= max_children:
            return []

        candidates = []
        num_to_generate = max_children - len(existing)

        # Generate diverse candidates
        for direction in self._directions:
            for horizon in self._time_horizons:
                action = TradingAction(
                    direction=direction,
                    position_size=self.sample_position_size(),
                    stop_loss=self.sample_stop_loss(),
                    time_horizon=horizon,
                )
                if action not in existing_set:
                    candidates.append(action)
                    if len(candidates) >= num_to_generate:
                        return candidates

        return candidates

    def to_feature_vector(self, action: TradingAction) -> NDArray[np.float64]:
        """
        Convert action to feature vector for neural network input.

        Args:
            action: TradingAction to encode

        Returns:
            Normalized feature vector
        """
        # Direction one-hot
        direction_vec = np.zeros(len(self._directions), dtype=np.float64)
        if action.direction in self._directions:
            direction_vec[self._directions.index(action.direction)] = 1.0

        # Time horizon one-hot
        horizon_vec = np.zeros(len(self._time_horizons), dtype=np.float64)
        if action.time_horizon in self._time_horizons:
            horizon_vec[self._time_horizons.index(action.time_horizon)] = 1.0

        # Continuous features (normalized)
        continuous_vec = np.array(
            [
                action.position_size.size_fraction / self.max_position_size,
                action.position_size.kelly_fraction / 2.0,
                (action.stop_loss.stop_loss_pct - self.stop_loss_min)
                / (self.stop_loss_max - self.stop_loss_min),
                action.confidence,
            ],
            dtype=np.float64,
        )

        return np.concatenate([direction_vec, horizon_vec, continuous_vec])
