"""
Market data service for price feeds and indicators.

Provides abstracted access to market data from various sources
including Alpaca, Finnhub, and Yahoo Finance.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Protocol

import numpy as np
from numpy.typing import NDArray
import structlog

from reasoning_trading.config import Settings, get_settings
from reasoning_trading.core.state import MarketRegime, TechnicalIndicators

logger = structlog.get_logger(__name__)


class TimeFrame(str, Enum):
    """Supported timeframes for market data."""

    MINUTE_1 = "1Min"
    MINUTE_5 = "5Min"
    MINUTE_15 = "15Min"
    HOUR_1 = "1H"
    HOUR_4 = "4H"
    DAY_1 = "1D"
    WEEK_1 = "1W"


@dataclass
class Bar:
    """Single OHLCV bar."""

    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass
class MarketSnapshot:
    """Current market snapshot for a symbol."""

    symbol: str
    last_price: float
    bid: float | None = None
    ask: float | None = None
    bid_size: int | None = None
    ask_size: int | None = None
    volume: int = 0
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def spread(self) -> float | None:
        """Calculate bid-ask spread."""
        if self.bid is not None and self.ask is not None:
            return self.ask - self.bid
        return None

    @property
    def spread_pct(self) -> float | None:
        """Calculate spread as percentage of mid price."""
        if self.spread is not None and self.last_price > 0:
            return self.spread / self.last_price
        return None


class MarketDataProvider(Protocol):
    """Protocol for market data providers."""

    async def get_bars(
        self,
        symbol: str,
        timeframe: TimeFrame,
        start: datetime,
        end: datetime,
        limit: int | None = None,
    ) -> list[Bar]:
        """Get historical bars."""
        ...

    async def get_snapshot(self, symbol: str) -> MarketSnapshot:
        """Get current market snapshot."""
        ...


class MarketDataService:
    """
    Service for market data retrieval and processing.

    Provides:
    - Historical OHLCV data
    - Real-time snapshots
    - Technical indicator calculation
    - Market regime detection
    """

    def __init__(
        self,
        settings: Settings | None = None,
        provider: MarketDataProvider | None = None,
    ):
        """
        Initialize market data service.

        Args:
            settings: Application settings
            provider: Market data provider (uses default if not provided)
        """
        self.settings = settings or get_settings()
        self._provider = provider
        self._cache: dict[str, tuple[datetime, Any]] = {}
        self._cache_ttl = timedelta(seconds=60)

    async def get_historical_bars(
        self,
        symbol: str,
        timeframe: TimeFrame = TimeFrame.DAY_1,
        limit: int = 200,
    ) -> list[Bar]:
        """
        Get historical bars for a symbol.

        Args:
            symbol: Trading symbol
            timeframe: Bar timeframe
            limit: Maximum number of bars

        Returns:
            List of Bar objects
        """
        cache_key = f"bars:{symbol}:{timeframe}:{limit}"

        # Check cache
        if cache_key in self._cache:
            cached_time, cached_data = self._cache[cache_key]
            if datetime.now() - cached_time < self._cache_ttl:
                return cached_data

        # Calculate date range
        end = datetime.now()
        days_needed = limit * (1 if timeframe == TimeFrame.DAY_1 else 2)
        start = end - timedelta(days=days_needed)

        if self._provider is not None:
            bars = await self._provider.get_bars(symbol, timeframe, start, end, limit)
        else:
            bars = await self._get_bars_default(symbol, timeframe, start, end, limit)

        # Update cache
        self._cache[cache_key] = (datetime.now(), bars)

        return bars

    async def _get_bars_default(
        self,
        symbol: str,
        timeframe: TimeFrame,
        start: datetime,
        end: datetime,
        limit: int | None,
    ) -> list[Bar]:
        """Get bars using yfinance as default provider."""
        try:
            import yfinance as yf

            # Map timeframe to yfinance interval
            interval_map = {
                TimeFrame.MINUTE_1: "1m",
                TimeFrame.MINUTE_5: "5m",
                TimeFrame.MINUTE_15: "15m",
                TimeFrame.HOUR_1: "1h",
                TimeFrame.HOUR_4: "4h",
                TimeFrame.DAY_1: "1d",
                TimeFrame.WEEK_1: "1wk",
            }

            interval = interval_map.get(timeframe, "1d")

            # yfinance needs adjusted symbol for crypto
            yf_symbol = symbol.replace("/", "-")

            ticker = yf.Ticker(yf_symbol)
            df = ticker.history(start=start, end=end, interval=interval)

            if df.empty:
                logger.warning("No data returned from yfinance", symbol=symbol)
                return []

            bars = []
            for idx, row in df.iterrows():
                bars.append(
                    Bar(
                        timestamp=idx.to_pydatetime(),
                        open=float(row["Open"]),
                        high=float(row["High"]),
                        low=float(row["Low"]),
                        close=float(row["Close"]),
                        volume=int(row["Volume"]),
                    )
                )

            if limit is not None:
                bars = bars[-limit:]

            return bars

        except ImportError:
            logger.warning("yfinance not installed")
            return []
        except Exception as e:
            logger.error("Failed to get market data", error=str(e), symbol=symbol)
            return []

    async def get_snapshot(self, symbol: str) -> MarketSnapshot:
        """Get current market snapshot."""
        if self._provider is not None:
            return await self._provider.get_snapshot(symbol)

        # Use last bar as snapshot
        bars = await self.get_historical_bars(symbol, TimeFrame.MINUTE_1, 1)
        if bars:
            return MarketSnapshot(
                symbol=symbol,
                last_price=bars[-1].close,
                volume=bars[-1].volume,
                timestamp=bars[-1].timestamp,
            )

        return MarketSnapshot(symbol=symbol, last_price=0.0)

    def bars_to_ohlcv(self, bars: list[Bar]) -> NDArray[np.float64]:
        """
        Convert bars to OHLCV numpy array.

        Args:
            bars: List of Bar objects

        Returns:
            Array of shape (N, 5) with O, H, L, C, V columns
        """
        if not bars:
            return np.array([], dtype=np.float64).reshape(0, 5)

        return np.array(
            [[b.open, b.high, b.low, b.close, b.volume] for b in bars],
            dtype=np.float64,
        )

    def calculate_indicators(self, bars: list[Bar]) -> TechnicalIndicators:
        """
        Calculate technical indicators from price data.

        Args:
            bars: Historical bars

        Returns:
            TechnicalIndicators with computed values
        """
        if len(bars) < 2:
            return TechnicalIndicators()

        closes = np.array([b.close for b in bars])
        highs = np.array([b.high for b in bars])
        lows = np.array([b.low for b in bars])
        volumes = np.array([b.volume for b in bars])

        indicators = TechnicalIndicators()

        # Simple Moving Averages
        if len(closes) >= 20:
            indicators.sma_20 = float(np.mean(closes[-20:]))
        if len(closes) >= 50:
            indicators.sma_50 = float(np.mean(closes[-50:]))
        if len(closes) >= 200:
            indicators.sma_200 = float(np.mean(closes[-200:]))

        # Exponential Moving Averages
        if len(closes) >= 12:
            indicators.ema_12 = self._ema(closes, 12)
        if len(closes) >= 26:
            indicators.ema_26 = self._ema(closes, 26)

        # MACD
        if len(closes) >= 26:
            ema_12 = self._ema_series(closes, 12)
            ema_26 = self._ema_series(closes, 26)
            macd_line = ema_12 - ema_26
            if len(macd_line) >= 9:
                signal_line = self._ema_series(macd_line, 9)
                indicators.macd = float(macd_line[-1])
                indicators.macd_signal = float(signal_line[-1])
                indicators.macd_histogram = indicators.macd - indicators.macd_signal

        # RSI
        if len(closes) >= 15:
            indicators.rsi_14 = self._rsi(closes, 14)

        # Bollinger Bands
        if len(closes) >= 20:
            sma = np.mean(closes[-20:])
            std = np.std(closes[-20:])
            indicators.bollinger_middle = float(sma)
            indicators.bollinger_upper = float(sma + 2 * std)
            indicators.bollinger_lower = float(sma - 2 * std)

        # ATR (Average True Range)
        if len(closes) >= 15:
            indicators.atr_14 = self._atr(highs, lows, closes, 14)

        # Volatility
        if len(closes) >= 21:
            returns = np.diff(closes[-21:]) / closes[-21:-1]
            indicators.volatility_20 = float(np.std(returns))

        # Volume SMA
        if len(volumes) >= 20:
            indicators.volume_sma_20 = float(np.mean(volumes[-20:]))

        # Stochastic
        if len(closes) >= 14:
            k, d = self._stochastic(highs, lows, closes, 14, 3)
            indicators.stochastic_k = k
            indicators.stochastic_d = d

        return indicators

    def detect_market_regime(self, bars: list[Bar]) -> MarketRegime:
        """
        Detect current market regime.

        Uses trend strength, volatility, and mean-reversion indicators
        to classify the market environment.

        Args:
            bars: Historical bars

        Returns:
            Detected MarketRegime
        """
        if len(bars) < 50:
            return MarketRegime.UNKNOWN

        closes = np.array([b.close for b in bars])

        # Calculate trend indicators
        sma_20 = np.mean(closes[-20:])
        sma_50 = np.mean(closes[-50:])
        current_price = closes[-1]

        # Calculate volatility
        returns = np.diff(closes[-21:]) / closes[-21:-1]
        volatility = np.std(returns)

        # Calculate ADX for trend strength (simplified)
        adx = self._simplified_adx(closes, 14)

        # Determine regime
        is_trending = adx > 25
        is_above_smas = current_price > sma_20 > sma_50
        is_below_smas = current_price < sma_20 < sma_50
        is_volatile = volatility > 0.025  # 2.5% daily vol
        is_low_vol = volatility < 0.01  # 1% daily vol

        if is_trending and is_above_smas:
            return MarketRegime.TRENDING_UP
        elif is_trending and is_below_smas:
            return MarketRegime.TRENDING_DOWN
        elif is_volatile:
            return MarketRegime.VOLATILE
        elif is_low_vol:
            return MarketRegime.LOW_VOLATILITY
        elif not is_trending:
            return MarketRegime.MEAN_REVERTING
        else:
            return MarketRegime.UNKNOWN

    def _ema(self, data: NDArray[np.float64], period: int) -> float:
        """Calculate EMA for latest value."""
        return float(self._ema_series(data, period)[-1])

    def _ema_series(self, data: NDArray[np.float64], period: int) -> NDArray[np.float64]:
        """Calculate EMA series."""
        alpha = 2 / (period + 1)
        ema = np.zeros_like(data)
        ema[0] = data[0]
        for i in range(1, len(data)):
            ema[i] = alpha * data[i] + (1 - alpha) * ema[i - 1]
        return ema

    def _rsi(self, closes: NDArray[np.float64], period: int) -> float:
        """Calculate RSI."""
        deltas = np.diff(closes)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])

        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return float(100 - (100 / (1 + rs)))

    def _atr(
        self,
        highs: NDArray[np.float64],
        lows: NDArray[np.float64],
        closes: NDArray[np.float64],
        period: int,
    ) -> float:
        """Calculate Average True Range."""
        tr1 = highs[1:] - lows[1:]
        tr2 = np.abs(highs[1:] - closes[:-1])
        tr3 = np.abs(lows[1:] - closes[:-1])
        tr = np.maximum(tr1, np.maximum(tr2, tr3))
        return float(np.mean(tr[-period:]))

    def _stochastic(
        self,
        highs: NDArray[np.float64],
        lows: NDArray[np.float64],
        closes: NDArray[np.float64],
        k_period: int,
        d_period: int,
    ) -> tuple[float, float]:
        """Calculate Stochastic oscillator."""
        lowest_low = np.min(lows[-k_period:])
        highest_high = np.max(highs[-k_period:])

        if highest_high == lowest_low:
            k = 50.0
        else:
            k = 100 * (closes[-1] - lowest_low) / (highest_high - lowest_low)

        # Calculate %D as SMA of %K
        k_values = []
        for i in range(d_period):
            idx = -d_period + i
            ll = np.min(lows[idx - k_period + 1 : idx + 1])
            hh = np.max(highs[idx - k_period + 1 : idx + 1])
            if hh != ll:
                k_values.append(100 * (closes[idx] - ll) / (hh - ll))
            else:
                k_values.append(50.0)

        d = float(np.mean(k_values))
        return float(k), d

    def _simplified_adx(self, closes: NDArray[np.float64], period: int) -> float:
        """Simplified ADX calculation using price momentum."""
        if len(closes) < period + 1:
            return 25.0  # Default neutral

        # Use simple trend strength measure
        changes = np.abs(np.diff(closes[-period - 1 :]))
        total_change = np.sum(changes)
        net_change = np.abs(closes[-1] - closes[-period - 1])

        if total_change == 0:
            return 0.0

        # Ratio of directional movement
        efficiency = net_change / total_change
        return float(efficiency * 100)
