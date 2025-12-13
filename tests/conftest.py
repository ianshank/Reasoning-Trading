"""
Pytest configuration and shared fixtures.

All test values come from TestConfig or factories - no hardcoded values.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from reasoning_trading.config import (
    MCTSSettings,
    RiskSettings,
    Settings,
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

from tests.config import (
    ScenarioConfig,
    TestConfig,
    TestScenario,
    get_scenario_configs,
    get_test_config,
)
from tests.factories import (
    ActionFactory,
    IndicatorFactory,
    MarketDataFactory,
    PortfolioFactory,
    SignalFactory,
    TradingStateFactory,
)


# =============================================================================
# Test Configuration Fixtures
# =============================================================================


@pytest.fixture(scope="session")
def test_config() -> TestConfig:
    """Get test configuration (session-scoped for efficiency)."""
    return get_test_config()


@pytest.fixture
def test_settings(test_config: TestConfig) -> Settings:
    """Create test settings with safe defaults from test config."""
    settings = Settings()
    settings.trading.trading_mode = TradingMode.PAPER
    settings.mcts.max_simulations = test_config.mcts_simulations
    settings.mcts.rollout_horizon_days = test_config.mcts_rollout_horizon
    settings.risk.max_position_size_fraction = test_config.max_position_size
    settings.risk.default_stop_loss_percent = test_config.default_stop_loss
    return settings


@pytest.fixture
def mcts_config(test_config: TestConfig) -> MCTSConfig:
    """Create MCTS config for testing from test config."""
    return MCTSConfig(
        max_simulations=test_config.mcts_simulations,
        max_depth=10,
        exploration_weight=1.414,
        discount_factor=0.99,
        rollout_horizon=test_config.mcts_rollout_horizon,
        time_budget_ms=test_config.mcts_timeout_ms,
    )


@pytest.fixture
def scenario_configs(test_config: TestConfig) -> dict[TestScenario, ScenarioConfig]:
    """Get all scenario configurations."""
    return get_scenario_configs(test_config)


# =============================================================================
# Factory Fixtures
# =============================================================================


@pytest.fixture
def market_data_factory(test_config: TestConfig) -> MarketDataFactory:
    """Get market data factory."""
    return MarketDataFactory(config=test_config)


@pytest.fixture
def indicator_factory(test_config: TestConfig) -> IndicatorFactory:
    """Get indicator factory."""
    return IndicatorFactory(config=test_config)


@pytest.fixture
def signal_factory(test_config: TestConfig) -> SignalFactory:
    """Get signal factory."""
    return SignalFactory(config=test_config)


@pytest.fixture
def portfolio_factory(test_config: TestConfig) -> PortfolioFactory:
    """Get portfolio factory."""
    return PortfolioFactory(config=test_config)


@pytest.fixture
def trading_state_factory(test_config: TestConfig) -> TradingStateFactory:
    """Get trading state factory."""
    return TradingStateFactory(config=test_config)


@pytest.fixture
def action_factory(test_config: TestConfig) -> ActionFactory:
    """Get action factory."""
    return ActionFactory(config=test_config)


# =============================================================================
# Data Fixtures
# =============================================================================


@pytest.fixture
def sample_ohlcv(market_data_factory: MarketDataFactory) -> np.ndarray:
    """Generate sample OHLCV data."""
    return market_data_factory.generate_ohlcv()


@pytest.fixture
def sample_bars(market_data_factory: MarketDataFactory) -> list:
    """Generate sample Bar objects."""
    return market_data_factory.generate_bars()


@pytest.fixture
def sample_technical_indicators(indicator_factory: IndicatorFactory) -> TechnicalIndicators:
    """Create sample technical indicators."""
    return indicator_factory.create_neutral()


@pytest.fixture
def sample_analyst_signals(signal_factory: SignalFactory) -> AnalystSignals:
    """Create sample analyst signals."""
    return signal_factory.create_neutral()


@pytest.fixture
def sample_portfolio_state(portfolio_factory: PortfolioFactory) -> PortfolioState:
    """Create sample portfolio state."""
    return portfolio_factory.create_with_position()


@pytest.fixture
def sample_trading_state(trading_state_factory: TradingStateFactory) -> TradingState:
    """Create a complete sample trading state."""
    return trading_state_factory.create()


@pytest.fixture
def sample_action(action_factory: ActionFactory) -> TradingAction:
    """Create a sample trading action."""
    return action_factory.create_buy()


@pytest.fixture
def action_space(test_config: TestConfig) -> ActionSpace:
    """Create action space for testing."""
    return ActionSpace(
        allow_shorts=False,
        max_position_size=test_config.max_position_size,
        min_position_size=0.01,
        stop_loss_range=(0.01, 0.10),
        progressive_widening_alpha=0.5,
    )


# =============================================================================
# MCTS Fixtures
# =============================================================================


@pytest.fixture
def sample_node(sample_trading_state: TradingState) -> Node:
    """Create a sample tree node."""
    return Node(state=sample_trading_state)


@pytest.fixture
def tree_with_children(
    sample_trading_state: TradingState,
    action_factory: ActionFactory,
    test_config: TestConfig,
) -> Node:
    """Create a tree with some children for testing."""
    np.random.seed(test_config.random_seed)

    root = Node(state=sample_trading_state)

    # Add children with different actions
    for direction in [TradingDirection.BUY, TradingDirection.SELL, TradingDirection.HOLD]:
        child_state = sample_trading_state.copy()
        child_state.simulation_step += 1

        if direction == TradingDirection.BUY:
            child_action = action_factory.create_buy()
        elif direction == TradingDirection.SELL:
            child_action = action_factory.create_sell()
        else:
            child_action = action_factory.create_hold()

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


# =============================================================================
# Scenario Fixtures
# =============================================================================


@pytest.fixture
def bullish_state(trading_state_factory: TradingStateFactory) -> TradingState:
    """Create a bullish trading state."""
    return trading_state_factory.create_for_scenario(TestScenario.BULLISH)


@pytest.fixture
def bearish_state(trading_state_factory: TradingStateFactory) -> TradingState:
    """Create a bearish trading state."""
    return trading_state_factory.create_for_scenario(TestScenario.BEARISH)


@pytest.fixture
def neutral_state(trading_state_factory: TradingStateFactory) -> TradingState:
    """Create a neutral trading state."""
    return trading_state_factory.create_for_scenario(TestScenario.NEUTRAL)


@pytest.fixture
def volatile_state(trading_state_factory: TradingStateFactory) -> TradingState:
    """Create a volatile trading state."""
    return trading_state_factory.create_for_scenario(TestScenario.VOLATILE)


# =============================================================================
# Mock Fixtures for Integration Tests
# =============================================================================


@pytest.fixture
def mock_trading_adapter(
    sample_trading_state: TradingState,
    sample_portfolio_state: PortfolioState,
    test_config: TestConfig,
) -> AsyncMock:
    """Create a mock trading adapter."""
    from reasoning_trading.services.adapter import OrderResult, TradingSignal

    adapter = AsyncMock()

    # Mock build_trading_state
    adapter.build_trading_state = AsyncMock(return_value=sample_trading_state)

    # Mock get_portfolio_state
    adapter.get_portfolio_state = AsyncMock(return_value=sample_portfolio_state)

    # Mock get_trading_signal
    adapter.get_trading_signal = AsyncMock(
        return_value=TradingSignal(
            symbol=test_config.primary_symbol,
            direction="hold",
            confidence=0.5,
            position_size_pct=0.0,
            stop_loss_pct=test_config.default_stop_loss,
            reasoning="Mock signal",
            analyst_signals={
                "market": 0.1,
                "news": 0.0,
                "social": -0.1,
                "fundamental": 0.2,
                "macro": 0.1,
            },
        )
    )

    # Mock execute_trade
    adapter.execute_trade = AsyncMock(
        return_value=OrderResult(
            order_id="mock_order_123",
            symbol=test_config.primary_symbol,
            side="buy",
            quantity=100,
            status="filled",
            filled_price=test_config.base_price,
        )
    )

    # Mock get_market_data
    adapter.get_market_data = AsyncMock(
        return_value={
            "symbol": test_config.primary_symbol,
            "bars": [
                {
                    "timestamp": datetime.now().isoformat(),
                    "open": test_config.base_price * 0.99,
                    "high": test_config.base_price * 1.02,
                    "low": test_config.base_price * 0.98,
                    "close": test_config.base_price,
                    "volume": 500000,
                }
            ],
        }
    )

    # Mock calculate_risk_metrics
    adapter.calculate_risk_metrics = AsyncMock(
        return_value={
            "symbol": test_config.primary_symbol,
            "daily_volatility": test_config.price_volatility,
            "var_95_pct": -0.03,
            "recommended_size_pct": test_config.default_position_size,
        }
    )

    # Mock initialization and cleanup
    adapter._initialize = AsyncMock()
    adapter._cleanup = AsyncMock()

    return adapter


@pytest.fixture
def mock_market_data_service(
    sample_bars: list,
    indicator_factory: IndicatorFactory,
    test_config: TestConfig,
) -> AsyncMock:
    """Create a mock market data service."""
    from reasoning_trading.services.market_data import MarketSnapshot

    service = AsyncMock()

    service.get_historical_bars = AsyncMock(return_value=sample_bars)

    service.get_snapshot = AsyncMock(
        return_value=MarketSnapshot(
            symbol=test_config.primary_symbol,
            last_price=test_config.base_price,
            bid=test_config.base_price - 0.01,
            ask=test_config.base_price + 0.01,
            volume=500000,
        )
    )

    service.calculate_indicators = MagicMock(
        return_value=indicator_factory.create_neutral()
    )

    return service


@pytest.fixture
def mock_portfolio_service(
    portfolio_factory: PortfolioFactory,
    test_config: TestConfig,
) -> MagicMock:
    """Create a mock portfolio service."""
    service = MagicMock()

    service.get_state = MagicMock(return_value=portfolio_factory.create_with_position())
    service.cash_balance = test_config.initial_cash
    service.portfolio_value = test_config.initial_portfolio_value
    service.can_open_position = MagicMock(return_value=(True, "OK"))

    return service


# =============================================================================
# Async Test Helpers
# =============================================================================


@pytest.fixture
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def integration_timeout(test_config: TestConfig) -> float:
    """Get timeout for integration tests."""
    return test_config.integration_timeout_seconds


@pytest.fixture
def e2e_timeout(test_config: TestConfig) -> float:
    """Get timeout for E2E tests."""
    return test_config.e2e_timeout_seconds


# =============================================================================
# Cleanup Fixtures
# =============================================================================


@pytest.fixture(autouse=True)
def reset_random_state(test_config: TestConfig) -> Generator[None, None, None]:
    """Reset random state before each test for reproducibility."""
    np.random.seed(test_config.random_seed)
    yield


@pytest.fixture
def temp_cache() -> Generator[dict, None, None]:
    """Provide a temporary cache for tests."""
    cache: dict[str, Any] = {}
    yield cache
    cache.clear()
