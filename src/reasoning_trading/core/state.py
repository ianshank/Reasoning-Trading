"""
Trading state representations for MCTS tree nodes.

This module defines the complete state space for trading decisions, including
market features, portfolio state, analyst signals, and tree search metadata.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

import numpy as np
from numpy.typing import NDArray
from pydantic import BaseModel, Field


class MarketRegime(str, Enum):
    """Market regime classification for strategy selection."""

    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    MEAN_REVERTING = "mean_reverting"
    VOLATILE = "volatile"
    LOW_VOLATILITY = "low_volatility"
    UNKNOWN = "unknown"


class TechnicalIndicators(BaseModel):
    """Technical analysis indicators computed from price data."""

    # Trend indicators
    sma_20: float | None = Field(default=None, description="20-period Simple Moving Average")
    sma_50: float | None = Field(default=None, description="50-period Simple Moving Average")
    sma_200: float | None = Field(default=None, description="200-period Simple Moving Average")
    ema_12: float | None = Field(default=None, description="12-period Exponential Moving Average")
    ema_26: float | None = Field(default=None, description="26-period Exponential Moving Average")

    # Momentum indicators
    rsi_14: float | None = Field(default=None, ge=0, le=100, description="14-period RSI")
    macd: float | None = Field(default=None, description="MACD line")
    macd_signal: float | None = Field(default=None, description="MACD signal line")
    macd_histogram: float | None = Field(default=None, description="MACD histogram")

    # Volatility indicators
    atr_14: float | None = Field(default=None, ge=0, description="14-period Average True Range")
    bollinger_upper: float | None = Field(default=None, description="Bollinger Band upper")
    bollinger_middle: float | None = Field(default=None, description="Bollinger Band middle")
    bollinger_lower: float | None = Field(default=None, description="Bollinger Band lower")
    volatility_20: float | None = Field(
        default=None, ge=0, description="20-day historical volatility"
    )

    # Volume indicators
    volume_sma_20: float | None = Field(default=None, description="20-period Volume SMA")
    obv: float | None = Field(default=None, description="On-Balance Volume")

    # Additional indicators
    adx_14: float | None = Field(default=None, ge=0, le=100, description="14-period ADX")
    cci_20: float | None = Field(default=None, description="20-period Commodity Channel Index")
    stochastic_k: float | None = Field(default=None, ge=0, le=100, description="Stochastic %K")
    stochastic_d: float | None = Field(default=None, ge=0, le=100, description="Stochastic %D")

    def to_feature_vector(self) -> NDArray[np.float64]:
        """Convert indicators to normalized feature vector for model input."""
        features = [
            self.rsi_14 / 100.0 if self.rsi_14 is not None else 0.5,
            np.tanh((self.macd or 0) / 10.0),
            np.tanh((self.macd_histogram or 0) / 5.0),
            self.adx_14 / 100.0 if self.adx_14 is not None else 0.25,
            self.stochastic_k / 100.0 if self.stochastic_k is not None else 0.5,
            self.stochastic_d / 100.0 if self.stochastic_d is not None else 0.5,
            np.tanh((self.cci_20 or 0) / 200.0),
        ]
        return np.array(features, dtype=np.float64)


class AnalystSignals(BaseModel):
    """Aggregated signals from the multi-agent analyst system."""

    # Individual analyst scores (-1 to 1 scale)
    market_analyst_score: float = Field(
        default=0.0, ge=-1.0, le=1.0, description="Market analyst signal"
    )
    news_analyst_score: float = Field(
        default=0.0, ge=-1.0, le=1.0, description="News analyst signal"
    )
    social_sentiment_score: float = Field(
        default=0.0, ge=-1.0, le=1.0, description="Social sentiment signal"
    )
    fundamental_analyst_score: float = Field(
        default=0.0, ge=-1.0, le=1.0, description="Fundamental analyst signal"
    )
    macro_analyst_score: float = Field(
        default=0.0, ge=-1.0, le=1.0, description="Macro analyst signal"
    )

    # Confidence levels (0 to 1)
    market_analyst_confidence: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Market analyst confidence"
    )
    news_analyst_confidence: float = Field(
        default=0.5, ge=0.0, le=1.0, description="News analyst confidence"
    )
    social_sentiment_confidence: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Social sentiment confidence"
    )
    fundamental_analyst_confidence: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Fundamental analyst confidence"
    )
    macro_analyst_confidence: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Macro analyst confidence"
    )

    # Bull/Bear debate outcomes
    researcher_consensus: float = Field(
        default=0.0, ge=-1.0, le=1.0, description="Bull/Bear debate consensus"
    )
    debate_confidence: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Confidence in debate outcome"
    )

    # Raw evidence packets (optional, for detailed analysis)
    evidence_packets: dict[str, Any] = Field(
        default_factory=dict, description="Raw evidence from analysts"
    )

    def weighted_consensus(self) -> float:
        """Calculate confidence-weighted consensus across analysts."""
        scores = [
            self.market_analyst_score,
            self.news_analyst_score,
            self.social_sentiment_score,
            self.fundamental_analyst_score,
            self.macro_analyst_score,
        ]
        confidences = [
            self.market_analyst_confidence,
            self.news_analyst_confidence,
            self.social_sentiment_confidence,
            self.fundamental_analyst_confidence,
            self.macro_analyst_confidence,
        ]

        total_weight = sum(confidences)
        if total_weight == 0:
            return 0.0

        weighted_sum = sum(s * c for s, c in zip(scores, confidences))
        return weighted_sum / total_weight

    def to_feature_vector(self) -> NDArray[np.float64]:
        """Convert signals to feature vector for model input."""
        return np.array(
            [
                self.market_analyst_score,
                self.news_analyst_score,
                self.social_sentiment_score,
                self.fundamental_analyst_score,
                self.macro_analyst_score,
                self.market_analyst_confidence,
                self.news_analyst_confidence,
                self.social_sentiment_confidence,
                self.fundamental_analyst_confidence,
                self.macro_analyst_confidence,
                self.researcher_consensus,
                self.debate_confidence,
            ],
            dtype=np.float64,
        )


class PortfolioState(BaseModel):
    """Current portfolio state including positions and risk metrics."""

    # Cash and total value
    cash_balance: float = Field(default=0.0, description="Available cash")
    portfolio_value: float = Field(default=0.0, description="Total portfolio value")

    # Position tracking (symbol -> quantity)
    positions: dict[str, float] = Field(default_factory=dict, description="Current positions")
    position_values: dict[str, float] = Field(
        default_factory=dict, description="Position market values"
    )
    position_costs: dict[str, float] = Field(
        default_factory=dict, description="Position cost bases"
    )

    # P&L tracking
    unrealized_pnl: float = Field(default=0.0, description="Unrealized profit/loss")
    realized_pnl_today: float = Field(default=0.0, description="Today's realized P&L")
    realized_pnl_total: float = Field(default=0.0, description="Total realized P&L")

    # Risk metrics
    margin_used: float = Field(default=0.0, ge=0.0, description="Margin currently used")
    margin_available: float = Field(default=0.0, ge=0.0, description="Available margin")
    daily_var_95: float | None = Field(default=None, description="95% daily Value at Risk")
    max_drawdown: float = Field(default=0.0, ge=0.0, le=1.0, description="Maximum drawdown")
    current_drawdown: float = Field(default=0.0, ge=0.0, le=1.0, description="Current drawdown")

    # Concentration metrics
    largest_position_pct: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Largest position as % of portfolio"
    )
    position_count: int = Field(default=0, ge=0, description="Number of open positions")

    def get_position_size(self, symbol: str) -> float:
        """Get current position size for a symbol."""
        return self.positions.get(symbol, 0.0)

    def get_position_pct(self, symbol: str) -> float:
        """Get position as percentage of portfolio."""
        if self.portfolio_value <= 0:
            return 0.0
        value = self.position_values.get(symbol, 0.0)
        return value / self.portfolio_value

    def can_open_position(self, required_value: float) -> bool:
        """Check if we have enough cash to open a position."""
        return self.cash_balance >= required_value


@dataclass
class TradingState:
    """
    Complete state representation for MCTS tree nodes.

    This captures everything relevant to making a trading decision,
    including market data, portfolio state, analyst signals, and
    tree search metadata.
    """

    # Identity
    symbol: str
    timestamp: datetime

    # Market data
    current_price: float
    ohlcv_history: NDArray[np.float64] | None = None  # Shape: (N, 5) - O, H, L, C, V
    technical_indicators: TechnicalIndicators = field(default_factory=TechnicalIndicators)

    # Portfolio
    portfolio: PortfolioState = field(default_factory=PortfolioState)

    # Agent signals
    analyst_signals: AnalystSignals = field(default_factory=AnalystSignals)

    # Risk context
    risk_profile: str = "moderate"  # conservative, moderate, aggressive

    # Market context
    market_regime: MarketRegime = MarketRegime.UNKNOWN

    # Simulation metadata
    simulation_step: int = 0
    is_terminal: bool = False

    def copy(self) -> TradingState:
        """Create a deep copy of the state."""
        return TradingState(
            symbol=self.symbol,
            timestamp=self.timestamp,
            current_price=self.current_price,
            ohlcv_history=self.ohlcv_history.copy() if self.ohlcv_history is not None else None,
            technical_indicators=self.technical_indicators.model_copy(deep=True),
            portfolio=self.portfolio.model_copy(deep=True),
            analyst_signals=self.analyst_signals.model_copy(deep=True),
            risk_profile=self.risk_profile,
            market_regime=self.market_regime,
            simulation_step=self.simulation_step,
            is_terminal=self.is_terminal,
        )

    def to_feature_vector(self) -> NDArray[np.float64]:
        """
        Convert state to a fixed-size feature vector for model input.

        Returns:
            Normalized feature vector suitable for neural network input.
        """
        # Price features (if history available)
        if self.ohlcv_history is not None and len(self.ohlcv_history) > 0:
            returns = np.diff(self.ohlcv_history[:, 3]) / self.ohlcv_history[:-1, 3]
            recent_return = returns[-1] if len(returns) > 0 else 0.0
            volatility = np.std(returns) if len(returns) > 1 else 0.0
            price_features = np.array(
                [np.tanh(recent_return * 10), np.tanh(volatility * 10)], dtype=np.float64
            )
        else:
            price_features = np.zeros(2, dtype=np.float64)

        # Technical indicator features
        tech_features = self.technical_indicators.to_feature_vector()

        # Analyst signal features
        signal_features = self.analyst_signals.to_feature_vector()

        # Portfolio features
        position_pct = self.portfolio.get_position_pct(self.symbol)
        portfolio_features = np.array(
            [
                position_pct,
                np.tanh(self.portfolio.unrealized_pnl / max(self.portfolio.portfolio_value, 1)),
                self.portfolio.current_drawdown,
                self.portfolio.largest_position_pct,
            ],
            dtype=np.float64,
        )

        # Market regime one-hot encoding
        regime_map = {
            MarketRegime.TRENDING_UP: 0,
            MarketRegime.TRENDING_DOWN: 1,
            MarketRegime.MEAN_REVERTING: 2,
            MarketRegime.VOLATILE: 3,
            MarketRegime.LOW_VOLATILITY: 4,
            MarketRegime.UNKNOWN: 5,
        }
        regime_features = np.zeros(6, dtype=np.float64)
        regime_features[regime_map[self.market_regime]] = 1.0

        # Risk profile one-hot encoding
        risk_map = {"conservative": 0, "moderate": 1, "aggressive": 2}
        risk_features = np.zeros(3, dtype=np.float64)
        risk_features[risk_map.get(self.risk_profile, 1)] = 1.0

        return np.concatenate(
            [
                price_features,  # 2
                tech_features,  # 7
                signal_features,  # 12
                portfolio_features,  # 4
                regime_features,  # 6
                risk_features,  # 3
            ]
        )

    def update_from_market_data(
        self, new_price: float, new_ohlcv: NDArray[np.float64] | None = None
    ) -> None:
        """Update state with new market data."""
        self.current_price = new_price
        if new_ohlcv is not None:
            if self.ohlcv_history is None:
                self.ohlcv_history = new_ohlcv
            else:
                self.ohlcv_history = np.vstack([self.ohlcv_history, new_ohlcv])
                # Keep only last 200 bars
                if len(self.ohlcv_history) > 200:
                    self.ohlcv_history = self.ohlcv_history[-200:]

    def __hash__(self) -> int:
        """Hash based on key state components for tree lookup."""
        return hash(
            (
                self.symbol,
                self.timestamp.isoformat(),
                round(self.current_price, 4),
                self.simulation_step,
            )
        )
