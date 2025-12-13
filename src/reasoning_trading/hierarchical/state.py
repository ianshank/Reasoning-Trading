"""
Hierarchical state abstraction for trading MCTS.

Implements multi-level state compression where:
- Strategic level: ~50 features (macro indicators, portfolio-level)
- Tactical level: ~200 features (individual security, technical)
- Execution level: ~500 features (microstructure, order book)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Protocol

import numpy as np
from numpy.typing import NDArray
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

if TYPE_CHECKING:
    from reasoning_trading.core.state import TradingState
    from reasoning_trading.hierarchical.levels import HierarchyLevelType, LevelState


class AbstractionMethod(str, Enum):
    """Methods for state abstraction."""

    PCA = "pca"
    AUTOENCODER = "autoencoder"
    ATTENTION = "attention"
    HANDCRAFTED = "handcrafted"


class StateAbstractionConfig(BaseSettings):
    """Configuration for state abstraction."""

    model_config = SettingsConfigDict(
        env_prefix="STATE_ABSTRACTION_",
        case_sensitive=False,
        extra="ignore",
    )

    method: AbstractionMethod = Field(
        default=AbstractionMethod.HANDCRAFTED,
        description="Abstraction method to use",
    )

    # Dimension targets
    strategic_dim: int = Field(default=50, ge=10, le=500)
    tactical_dim: int = Field(default=200, ge=50, le=1000)
    execution_dim: int = Field(default=500, ge=100, le=2000)

    # PCA settings
    pca_variance_threshold: float = Field(
        default=0.95,
        ge=0.5,
        le=1.0,
        description="Variance to retain in PCA",
    )

    # Autoencoder settings
    autoencoder_hidden_dims: list[int] = Field(
        default=[256, 128, 64],
        description="Hidden layer dimensions for autoencoder",
    )
    autoencoder_latent_dim: int = Field(
        default=32,
        description="Latent dimension for autoencoder",
    )


class StateAbstractor(Protocol):
    """Protocol for state abstraction functions."""

    def abstract(self, state: TradingState, target_dim: int) -> NDArray[np.float64]:
        """Abstract trading state to target dimension."""
        ...


@dataclass
class HierarchicalState:
    """
    Multi-level state representation for hierarchical MCTS.

    Maintains views of the trading state at different abstraction levels,
    enabling efficient planning at each level of the hierarchy.
    """

    # Raw trading state
    raw_state: TradingState

    # Abstracted representations at each level
    strategic_features: NDArray[np.float64] | None = None
    tactical_features: NDArray[np.float64] | None = None
    execution_features: NDArray[np.float64] | None = None

    # Metadata
    abstraction_method: AbstractionMethod = AbstractionMethod.HANDCRAFTED
    created_at: float = field(default_factory=lambda: __import__("time").time())

    @property
    def has_strategic(self) -> bool:
        """Check if strategic features are computed."""
        return self.strategic_features is not None

    @property
    def has_tactical(self) -> bool:
        """Check if tactical features are computed."""
        return self.tactical_features is not None

    @property
    def has_execution(self) -> bool:
        """Check if execution features are computed."""
        return self.execution_features is not None

    def get_features(self, level: str) -> NDArray[np.float64] | None:
        """Get features for a specific level."""
        level_map = {
            "strategic": self.strategic_features,
            "tactical": self.tactical_features,
            "execution": self.execution_features,
        }
        return level_map.get(level.lower())


class StateAbstraction:
    """
    Hierarchical state abstraction engine.

    Transforms raw trading states into compressed representations
    suitable for each level of the hierarchy.
    """

    def __init__(self, config: StateAbstractionConfig | None = None):
        """Initialize state abstraction."""
        self.config = config or StateAbstractionConfig()

        # Lazy-initialized abstractors
        self._strategic_abstractor: StateAbstractor | None = None
        self._tactical_abstractor: StateAbstractor | None = None
        self._execution_abstractor: StateAbstractor | None = None

    def create_hierarchical_state(self, state: TradingState) -> HierarchicalState:
        """
        Create hierarchical state with all abstraction levels.

        Args:
            state: Raw trading state

        Returns:
            HierarchicalState with all levels computed
        """
        return HierarchicalState(
            raw_state=state,
            strategic_features=self._abstract_strategic(state),
            tactical_features=self._abstract_tactical(state),
            execution_features=self._abstract_execution(state),
            abstraction_method=self.config.method,
        )

    def abstract_for_level(
        self,
        state: TradingState,
        level: str,
    ) -> NDArray[np.float64]:
        """
        Abstract state for a specific hierarchy level.

        Args:
            state: Raw trading state
            level: Hierarchy level ("strategic", "tactical", "execution")

        Returns:
            Abstracted feature vector
        """
        level_methods = {
            "strategic": self._abstract_strategic,
            "tactical": self._abstract_tactical,
            "execution": self._abstract_execution,
        }

        if level.lower() not in level_methods:
            raise ValueError(f"Unknown level: {level}")

        return level_methods[level.lower()](state)

    def _abstract_strategic(self, state: TradingState) -> NDArray[np.float64]:
        """
        Abstract state for strategic level (~50 features).

        Focus on:
        - Portfolio-level metrics
        - Macro regime indicators
        - Asset class correlations
        - Risk metrics
        """
        features = []

        # 1. Portfolio metrics (5 features)
        portfolio = state.portfolio
        features.extend([
            portfolio.portfolio_value / max(portfolio.cash_balance + portfolio.portfolio_value, 1),
            portfolio.current_drawdown,
            portfolio.max_drawdown,
            portfolio.largest_position_pct,
            portfolio.position_count / 20.0,  # Normalized
        ])

        # 2. Market regime one-hot (6 features)
        from reasoning_trading.core.state import MarketRegime
        regime_vec = np.zeros(6)
        regime_map = {
            MarketRegime.TRENDING_UP: 0,
            MarketRegime.TRENDING_DOWN: 1,
            MarketRegime.MEAN_REVERTING: 2,
            MarketRegime.VOLATILE: 3,
            MarketRegime.LOW_VOLATILITY: 4,
            MarketRegime.UNKNOWN: 5,
        }
        regime_vec[regime_map[state.market_regime]] = 1.0
        features.extend(regime_vec.tolist())

        # 3. Analyst consensus (4 features)
        signals = state.analyst_signals
        features.extend([
            signals.weighted_consensus(),
            signals.debate_confidence,
            signals.macro_analyst_score,
            signals.fundamental_analyst_score,
        ])

        # 4. Technical summary (7 features - aggregated)
        tech = state.technical_indicators
        features.extend([
            (tech.rsi_14 or 50) / 100,
            np.tanh((tech.macd or 0) / 10),
            (tech.adx_14 or 25) / 100,
            np.tanh((tech.cci_20 or 0) / 200),
            (tech.stochastic_k or 50) / 100,
            np.tanh(tech.volatility_20 or 0.02),
            1.0 if (tech.sma_20 or 0) > (tech.sma_50 or 0) else 0.0,  # Trend signal
        ])

        # 5. Risk profile one-hot (3 features)
        risk_map = {"conservative": 0, "moderate": 1, "aggressive": 2}
        risk_vec = np.zeros(3)
        risk_vec[risk_map.get(state.risk_profile, 1)] = 1.0
        features.extend(risk_vec.tolist())

        # 6. OHLCV summary if available (8 features)
        if state.ohlcv_history is not None and len(state.ohlcv_history) >= 20:
            closes = state.ohlcv_history[-20:, 3]
            volumes = state.ohlcv_history[-20:, 4]
            returns = np.diff(closes) / closes[:-1]

            features.extend([
                np.mean(returns),
                np.std(returns),
                np.min(returns),
                np.max(returns),
                (closes[-1] - closes[0]) / closes[0],  # 20-bar return
                np.mean(volumes) / (np.max(volumes) + 1e-8),  # Volume ratio
                np.std(volumes) / (np.mean(volumes) + 1e-8),  # Volume volatility
                1.0 if closes[-1] > np.mean(closes) else 0.0,  # Above average
            ])
        else:
            features.extend([0.0] * 8)

        # Convert to array and pad/truncate
        feature_array = np.array(features, dtype=np.float64)
        return self._pad_or_truncate(feature_array, self.config.strategic_dim)

    def _abstract_tactical(self, state: TradingState) -> NDArray[np.float64]:
        """
        Abstract state for tactical level (~200 features).

        Focus on:
        - Individual security signals
        - Technical indicators
        - Momentum and mean reversion
        - Position-level details
        """
        features = []

        # 1. All technical indicators (expand more than strategic)
        tech = state.technical_indicators
        features.extend([
            (tech.sma_20 or 0) / max(state.current_price, 1),
            (tech.sma_50 or 0) / max(state.current_price, 1),
            (tech.sma_200 or 0) / max(state.current_price, 1),
            (tech.ema_12 or 0) / max(state.current_price, 1),
            (tech.ema_26 or 0) / max(state.current_price, 1),
            (tech.rsi_14 or 50) / 100,
            np.tanh((tech.macd or 0) / 10),
            np.tanh((tech.macd_signal or 0) / 10),
            np.tanh((tech.macd_histogram or 0) / 5),
            tech.atr_14 or 0,
            (tech.bollinger_upper or 0) / max(state.current_price, 1),
            (tech.bollinger_middle or 0) / max(state.current_price, 1),
            (tech.bollinger_lower or 0) / max(state.current_price, 1),
            tech.volatility_20 or 0.02,
            (tech.volume_sma_20 or 0) / 1e6,  # Normalized
            (tech.adx_14 or 25) / 100,
            np.tanh((tech.cci_20 or 0) / 200),
            (tech.stochastic_k or 50) / 100,
            (tech.stochastic_d or 50) / 100,
        ])

        # 2. All analyst signals (12 features)
        signals = state.analyst_signals
        features.extend([
            signals.market_analyst_score,
            signals.news_analyst_score,
            signals.social_sentiment_score,
            signals.fundamental_analyst_score,
            signals.macro_analyst_score,
            signals.market_analyst_confidence,
            signals.news_analyst_confidence,
            signals.social_sentiment_confidence,
            signals.fundamental_analyst_confidence,
            signals.macro_analyst_confidence,
            signals.researcher_consensus,
            signals.debate_confidence,
        ])

        # 3. Position details (8 features)
        portfolio = state.portfolio
        position_qty = portfolio.get_position_size(state.symbol)
        position_pct = portfolio.get_position_pct(state.symbol)
        features.extend([
            position_qty / 100,  # Normalized
            position_pct,
            portfolio.unrealized_pnl / max(portfolio.portfolio_value, 1),
            portfolio.realized_pnl_today / max(portfolio.portfolio_value, 1),
            portfolio.current_drawdown,
            portfolio.cash_balance / max(portfolio.portfolio_value, 1),
            portfolio.margin_used / max(portfolio.margin_available + 1, 1),
            portfolio.daily_var_95 or 0,
        ])

        # 4. OHLCV detailed history (more granular)
        if state.ohlcv_history is not None and len(state.ohlcv_history) >= 5:
            # Last 50 bars worth of features
            for lookback in [5, 10, 20, 50]:
                if len(state.ohlcv_history) >= lookback:
                    data = state.ohlcv_history[-lookback:]
                    opens = data[:, 0]
                    highs = data[:, 1]
                    lows = data[:, 2]
                    closes = data[:, 3]
                    volumes = data[:, 4]
                    returns = np.diff(closes) / closes[:-1] if len(closes) > 1 else [0]

                    features.extend([
                        np.mean(returns),
                        np.std(returns),
                        (closes[-1] - closes[0]) / closes[0] if closes[0] != 0 else 0,
                        np.mean(highs - lows) / closes[-1] if closes[-1] != 0 else 0,  # Average range
                        np.mean(volumes) / 1e6,
                    ])
                else:
                    features.extend([0.0] * 5)
        else:
            features.extend([0.0] * 20)  # 4 lookbacks * 5 features

        # 5. Market regime (6 features)
        from reasoning_trading.core.state import MarketRegime
        regime_vec = np.zeros(6)
        regime_map = {
            MarketRegime.TRENDING_UP: 0,
            MarketRegime.TRENDING_DOWN: 1,
            MarketRegime.MEAN_REVERTING: 2,
            MarketRegime.VOLATILE: 3,
            MarketRegime.LOW_VOLATILITY: 4,
            MarketRegime.UNKNOWN: 5,
        }
        regime_vec[regime_map[state.market_regime]] = 1.0
        features.extend(regime_vec.tolist())

        # Convert and resize
        feature_array = np.array(features, dtype=np.float64)
        return self._pad_or_truncate(feature_array, self.config.tactical_dim)

    def _abstract_execution(self, state: TradingState) -> NDArray[np.float64]:
        """
        Abstract state for execution level (~500 features).

        Focus on:
        - Microstructure (order book, spread, depth)
        - Short-term price dynamics
        - Volume patterns
        - Execution quality metrics
        """
        features = []

        # 1. Current price and position
        features.extend([
            state.current_price,
            state.portfolio.get_position_size(state.symbol),
            state.portfolio.cash_balance,
        ])

        # 2. Technical indicators (all available)
        tech = state.technical_indicators
        features.extend([
            tech.sma_20 or state.current_price,
            tech.sma_50 or state.current_price,
            tech.ema_12 or state.current_price,
            tech.ema_26 or state.current_price,
            tech.rsi_14 or 50,
            tech.macd or 0,
            tech.macd_signal or 0,
            tech.macd_histogram or 0,
            tech.atr_14 or 0,
            tech.bollinger_upper or state.current_price * 1.02,
            tech.bollinger_lower or state.current_price * 0.98,
            tech.volatility_20 or 0.02,
            tech.adx_14 or 25,
            tech.cci_20 or 0,
            tech.stochastic_k or 50,
            tech.stochastic_d or 50,
        ])

        # 3. Full OHLCV history (flattened, last 50 bars)
        if state.ohlcv_history is not None:
            data = state.ohlcv_history[-50:] if len(state.ohlcv_history) >= 50 else state.ohlcv_history
            flattened = data.flatten()
            features.extend(flattened.tolist())
            # Pad if needed
            if len(data) < 50:
                features.extend([0.0] * (50 * 5 - len(flattened)))
        else:
            features.extend([0.0] * 250)  # 50 bars * 5 OHLCV

        # 4. Microstructure estimates (simulated for now)
        # In production, these would come from order book data
        spread_estimate = state.current_price * 0.001  # 0.1% spread
        features.extend([
            spread_estimate,
            spread_estimate / state.current_price,  # Relative spread
            np.random.uniform(0.4, 0.6),  # Order imbalance (simulated)
            np.random.uniform(1000, 10000),  # Bid depth (simulated)
            np.random.uniform(1000, 10000),  # Ask depth (simulated)
        ])

        # 5. Short-term momentum (tick-level if available)
        if state.ohlcv_history is not None and len(state.ohlcv_history) >= 10:
            recent = state.ohlcv_history[-10:]
            closes = recent[:, 3]
            volumes = recent[:, 4]
            returns = np.diff(closes) / closes[:-1]

            # Microstructure features
            features.extend([
                np.mean(returns[-5:]) if len(returns) >= 5 else 0,
                np.std(returns[-5:]) if len(returns) >= 5 else 0,
                np.sum(returns[-5:] > 0) / 5 if len(returns) >= 5 else 0.5,  # Win rate
                np.mean(volumes[-5:]) if len(volumes) >= 5 else 0,
                np.std(volumes[-5:]) if len(volumes) >= 5 else 0,
            ])
        else:
            features.extend([0.0] * 5)

        # 6. Portfolio and execution state
        portfolio = state.portfolio
        features.extend([
            portfolio.portfolio_value,
            portfolio.unrealized_pnl,
            portfolio.realized_pnl_today,
            portfolio.current_drawdown,
            portfolio.position_count,
        ])

        # Convert and resize
        feature_array = np.array(features, dtype=np.float64)
        return self._pad_or_truncate(feature_array, self.config.execution_dim)

    def _pad_or_truncate(
        self,
        features: NDArray[np.float64],
        target_dim: int,
    ) -> NDArray[np.float64]:
        """Pad or truncate feature vector to target dimension."""
        if len(features) < target_dim:
            return np.pad(features, (0, target_dim - len(features)))
        return features[:target_dim]

    def compute_state_hash(
        self,
        features: NDArray[np.float64],
        precision: int = 2,
    ) -> str:
        """Compute hash of state features for caching."""
        import hashlib

        # Discretize features
        discretized = np.round(features, precision)
        return hashlib.md5(discretized.tobytes()).hexdigest()
