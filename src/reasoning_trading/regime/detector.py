"""
Regime Detector for Trading MCTS.

High-level interface for regime detection that combines:
- HMM-based regime inference
- Technical indicator analysis
- Regime change detection and triggering
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, Callable

import numpy as np
from numpy.typing import NDArray
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from reasoning_trading.regime.hmm import HiddenMarkovModel, HMMConfig, RegimeState

if TYPE_CHECKING:
    from reasoning_trading.core.state import TradingState


class RegimeDetectorConfig(BaseSettings):
    """Configuration for regime detector."""

    model_config = SettingsConfigDict(
        env_prefix="REGIME_",
        case_sensitive=False,
        extra="ignore",
    )

    # Detection thresholds
    change_confidence_threshold: float = Field(
        default=0.7,
        ge=0.5,
        le=0.95,
        description="Confidence needed to confirm regime change",
    )
    min_regime_duration_seconds: int = Field(
        default=300,
        ge=60,
        le=3600,
        description="Minimum duration before regime can change",
    )

    # HMM settings
    use_hmm: bool = Field(
        default=True,
        description="Use HMM for regime detection",
    )
    hmm_weight: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="Weight for HMM prediction",
    )

    # Technical indicator settings
    volatility_high_threshold: float = Field(
        default=0.03,
        ge=0.01,
        le=0.10,
        description="Volatility threshold for high-vol regime",
    )
    volatility_low_threshold: float = Field(
        default=0.01,
        ge=0.001,
        le=0.05,
        description="Volatility threshold for low-vol regime",
    )
    trend_adx_threshold: float = Field(
        default=25,
        ge=10,
        le=50,
        description="ADX threshold for trending regime",
    )

    # History settings
    lookback_periods: int = Field(
        default=20,
        ge=5,
        le=100,
        description="Periods for feature calculation",
    )


@dataclass
class RegimeClassification:
    """Classification result from regime detector."""

    regime: str
    confidence: float

    # Alternative classifications
    regime_probabilities: dict[str, float] = field(default_factory=dict)

    # Contributing factors
    hmm_regime: str | None = None
    hmm_confidence: float = 0.0
    technical_regime: str | None = None
    technical_confidence: float = 0.0

    # Metadata
    timestamp: datetime = field(default_factory=datetime.now)
    symbol: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "regime": self.regime,
            "confidence": self.confidence,
            "regime_probabilities": self.regime_probabilities,
            "hmm_regime": self.hmm_regime,
            "hmm_confidence": self.hmm_confidence,
            "technical_regime": self.technical_regime,
            "technical_confidence": self.technical_confidence,
            "timestamp": self.timestamp.isoformat(),
            "symbol": self.symbol,
        }


@dataclass
class RegimeHistory:
    """History of regime classifications."""

    classifications: list[RegimeClassification] = field(default_factory=list)
    regime_durations: dict[str, float] = field(default_factory=dict)

    # Current regime
    current_regime: str = "neutral"
    current_regime_start: datetime = field(default_factory=datetime.now)

    def add_classification(self, classification: RegimeClassification) -> None:
        """Add a classification to history."""
        self.classifications.append(classification)

        # Update current regime if changed
        if classification.regime != self.current_regime:
            # Record duration of previous regime
            duration = (classification.timestamp - self.current_regime_start).total_seconds()
            if self.current_regime in self.regime_durations:
                self.regime_durations[self.current_regime] += duration
            else:
                self.regime_durations[self.current_regime] = duration

            self.current_regime = classification.regime
            self.current_regime_start = classification.timestamp

        # Limit history
        max_history = 1000
        if len(self.classifications) > max_history:
            self.classifications = self.classifications[-max_history:]

    def get_regime_frequency(self) -> dict[str, float]:
        """Get frequency of each regime."""
        if not self.classifications:
            return {}

        counts = {}
        for c in self.classifications:
            counts[c.regime] = counts.get(c.regime, 0) + 1

        total = len(self.classifications)
        return {k: v / total for k, v in counts.items()}

    def get_average_duration(self, regime: str) -> float | None:
        """Get average duration of a regime in seconds."""
        if regime not in self.regime_durations:
            return None
        return self.regime_durations[regime]


class RegimeDetector:
    """
    Regime detector combining HMM and technical analysis.

    Provides:
    - Real-time regime classification
    - Regime change detection
    - Trigger callbacks for batch recomputation
    """

    def __init__(
        self,
        config: RegimeDetectorConfig | None = None,
        hmm_config: HMMConfig | None = None,
        on_regime_change: Callable[[str, str, float], None] | None = None,
    ):
        """
        Initialize regime detector.

        Args:
            config: Detector configuration
            hmm_config: HMM configuration
            on_regime_change: Callback for regime changes (old, new, confidence)
        """
        self.config = config or RegimeDetectorConfig()
        self.hmm = HiddenMarkovModel(hmm_config) if self.config.use_hmm else None

        self.on_regime_change = on_regime_change

        # State
        self.history = RegimeHistory()
        self._last_classification: RegimeClassification | None = None

    def detect(self, state: TradingState) -> RegimeClassification:
        """
        Detect current market regime from trading state.

        Args:
            state: Current trading state

        Returns:
            RegimeClassification with regime and confidence
        """
        # Technical indicator-based detection
        tech_regime, tech_confidence = self._detect_from_technicals(state)

        # HMM-based detection
        hmm_regime, hmm_confidence = None, 0.0
        if self.hmm is not None and state.ohlcv_history is not None:
            hmm_regime, hmm_confidence = self._detect_from_hmm(state)

        # Combine predictions
        if hmm_regime is not None and self.hmm is not None:
            # Weighted combination
            regime, confidence = self._combine_predictions(
                tech_regime,
                tech_confidence,
                hmm_regime,
                hmm_confidence,
            )
        else:
            regime = tech_regime
            confidence = tech_confidence

        # Build classification
        classification = RegimeClassification(
            regime=regime,
            confidence=confidence,
            hmm_regime=hmm_regime,
            hmm_confidence=hmm_confidence,
            technical_regime=tech_regime,
            technical_confidence=tech_confidence,
            symbol=state.symbol,
        )

        # Get probability distribution
        if self.hmm is not None:
            classification.regime_probabilities = self.hmm.get_state_probabilities()
        else:
            classification.regime_probabilities = {regime: confidence}

        # Check for regime change
        self._check_regime_change(classification)

        # Update history
        self.history.add_classification(classification)
        self._last_classification = classification

        return classification

    def _detect_from_technicals(
        self,
        state: TradingState,
    ) -> tuple[str, float]:
        """
        Detect regime from technical indicators.

        Args:
            state: Trading state

        Returns:
            Tuple of (regime, confidence)
        """
        tech = state.technical_indicators
        volatility = tech.volatility_20 or 0.02
        adx = tech.adx_14 or 25
        rsi = tech.rsi_14 or 50

        # Determine base regime
        if volatility > self.config.volatility_high_threshold:
            regime = "high_volatility"
            confidence = min((volatility - self.config.volatility_high_threshold) / 0.02, 1.0) * 0.5 + 0.5
        elif volatility < self.config.volatility_low_threshold:
            regime = "low_volatility"
            confidence = min((self.config.volatility_low_threshold - volatility) / 0.005, 1.0) * 0.5 + 0.5
        elif adx > self.config.trend_adx_threshold:
            # Check trend direction
            sma_20 = tech.sma_20 or state.current_price
            sma_50 = tech.sma_50 or state.current_price

            if sma_20 > sma_50:
                regime = "bull"
            else:
                regime = "bear"
            confidence = min((adx - self.config.trend_adx_threshold) / 25, 1.0) * 0.5 + 0.5
        else:
            regime = "neutral"
            confidence = 0.5

        # Adjust confidence based on RSI extremes
        if rsi > 70 or rsi < 30:
            if regime == "bull" and rsi > 70:
                confidence = min(confidence + 0.1, 1.0)
            elif regime == "bear" and rsi < 30:
                confidence = min(confidence + 0.1, 1.0)

        return regime, confidence

    def _detect_from_hmm(
        self,
        state: TradingState,
    ) -> tuple[str, float]:
        """
        Detect regime using HMM.

        Args:
            state: Trading state

        Returns:
            Tuple of (regime, confidence)
        """
        if self.hmm is None or state.ohlcv_history is None:
            return "neutral", 0.5

        # Calculate returns and volatility from OHLCV
        if len(state.ohlcv_history) < 2:
            return "neutral", 0.5

        closes = state.ohlcv_history[:, 3]
        returns = np.diff(closes) / closes[:-1]

        if len(returns) == 0:
            return "neutral", 0.5

        recent_return = returns[-1]
        recent_volatility = np.std(returns[-self.config.lookback_periods:]) if len(returns) >= self.config.lookback_periods else np.std(returns)

        # Update HMM and get prediction
        regime, confidence = self.hmm.update_from_returns(recent_return, recent_volatility)

        return regime, confidence

    def _combine_predictions(
        self,
        tech_regime: str,
        tech_confidence: float,
        hmm_regime: str,
        hmm_confidence: float,
    ) -> tuple[str, float]:
        """
        Combine technical and HMM predictions.

        Args:
            tech_regime: Technical indicator regime
            tech_confidence: Technical confidence
            hmm_regime: HMM regime
            hmm_confidence: HMM confidence

        Returns:
            Combined (regime, confidence)
        """
        hmm_weight = self.config.hmm_weight
        tech_weight = 1.0 - hmm_weight

        # If both agree
        if tech_regime == hmm_regime:
            combined_confidence = (
                tech_weight * tech_confidence + hmm_weight * hmm_confidence
            )
            return tech_regime, combined_confidence

        # Disagree: pick higher confidence
        if hmm_confidence * hmm_weight > tech_confidence * tech_weight:
            return hmm_regime, hmm_confidence * 0.8  # Discount for disagreement
        else:
            return tech_regime, tech_confidence * 0.8

    def _check_regime_change(
        self,
        classification: RegimeClassification,
    ) -> None:
        """Check for regime change and trigger callback."""
        if self._last_classification is None:
            return

        if classification.regime == self._last_classification.regime:
            return

        # Check minimum duration
        time_in_regime = (
            classification.timestamp - self.history.current_regime_start
        ).total_seconds()

        if time_in_regime < self.config.min_regime_duration_seconds:
            return

        # Check confidence threshold
        if classification.confidence < self.config.change_confidence_threshold:
            return

        # Trigger callback
        if self.on_regime_change is not None:
            self.on_regime_change(
                self._last_classification.regime,
                classification.regime,
                classification.confidence,
            )

    def get_current_regime(self) -> tuple[str, float]:
        """
        Get current regime and confidence.

        Returns:
            Tuple of (regime, confidence)
        """
        if self._last_classification is None:
            return "neutral", 0.5

        return (
            self._last_classification.regime,
            self._last_classification.confidence,
        )

    def get_regime_probabilities(self) -> dict[str, float]:
        """Get probability distribution over regimes."""
        if self._last_classification is None:
            return {"neutral": 1.0}
        return self._last_classification.regime_probabilities

    def get_statistics(self) -> dict[str, Any]:
        """Get detector statistics."""
        return {
            "current_regime": self.history.current_regime,
            "regime_start": self.history.current_regime_start.isoformat(),
            "total_classifications": len(self.history.classifications),
            "regime_frequency": self.history.get_regime_frequency(),
            "regime_durations": self.history.regime_durations,
            "hmm_enabled": self.hmm is not None,
        }

    def save_state(self) -> dict[str, Any]:
        """Save detector state."""
        state = {
            "current_regime": self.history.current_regime,
            "current_regime_start": self.history.current_regime_start.isoformat(),
            "regime_durations": self.history.regime_durations,
        }

        if self.hmm is not None:
            state["hmm"] = self.hmm.save_state()

        return state

    def load_state(self, state: dict[str, Any]) -> None:
        """Load detector state."""
        self.history.current_regime = state.get("current_regime", "neutral")
        if "current_regime_start" in state:
            self.history.current_regime_start = datetime.fromisoformat(
                state["current_regime_start"]
            )
        self.history.regime_durations = state.get("regime_durations", {})

        if self.hmm is not None and "hmm" in state:
            self.hmm.load_state(state["hmm"])
