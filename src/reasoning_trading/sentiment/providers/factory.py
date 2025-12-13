"""
Factory for creating news providers.

Creates and configures news providers based on application settings.
"""

from __future__ import annotations

import structlog

from reasoning_trading.config import NewsProviderType, Settings, get_settings
from reasoning_trading.sentiment.providers.base import NewsProvider
from reasoning_trading.sentiment.providers.finnhub import FinnhubNewsProvider
from reasoning_trading.sentiment.providers.newsapi import NewsAPIProvider

logger = structlog.get_logger(__name__)


def create_news_providers(
    settings: Settings | None = None,
    provider_types: list[NewsProviderType] | None = None,
) -> list[NewsProvider]:
    """
    Create news providers based on settings.

    Args:
        settings: Application settings
        provider_types: Override which providers to create

    Returns:
        List of configured news providers
    """
    settings = settings or get_settings()
    types_to_create = provider_types or settings.sentiment.enabled_providers

    providers: list[NewsProvider] = []

    for provider_type in types_to_create:
        provider = _create_provider(provider_type, settings)
        if provider is not None and provider.is_available():
            providers.append(provider)
            logger.info(
                "Created news provider",
                provider=provider.name,
            )
        elif provider is not None:
            logger.warning(
                "Provider not available (missing API key?)",
                provider=provider.name,
            )

    if not providers:
        logger.warning("No news providers available")

    return providers


def _create_provider(
    provider_type: NewsProviderType,
    settings: Settings,
) -> NewsProvider | None:
    """Create a single provider by type."""
    if provider_type == NewsProviderType.FINNHUB:
        return FinnhubNewsProvider(settings=settings)
    elif provider_type == NewsProviderType.NEWSAPI:
        return NewsAPIProvider(settings=settings)
    elif provider_type == NewsProviderType.ALPACA:
        # Alpaca news provider could be implemented later
        logger.debug("Alpaca news provider not yet implemented")
        return None
    else:
        logger.warning(f"Unknown provider type: {provider_type}")
        return None


def get_available_providers(settings: Settings | None = None) -> list[str]:
    """
    Get list of available provider names.

    Returns:
        List of provider names that have valid credentials
    """
    settings = settings or get_settings()
    available = []

    # Check Finnhub
    if settings.data_apis.finnhub_api_key is not None:
        available.append("finnhub")

    # Check NewsAPI
    if settings.sentiment.newsapi_api_key is not None:
        available.append("newsapi")

    # Check Alpaca (uses trading credentials)
    if settings.trading.api_key is not None:
        available.append("alpaca")

    return available
