"""
Tests for core state and action representations.
"""

from __future__ import annotations

from datetime import datetime

import numpy as np
import pytest

from reasoning_trading.core.actions import (
    ActionSpace,
    PositionSizeAction,
    StopLossAction,
    TimeHorizon,
    TradingAction,
    TradingDirection,
)
from reasoning_trading.core.state import (
    AnalystSignals,
    MarketRegime,
    PortfolioState,
    TechnicalIndicators,
    TradingState,
)


class TestTradingDirection:
    """Tests for TradingDirection enum."""

    def test_is_entry(self) -> None:
        """Test entry direction detection."""
        assert TradingDirection.BUY.is_entry() is True
        assert TradingDirection.SHORT.is_entry() is True
        assert TradingDirection.SELL.is_entry() is False
        assert TradingDirection.HOLD.is_entry() is False

    def test_is_exit(self) -> None:
        """Test exit direction detection."""
        assert TradingDirection.SELL.is_exit() is True
        assert TradingDirection.COVER.is_exit() is True
        assert TradingDirection.BUY.is_exit() is False

    def test_opposite(self) -> None:
        """Test opposite direction lookup."""
        assert TradingDirection.BUY.opposite() == TradingDirection.SELL
        assert TradingDirection.SELL.opposite() == TradingDirection.BUY
        assert TradingDirection.SHORT.opposite() == TradingDirection.COVER


class TestPositionSizeAction:
    """Tests for PositionSizeAction."""

    def test_from_kelly_optimal(self) -> None:
        """Test Kelly Criterion calculation."""
        action = PositionSizeAction.from_kelly_optimal(
            win_probability=0.6,
            win_loss_ratio=1.5,
            kelly_multiplier=0.5,
            max_size=0.25,
        )
        assert 0 < action.size_fraction <= 0.25
        assert action.kelly_fraction == 0.5

    def test_from_kelly_zero_probability(self) -> None:
        """Test Kelly with zero win probability."""
        action = PositionSizeAction.from_kelly_optimal(
            win_probability=0.0,
            win_loss_ratio=1.5,
        )
        assert action.size_fraction == 0.0


class TestStopLossAction:
    """Tests for StopLossAction."""

    def test_risk_reward_ratio(self) -> None:
        """Test risk/reward calculation."""
        action = StopLossAction(stop_loss_pct=0.05, take_profit_pct=0.15)
        assert action.risk_reward_ratio() == 3.0

    def test_risk_reward_no_take_profit(self) -> None:
        """Test risk/reward with no take profit."""
        action = StopLossAction(stop_loss_pct=0.05, take_profit_pct=None)
        assert action.risk_reward_ratio() is None


class TestTradingAction:
    """Tests for TradingAction."""

    def test_hold_action(self) -> None:
        """Test HOLD action creation."""
        action = TradingAction.hold()
        assert action.direction == TradingDirection.HOLD
        assert action.position_size.size_fraction == 0.0
        assert action.confidence == 1.0

    def test_to_dict_from_dict(self, sample_action: TradingAction) -> None:
        """Test serialization roundtrip."""
        data = sample_action.to_dict()
        restored = TradingAction.from_dict(data)

        assert restored.direction == sample_action.direction
        assert restored.position_size.size_fraction == sample_action.position_size.size_fraction
        assert restored.stop_loss.stop_loss_pct == sample_action.stop_loss.stop_loss_pct
        assert restored.time_horizon == sample_action.time_horizon

    def test_hash(self, sample_action: TradingAction) -> None:
        """Test action hashing."""
        hash1 = hash(sample_action)

        # Same parameters should give same hash
        action2 = TradingAction(
            direction=sample_action.direction,
            position_size=PositionSizeAction(size_fraction=sample_action.position_size.size_fraction),
            stop_loss=StopLossAction(stop_loss_pct=sample_action.stop_loss.stop_loss_pct),
            time_horizon=sample_action.time_horizon,
        )
        assert hash(action2) == hash1


