"""
Test configuration - all test parameters in one place.

No hardcoded values in tests - all values come from this config
or from the main application config via fixtures.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class TestScenario(str, Enum):
    """Available test scenarios."""

    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    VOLATILE = "volatile"
    TRENDING = "trending"
    MEAN_REVERTING = "mean_reverting"


class TestConfig(BaseSettings):
    """
    Test configuration loaded from environment or defaults.

    All test parameters are configurable - no hardcoded values.
    Set TEST_* environment variables to override.
    """

    model_config = SettingsConfigDict(
        env_prefix="TEST_",
        case_sensitive=False,
        extra="ignore",
    )

    # Test symbols
    primary_symbol: str = Field(default="AAPL", description="Primary test symbol")
    secondary_symbol: str = Field(default="NVDA", description="Secondary test symbol")
    crypto_symbol: str = Field(default="BTC/USD", description="Crypto test symbol")
    batch_symbols: list[str] = Field(
        default=["AAPL", "NVDA", "TSLA", "GOOGL"],
        description="Symbols for batch tests",
    )

    # Price parameters
    base_price: float = Field(default=100.0, ge=1.0, description="Base price for simulations")
    price_volatility: float = Field(default=0.02, ge=0.001, le=0.5, description="Daily volatility")

    # Portfolio parameters
    initial_cash: float = Field(default=100000.0, ge=1000.0, description="Initial cash balance")
    initial_portfolio_value: float = Field(
        default=100000.0, ge=1000.0, description="Initial portfolio value"
    )

    # MCTS test parameters
    mcts_simulations: int = Field(default=50, ge=1, le=1000, description="MCTS simulations for tests")
    mcts_rollout_horizon: int = Field(default=5, ge=1, le=30, description="Rollout horizon for tests")
    mcts_timeout_ms: int = Field(default=5000, ge=100, le=30000, description="MCTS timeout for tests")

    # Integration test parameters
    integration_timeout_seconds: float = Field(
        default=30.0, ge=1.0, le=120.0, description="Integration test timeout"
    )
    e2e_timeout_seconds: float = Field(
        default=60.0, ge=5.0, le=300.0, description="E2E test timeout"
    )

    # Data generation parameters
    ohlcv_bars: int = Field(default=100, ge=10, le=500, description="Number of OHLCV bars to generate")
    random_seed: int = Field(default=42, description="Random seed for reproducibility")

    # Risk parameters
    default_stop_loss: float = Field(default=0.05, ge=0.01, le=0.20, description="Default stop loss")
    default_position_size: float = Field(
        default=0.10, ge=0.01, le=0.50, description="Default position size"
    )
    max_position_size: float = Field(
        default=0.25, ge=0.05, le=1.0, description="Max position size"
    )

    # Analyst signal parameters
    bullish_consensus: float = Field(default=0.6, ge=0.0, le=1.0, description="Bullish consensus score")
    bearish_consensus: float = Field(default=-0.6, ge=-1.0, le=0.0, description="Bearish consensus score")
    neutral_consensus: float = Field(default=0.0, ge=-0.3, le=0.3, description="Neutral consensus score")

    # Technical indicator parameters
    overbought_rsi: float = Field(default=75.0, ge=70.0, le=100.0, description="Overbought RSI level")
    oversold_rsi: float = Field(default=25.0, ge=0.0, le=30.0, description="Oversold RSI level")
    neutral_rsi: float = Field(default=50.0, ge=30.0, le=70.0, description="Neutral RSI level")

    # Cache test parameters
    cache_ttl_seconds: int = Field(default=60, ge=1, le=3600, description="Cache TTL for tests")

    # Retry parameters
    max_retries: int = Field(default=3, ge=1, le=10, description="Max retries for flaky operations")
    retry_delay_seconds: float = Field(
        default=0.1, ge=0.01, le=5.0, description="Delay between retries"
    )


@dataclass
class ScenarioConfig:
    """Configuration for a specific test scenario."""

    name: TestScenario
    rsi: float
    macd_histogram: float
    consensus: float
    expected_direction: str  # "buy", "sell", "hold"
    confidence_min: float
    price_trend: float  # Multiplier for price movement


# Pre-defined scenarios using config values
def get_scenario_configs(config: TestConfig) -> dict[TestScenario, ScenarioConfig]:
    """Get scenario configurations derived from test config."""
    return {
        TestScenario.BULLISH: ScenarioConfig(
            name=TestScenario.BULLISH,
            rsi=config.neutral_rsi + 10,
            macd_histogram=1.0,
            consensus=config.bullish_consensus,
            expected_direction="buy",
            confidence_min=0.5,
            price_trend=1.005,
        ),
        TestScenario.BEARISH: ScenarioConfig(
            name=TestScenario.BEARISH,
            rsi=config.neutral_rsi - 10,
            macd_histogram=-1.0,
            consensus=config.bearish_consensus,
            expected_direction="sell",
            confidence_min=0.5,
            price_trend=0.995,
        ),
        TestScenario.NEUTRAL: ScenarioConfig(
            name=TestScenario.NEUTRAL,
            rsi=config.neutral_rsi,
            macd_histogram=0.0,
            consensus=config.neutral_consensus,
            expected_direction="hold",
            confidence_min=0.3,
            price_trend=1.0,
        ),
        TestScenario.VOLATILE: ScenarioConfig(
            name=TestScenario.VOLATILE,
            rsi=config.neutral_rsi,
            macd_histogram=0.5,
            consensus=0.1,
            expected_direction="hold",
            confidence_min=0.2,
            price_trend=1.0,
        ),
        TestScenario.TRENDING: ScenarioConfig(
            name=TestScenario.TRENDING,
            rsi=config.neutral_rsi + 15,
            macd_histogram=2.0,
            consensus=config.bullish_consensus + 0.1,
            expected_direction="buy",
            confidence_min=0.6,
            price_trend=1.01,
        ),
        TestScenario.MEAN_REVERTING: ScenarioConfig(
            name=TestScenario.MEAN_REVERTING,
            rsi=config.oversold_rsi,
            macd_histogram=-0.5,
            consensus=-0.2,
            expected_direction="buy",  # Mean reversion expects bounce
            confidence_min=0.4,
            price_trend=0.99,
        ),
    }


# Singleton test config instance
_test_config: TestConfig | None = None


def get_test_config() -> TestConfig:
    """Get test configuration singleton."""
    global _test_config
    if _test_config is None:
        _test_config = TestConfig()
    return _test_config


def reset_test_config() -> None:
    """Reset test configuration (useful for testing the test config)."""
    global _test_config
    _test_config = None
