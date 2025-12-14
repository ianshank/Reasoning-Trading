"""
Backend configuration extending reasoning_trading.config.

Adds backend-specific settings for JWT authentication, rate limiting,
CORS, and WebSocket connections while inheriting all core trading settings.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from reasoning_trading.config import Settings as CoreSettings


class JWTSettings(BaseSettings):
    """JWT authentication configuration."""

    model_config = SettingsConfigDict(
        env_prefix="JWT_",
        case_sensitive=False,
        extra="ignore",
    )

    secret_key: SecretStr = Field(
        default=SecretStr("CHANGE_ME_IN_PRODUCTION_USE_OPENSSL_RAND_HEX_32"),
        alias="JWT_SECRET_KEY",
        description="Secret key for JWT signing (use openssl rand -hex 32)",
    )
    algorithm: str = Field(
        default="HS256",
        alias="JWT_ALGORITHM",
        description="JWT signing algorithm",
    )
    access_token_expire_minutes: int = Field(
        default=30,
        ge=5,
        le=1440,
        alias="JWT_ACCESS_TOKEN_EXPIRE_MINUTES",
        description="Access token expiration in minutes",
    )
    refresh_token_expire_days: int = Field(
        default=7,
        ge=1,
        le=90,
        alias="JWT_REFRESH_TOKEN_EXPIRE_DAYS",
        description="Refresh token expiration in days",
    )


class RateLimitSettings(BaseSettings):
    """Rate limiting configuration."""

    model_config = SettingsConfigDict(
        env_prefix="RATE_LIMIT_",
        case_sensitive=False,
        extra="ignore",
    )

    enabled: bool = Field(
        default=True,
        alias="RATE_LIMIT_ENABLED",
        description="Enable rate limiting",
    )
    requests_per_minute: int = Field(
        default=60,
        ge=1,
        le=10000,
        alias="RATE_LIMIT_REQUESTS_PER_MINUTE",
        description="Maximum requests per minute per client",
    )
    burst_size: int = Field(
        default=10,
        ge=1,
        le=1000,
        alias="RATE_LIMIT_BURST_SIZE",
        description="Burst allowance for rate limiting",
    )


class CORSSettings(BaseSettings):
    """CORS configuration."""

    model_config = SettingsConfigDict(
        env_prefix="CORS_",
        case_sensitive=False,
        extra="ignore",
    )

    enabled: bool = Field(
        default=True,
        alias="CORS_ENABLED",
        description="Enable CORS",
    )
    allowed_origins: list[str] = Field(
        default=[
            "http://localhost:3000",
            "http://localhost:7860",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:7860",
        ],
        alias="CORS_ALLOWED_ORIGINS",
        description="Allowed CORS origins",
    )
    allowed_methods: list[str] = Field(
        default=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        alias="CORS_ALLOWED_METHODS",
        description="Allowed HTTP methods",
    )
    allowed_headers: list[str] = Field(
        default=["*"],
        alias="CORS_ALLOWED_HEADERS",
        description="Allowed HTTP headers",
    )
    allow_credentials: bool = Field(
        default=True,
        alias="CORS_ALLOW_CREDENTIALS",
        description="Allow credentials in CORS requests",
    )

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v: str | list[str]) -> list[str]:
        """Parse comma-separated origins."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v


class WebSocketSettings(BaseSettings):
    """WebSocket configuration."""

    model_config = SettingsConfigDict(
        env_prefix="WS_",
        case_sensitive=False,
        extra="ignore",
    )

    heartbeat_interval_seconds: int = Field(
        default=30,
        ge=5,
        le=300,
        alias="WS_HEARTBEAT_INTERVAL_SECONDS",
        description="WebSocket heartbeat interval",
    )
    max_message_size_bytes: int = Field(
        default=1024 * 1024,  # 1MB
        ge=1024,
        le=10 * 1024 * 1024,
        alias="WS_MAX_MESSAGE_SIZE_BYTES",
        description="Maximum WebSocket message size",
    )
    connection_timeout_seconds: int = Field(
        default=300,
        ge=60,
        le=3600,
        alias="WS_CONNECTION_TIMEOUT_SECONDS",
        description="WebSocket connection timeout",
    )


