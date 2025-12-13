"""
Integration tests for service layer components.

Tests the interaction between:
- TradingServiceAdapter + Portfolio/Market services
- Market data flow to indicators
- Portfolio state management
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from reasoning_trading.config import Settings, TradingMode
from reasoning_trading.core.actions import TradingAction, TradingDirection
from reasoning_trading.core.state import PortfolioState, TradingState
from reasoning_trading.services.adapter import TradingServiceAdapter
from reasoning_trading.services.market_data import Bar, MarketDataService, TimeFrame
from reasoning_trading.services.portfolio import PortfolioService, Position

from tests.config import TestConfig, TestScenario
from tests.factories import (
    MarketDataFactory,
    PortfolioFactory,
    TradingStateFactory,
)


class TestMarketDataToIndicators:
    """Test market data flow to technical indicators."""

    def test_bars_produce_valid_indicators(
        self,
        market_data_factory: MarketDataFactory,
        test_config: TestConfig,
    ) -> None:
        """Test that bars produce valid indicators."""
        service = MarketDataService()
        bars = market_data_factory.generate_bars(n_bars=test_config.ohlcv_bars)

        indicators = service.calculate_indicators(bars)

        # Should have computed key indicators
        assert indicators.sma_20 is not None
        assert indicators.rsi_14 is not None
        assert indicators.volatility_20 is not None

        # RSI should be in valid range
        assert 0 <= indicators.rsi_14 <= 100

        # Volatility should be positive
        assert indicators.volatility_20 > 0

    def test_market_regime_detection(
        self,
        market_data_factory: MarketDataFactory,
        test_config: TestConfig,
    ) -> None:
        """Test market regime detection from price data."""
        service = MarketDataService()

        # Generate trending up data
        trending_bars = market_data_factory.generate_bars(
            n_bars=test_config.ohlcv_bars,
            base_price=test_config.base_price,
        )
        # Artificially create uptrend
        for i, bar in enumerate(trending_bars):
            bar.close = test_config.base_price * (1 + 0.002 * i)
            bar.open = bar.close * 0.99
            bar.high = bar.close * 1.01
            bar.low = bar.close * 0.98

        regime = service.detect_market_regime(trending_bars)

        # Should detect some regime
        from reasoning_trading.core.state import MarketRegime

        assert regime in list(MarketRegime)

    def test_ohlcv_conversion(
        self,
        market_data_factory: MarketDataFactory,
        test_config: TestConfig,
    ) -> None:
        """Test bar to OHLCV array conversion."""
        service = MarketDataService()
        bars = market_data_factory.generate_bars(n_bars=test_config.ohlcv_bars)

        ohlcv = service.bars_to_ohlcv(bars)

        # Should have correct shape
        assert ohlcv.shape == (test_config.ohlcv_bars, 5)

        # Values should be positive
        assert np.all(ohlcv[:, :4] > 0)  # OHLC
        assert np.all(ohlcv[:, 4] >= 0)  # Volume


class TestPortfolioManagement:
    """Test portfolio management operations."""

    def test_position_lifecycle(
        self,
        test_config: TestConfig,
    ) -> None:
        """Test complete position lifecycle: open, update, close."""
        portfolio = PortfolioService(initial_cash=test_config.initial_cash)

        # Open position
        trade1 = portfolio.execute_trade(
            symbol=test_config.primary_symbol,
            direction=TradingDirection.BUY,
            quantity=100,
            price=test_config.base_price,
            stop_loss_pct=test_config.default_stop_loss,
        )

        assert trade1.symbol == test_config.primary_symbol
        position = portfolio.get_position(test_config.primary_symbol)
        assert position is not None
        assert position.quantity == 100

        # Update price
        new_price = test_config.base_price * 1.05
        portfolio.update_prices({test_config.primary_symbol: new_price})
        position = portfolio.get_position(test_config.primary_symbol)
        assert position.current_price == new_price
        assert position.unrealized_pnl > 0

        # Close position
        trade2 = portfolio.execute_trade(
            symbol=test_config.primary_symbol,
            direction=TradingDirection.SELL,
            quantity=100,
            price=new_price,
        )

        assert trade2.pnl > 0  # Profit from price increase
        assert portfolio.get_position(test_config.primary_symbol) is None

    def test_risk_limits_enforced(
        self,
        test_config: TestConfig,
    ) -> None:
        """Test that risk limits are enforced."""
        portfolio = PortfolioService(initial_cash=test_config.initial_cash)

        # Try to open position larger than cash
        can_open, reason = portfolio.can_open_position(
            symbol=test_config.primary_symbol,
            direction=TradingDirection.BUY,
            value=test_config.initial_cash * 2,
        )

        assert not can_open
        assert "Insufficient" in reason

    def test_stop_loss_detection(
        self,
        test_config: TestConfig,
    ) -> None:
        """Test stop-loss trigger detection."""
        portfolio = PortfolioService(initial_cash=test_config.initial_cash)

        # Open position with stop-loss
        portfolio.execute_trade(
            symbol=test_config.primary_symbol,
            direction=TradingDirection.BUY,
            quantity=100,
            price=test_config.base_price,
            stop_loss_pct=test_config.default_stop_loss,
        )

        # Price above stop
        portfolio.update_prices(
            {test_config.primary_symbol: test_config.base_price * 0.97}
        )
        triggered = portfolio.check_stop_losses()
        assert test_config.primary_symbol not in triggered

        # Price below stop
        stop_price = test_config.base_price * (1 - test_config.default_stop_loss)
        portfolio.update_prices({test_config.primary_symbol: stop_price * 0.99})
        triggered = portfolio.check_stop_losses()
        assert test_config.primary_symbol in triggered

    def test_portfolio_metrics_computation(
        self,
        test_config: TestConfig,
    ) -> None:
        """Test portfolio metrics are computed correctly."""
        portfolio = PortfolioService(initial_cash=test_config.initial_cash)

        # Execute some trades
        for i in range(5):
            price = test_config.base_price * (1 + i * 0.01)
            portfolio.execute_trade(
                symbol=test_config.primary_symbol,
                direction=TradingDirection.BUY,
                quantity=10,
                price=price,
            )
            portfolio.update_prices({test_config.primary_symbol: price * 1.02})
            portfolio.execute_trade(
                symbol=test_config.primary_symbol,
                direction=TradingDirection.SELL,
                quantity=10,
                price=price * 1.02,
            )

        sharpe = portfolio.calculate_sharpe_ratio()
        assert isinstance(sharpe, float)

        state = portfolio.get_state()
        assert state.realized_pnl_total != 0  # Some P&L from trades


class TestTradingAdapterIntegration:
    """Test trading adapter integration."""

    @pytest.mark.asyncio
    async def test_adapter_builds_trading_state(
        self,
        test_config: TestConfig,
        test_settings: Settings,
        mock_trading_adapter: AsyncMock,
    ) -> None:
        """Test adapter builds complete trading state."""
        state = await mock_trading_adapter.build_trading_state(test_config.primary_symbol)

        assert isinstance(state, TradingState)
        assert state.symbol == test_config.primary_symbol
        assert state.portfolio is not None
        assert state.analyst_signals is not None

    @pytest.mark.asyncio
    async def test_adapter_tools_creation(
        self,
        test_settings: Settings,
    ) -> None:
        """Test adapter creates LangGraph tools."""
        adapter = TradingServiceAdapter(
            mode=TradingMode.PAPER,
            settings=test_settings,
        )

        tools = adapter.get_tools()

        assert len(tools) == 5
        # Check tool names (they're decorated functions)
        tool_names = {t.name for t in tools}
        expected_names = {
            "get_trading_signal",
            "execute_trade",
            "get_portfolio_state",
            "get_market_data",
            "calculate_risk_metrics",
        }
        assert tool_names == expected_names

    @pytest.mark.asyncio
    async def test_adapter_mock_mode(
        self,
        test_config: TestConfig,
        test_settings: Settings,
    ) -> None:
        """Test adapter works in mock mode without external services."""
        adapter = TradingServiceAdapter(
            mode=TradingMode.PAPER,
            settings=test_settings,
        )

        # Should work without external services
        signal = await adapter.get_trading_signal(
            test_config.primary_symbol,
            datetime.now().strftime("%Y-%m-%d"),
        )

        assert signal.symbol == test_config.primary_symbol
        assert signal.direction in ["buy", "sell", "hold"]

        portfolio = await adapter.get_portfolio_state()
        assert portfolio.portfolio_value > 0


class TestServiceDataFlow:
    """Test data flow between services."""

    @pytest.mark.asyncio
    async def test_market_data_to_trading_state(
        self,
        market_data_factory: MarketDataFactory,
        portfolio_factory: PortfolioFactory,
        test_config: TestConfig,
    ) -> None:
        """Test market data flows correctly to trading state."""
        bars = market_data_factory.generate_bars()
        market_service = MarketDataService()

        # Calculate indicators from bars
        indicators = market_service.calculate_indicators(bars)
        ohlcv = market_service.bars_to_ohlcv(bars)
        regime = market_service.detect_market_regime(bars)

        # Build trading state
        state = TradingState(
            symbol=test_config.primary_symbol,
            timestamp=datetime.now(),
            current_price=bars[-1].close,
            ohlcv_history=ohlcv,
            technical_indicators=indicators,
            portfolio=portfolio_factory.create_with_position(),
            market_regime=regime,
        )

        # Validate state
        assert state.current_price == bars[-1].close
        assert state.ohlcv_history is not None
        assert state.ohlcv_history.shape[0] == len(bars)
        assert state.technical_indicators.rsi_14 is not None

    @pytest.mark.asyncio
    async def test_portfolio_state_persistence(
        self,
        test_config: TestConfig,
    ) -> None:
        """Test portfolio state is correctly persisted."""
        portfolio = PortfolioService(initial_cash=test_config.initial_cash)

        # Execute trade
        portfolio.execute_trade(
            symbol=test_config.primary_symbol,
            direction=TradingDirection.BUY,
            quantity=100,
            price=test_config.base_price,
        )

        # Get state snapshot
        state1 = portfolio.get_state()

        # Execute another trade
        portfolio.update_prices({test_config.primary_symbol: test_config.base_price * 1.1})

        # Get new state
        state2 = portfolio.get_state()

        # States should reflect changes
        assert state1.position_count == state2.position_count
        assert state2.unrealized_pnl > state1.unrealized_pnl  # Price went up
