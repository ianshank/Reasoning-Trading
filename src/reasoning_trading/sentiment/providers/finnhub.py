"""
Finnhub news provider implementation.

Provides access to Finnhub's financial news API including:
- Company news
- Market news
- News sentiment scores
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
import hashlib

import httpx
import structlog

from reasoning_trading.config import Settings, get_settings
from reasoning_trading.sentiment.models import NewsArticle, NewsSource
from reasoning_trading.sentiment.providers.base import (
    BaseNewsProvider,
    NewsProviderError,
)

logger = structlog.get_logger(__name__)


class FinnhubNewsProvider(BaseNewsProvider):
    """
    Finnhub news provider.

    Uses Finnhub API to fetch financial news and sentiment data.
    Requires a valid FINNHUB_API_KEY in configuration.
    """

    def __init__(
        self,
        settings: Settings | None = None,
        rate_limit_per_minute: int | None = None,
    ):
        """
        Initialize Finnhub provider.

        Args:
            settings: Application settings (uses default if not provided)
            rate_limit_per_minute: Override rate limit (defaults to settings)
        """
        self._settings = settings or get_settings()
        rate_limit = rate_limit_per_minute or self._settings.sentiment.max_requests_per_minute
        super().__init__(rate_limit_per_minute=rate_limit)

        self._base_url = "https://finnhub.io/api/v1"
        self._client: httpx.AsyncClient | None = None

    @property
    def source(self) -> NewsSource:
        """Get the news source identifier."""
        return NewsSource.FINNHUB

    @property
    def name(self) -> str:
        """Get human-readable provider name."""
        return "Finnhub"

    def is_available(self) -> bool:
        """Check if Finnhub API key is configured."""
        return self._settings.data_apis.finnhub_api_key is not None

    def _get_api_key(self) -> str:
        """Get the API key, raising error if not available."""
        if not self.is_available():
            raise NewsProviderError(
                message="Finnhub API key not configured",
                provider=self.name,
                retriable=False,
            )
        return self._settings.data_apis.finnhub_api_key.get_secret_value()

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=httpx.Timeout(30.0, connect=10.0),
                headers={"X-Finnhub-Token": self._get_api_key()},
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def get_news(
        self,
        symbol: str,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        limit: int | None = None,
    ) -> list[NewsArticle]:
        """
        Fetch company news from Finnhub.

        Args:
            symbol: Stock symbol (e.g., "AAPL")
            from_date: Start date (defaults to 48 hours ago)
            to_date: End date (defaults to now)
            limit: Maximum articles (defaults to settings)

        Returns:
            List of NewsArticle objects
        """
        await self._check_rate_limit()

        # Set defaults from settings
        lookback_hours = self._settings.sentiment.news_lookback_hours
        max_articles = limit or self._settings.sentiment.max_articles_per_symbol

        # Calculate date range
        end_date = to_date or datetime.now()
        start_date = from_date or (end_date - timedelta(hours=lookback_hours))

        # Normalize symbol
        normalized_symbol = self._normalize_symbol(symbol)

        try:
            client = await self._get_client()
            response = await client.get(
                "/company-news",
                params={
                    "symbol": normalized_symbol,
                    "from": start_date.strftime("%Y-%m-%d"),
                    "to": end_date.strftime("%Y-%m-%d"),
                },
            )
            response.raise_for_status()
            data = response.json()

            if not isinstance(data, list):
                logger.warning(
                    "Unexpected response format from Finnhub",
                    symbol=symbol,
                    response_type=type(data).__name__,
                )
                return []

            # Convert to NewsArticle objects
            articles = []
            for item in data[:max_articles]:
                article = self._parse_news_item(item, symbol)
                if article:
                    articles.append(article)

            logger.info(
                "Fetched news from Finnhub",
                symbol=symbol,
                article_count=len(articles),
            )
            return articles

        except httpx.HTTPStatusError as e:
            raise NewsProviderError(
                message=f"HTTP error fetching news: {e.response.status_code}",
                provider=self.name,
                retriable=e.response.status_code >= 500,
                original_error=e,
            )
        except Exception as e:
            raise NewsProviderError(
                message=f"Error fetching news: {str(e)}",
                provider=self.name,
                retriable=True,
                original_error=e,
            )

    async def get_market_news(
        self,
        category: str | None = None,
        limit: int | None = None,
    ) -> list[NewsArticle]:
        """
        Fetch general market news from Finnhub.

        Args:
            category: News category (general, forex, crypto, merger)
            limit: Maximum articles

        Returns:
            List of NewsArticle objects
        """
        await self._check_rate_limit()

        max_articles = limit or self._settings.sentiment.max_articles_per_symbol
        news_category = category or "general"

        try:
            client = await self._get_client()
            response = await client.get(
                "/news",
                params={"category": news_category},
            )
            response.raise_for_status()
            data = response.json()

            if not isinstance(data, list):
                return []

            articles = []
            for item in data[:max_articles]:
                article = self._parse_market_news_item(item, news_category)
                if article:
                    articles.append(article)

            logger.info(
                "Fetched market news from Finnhub",
                category=news_category,
                article_count=len(articles),
            )
            return articles

        except httpx.HTTPStatusError as e:
            raise NewsProviderError(
                message=f"HTTP error fetching market news: {e.response.status_code}",
                provider=self.name,
                retriable=e.response.status_code >= 500,
                original_error=e,
            )
        except Exception as e:
            raise NewsProviderError(
                message=f"Error fetching market news: {str(e)}",
                provider=self.name,
                retriable=True,
                original_error=e,
            )

    async def get_news_sentiment(self, symbol: str) -> dict[str, Any]:
        """
        Get pre-computed news sentiment from Finnhub.

        Args:
            symbol: Stock symbol

        Returns:
            Sentiment data including buzz, sentiment scores
        """
        await self._check_rate_limit()

        try:
            client = await self._get_client()
            response = await client.get(
                "/news-sentiment",
                params={"symbol": self._normalize_symbol(symbol)},
            )
            response.raise_for_status()
            return response.json()

        except Exception as e:
            logger.warning(
                "Failed to get Finnhub sentiment",
                symbol=symbol,
                error=str(e),
            )
            return {}

    def _parse_news_item(
        self,
        item: dict[str, Any],
        symbol: str,
    ) -> NewsArticle | None:
        """Parse a Finnhub company news item into NewsArticle."""
        try:
            # Generate stable ID from URL or headline
            item_id = item.get("id") or hashlib.md5(
                f"{item.get('headline', '')}{item.get('datetime', '')}".encode()
            ).hexdigest()

            # Parse timestamp
            timestamp = datetime.fromtimestamp(item.get("datetime", 0))

            return NewsArticle(
                id=str(item_id),
                headline=item.get("headline", ""),
                summary=item.get("summary", ""),
                content="",  # Finnhub doesn't provide full content
                source=NewsSource.FINNHUB,
                source_name=item.get("source", ""),
                url=item.get("url", ""),
                published_at=timestamp,
                symbols=[symbol],
                category=item.get("category", ""),
                image_url=item.get("image", ""),
                relevance_score=1.0,  # Company news is highly relevant
                raw_data=item,
            )
        except Exception as e:
            logger.warning(
                "Failed to parse Finnhub news item",
                error=str(e),
                item=item,
            )
            return None

    def _parse_market_news_item(
        self,
        item: dict[str, Any],
        category: str,
    ) -> NewsArticle | None:
        """Parse a Finnhub market news item into NewsArticle."""
        try:
            item_id = item.get("id") or hashlib.md5(
                f"{item.get('headline', '')}{item.get('datetime', '')}".encode()
            ).hexdigest()

            timestamp = datetime.fromtimestamp(item.get("datetime", 0))

            # Extract symbols from related field
            related = item.get("related", "")
            symbols = [s.strip() for s in related.split(",") if s.strip()]

            return NewsArticle(
                id=str(item_id),
                headline=item.get("headline", ""),
                summary=item.get("summary", ""),
                content="",
                source=NewsSource.FINNHUB,
                source_name=item.get("source", ""),
                url=item.get("url", ""),
                published_at=timestamp,
                symbols=symbols,
                category=category,
                image_url=item.get("image", ""),
                relevance_score=0.7,  # Market news is less specific
                raw_data=item,
            )
        except Exception as e:
            logger.warning(
                "Failed to parse Finnhub market news item",
                error=str(e),
            )
            return None