class DatabaseSettings(BaseSettings):
    """Database configuration for session/state persistence."""

    model_config = SettingsConfigDict(
        env_prefix="DATABASE_",
        case_sensitive=False,
        extra="ignore",
    )

    url: str = Field(
        default="sqlite:///./data/enterprise_ui.db",
        alias="DATABASE_URL",
        description="Database URL (SQLite, PostgreSQL, etc.)",
    )
    echo: bool = Field(
        default=False,
        alias="DATABASE_ECHO",
        description="Echo SQL queries (debug only)",
    )
    pool_size: int = Field(
        default=5,
        ge=1,
        le=100,
        alias="DATABASE_POOL_SIZE",
        description="Database connection pool size",
    )
    max_overflow: int = Field(
        default=10,
        ge=0,
        le=100,
        alias="DATABASE_MAX_OVERFLOW",
        description="Maximum connection pool overflow",
    )


class BackendSettings(BaseSettings):
    """
    Backend-specific configuration extending core trading settings.

    Inherits all settings from reasoning_trading.config.Settings and adds
    backend-specific settings for API server, authentication, and WebSocket.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Environment
    environment: Literal["development", "staging", "production", "test"] = Field(
        default="development",
        alias="ENVIRONMENT",
        description="Deployment environment",
    )

    # Server
    host: str = Field(
        default="0.0.0.0",
        alias="API_HOST",
        description="API server host",
    )
    port: int = Field(
        default=8000,
        ge=1,
        le=65535,
        alias="API_PORT",
        description="API server port",
    )
    reload: bool = Field(
        default=True,
        alias="API_RELOAD",
        description="Enable auto-reload (development only)",
    )
    workers: int = Field(
        default=1,
        ge=1,
        le=16,
        alias="API_WORKERS",
        description="Number of worker processes",
    )

    # OpenAPI documentation
    title: str = Field(
        default="Reasoning Trading Enterprise API",
        description="API documentation title",
    )
    description: str = Field(
        default="Multi-agent reasoning-based trading system with MCTS planning",
        description="API documentation description",
    )
    version: str = Field(
        default="1.0.0",
        description="API version",
    )
    openapi_url: str | None = Field(
        default="/api/openapi.json",
        description="OpenAPI schema URL (None to disable)",
    )
    docs_url: str | None = Field(
        default="/docs",
        description="Swagger UI URL (None to disable)",
    )
    redoc_url: str | None = Field(
        default="/redoc",
        description="ReDoc URL (None to disable)",
    )

    # Backend-specific settings
    jwt: JWTSettings = Field(default_factory=JWTSettings)
    rate_limit: RateLimitSettings = Field(default_factory=RateLimitSettings)
    cors: CORSSettings = Field(default_factory=CORSSettings)
    websocket: WebSocketSettings = Field(default_factory=WebSocketSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)

    # Core trading settings (inherited)
    core: CoreSettings = Field(default_factory=CoreSettings)

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == "development"

    def disable_docs_in_production(self) -> None:
        """Disable API documentation in production."""
        if self.is_production:
            self.openapi_url = None
            self.docs_url = None
            self.redoc_url = None


@lru_cache
def get_backend_settings() -> BackendSettings:
    """
    Get cached backend settings instance.

    Uses LRU cache to avoid re-reading environment on every access.
    Call get_backend_settings.cache_clear() to force reload.

    Returns:
        BackendSettings instance with all configuration
    """
    return BackendSettings()


def reload_backend_settings() -> BackendSettings:
    """
    Force reload backend settings from environment.

    Returns:
        Fresh BackendSettings instance
    """
    get_backend_settings.cache_clear()
    return get_backend_settings()
