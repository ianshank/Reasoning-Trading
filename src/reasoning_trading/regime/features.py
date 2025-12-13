"""
Feature extraction for regime detection.

Provides specialized features for regime classification:
- Price momentum features
- Volatility features
- Volume features
- Correlation features
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
from numpy.typing import NDArray
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class RegimeFeatureConfig(BaseSettings):
    """Configuration for regime feature extraction."""

    model_config = SettingsConfigDict(
        env_prefix="REGIME_FEATURE_",
        case_sensitive=False,
        extra="ignore",
    )

    # Lookback periods
    short_lookback: int = Field(default=5, ge=2, le=20)
    medium_lookback: int = Field(default=20, ge=10, le=50)
    long_lookback: int = Field(default=60, ge=30, le=200)

    # Volatility settings
    volatility_method: str = Field(
        default="std",
        description="Method for volatility calculation (std, parkinson, garman_klass)",
    )

    # Feature normalization
    normalize_features: bool = Field(default=True)
    clip_outliers: bool = Field(default=True)
    outlier_std: float = Field(default=3.0, ge=1.0, le=10.0)


@dataclass
class RegimeFeatures:
    """Extracted features for regime detection."""

    # Momentum features
    returns_short: float = 0.0
    returns_medium: float = 0.0
    returns_long: float = 0.0
    momentum_short: float = 0.0
    momentum_medium: float = 0.0

    # Volatility features
    volatility_short: float = 0.0
    volatility_medium: float = 0.0
    volatility_long: float = 0.0
    volatility_ratio: float = 0.0  # short/long
    volatility_trend: float = 0.0

    # Volume features
    volume_ratio: float = 0.0  # recent/avg
    volume_trend: float = 0.0
    volume_volatility: float = 0.0

    # Trend features
    trend_strength: float = 0.0  # ADX-like
    trend_direction: float = 0.0  # +1 up, -1 down

    # Mean reversion features
    distance_from_mean: float = 0.0
    bollinger_position: float = 0.0  # -1 to 1

    # Correlation features (if multi-asset)
    avg_correlation: float = 0.0

    # Metadata
    timestamp: str = ""
    symbol: str = ""

    def to_array(self) -> NDArray[np.float64]:
        """Convert to numpy array for model input."""
        return np.array([
            self.returns_short,
            self.returns_medium,
            self.returns_long,
            self.momentum_short,
            self.momentum_medium,
            self.volatility_short,
            self.volatility_medium,
            self.volatility_long,
            self.volatility_ratio,
            self.volatility_trend,
            self.volume_ratio,
            self.volume_trend,
            self.volume_volatility,
            self.trend_strength,
            self.trend_direction,
            self.distance_from_mean,
            self.bollinger_position,
            self.avg_correlation,
        ], dtype=np.float64)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "returns_short": self.returns_short,
            "returns_medium": self.returns_medium,
            "returns_long": self.returns_long,
            "momentum_short": self.momentum_short,
            "momentum_medium": self.momentum_medium,
            "volatility_short": self.volatility_short,
            "volatility_medium": self.volatility_medium,
            "volatility_long": self.volatility_long,
            "volatility_ratio": self.volatility_ratio,
            "volatility_trend": self.volatility_trend,
            "volume_ratio": self.volume_ratio,
            "volume_trend": self.volume_trend,
            "volume_volatility": self.volume_volatility,
            "trend_strength": self.trend_strength,
            "trend_direction": self.trend_direction,
            "distance_from_mean": self.distance_from_mean,
            "bollinger_position": self.bollinger_position,
            "avg_correlation": self.avg_correlation,
            "timestamp": self.timestamp,
            "symbol": self.symbol,
        }


class RegimeFeatureExtractor:
    """
    Extract features for regime detection.

    Processes OHLCV data to extract momentum, volatility,
    volume, and trend features useful for regime classification.
    """

    def __init__(self, config: RegimeFeatureConfig | None = None):
        """Initialize feature extractor."""
        self.config = config or RegimeFeatureConfig()

    def extract(
        self,
        ohlcv: NDArray[np.float64],
        symbol: str = "",
    ) -> RegimeFeatures:
        """
        Extract features from OHLCV data.

        Args:
            ohlcv: OHLCV array of shape (N, 5) - Open, High, Low, Close, Volume
            symbol: Symbol identifier

        Returns:
            RegimeFeatures object
        """
        if len(ohlcv) < self.config.long_lookback:
            # Not enough data, return defaults
            return RegimeFeatures(symbol=symbol)

        closes = ohlcv[:, 3]
        highs = ohlcv[:, 1]
        lows = ohlcv[:, 2]
        volumes = ohlcv[:, 4]

        features = RegimeFeatures(symbol=symbol)

        # Calculate returns
        returns = np.diff(closes) / closes[:-1]

        # Momentum features
        features.returns_short = self._safe_mean(returns[-self.config.short_lookback:])
        features.returns_medium = self._safe_mean(returns[-self.config.medium_lookback:])
        features.returns_long = self._safe_mean(returns[-self.config.long_lookback:])

        features.momentum_short = (
            closes[-1] / closes[-self.config.short_lookback] - 1
            if len(closes) >= self.config.short_lookback
            else 0
        )
        features.momentum_medium = (
            closes[-1] / closes[-self.config.medium_lookback] - 1
            if len(closes) >= self.config.medium_lookback
            else 0
        )

        # Volatility features
        features.volatility_short = self._calculate_volatility(
            returns[-self.config.short_lookback:]
        )
        features.volatility_medium = self._calculate_volatility(
            returns[-self.config.medium_lookback:]
        )
        features.volatility_long = self._calculate_volatility(
            returns[-self.config.long_lookback:]
        )

        if features.volatility_long > 0:
            features.volatility_ratio = features.volatility_short / features.volatility_long
        else:
            features.volatility_ratio = 1.0

        # Volatility trend (is volatility increasing?)
        mid_point = len(returns) // 2
        if mid_point > self.config.short_lookback:
            vol_recent = self._calculate_volatility(returns[-self.config.short_lookback:])
            vol_past = self._calculate_volatility(returns[mid_point - self.config.short_lookback:mid_point])
            if vol_past > 0:
                features.volatility_trend = (vol_recent - vol_past) / vol_past
            else:
                features.volatility_trend = 0.0

        # Volume features
        avg_volume = self._safe_mean(volumes[-self.config.medium_lookback:])
        recent_volume = self._safe_mean(volumes[-self.config.short_lookback:])

        if avg_volume > 0:
            features.volume_ratio = recent_volume / avg_volume
        else:
            features.volume_ratio = 1.0

        features.volume_volatility = self._safe_std(volumes[-self.config.medium_lookback:]) / (avg_volume + 1e-10)

        # Volume trend
        if len(volumes) >= self.config.medium_lookback * 2:
            vol_recent = self._safe_mean(volumes[-self.config.short_lookback:])
            vol_past = self._safe_mean(volumes[-self.config.medium_lookback:-self.config.short_lookback])
            if vol_past > 0:
                features.volume_trend = (vol_recent - vol_past) / vol_past
            else:
                features.volume_trend = 0.0

        # Trend features (simplified ADX-like)
        features.trend_strength = self._calculate_trend_strength(closes, highs, lows)
        features.trend_direction = 1.0 if features.returns_medium > 0 else -1.0

        # Mean reversion features
        mean_price = self._safe_mean(closes[-self.config.medium_lookback:])
        std_price = self._safe_std(closes[-self.config.medium_lookback:])

        if mean_price > 0:
            features.distance_from_mean = (closes[-1] - mean_price) / mean_price
        else:
            features.distance_from_mean = 0.0

        # Bollinger position
        if std_price > 0:
            features.bollinger_position = (closes[-1] - mean_price) / (2 * std_price)
            features.bollinger_position = np.clip(features.bollinger_position, -1, 1)
        else:
            features.bollinger_position = 0.0

        # Normalize if configured
        if self.config.normalize_features:
            features = self._normalize_features(features)

        return features

    def _calculate_volatility(
        self,
        returns: NDArray[np.float64],
    ) -> float:
        """Calculate volatility using configured method."""
        if len(returns) < 2:
            return 0.0

        if self.config.volatility_method == "std":
            return float(np.std(returns))
        else:
            # Default to standard deviation
            return float(np.std(returns))

    def _calculate_trend_strength(
        self,
        closes: NDArray[np.float64],
        highs: NDArray[np.float64],
        lows: NDArray[np.float64],
    ) -> float:
        """
        Calculate trend strength (simplified ADX).

        Uses directional movement to estimate trend strength.
        """
        if len(closes) < self.config.medium_lookback:
            return 0.0

        lookback = self.config.medium_lookback

        # Simplified: use price range and direction consistency
        price_range = np.max(closes[-lookback:]) - np.min(closes[-lookback:])
        avg_price = np.mean(closes[-lookback:])

        if avg_price > 0:
            relative_range = price_range / avg_price
        else:
            return 0.0

        # Calculate direction consistency
        returns = np.diff(closes[-lookback:])
        positive_returns = np.sum(returns > 0)
        negative_returns = np.sum(returns < 0)

        total = positive_returns + negative_returns
        if total == 0:
            direction_consistency = 0.5
        else:
            direction_consistency = max(positive_returns, negative_returns) / total

        # Combine: strong trend = high range + consistent direction
        trend_strength = relative_range * direction_consistency * 100

        return float(np.clip(trend_strength, 0, 100))

    def _normalize_features(self, features: RegimeFeatures) -> RegimeFeatures:
        """Normalize features to reasonable ranges."""
        # Clip returns to ±10%
        features.returns_short = np.clip(features.returns_short, -0.1, 0.1)
        features.returns_medium = np.clip(features.returns_medium, -0.1, 0.1)
        features.returns_long = np.clip(features.returns_long, -0.1, 0.1)

        # Clip momentum to ±50%
        features.momentum_short = np.clip(features.momentum_short, -0.5, 0.5)
        features.momentum_medium = np.clip(features.momentum_medium, -0.5, 0.5)

        # Normalize volatility to typical range [0, 0.1]
        max_vol = 0.1
        features.volatility_short = min(features.volatility_short / max_vol, 1.0)
        features.volatility_medium = min(features.volatility_medium / max_vol, 1.0)
        features.volatility_long = min(features.volatility_long / max_vol, 1.0)

        # Clip ratios
        features.volatility_ratio = np.clip(features.volatility_ratio, 0.1, 10.0) / 10.0
        features.volume_ratio = np.clip(features.volume_ratio, 0.1, 10.0) / 10.0

        # Normalize trend strength to [0, 1]
        features.trend_strength = features.trend_strength / 100.0

        return features

    @staticmethod
    def _safe_mean(arr: NDArray[np.float64]) -> float:
        """Calculate mean safely handling empty arrays."""
        if len(arr) == 0:
            return 0.0
        return float(np.mean(arr))

    @staticmethod
    def _safe_std(arr: NDArray[np.float64]) -> float:
        """Calculate std safely handling small arrays."""
        if len(arr) < 2:
            return 0.0
        return float(np.std(arr))

    def extract_batch(
        self,
        ohlcv_data: dict[str, NDArray[np.float64]],
    ) -> dict[str, RegimeFeatures]:
        """
        Extract features for multiple symbols.

        Args:
            ohlcv_data: Dictionary mapping symbols to OHLCV arrays

        Returns:
            Dictionary mapping symbols to RegimeFeatures
        """
        return {
            symbol: self.extract(ohlcv, symbol)
            for symbol, ohlcv in ohlcv_data.items()
        }
