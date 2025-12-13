"""
Pytest configuration and shared fixtures.
"""

from __future__ import annotations

from datetime import datetime
from typing import Generator

import numpy as np
import pytest

from reasoning_trading.config import (
    Settings,
    MCTSSettings,
    RiskSettings,
    TradingMode,
)
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
from reasoning_trading.mcts.node import Node
from reasoning_trading.mcts.tree import MCTSConfig


@pytest.fixture
def test_settings() -> Settings:
    """Create test settings with safe defaults."""
    settings = Settings()
    settings.trading.trading_mode = TradingMode.PAPER
    settings.mcts.max_simulations = 100  # Reduce for faster tests
    settings.mcts.rollout_horizon_days = 5
    return settings


@pytest.fixture
def mcts_config() -> MCTSConfig:
    """Create MCTS config for testing."""
    return MCTSConfig(
        max_simulations=50,
        max_depth=10,
        exploration_weight=1.414,
        discount_factor=0.99,
        rollout_horizon=5,
        time_budget_ms=5000,
    )


@pytest.fixture
def sample_ohlcv() -> np.ndarray:
    """Generate sample OHLCV data."""
    np.random.seed(42)
    n_bars = 100

    # Generate random walk price data
    returns = np.random.normal(0.001, 0.02, n_bars)
    close = 100 * np.exp(np.cumsum(returns))

    # Generate OHLCV
    high = close * (1 + np.abs(np.random.normal(0, 0.01, n_bars)))
    low = close * (1 - np.abs(np.random.normal(0, 0.01, n_bars)))
    open_price = np.roll(close, 1)
    open_price[0] = 100
    volume = np.random.randint(100000, 1000000, n_bars)

    return np.column_stack([open_price, high, low, close, volume])


@pytest.fixture
def sample_technical_indicators() -> TechnicalIndicators:
    """Create sample technical indicators."""
    return TechnicalIndicators(
        sma_20=105.0,
        sma_50=102.0,
        sma_200=98.0,
        ema_12=104.0,
        ema_26=103.0,
        rsi_14=55.0,
        macd=1.5,
        macd_signal=1.2,
        macd_histogram=0.3,
        atr_14=2.5,
        bollinger_upper=110.0,
        bollinger_middle=105.0,
        bollinger_lower=100.0,
        volatility_20=0.02,
        volume_sma_20=500000.0,
        adx_14=30.0,
        stochastic_k=60.0,
        stochastic_d=55.0,
    )


@pytest.fixture
def sample_analyst_signals() -> AnalystSignals:
    """Create sample analyst signals."""
    return AnalystSignals(
        market_analyst_score=0.3,
        news_analyst_score=0.2,
        social_sentiment_score=0.1,
        fundamental_analyst_score=0.4,
        macro_analyst_score=0.2,
        market_analyst_confidence=0.7,
        news_analyst_confidence=0.6,
        social_sentiment_confidence=0.5,
        fundamental_analyst_confidence=0.8,
        macro_analyst_confidence=0.7,
        researcher_consensus=0.25,
        debate_confidence=0.65,
    )


@pytest.fixture
def sample_portfolio_state() -> PortfolioState:
    """Create sample portfolio state."""
    return PortfolioState(
        cash_balance=50000.0,
        portfolio_value=100000.0,
        positions={"AAPL": 100, "NVDA": 50},
        position_values={"AAPL": 25000.0, "NVDA": 25000.0},
        position_costs={"AAPL": 23000.0, "NVDA": 22000.0},
        unrealized_pnl=5000.0,
        realized_pnl_today=500.0,
        realized_pnl_total=2000.0,
        current_drawdown=0.05,
        max_drawdown=0.10,
        largest_position_pct=0.25,
        position_count=2,
    )


@pytest.fixture
def sample_trading_state(
    sample_ohlcv: np.ndarray,
    sample_technical_indicators: TechnicalIndicators,
    sample_analyst_signals: AnalystSignals,
    sample_portfolio_state: PortfolioState,
) -> TradingState:
    """Create a complete sample trading state."""
    return TradingState(
        symbol="AAPL",
        timestamp=datetime.now(),
        current_price=105.0,
        ohlcv_history=sample_ohlcv,
        technical_indicators=sample_technical_indicators,
        portfolio=sample_portfolio_state,
        analyst_signals=sample_analyst_signals,
        risk_profile="moderate",
        market_regime=MarketRegime.TRENDING_UP,
    )


@pytest.fixture
def sample_action() -> TradingAction:
    """Create a sample trading action."""
    return TradingAction(
        direction=TradingDirection.BUY,
        position_size=PositionSizeAction(size_fraction=0.1, kelly_fraction=0.5),
        stop_loss=StopLossAction(stop_loss_pct=0.05, take_profit_pct=0.15),
        time_horizon=TimeHorizon.INTRADAY,
        confidence=0.7,
        reasoning="Test action",
    )


@pytest.fixture
def action_space() -> ActionSpace:
    """Create action space for testing."""
    return ActionSpace(
        allow_shorts=False,
        max_position_size=0.25,
        min_position_size=0.01,
        stop_loss_range=(0.01, 0.10),
        progressive_widening_alpha=0.5,
    )


@pytest.fixture
def sample_node(sample_trading_state: TradingState) -> Node:
    """Create a sample tree node."""
    return Node(state=sample_trading_state)


@pytest.fixture
def tree_with_children(
    sample_trading_state: TradingState,
    sample_action: TradingAction,
) -> Node:
    """Create a tree with some children for testing."""
    root = Node(state=sample_trading_state)

    # Add children with different actions
    for direction in [TradingDirection.BUY, TradingDirection.SELL, TradingDirection.HOLD]:
        child_state = sample_trading_state.copy()
        child_state.simulation_step += 1

        child_action = TradingAction(
            direction=direction,
            position_size=PositionSizeAction(size_fraction=0.1),
            stop_loss=StopLossAction(stop_loss_pct=0.05),
            time_horizon=TimeHorizon.INTRADAY,
            confidence=0.6,
        )

        child = root.expand(
            action=child_action,
            new_state=child_state,
            prior=0.3,
        )

        # Add some visits
        child.visits = np.random.randint(10, 100)
        child.value_sum = child.visits * np.random.uniform(-0.5, 0.5)

    root.visits = sum(c.visits for c in root.children) + 10

    return root
