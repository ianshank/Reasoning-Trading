"""
NewsAPI.org news provider implementation.

Provides access to NewsAPI's news aggregation service,
covering major news sources worldwide.
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


# Company name mappings for search queries
SYMBOL_TO_COMPANY: dict[str, str] = {
    "AAPL": "Apple",
    "GOOGL": "Google Alphabet",
    "GOOG": "Google Alphabet",
    "MSFT": "Microsoft",
    "AMZN": "Amazon",
    "NVDA": "NVIDIA",
    "TSLA": "Tesla",
    "META": "Meta Facebook",
    "BRK.A": "Berkshire Hathaway",
    "BRK.B": "Berkshire Hathaway",
    "JPM": "JPMorgan Chase",
    "V": "Visa",
    "UNH": "UnitedHealth",
    "MA": "Mastercard",
    "HD": "Home Depot",
    "PG": "Procter Gamble",
    "JNJ": "Johnson Johnson",
    "XOM": "Exxon Mobil",
    "CVX": "Chevron",
    "BAC": "Bank of America",
    "COIN": "Coinbase",
    "BTC": "Bitcoin",
    "ETH": "Ethereum",
}


class NewsAPIProvider(BaseNewsProvider):
    """
    NewsAPI.org news provider.

    Uses NewsAPI to fetch news from various sources.
    Requires a valid NEWSAPI_API_KEY in configuration.
    """

    def __init__(
        self,
        settings: Settings | None = None,
        rate_limit_per_minute: int | None = None,
    ):
        """
        Initialize NewsAPI provider.

        Args:
            settings: Application settings
            rate_limit_per_minute: Override rate limit
        """
        self._settings = settings or get_settings()
        rate_limit = rate_limit_per_minute or self._settings.sentiment.max_requests_per_minute
        super().__init__(rate_limit_per_minute=rate_limit)

        self._base_url = "https://newsapi.org/v2"
        self._client: httpx.AsyncClient | None = None

    @property
    def source(self) -> NewsSource:
        """Get the news source identifier."""
        return NewsSource.NEWSAPI

    @property
    def name(self) -> str:
        """Get human-readable provider name."""
        return "NewsAPI"

    def is_available(self) -> bool:
        """Check if NewsAPI key is configured."""
        return self._settings.sentiment.newsapi_api_key is not None

    def _get_api_key(self) -> str:
        """Get the API key, raising error if not available."""
        if not self.is_available():
            raise NewsProviderError(
                message="NewsAPI API key not configured",
                provider=self.name,
                retriable=False,
            )
        return self._settings.sentiment.newsapi_api_key.get_secret_value()

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=httpx.Timeout(30.0, connect=10.0),
                headers={"X-Api-Key": self._get_api_key()},
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _symbol_to_query(self, symbol: str) -> str:
        """
        Convert trading symbol to search query.

        Args:
            symbol: Trading symbol

        Returns:
            Search query string
        """
        normalized = symbol.upper().replace("/", "")

        # Check for known company name
        if normalized in SYMBOL_TO_COMPANY:
            company = SYMBOL_TO_COMPANY[normalized]
            return f'"{company}" OR "{normalized}"'

        # For unknown symbols, search for both ticker and potential company name
        return f'"{normalized}" stock OR "{normalized}" shares'

    async def get_news(
        self,
        symbol: str,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        limit: int | None = None,
    ) -> list[NewsArticle]:
        """
        Fetch news articles for a symbol from NewsAPI.

        Args:
            symbol: Trading symbol
            from_date: Start date
            to_date: End date
            limit: Maximum articles

        Returns:
            List of NewsArticle objects
        """
        await self._check_rate_limit()

        lookback_hours = self._settings.sentiment.news_lookback_hours
        max_articles = limit or self._settings.sentiment.max_articles_per_symbol

        # NewsAPI free tier only allows 1 month back
        end_date = to_date or datetime.now()
        start_date = from_date or (end_date - timedelta(hours=lookback_hours))

        # Ensure we don't exceed NewsAPI limits
        max_lookback = end_date - timedelta(days=30)
        if start_date < max_lookback:
            start_date = max_lookback

        query = self._symbol_to_query(symbol)

        try:
            client = await self._get_client()
            response = await client.get(
                "/everything",
                params={
                    "q": query,
                    "from": start_date.strftime("%Y-%m-%dT%H:%M:%S"),
                    "to": end_date.strftime("%Y-%m-%dT%H:%M:%S"),
                    "sortBy": "publishedAt",
                    "pageSize": min(max_articles, 100),  # NewsAPI max is 100
                    "language": "en",
                },
            )
            response.raise_for_status()
            data = response.json()

            if data.get("status") != "ok":
                logger.warning(
                    "NewsAPI returned error status",
                    status=data.get("status"),
                    message=data.get("message"),
                )
                return []

            articles = []
            for item in data.get("articles", [])[:max_articles]:
                article = self._parse_news_item(item, symbol)
                if article:
                    articles.append(article)

            logger.info(
                "Fetched news from NewsAPI",
                symbol=symbol,
                article_count=len(articles),
                total_results=data.get("totalResults", 0),
            )
            return articles

        except httpx.HTTPStatusError as e:
            # Handle specific NewsAPI errors
            if e.response.status_code == 426:
                # Upgrade required - free tier limitation
                logger.warning(
                    "NewsAPI requires upgrade for this request",
                    symbol=symbol,
                )
                return []
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
        Fetch top business/finance headlines from NewsAPI.

        Args:
            category: News category (business, technology, etc.)
            limit: Maximum articles

        Returns:
            List of NewsArticle objects
        """
        await self._check_rate_limit()

        max_articles = limit or self._settings.sentiment.max_articles_per_symbol
        news_category = category or "business"

        try:
            client = await self._get_client()
            response = await client.get(
                "/top-headlines",
                params={
                    "category": news_category,
                    "country": "us",
                    "pageSize": min(max_articles, 100),
                },
            )
            response.raise_for_status()
            data = response.json()

            if data.get("status") != "ok":
                return []

            articles = []
            for item in data.get("articles", [])[:max_articles]:
                article = self._parse_headline_item(item, news_category)
                if article:
                    articles.append(article)

            logger.info(
                "Fetched headlines from NewsAPI",
                category=news_category,
                article_count=len(articles),
            )
            return articles

        except httpx.HTTPStatusError as e:
            raise NewsProviderError(
                message=f"HTTP error fetching headlines: {e.response.status_code}",
                provider=self.name,
                retriable=e.response.status_code >= 500,
                original_error=e,
            )
        except Exception as e:
            raise NewsProviderError(
                message=f"Error fetching headlines: {str(e)}",
                provider=self.name,
                retriable=True,
                original_error=e,
            )

    def _parse_news_item(
        self,
        item: dict[str, Any],
        symbol: str,
    ) -> NewsArticle | None:
        """Parse a NewsAPI article into NewsArticle."""
        try:
            # Generate ID from URL
            url = item.get("url", "")
            item_id = hashlib.md5(url.encode()).hexdigest() if url else str(hash(item.get("title", "")))

            # Parse publication date
            published_str = item.get("publishedAt", "")
            try:
                published_at = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
                # Remove timezone info for consistency
                published_at = published_at.replace(tzinfo=None)
            except (ValueError, AttributeError):
                published_at = datetime.now()

            # Calculate relevance based on title/description match
            title = item.get("title", "").lower()
            description = item.get("description", "").lower()
            symbol_lower = symbol.lower()

            relevance = 0.5  # Base relevance
            if symbol_lower in title:
                relevance = 1.0
            elif symbol_lower in description:
                relevance = 0.8
            elif SYMBOL_TO_COMPANY.get(symbol.upper(), "").lower() in title:
                relevance = 0.9

            return NewsArticle(
                id=item_id,
                headline=item.get("title", ""),
                summary=item.get("description", ""),
                content=item.get("content", ""),
                source=NewsSource.NEWSAPI,
                source_name=item.get("source", {}).get("name", ""),
                url=url,
                published_at=published_at,
                symbols=[symbol],
                category="",
                image_url=item.get("urlToImage", ""),
                relevance_score=relevance,
                raw_data=item,
            )
        except Exception as e:
            logger.warning(
                "Failed to parse NewsAPI item",
                error=str(e),
            )
            return None

    def _parse_headline_item(
        self,
        item: dict[str, Any],
        category: str,
    ) -> NewsArticle | None:
        """Parse a NewsAPI headline into NewsArticle."""
        try:
            url = item.get("url", "")
            item_id = hashlib.md5(url.encode()).hexdigest() if url else str(hash(item.get("title", "")))

            published_str = item.get("publishedAt", "")
            try:
                published_at = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
                published_at = published_at.replace(tzinfo=None)
            except (ValueError, AttributeError):
                published_at = datetime.now()

            return NewsArticle(
                id=item_id,
                headline=item.get("title", ""),
                summary=item.get("description", ""),
                content=item.get("content", ""),
                source=NewsSource.NEWSAPI,
                source_name=item.get("source", {}).get("name", ""),
                url=url,
                published_at=published_at,
                symbols=[],  # Headlines don't have specific symbols
                category=category,
                image_url=item.get("urlToImage", ""),
                relevance_score=0.6,  # Headlines are general
                raw_data=item,
            )
        except Exception as e:
            logger.warning(
                "Failed to parse NewsAPI headline",
                error=str(e),
            )
            return None
