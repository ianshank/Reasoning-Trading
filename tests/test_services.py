"""
Tests for trading services.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from reasoning_trading.config import Settings, TradingMode
from reasoning_trading.core.actions import TradingAction, TradingDirection
from reasoning_trading.core.state import PortfolioState, TradingState
from reasoning_trading.services.adapter import (
    OrderResult,
    TradingServiceAdapter,
    TradingSignal,
)
from reasoning_trading.services.market_data import (
    Bar,
    MarketDataService,
    MarketSnapshot,
    TimeFrame,
)
from reasoning_trading.services.portfolio import (
    PortfolioService,
    Position,
    TradeRecord,
)


class TestTradingSignal:
    """Tests for TradingSignal model."""

    def test_creation(self) -> None:
        """Test signal creation."""
        signal = TradingSignal(
            symbol="AAPL",
            direction="buy",
            confidence=0.8,
            position_size_pct=0.1,
            stop_loss_pct=0.05,
            reasoning="Test",
        )

        assert signal.symbol == "AAPL"
        assert signal.direction == "buy"
        assert signal.confidence == 0.8

    def test_validation(self) -> None:
        """Test validation constraints."""
        with pytest.raises(ValueError):
            TradingSignal(
                symbol="AAPL",
                direction="buy",
                confidence=1.5,  # Invalid: > 1.0
                position_size_pct=0.1,
                stop_loss_pct=0.05,
            )


class TestOrderResult:
    """Tests for OrderResult model."""

    def test_creation(self) -> None:
        """Test order result creation."""
        result = OrderResult(
            order_id="test123",
            symbol="AAPL",
            side="buy",
            quantity=100,
            status="filled",
            filled_price=150.0,
        )

        assert result.order_id == "test123"
        assert result.status == "filled"


class TestTradingServiceAdapter:
    """Tests for TradingServiceAdapter."""

    @pytest.fixture
    def adapter(self, test_settings: Settings) -> TradingServiceAdapter:
        """Create adapter for testing."""
        return TradingServiceAdapter(
            mode=TradingMode.PAPER,
            settings=test_settings,
        )

    @pytest.mark.asyncio
    async def test_get_trading_signal_mock(self, adapter: TradingServiceAdapter) -> None:
        """Test getting trading signal (mock mode)."""
        signal = await adapter.get_trading_signal("AAPL", "2024-01-15")

        assert signal.symbol == "AAPL"
        assert signal.direction == "hold"  # Mock always returns hold

    @pytest.mark.asyncio
    async def test_execute_trade_mock(self, adapter: TradingServiceAdapter) -> None:
        """Test trade execution (mock mode)."""
        result = await adapter.execute_trade(
            symbol="AAPL",
            side="buy",
            quantity=100,
            order_type="market",
        )

        assert result.symbol == "AAPL"
        assert result.side == "buy"
        assert result.quantity == 100

    @pytest.mark.asyncio
    async def test_get_portfolio_state_mock(self, adapter: TradingServiceAdapter) -> None:
        """Test portfolio state retrieval (mock mode)."""
        state = await adapter.get_portfolio_state()

        assert isinstance(state, PortfolioState)
        assert state.portfolio_value > 0

    @pytest.mark.asyncio
    async def test_get_market_data_mock(self, adapter: TradingServiceAdapter) -> None:
        """Test market data retrieval (mock mode)."""
        data = await adapter.get_market_data("AAPL", "1D", 10)

        assert "symbol" in data
        assert data["symbol"] == "AAPL"

    @pytest.mark.asyncio
    async def test_calculate_risk_metrics_mock(self, adapter: TradingServiceAdapter) -> None:
        """Test risk metrics calculation (mock mode)."""
        metrics = await adapter.calculate_risk_metrics("AAPL", 0.1)

        assert "symbol" in metrics

    def test_get_tools(self, adapter: TradingServiceAdapter) -> None:
        """Test tools creation."""
        tools = adapter.get_tools()

        assert len(tools) == 5  # 5 trading tools
        assert all(callable(t) for t in tools)


class TestPosition:
    """Tests for Position class."""

    def test_market_value(self) -> None:
        """Test market value calculation."""
        pos = Position(
            symbol="AAPL",
            quantity=100,
            entry_price=150.0,
            entry_time=datetime.now(),
            current_price=160.0,
        )

        assert pos.market_value == 16000.0
        assert pos.cost_basis == 15000.0

    def test_unrealized_pnl(self) -> None:
        """Test unrealized P&L calculation."""
        pos = Position(
            symbol="AAPL",
            quantity=100,
            entry_price=150.0,
            entry_time=datetime.now(),
            current_price=160.0,
        )

        assert pos.unrealized_pnl == 1000.0
        assert pos.unrealized_pnl_pct == pytest.approx(1000.0 / 15000.0)

    def test_is_long_short(self) -> None:
        """Test position direction detection."""
        long_pos = Position(
            symbol="AAPL",
            quantity=100,
            entry_price=150.0,
            entry_time=datetime.now(),
        )
        assert long_pos.is_long
        assert not long_pos.is_short

        short_pos = Position(
            symbol="AAPL",
            quantity=-100,
            entry_price=150.0,
            entry_time=datetime.now(),
        )
        assert short_pos.is_short
        assert not short_pos.is_long

    def test_stop_loss_trigger(self) -> None:
        """Test stop-loss trigger detection."""
        pos = Position(
            symbol="AAPL",
            quantity=100,
            entry_price=150.0,
            entry_time=datetime.now(),
            current_price=140.0,
            stop_loss_price=142.0,
        )

        assert pos.should_stop_loss()

        pos.current_price = 145.0
        assert not pos.should_stop_loss()

    def test_take_profit_trigger(self) -> None:
        """Test take-profit trigger detection."""
        pos = Position(
            symbol="AAPL",
            quantity=100,
            entry_price=150.0,
            entry_time=datetime.now(),
            current_price=170.0,
            take_profit_price=165.0,
        )

        assert pos.should_take_profit()


class TestPortfolioService:
    """Tests for PortfolioService."""

    @pytest.fixture
    def portfolio(self) -> PortfolioService:
        """Create portfolio service for testing."""
        return PortfolioService(initial_cash=100000.0)

    def test_initial_state(self, portfolio: PortfolioService) -> None:
        """Test initial portfolio state."""
        assert portfolio.cash_balance == 100000.0
        assert portfolio.portfolio_value == 100000.0
        assert portfolio.positions_value == 0.0

    def test_execute_buy(self, portfolio: PortfolioService) -> None:
        """Test buy order execution."""
        trade = portfolio.execute_trade(
            symbol="AAPL",
            direction=TradingDirection.BUY,
            quantity=100,
            price=150.0,
        )

        assert trade.symbol == "AAPL"
        assert trade.side == "buy"
        assert portfolio.get_position("AAPL") is not None
        assert portfolio.get_position("AAPL").quantity == 100

    def test_execute_sell(self, portfolio: PortfolioService) -> None:
        """Test sell order execution."""
        # First buy
        portfolio.execute_trade(
            symbol="AAPL",
            direction=TradingDirection.BUY,
            quantity=100,
            price=150.0,
        )

        # Update price
        portfolio.update_prices({"AAPL": 160.0})

        # Then sell
        trade = portfolio.execute_trade(
            symbol="AAPL",
            direction=TradingDirection.SELL,
            quantity=100,
            price=160.0,
        )

        assert trade.pnl > 0  # Made profit
        assert portfolio.get_position("AAPL") is None

    def test_can_open_position(self, portfolio: PortfolioService) -> None:
        """Test position opening check."""
        can, reason = portfolio.can_open_position(
            symbol="AAPL",
            direction=TradingDirection.BUY,
            value=10000.0,
        )
        assert can

        # Try to open position larger than cash
        can, reason = portfolio.can_open_position(
            symbol="AAPL",
            direction=TradingDirection.BUY,
            value=200000.0,
        )
        assert not can
        assert "Insufficient cash" in reason

    def test_get_state(self, portfolio: PortfolioService) -> None:
        """Test state snapshot."""
        state = portfolio.get_state()

        assert isinstance(state, PortfolioState)
        assert state.cash_balance == 100000.0
        assert state.portfolio_value == 100000.0

    def test_check_stop_losses(self, portfolio: PortfolioService) -> None:
        """Test stop-loss checking."""
        # Buy with stop-loss
        portfolio.execute_trade(
            symbol="AAPL",
            direction=TradingDirection.BUY,
            quantity=100,
            price=150.0,
            stop_loss_pct=0.05,  # 5% stop
        )

        # Price drops below stop
        portfolio.update_prices({"AAPL": 140.0})

        triggered = portfolio.check_stop_losses()
        assert "AAPL" in triggered

    def test_calculate_sharpe(self, portfolio: PortfolioService) -> None:
        """Test Sharpe ratio calculation."""
        # Execute some trades
        for i in range(5):
            portfolio.execute_trade(
                symbol="AAPL",
                direction=TradingDirection.BUY,
                quantity=10,
                price=150.0 + i,
            )
            portfolio.update_prices({"AAPL": 155.0 + i})
            portfolio.execute_trade(
                symbol="AAPL",
                direction=TradingDirection.SELL,
                quantity=10,
                price=155.0 + i,
            )

        sharpe = portfolio.calculate_sharpe_ratio()
        assert isinstance(sharpe, float)

    def test_reset(self, portfolio: PortfolioService) -> None:
        """Test portfolio reset."""
        # Make some changes
        portfolio.execute_trade(
            symbol="AAPL",
            direction=TradingDirection.BUY,
            quantity=100,
            price=150.0,
        )

        # Reset
        portfolio.reset()

        assert portfolio.cash_balance == 100000.0
        assert len(portfolio.get_all_positions()) == 0


class TestMarketDataService:
    """Tests for MarketDataService."""

    @pytest.fixture
    def market_data(self, test_settings: Settings) -> MarketDataService:
        """Create market data service for testing."""
        return MarketDataService(settings=test_settings)

    def test_bars_to_ohlcv(self, market_data: MarketDataService) -> None:
        """Test bar to OHLCV conversion."""
        bars = [
            Bar(
                timestamp=datetime.now(),
                open=100.0,
                high=105.0,
                low=99.0,
                close=103.0,
                volume=100000,
            )
            for _ in range(10)
        ]

        ohlcv = market_data.bars_to_ohlcv(bars)

        assert ohlcv.shape == (10, 5)
        assert ohlcv[0, 0] == 100.0  # Open
        assert ohlcv[0, 3] == 103.0  # Close

    def test_calculate_indicators(self, market_data: MarketDataService) -> None:
        """Test indicator calculation."""
        # Generate sample bars
        np.random.seed(42)
        bars = []
        price = 100.0
        for i in range(50):
            returns = np.random.normal(0.001, 0.02)
            price *= (1 + returns)
            bars.append(
                Bar(
                    timestamp=datetime.now() - timedelta(days=50 - i),
                    open=price * 0.99,
                    high=price * 1.02,
                    low=price * 0.98,
                    close=price,
                    volume=100000,
                )
            )

        indicators = market_data.calculate_indicators(bars)

        assert indicators.sma_20 is not None
        assert indicators.rsi_14 is not None
        assert 0 <= indicators.rsi_14 <= 100

    def test_detect_market_regime(self, market_data: MarketDataService) -> None:
        """Test market regime detection."""
        # Generate trending up bars
        bars = []
        price = 100.0
        for i in range(60):
            price *= 1.005  # Consistent uptrend
            bars.append(
                Bar(
                    timestamp=datetime.now() - timedelta(days=60 - i),
                    open=price * 0.99,
                    high=price * 1.01,
                    low=price * 0.98,
                    close=price,
                    volume=100000,
                )
            )

        from reasoning_trading.core.state import MarketRegime

        regime = market_data.detect_market_regime(bars)
        assert regime in list(MarketRegime)


class TestMarketSnapshot:
    """Tests for MarketSnapshot."""

    def test_spread(self) -> None:
        """Test spread calculation."""
        snapshot = MarketSnapshot(
            symbol="AAPL",
            last_price=150.0,
            bid=149.95,
            ask=150.05,
        )

        assert snapshot.spread == 0.10
        assert snapshot.spread_pct == pytest.approx(0.10 / 150.0)

    def test_spread_none(self) -> None:
        """Test spread with missing bid/ask."""
        snapshot = MarketSnapshot(
            symbol="AAPL",
            last_price=150.0,
        )

        assert snapshot.spread is None
        assert snapshot.spread_pct is None