class TestActionSpace:
    """Tests for ActionSpace."""

    def test_directions_with_shorts(self) -> None:
        """Test available directions with shorts enabled."""
        space = ActionSpace(allow_shorts=True)
        directions = space.directions
        assert TradingDirection.SHORT in directions
        assert TradingDirection.COVER in directions

    def test_directions_without_shorts(self) -> None:
        """Test available directions without shorts."""
        space = ActionSpace(allow_shorts=False)
        directions = space.directions
        assert TradingDirection.SHORT not in directions
        assert TradingDirection.COVER not in directions

    def test_sample_position_size(self, action_space: ActionSpace) -> None:
        """Test position size sampling."""
        for _ in range(10):
            size = action_space.sample_position_size()
            assert action_space.min_position_size <= size.size_fraction <= action_space.max_position_size

    def test_sample_stop_loss(self, action_space: ActionSpace) -> None:
        """Test stop-loss sampling."""
        for _ in range(10):
            sl = action_space.sample_stop_loss(volatility=0.02)
            assert sl.stop_loss_pct >= action_space.stop_loss_min
            assert sl.stop_loss_pct <= action_space.stop_loss_max

    def test_sample_action(self, action_space: ActionSpace) -> None:
        """Test full action sampling."""
        action = action_space.sample_action()
        assert action.direction in action_space.directions
        assert action.time_horizon in action_space.time_horizons

    def test_get_candidate_actions(self, action_space: ActionSpace) -> None:
        """Test progressive widening candidate generation."""
        # With few visits, should get some candidates
        candidates = action_space.get_candidate_actions(visit_count=10)
        assert len(candidates) > 0

        # With zero visits, should get at least one
        candidates = action_space.get_candidate_actions(visit_count=0)
        assert len(candidates) >= 1

    def test_to_feature_vector(self, action_space: ActionSpace, sample_action: TradingAction) -> None:
        """Test action feature vector conversion."""
        features = action_space.to_feature_vector(sample_action)
        assert isinstance(features, np.ndarray)
        assert features.dtype == np.float64
        assert len(features) > 0


class TestTechnicalIndicators:
    """Tests for TechnicalIndicators."""

    def test_to_feature_vector(self, sample_technical_indicators: TechnicalIndicators) -> None:
        """Test feature vector conversion."""
        features = sample_technical_indicators.to_feature_vector()
        assert isinstance(features, np.ndarray)
        assert len(features) == 7
        # All features should be normalized (roughly -1 to 1)
        assert all(-2 <= f <= 2 for f in features)


class TestAnalystSignals:
    """Tests for AnalystSignals."""

    def test_weighted_consensus(self, sample_analyst_signals: AnalystSignals) -> None:
        """Test weighted consensus calculation."""
        consensus = sample_analyst_signals.weighted_consensus()
        assert -1.0 <= consensus <= 1.0

    def test_to_feature_vector(self, sample_analyst_signals: AnalystSignals) -> None:
        """Test feature vector conversion."""
        features = sample_analyst_signals.to_feature_vector()
        assert isinstance(features, np.ndarray)
        assert len(features) == 12


class TestPortfolioState:
    """Tests for PortfolioState."""

    def test_get_position_size(self, sample_portfolio_state: PortfolioState) -> None:
        """Test position size retrieval."""
        assert sample_portfolio_state.get_position_size("AAPL") == 100
        assert sample_portfolio_state.get_position_size("UNKNOWN") == 0.0

    def test_get_position_pct(self, sample_portfolio_state: PortfolioState) -> None:
        """Test position percentage calculation."""
        pct = sample_portfolio_state.get_position_pct("AAPL")
        assert pct == 0.25  # 25000 / 100000

    def test_can_open_position(self, sample_portfolio_state: PortfolioState) -> None:
        """Test position opening check."""
        assert sample_portfolio_state.can_open_position(10000.0) is True
        assert sample_portfolio_state.can_open_position(100000.0) is False


class TestTradingState:
    """Tests for TradingState."""

    def test_copy(self, sample_trading_state: TradingState) -> None:
        """Test state copying."""
        copy = sample_trading_state.copy()

        assert copy.symbol == sample_trading_state.symbol
        assert copy.current_price == sample_trading_state.current_price
        assert copy is not sample_trading_state

        # Modify copy and ensure original unchanged
        copy.simulation_step = 100
        assert sample_trading_state.simulation_step != 100

    def test_to_feature_vector(self, sample_trading_state: TradingState) -> None:
        """Test feature vector conversion."""
        features = sample_trading_state.to_feature_vector()
        assert isinstance(features, np.ndarray)
        assert features.dtype == np.float64
        # Total: 2 + 7 + 12 + 4 + 6 + 3 = 34 features
        assert len(features) == 34

    def test_update_from_market_data(self, sample_trading_state: TradingState) -> None:
        """Test market data update."""
        new_price = 110.0
        sample_trading_state.update_from_market_data(new_price)
        assert sample_trading_state.current_price == new_price

    def test_hash(self, sample_trading_state: TradingState) -> None:
        """Test state hashing."""
        hash1 = hash(sample_trading_state)

        # Same parameters should give same hash
        state2 = TradingState(
            symbol=sample_trading_state.symbol,
            timestamp=sample_trading_state.timestamp,
            current_price=sample_trading_state.current_price,
            simulation_step=sample_trading_state.simulation_step,
        )
        assert hash(state2) == hash1
