"""
Base provider interface for news data sources.

Defines the protocol that all news providers must implement,
enabling pluggable provider architecture.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Protocol, runtime_checkable

import structlog

from reasoning_trading.sentiment.models import NewsArticle, NewsSource

logger = structlog.get_logger(__name__)


class NewsProviderError(Exception):
    """Exception raised by news providers."""

    def __init__(
        self,
        message: str,
        provider: str,
        retriable: bool = True,
        original_error: Exception | None = None,
    ):
        super().__init__(message)
        self.provider = provider
        self.retriable = retriable
        self.original_error = original_error


@runtime_checkable
class NewsProvider(Protocol):
    """
    Protocol for news data providers.

    All news providers must implement this interface to be
    used by the sentiment analysis service.
    """

    @property
    def source(self) -> NewsSource:
        """Get the news source identifier."""
        ...

    @property
    def name(self) -> str:
        """Get human-readable provider name."""
        ...

    async def get_news(
        self,
        symbol: str,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        limit: int | None = None,
    ) -> list[NewsArticle]:
        """
        Fetch news articles for a symbol.

        Args:
            symbol: Trading symbol (e.g., "AAPL", "BTC/USD")
            from_date: Start of date range (defaults to provider-specific)
            to_date: End of date range (defaults to now)
            limit: Maximum number of articles (defaults to provider-specific)

        Returns:
            List of NewsArticle objects

        Raises:
            NewsProviderError: If fetching fails
        """
        ...

    async def get_market_news(
        self,
        category: str | None = None,
        limit: int | None = None,
    ) -> list[NewsArticle]:
        """
        Fetch general market news.

        Args:
            category: News category filter
            limit: Maximum number of articles

        Returns:
            List of NewsArticle objects
        """
        ...

    def is_available(self) -> bool:
        """Check if the provider is available (has valid credentials)."""
        ...

    async def health_check(self) -> bool:
        """Perform health check on the provider."""
        ...


class BaseNewsProvider(ABC):
    """
    Abstract base class for news providers.

    Provides common functionality and enforces the NewsProvider protocol.
    """

    def __init__(self, rate_limit_per_minute: int):
        """
        Initialize base provider.

        Args:
            rate_limit_per_minute: Maximum API calls per minute
        """
        self._rate_limit = rate_limit_per_minute
        self._request_times: list[datetime] = []

    @property
    @abstractmethod
    def source(self) -> NewsSource:
        """Get the news source identifier."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Get human-readable provider name."""
        ...

    @abstractmethod
    async def get_news(
        self,
        symbol: str,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        limit: int | None = None,
    ) -> list[NewsArticle]:
        """Fetch news articles for a symbol."""
        ...

    @abstractmethod
    async def get_market_news(
        self,
        category: str | None = None,
        limit: int | None = None,
    ) -> list[NewsArticle]:
        """Fetch general market news."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is available."""
        ...

    async def health_check(self) -> bool:
        """Perform health check on the provider."""
        if not self.is_available():
            return False
        try:
            # Try to fetch a small amount of news
            await self.get_market_news(limit=1)
            return True
        except Exception as e:
            logger.warning(
                "Health check failed",
                provider=self.name,
                error=str(e),
            )
            return False

    async def _check_rate_limit(self) -> None:
        """Check and enforce rate limiting."""
        import asyncio
        from datetime import timedelta

        now = datetime.now()
        cutoff = now - timedelta(minutes=1)

        # Remove old requests
        self._request_times = [t for t in self._request_times if t > cutoff]

        # Check if at limit
        if len(self._request_times) >= self._rate_limit:
            # Calculate wait time
            oldest = min(self._request_times)
            wait_seconds = (oldest - cutoff).total_seconds() + 0.1
            if wait_seconds > 0:
                logger.debug(
                    "Rate limit reached, waiting",
                    provider=self.name,
                    wait_seconds=wait_seconds,
                )
                await asyncio.sleep(wait_seconds)

        # Record this request
        self._request_times.append(now)

    def _normalize_symbol(self, symbol: str) -> str:
        """
        Normalize symbol for provider-specific format.

        Args:
            symbol: Input symbol (e.g., "AAPL", "BTC/USD")

        Returns:
            Normalized symbol for this provider
        """
        # Default: just uppercase
        return symbol.upper().replace("/", "")
