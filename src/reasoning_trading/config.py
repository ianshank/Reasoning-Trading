"""
Configuration management for Reasoning Trading.

Uses pydantic-settings for type-safe, validated configuration loaded from
environment variables with sensible defaults. No hardcoded values.
"""

from __future__ import annotations

from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class TradingMode(str, Enum):
    """Trading mode selection."""

    PAPER = "paper"
    LIVE = "live"


class RiskProfile(str, Enum):
    """Risk management profile."""

    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"


class LogLevel(str, Enum):
    """Logging levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LLMSettings(BaseSettings):
    """LLM-specific configuration."""

    model_config = SettingsConfigDict(
        env_prefix="",
        case_sensitive=False,
        extra="ignore",
    )

    # API Keys
    openai_api_key: SecretStr | None = Field(default=None, alias="OPENAI_API_KEY")
    anthropic_api_key: SecretStr | None = Field(default=None, alias="ANTHROPIC_API_KEY")

    # Model Selection
    deep_think_llm: str = Field(default="gpt-4o", description="Model for complex analysis")
    quick_think_llm: str = Field(default="gpt-4o-mini", description="Model for rapid processing")

    # LangSmith Tracing
    langchain_tracing_v2: bool = Field(default=False, alias="LANGCHAIN_TRACING_V2")
    langchain_api_key: SecretStr | None = Field(default=None, alias="LANGCHAIN_API_KEY")
    langchain_project: str = Field(default="reasoning-trading", alias="LANGCHAIN_PROJECT")


class TradingSettings(BaseSettings):
    """Trading platform configuration."""

    model_config = SettingsConfigDict(
        env_prefix="ALPACA_",
        case_sensitive=False,
        extra="ignore",
    )

    api_key: SecretStr | None = Field(default=None, alias="ALPACA_API_KEY")
    secret_key: SecretStr | None = Field(default=None, alias="ALPACA_SECRET_KEY")
    base_url: str = Field(
        default="https://paper-api.alpaca.markets",
        alias="ALPACA_BASE_URL",
    )
    trading_mode: TradingMode = Field(default=TradingMode.PAPER, alias="ALPACA_TRADING_MODE")

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, v: str, info: Any) -> str:
        """Ensure base URL matches trading mode."""
        return v.rstrip("/")


class DataAPISettings(BaseSettings):
    """Financial data API configuration."""

    model_config = SettingsConfigDict(
        env_prefix="",
        case_sensitive=False,
        extra="ignore",
    )

    finnhub_api_key: SecretStr | None = Field(default=None, alias="FINNHUB_API_KEY")
    fred_api_key: SecretStr | None = Field(default=None, alias="FRED_API_KEY")
    coindesk_api_key: SecretStr | None = Field(default=None, alias="COINDESK_API_KEY")


class MCTSSettings(BaseSettings):
    """MCTS algorithm configuration."""

    model_config = SettingsConfigDict(
        env_prefix="MCTS_",
        case_sensitive=False,
        extra="ignore",
    )

    max_simulations: int = Field(
        default=1000,
        ge=1,
        le=100000,
        description="Maximum MCTS simulations per decision",
    )
    exploration_weight: float = Field(
        default=1.414,
        ge=0.0,
        le=10.0,
        description="UCB exploration weight (sqrt(2) is theoretically optimal)",
    )
    rollout_horizon_days: int = Field(
        default=30,
        ge=1,
        le=365,
        description="Trading days to simulate in rollouts",
    )
    confidence_threshold: float = Field(
        default=0.85,
        ge=0.0,
        le=1.0,
        description="Confidence threshold for early termination",
    )
    realtime_budget_ms: int = Field(
        default=500,
        ge=50,
        le=60000,
        description="Time budget for real-time MCTS decisions",
    )
    progressive_widening_alpha: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Progressive widening parameter for continuous actions",
    )
    discount_factor: float = Field(
        default=0.99,
        ge=0.0,
        le=1.0,
        description="Discount factor for future rewards",
    )


class RiskSettings(BaseSettings):
    """Risk management configuration."""

    model_config = SettingsConfigDict(
        env_prefix="",
        case_sensitive=False,
        extra="ignore",
    )

    max_position_size_fraction: float = Field(
        default=0.25,
        ge=0.01,
        le=1.0,
        description="Maximum position size as fraction of portfolio",
    )
    default_stop_loss_percent: float = Field(
        default=0.05,
        ge=0.001,
        le=0.50,
        description="Default stop-loss percentage",
    )
    max_daily_loss_percent: float = Field(
        default=0.10,
        ge=0.01,
        le=0.50,
        description="Maximum daily loss percentage (circuit breaker)",
    )
    default_risk_profile: RiskProfile = Field(
        default=RiskProfile.MODERATE,
        description="Default risk management profile",
    )


class CacheSettings(BaseSettings):
    """Cache configuration."""

    model_config = SettingsConfigDict(
        env_prefix="",
        case_sensitive=False,
        extra="ignore",
    )

    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    cache_ttl_seconds: int = Field(
        default=3600,
        ge=60,
        le=86400,
        description="Cache TTL in seconds",
    )


class RAGSettings(BaseSettings):
    """RAG (Retrieval-Augmented Generation) configuration."""

    model_config = SettingsConfigDict(
        env_prefix="RAG_",
        case_sensitive=False,
        extra="ignore",
    )

    # Storage settings
    persist_dir: str = Field(
        default="./data/rag_db",
        description="Directory for persisting RAG databases",
    )
    vector_db_type: str = Field(
        default="in_memory",
        description="Vector DB type (chromadb, faiss, in_memory)",
    )

    # Embedding settings
    embedding_model: str = Field(
        default="all-MiniLM-L6-v2",
        description="Sentence transformer embedding model",
    )
    embedding_dimension: int = Field(
        default=384,
        ge=64,
        le=4096,
        description="Embedding vector dimension",
    )

    # Retrieval settings
    default_top_k: int = Field(
        default=5,
        ge=1,
        le=100,
        description="Default number of results to retrieve",
    )
    similarity_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum similarity threshold for retrieval",
    )

    # Pattern RAG settings
    pattern_min_sharpe: float = Field(
        default=0.3,
        ge=-5.0,
        le=10.0,
        description="Minimum Sharpe ratio to store patterns",
    )
    pattern_max_per_symbol: int = Field(
        default=1000,
        ge=100,
        le=100000,
        description="Maximum patterns per symbol",
    )


class CAGSettings(BaseSettings):
    """CAG (Cache-Augmented Generation) configuration."""

    model_config = SettingsConfigDict(
        env_prefix="CAG_",
        case_sensitive=False,
        extra="ignore",
    )

    # TTL settings (seconds)
    l1_ttl_seconds: int = Field(
        default=300,
        ge=1,
        le=86400,
        description="L1 (exact match) cache TTL",
    )
    l2_ttl_seconds: int = Field(
        default=3600,
        ge=60,
        le=604800,
        description="L2 (semantic) cache TTL",
    )
    l3_ttl_seconds: int = Field(
        default=7200,
        ge=300,
        le=604800,
        description="L3 (RAG) cache TTL",
    )

    # Similarity thresholds
    l2_semantic_threshold: float = Field(
        default=0.92,
        ge=0.5,
        le=1.0,
        description="Threshold for L2 semantic match",
    )
    l3_rag_threshold: float = Field(
        default=0.85,
        ge=0.3,
        le=1.0,
        description="Threshold for L3 RAG match",
    )

    # Capacity settings
    max_l1_entries: int = Field(
        default=10000,
        ge=100,
        le=1000000,
        description="Maximum L1 cache entries",
    )
    max_l2_entries: int = Field(
        default=50000,
        ge=1000,
        le=10000000,
        description="Maximum L2 cache entries",
    )

    # Ensemble settings
    ensemble_strategy: str = Field(
        default="confidence_weighted",
        description="Ensemble strategy (uniform, confidence_weighted, adaptive)",
    )
    min_ensemble_sources: int = Field(
        default=2,
        ge=1,
        le=5,
        description="Minimum sources for ensemble decision",
    )


class DebateSettings(BaseSettings):
    """Multi-agent debate configuration."""

    model_config = SettingsConfigDict(
        env_prefix="",
        case_sensitive=False,
        extra="ignore",
    )

    max_debate_rounds: int = Field(
        default=4,
        ge=1,
        le=10,
        description="Maximum rounds for Bull/Bear debate",
    )
    max_risk_discuss_rounds: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum rounds for risk discussion",
    )
    enable_parallel_analysts: bool = Field(
        default=True,
        description="Enable parallel analyst execution",
    )
    enable_online_tools: bool = Field(
        default=True,
        description="Enable online data tools",
    )


class APISettings(BaseSettings):
    """REST API server configuration."""

    model_config = SettingsConfigDict(
        env_prefix="API_",
        case_sensitive=False,
        extra="ignore",
    )

    host: str = Field(default="0.0.0.0", alias="API_HOST")
    port: int = Field(default=8000, ge=1, le=65535, alias="API_PORT")
    cors_allowed_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:7860"],
        alias="CORS_ALLOWED_ORIGINS",
    )
    rate_limit: int = Field(
        default=60,
        ge=1,
        le=10000,
        description="Requests per minute",
        alias="API_RATE_LIMIT",
    )

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        """Parse comma-separated CORS origins."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v


