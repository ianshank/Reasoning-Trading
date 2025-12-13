"""
Test data factories for generating realistic test data.

All values are derived from TestConfig - no hardcoded values.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Iterator

import numpy as np
from numpy.typing import NDArray

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
from reasoning_trading.services.market_data import Bar

from tests.config import ScenarioConfig, TestConfig, TestScenario, get_test_config


@dataclass
class MarketDataFactory:
    """Factory for generating market data."""

    config: TestConfig = field(default_factory=get_test_config)

    def __post_init__(self) -> None:
        """Initialize random state."""
        np.random.seed(self.config.random_seed)

    def generate_ohlcv(
        self,
        n_bars: int | None = None,
        base_price: float | None = None,
        trend: float = 1.0,
        volatility: float | None = None,
    ) -> NDArray[np.float64]:
        """
        Generate OHLCV data.

        Args:
            n_bars: Number of bars (defaults to config)
            base_price: Starting price (defaults to config)
            trend: Price trend multiplier per bar
            volatility: Daily volatility (defaults to config)

        Returns:
            Array of shape (n_bars, 5) with O, H, L, C, V
        """
        n = n_bars or self.config.ohlcv_bars
        price = base_price or self.config.base_price
        vol = volatility or self.config.price_volatility

        # Generate returns with trend
        trend_component = np.log(trend)
        returns = np.random.normal(trend_component, vol, n)
        close = price * np.exp(np.cumsum(returns))

        # Generate OHLCV
        high = close * (1 + np.abs(np.random.normal(0, vol / 2, n)))
        low = close * (1 - np.abs(np.random.normal(0, vol / 2, n)))
        open_price = np.roll(close, 1)
        open_price[0] = price
        volume = np.random.randint(100000, 1000000, n)

        return np.column_stack([open_price, high, low, close, volume]).astype(np.float64)

    def generate_bars(
        self,
        n_bars: int | None = None,
        base_price: float | None = None,
        start_date: datetime | None = None,
    ) -> list[Bar]:
        """Generate list of Bar objects."""
        ohlcv = self.generate_ohlcv(n_bars, base_price)
        start = start_date or datetime.now() - timedelta(days=len(ohlcv))

        bars = []
        for i, row in enumerate(ohlcv):
            bars.append(
                Bar(
                    timestamp=start + timedelta(days=i),
                    open=float(row[0]),
                    high=float(row[1]),
                    low=float(row[2]),
                    close=float(row[3]),
                    volume=int(row[4]),
                )
            )
        return bars

    def generate_price_series(
        self,
        n_points: int,
        scenario: ScenarioConfig,
    ) -> NDArray[np.float64]:
        """Generate price series for a scenario."""
        base = self.config.base_price
        trend = scenario.price_trend
        vol = self.config.price_volatility

        returns = np.random.normal(np.log(trend), vol, n_points)
        return base * np.exp(np.cumsum(returns))


@dataclass
class IndicatorFactory:
    """Factory for generating technical indicators."""

    config: TestConfig = field(default_factory=get_test_config)

    def create_neutral(self) -> TechnicalIndicators:
        """Create neutral/balanced indicators."""
        base = self.config.base_price
        return TechnicalIndicators(
            sma_20=base * 1.02,
            sma_50=base * 1.01,
            sma_200=base * 0.98,
            ema_12=base * 1.01,
            ema_26=base * 1.005,
            rsi_14=self.config.neutral_rsi,
            macd=0.5,
            macd_signal=0.3,
            macd_histogram=0.2,
            atr_14=base * self.config.price_volatility,
            bollinger_upper=base * 1.05,
            bollinger_middle=base,
            bollinger_lower=base * 0.95,
            volatility_20=self.config.price_volatility,
            volume_sma_20=500000.0,
            adx_14=25.0,
            stochastic_k=50.0,
            stochastic_d=48.0,
        )

    def create_from_scenario(self, scenario: ScenarioConfig) -> TechnicalIndicators:
        """Create indicators matching a scenario."""
        base = self.config.base_price
        indicators = self.create_neutral()

        # Override with scenario-specific values
        indicators.rsi_14 = scenario.rsi
        indicators.macd_histogram = scenario.macd_histogram

        # Adjust SMAs based on trend
        if scenario.price_trend > 1.0:
            indicators.sma_20 = base * 1.05
            indicators.sma_50 = base * 1.02
            indicators.adx_14 = 35.0  # Strong trend
        elif scenario.price_trend < 1.0:
            indicators.sma_20 = base * 0.95
            indicators.sma_50 = base * 0.98
            indicators.adx_14 = 35.0

        return indicators

    def create_overbought(self) -> TechnicalIndicators:
        """Create overbought indicators."""
        indicators = self.create_neutral()
        indicators.rsi_14 = self.config.overbought_rsi
        indicators.stochastic_k = 85.0
        indicators.stochastic_d = 82.0
        indicators.macd_histogram = 2.0
        return indicators

    def create_oversold(self) -> TechnicalIndicators:
        """Create oversold indicators."""
        indicators = self.create_neutral()
        indicators.rsi_14 = self.config.oversold_rsi
        indicators.stochastic_k = 15.0
        indicators.stochastic_d = 18.0
        indicators.macd_histogram = -2.0
        return indicators


@dataclass
class SignalFactory:
    """Factory for generating analyst signals."""

    config: TestConfig = field(default_factory=get_test_config)

    def create_neutral(self) -> AnalystSignals:
        """Create neutral signals."""
        return AnalystSignals(
            market_analyst_score=0.0,
            news_analyst_score=0.0,
            social_sentiment_score=0.0,
            fundamental_analyst_score=0.0,
            macro_analyst_score=0.0,
            market_analyst_confidence=0.5,
            news_analyst_confidence=0.5,
            social_sentiment_confidence=0.5,
            fundamental_analyst_confidence=0.5,
            macro_analyst_confidence=0.5,
            researcher_consensus=self.config.neutral_consensus,
            debate_confidence=0.5,
        )

    def create_from_scenario(self, scenario: ScenarioConfig) -> AnalystSignals:
        """Create signals matching a scenario."""
        # Distribute consensus across analysts
        base_score = scenario.consensus

        return AnalystSignals(
            market_analyst_score=base_score * 1.1,
            news_analyst_score=base_score * 0.9,
            social_sentiment_score=base_score * 0.7,
            fundamental_analyst_score=base_score * 1.2,
            macro_analyst_score=base_score * 0.8,
            market_analyst_confidence=0.7,
            news_analyst_confidence=0.6,
            social_sentiment_confidence=0.5,
            fundamental_analyst_confidence=0.8,
            macro_analyst_confidence=0.7,
            researcher_consensus=scenario.consensus,
            debate_confidence=abs(scenario.consensus) + 0.3,
        )

    def create_bullish(self) -> AnalystSignals:
        """Create bullish signals."""
        return AnalystSignals(
            market_analyst_score=0.6,
            news_analyst_score=0.5,
            social_sentiment_score=0.4,
            fundamental_analyst_score=0.7,
            macro_analyst_score=0.5,
            market_analyst_confidence=0.8,
            news_analyst_confidence=0.7,
            social_sentiment_confidence=0.6,
            fundamental_analyst_confidence=0.85,
            macro_analyst_confidence=0.75,
            researcher_consensus=self.config.bullish_consensus,
            debate_confidence=0.8,
        )

    def create_bearish(self) -> AnalystSignals:
        """Create bearish signals."""
        return AnalystSignals(
            market_analyst_score=-0.6,
            news_analyst_score=-0.5,
            social_sentiment_score=-0.4,
            fundamental_analyst_score=-0.7,
            macro_analyst_score=-0.5,
            market_analyst_confidence=0.8,
            news_analyst_confidence=0.7,
            social_sentiment_confidence=0.6,
            fundamental_analyst_confidence=0.85,
            macro_analyst_confidence=0.75,
            researcher_consensus=self.config.bearish_consensus,
            debate_confidence=0.8,
        )


@dataclass
class PortfolioFactory:
    """Factory for generating portfolio states."""

    config: TestConfig = field(default_factory=get_test_config)

    def create_empty(self) -> PortfolioState:
        """Create empty portfolio with just cash."""
        return PortfolioState(
            cash_balance=self.config.initial_cash,
            portfolio_value=self.config.initial_cash,
            positions={},
            position_values={},
            position_costs={},
            unrealized_pnl=0.0,
            realized_pnl_today=0.0,
            realized_pnl_total=0.0,
            current_drawdown=0.0,
            max_drawdown=0.0,
            largest_position_pct=0.0,
            position_count=0,
        )

    def create_with_position(
        self,
        symbol: str | None = None,
        position_pct: float | None = None,
    ) -> PortfolioState:
        """Create portfolio with a single position."""
        sym = symbol or self.config.primary_symbol
        pct = position_pct or self.config.default_position_size
        total = self.config.initial_portfolio_value

        position_value = total * pct
        cash = total - position_value

        return PortfolioState(
            cash_balance=cash,
            portfolio_value=total,
            positions={sym: position_value / self.config.base_price},
            position_values={sym: position_value},
            position_costs={sym: position_value * 0.95},  # 5% paper gain
            unrealized_pnl=position_value * 0.05,
            realized_pnl_today=0.0,
            realized_pnl_total=0.0,
            current_drawdown=0.02,
            max_drawdown=0.05,
            largest_position_pct=pct,
            position_count=1,
        )

    def create_diversified(self) -> PortfolioState:
        """Create diversified portfolio with multiple positions."""
        symbols = self.config.batch_symbols[:3]
        total = self.config.initial_portfolio_value
        per_position = total * 0.2  # 20% each
        cash = total - (per_position * len(symbols))

        positions = {}
        position_values = {}
        position_costs = {}

        for i, sym in enumerate(symbols):
            qty = per_position / (self.config.base_price * (1 + i * 0.1))
            positions[sym] = qty
            position_values[sym] = per_position
            position_costs[sym] = per_position * 0.98

        return PortfolioState(
            cash_balance=cash,
            portfolio_value=total,
            positions=positions,
            position_values=position_values,
            position_costs=position_costs,
            unrealized_pnl=per_position * 0.02 * len(symbols),
            realized_pnl_today=100.0,
            realized_pnl_total=500.0,
            current_drawdown=0.03,
            max_drawdown=0.08,
            largest_position_pct=0.2,
            position_count=len(symbols),
        )


@dataclass
class TradingStateFactory:
    """Factory for generating complete trading states."""

    config: TestConfig = field(default_factory=get_test_config)
    market_data: MarketDataFactory = field(default_factory=MarketDataFactory)
    indicators: IndicatorFactory = field(default_factory=IndicatorFactory)
    signals: SignalFactory = field(default_factory=SignalFactory)
    portfolio: PortfolioFactory = field(default_factory=PortfolioFactory)

    def create(
        self,
        symbol: str | None = None,
        scenario: ScenarioConfig | None = None,
    ) -> TradingState:
        """
        Create a trading state.

        Args:
            symbol: Trading symbol (defaults to config)
            scenario: Optional scenario to configure state

        Returns:
            Complete TradingState
        """
        sym = symbol or self.config.primary_symbol

        if scenario:
            indicators = self.indicators.create_from_scenario(scenario)
            signals = self.signals.create_from_scenario(scenario)
            ohlcv = self.market_data.generate_ohlcv(trend=scenario.price_trend)
            regime = self._scenario_to_regime(scenario)
        else:
            indicators = self.indicators.create_neutral()
            signals = self.signals.create_neutral()
            ohlcv = self.market_data.generate_ohlcv()
            regime = MarketRegime.UNKNOWN

        return TradingState(
            symbol=sym,
            timestamp=datetime.now(),
            current_price=self.config.base_price,
            ohlcv_history=ohlcv,
            technical_indicators=indicators,
            portfolio=self.portfolio.create_with_position(sym),
            analyst_signals=signals,
            risk_profile="moderate",
            market_regime=regime,
        )

    def create_for_scenario(self, scenario: TestScenario) -> TradingState:
        """Create state for a named scenario."""
        from tests.config import get_scenario_configs

        configs = get_scenario_configs(self.config)
        return self.create(scenario=configs[scenario])

    def _scenario_to_regime(self, scenario: ScenarioConfig) -> MarketRegime:
        """Map scenario to market regime."""
        mapping = {
            TestScenario.BULLISH: MarketRegime.TRENDING_UP,
            TestScenario.BEARISH: MarketRegime.TRENDING_DOWN,
            TestScenario.NEUTRAL: MarketRegime.MEAN_REVERTING,
            TestScenario.VOLATILE: MarketRegime.VOLATILE,
            TestScenario.TRENDING: MarketRegime.TRENDING_UP,
            TestScenario.MEAN_REVERTING: MarketRegime.MEAN_REVERTING,
        }
        return mapping.get(scenario.name, MarketRegime.UNKNOWN)


@dataclass
class ActionFactory:
    """Factory for generating trading actions."""

    config: TestConfig = field(default_factory=get_test_config)

    def create_buy(
        self,
        size: float | None = None,
        stop_loss: float | None = None,
        confidence: float = 0.7,
    ) -> TradingAction:
        """Create a buy action."""
        return TradingAction(
            direction=TradingDirection.BUY,
            position_size=PositionSizeAction(
                size_fraction=size or self.config.default_position_size
            ),
            stop_loss=StopLossAction(
                stop_loss_pct=stop_loss or self.config.default_stop_loss
            ),
            time_horizon=TimeHorizon.INTRADAY,
            confidence=confidence,
            reasoning="Factory generated buy action",
        )

    def create_sell(
        self,
        size: float | None = None,
        stop_loss: float | None = None,
        confidence: float = 0.7,
    ) -> TradingAction:
        """Create a sell action."""
        return TradingAction(
            direction=TradingDirection.SELL,
            position_size=PositionSizeAction(
                size_fraction=size or self.config.default_position_size
            ),
            stop_loss=StopLossAction(
                stop_loss_pct=stop_loss or self.config.default_stop_loss
            ),
            time_horizon=TimeHorizon.INTRADAY,
            confidence=confidence,
            reasoning="Factory generated sell action",
        )

    def create_hold(self) -> TradingAction:
        """Create a hold action."""
        return TradingAction.hold()

    def create_for_scenario(self, scenario: ScenarioConfig) -> TradingAction:
        """Create action matching scenario expectation."""
        if scenario.expected_direction == "buy":
            return self.create_buy(confidence=scenario.confidence_min + 0.1)
        elif scenario.expected_direction == "sell":
            return self.create_sell(confidence=scenario.confidence_min + 0.1)
        else:
            return self.create_hold()


# Convenience functions for direct access
def create_trading_state(
    symbol: str | None = None,
    scenario: TestScenario | None = None,
) -> TradingState:
    """Quick helper to create a trading state."""
    factory = TradingStateFactory()
    if scenario:
        return factory.create_for_scenario(scenario)
    return factory.create(symbol)


def create_ohlcv(n_bars: int | None = None) -> NDArray[np.float64]:
    """Quick helper to create OHLCV data."""
    return MarketDataFactory().generate_ohlcv(n_bars)


def create_portfolio(with_positions: bool = False) -> PortfolioState:
    """Quick helper to create portfolio state."""
    factory = PortfolioFactory()
    if with_positions:
        return factory.create_diversified()
    return factory.create_empty()