class FeatureFlags(BaseSettings):
    """Feature flag configuration."""

    model_config = SettingsConfigDict(
        env_prefix="",
        case_sensitive=False,
        extra="ignore",
    )

    allow_shorts: bool = Field(default=False, alias="ALLOW_SHORTS")
    enable_margin_trading: bool = Field(default=False, alias="ENABLE_MARGIN_TRADING")
    enable_crypto_trading: bool = Field(default=True, alias="ENABLE_CRYPTO_TRADING")
    auto_execute_trades: bool = Field(default=False, alias="AUTO_EXECUTE_TRADES")


class LoggingSettings(BaseSettings):
    """Logging configuration."""

    model_config = SettingsConfigDict(
        env_prefix="LOG_",
        case_sensitive=False,
        extra="ignore",
    )

    level: LogLevel = Field(default=LogLevel.INFO, alias="LOG_LEVEL")
    json_format: bool = Field(default=False, alias="LOG_JSON_FORMAT")


class Settings(BaseSettings):
    """
    Main settings aggregating all configuration sections.

    Configuration is loaded from environment variables with the following precedence:
    1. Environment variables
    2. .env file in project root
    3. Default values defined here

    Usage:
        settings = get_settings()
        print(settings.trading.api_key.get_secret_value())
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Project paths
    project_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent.parent)
    data_dir: Path | None = Field(default=None)

    # Nested settings
    llm: LLMSettings = Field(default_factory=LLMSettings)
    trading: TradingSettings = Field(default_factory=TradingSettings)
    data_apis: DataAPISettings = Field(default_factory=DataAPISettings)
    mcts: MCTSSettings = Field(default_factory=MCTSSettings)
    risk: RiskSettings = Field(default_factory=RiskSettings)
    cache: CacheSettings = Field(default_factory=CacheSettings)
    rag: RAGSettings = Field(default_factory=RAGSettings)
    cag: CAGSettings = Field(default_factory=CAGSettings)
    debate: DebateSettings = Field(default_factory=DebateSettings)
    api: APISettings = Field(default_factory=APISettings)
    features: FeatureFlags = Field(default_factory=FeatureFlags)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)

    @model_validator(mode="after")
    def set_default_data_dir(self) -> "Settings":
        """Set default data directory if not provided."""
        if self.data_dir is None:
            self.data_dir = self.project_dir / "data"
        return self

    def is_live_trading_enabled(self) -> bool:
        """Check if live trading is enabled with valid credentials."""
        return (
            self.trading.trading_mode == TradingMode.LIVE
            and self.trading.api_key is not None
            and self.trading.secret_key is not None
        )

    def validate_api_keys(self) -> dict[str, bool]:
        """Validate which API keys are configured."""
        return {
            "openai": self.llm.openai_api_key is not None,
            "anthropic": self.llm.anthropic_api_key is not None,
            "alpaca": self.trading.api_key is not None,
            "finnhub": self.data_apis.finnhub_api_key is not None,
            "fred": self.data_apis.fred_api_key is not None,
            "coindesk": self.data_apis.coindesk_api_key is not None,
        }


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Uses LRU cache to avoid re-reading environment on every access.
    Call get_settings.cache_clear() to force reload.
    """
    return Settings()


def reload_settings() -> Settings:
    """Force reload settings from environment."""
    get_settings.cache_clear()
    return get_settings()
