"""
Main sentiment analysis service.

Coordinates news providers, sentiment analyzers, and aggregation
to provide a unified interface for sentiment analysis.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Any

import structlog

from reasoning_trading.config import Settings, get_settings
from reasoning_trading.sentiment.aggregator import SentimentAggregator
from reasoning_trading.sentiment.analyzers import (
    SentimentAnalyzer,
    create_sentiment_analyzer,
)
from reasoning_trading.sentiment.models import (
    AggregatedSentiment,
    NewsArticle,
    SentimentCache,
    SentimentResult,
    SentimentScore,
)
from reasoning_trading.sentiment.providers import (
    NewsProvider,
    NewsProviderError,
    create_news_providers,
)

logger = structlog.get_logger(__name__)


class SentimentService:
    """
    Main sentiment analysis service.

    Provides a unified interface for:
    - Fetching news from multiple providers
    - Analyzing sentiment using configured models
    - Aggregating results with time-decay weighting
    - Caching results to reduce API calls

    Usage:
        service = SentimentService()
        sentiment = await service.get_sentiment("AAPL")
        print(f"Score: {sentiment.combined_score}")
    """

    def __init__(
        self,
        settings: Settings | None = None,
        providers: list[NewsProvider] | None = None,
        analyzer: SentimentAnalyzer | None = None,
    ):
        """
        Initialize the sentiment service.

        Args:
            settings: Application settings
            providers: News providers (created from settings if None)
            analyzer: Sentiment analyzer (created from settings if None)
        """
        self._settings = settings or get_settings()
        self._providers = providers or create_news_providers(self._settings)
        self._analyzer = analyzer or create_sentiment_analyzer(self._settings)
        self._aggregator = SentimentAggregator(self._settings)
        self._cache: dict[str, SentimentCache] = {}

    @property
    def cache_ttl_minutes(self) -> int:
        """Get cache TTL in minutes."""
        return self._settings.sentiment.cache_ttl_minutes

    def clear_cache(self) -> None:
        """Clear the sentiment cache."""
        self._cache.clear()
        logger.debug("Sentiment cache cleared")

    async def get_sentiment(
        self,
        symbol: str,
        force_refresh: bool = False,
    ) -> AggregatedSentiment:
        """
        Get aggregated sentiment for a symbol.

        Args:
            symbol: Trading symbol
            force_refresh: Bypass cache and fetch fresh data

        Returns:
            AggregatedSentiment with combined scores
        """
        # Check cache
        if not force_refresh:
            cached = self._get_cached(symbol)
            if cached is not None:
                logger.debug(
                    "Returning cached sentiment",
                    symbol=symbol,
                )
                return cached

        # Fetch and analyze news
        articles = await self._fetch_news(symbol)

        if not articles:
            logger.warning(
                "No articles found for sentiment analysis",
                symbol=symbol,
            )
            return AggregatedSentiment(
                symbol=symbol,
                analyzed_at=datetime.now(),
            )

        # Analyze articles
        results = await self._analyze_articles(articles)

        # Aggregate results
        aggregated = self._aggregator.aggregate(
            symbol=symbol,
            results=results,
        )

        # Cache results
        self._cache[symbol] = SentimentCache(
            sentiment=aggregated,
            ttl_minutes=self.cache_ttl_minutes,
        )

        return aggregated

    async def get_sentiment_batch(
        self,
        symbols: list[str],
        force_refresh: bool = False,
    ) -> dict[str, AggregatedSentiment]:
        """
        Get sentiment for multiple symbols.

        Processes symbols in parallel for efficiency.

        Args:
            symbols: List of trading symbols
            force_refresh: Bypass cache

        Returns:
            Dict mapping symbols to their sentiment
        """
        results = await asyncio.gather(
            *[self.get_sentiment(s, force_refresh) for s in symbols],
            return_exceptions=True,
        )

        sentiment_map = {}
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(
                    "Failed to get sentiment",
                    symbol=symbols[i],
                    error=str(result),
                )
                sentiment_map[symbols[i]] = AggregatedSentiment(
                    symbol=symbols[i],
                    analyzed_at=datetime.now(),
                )
            else:
                sentiment_map[symbols[i]] = result

        return sentiment_map

    async def analyze_text(self, text: str) -> SentimentScore:
        """
        Analyze sentiment of arbitrary text.

        Args:
            text: Text to analyze

        Returns:
            SentimentScore with results
        """
        return await self._analyzer.analyze(text)

    async def get_news(
        self,
        symbol: str,
        hours: int | None = None,
        limit: int | None = None,
    ) -> list[NewsArticle]:
        """
        Get news articles for a symbol.

        Args:
            symbol: Trading symbol
            hours: Hours of history (defaults to settings)
            limit: Maximum articles (defaults to settings)

        Returns:
            List of NewsArticle objects
        """
        lookback = hours or self._settings.sentiment.news_lookback_hours
        max_articles = limit or self._settings.sentiment.max_articles_per_symbol

        from_date = datetime.now() - timedelta(hours=lookback)

        return await self._fetch_news(
            symbol,
            from_date=from_date,
            limit=max_articles,
        )

    async def get_market_sentiment(
        self,
        category: str | None = None,
    ) -> AggregatedSentiment:
        """
        Get general market sentiment from headlines.

        Args:
            category: News category filter

        Returns:
            AggregatedSentiment for market overall
        """
        articles = await self._fetch_market_news(category=category)

        if not articles:
            return AggregatedSentiment(
                symbol="MARKET",
                analyzed_at=datetime.now(),
            )

        results = await self._analyze_articles(articles)

        return self._aggregator.aggregate(
            symbol="MARKET",
            results=results,
        )

    def _get_cached(self, symbol: str) -> AggregatedSentiment | None:
        """Get cached sentiment if not expired."""
        cached = self._cache.get(symbol)
        if cached is not None and not cached.is_expired():
            return cached.sentiment
        return None

    async def _fetch_news(
        self,
        symbol: str,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        limit: int | None = None,
    ) -> list[NewsArticle]:
        """Fetch news from all providers."""
        if not self._providers:
            logger.warning("No news providers available")
            return []

        # Fetch from all providers in parallel
        results = await asyncio.gather(
            *[
                self._safe_fetch_news(p, symbol, from_date, to_date, limit)
                for p in self._providers
            ],
            return_exceptions=False,
        )

        # Combine and deduplicate
        all_articles: list[NewsArticle] = []
        seen_ids: set[str] = set()

        for articles in results:
            if articles is not None:
                for article in articles:
                    if article.id not in seen_ids:
                        seen_ids.add(article.id)
                        all_articles.append(article)

        # Sort by published time (newest first)
        all_articles.sort(key=lambda a: a.published_at, reverse=True)

        # Limit total articles
        max_articles = limit or self._settings.sentiment.max_articles_per_symbol
        return all_articles[:max_articles]

    async def _safe_fetch_news(
        self,
        provider: NewsProvider,
        symbol: str,
        from_date: datetime | None,
        to_date: datetime | None,
        limit: int | None,
    ) -> list[NewsArticle] | None:
        """Safely fetch news from a provider."""
        try:
            return await provider.get_news(
                symbol=symbol,
                from_date=from_date,
                to_date=to_date,
                limit=limit,
            )
        except NewsProviderError as e:
            logger.warning(
                "Provider failed to fetch news",
                provider=e.provider,
                error=str(e),
                retriable=e.retriable,
            )
            return None
        except Exception as e:
            logger.warning(
                "Unexpected error fetching news",
                provider=provider.name,
                error=str(e),
            )
            return None

    async def _fetch_market_news(
        self,
        category: str | None = None,
    ) -> list[NewsArticle]:
        """Fetch general market news."""
        if not self._providers:
            return []

        results = await asyncio.gather(
            *[
                self._safe_fetch_market_news(p, category)
                for p in self._providers
            ],
            return_exceptions=False,
        )

        all_articles: list[NewsArticle] = []
        seen_ids: set[str] = set()

        for articles in results:
            if articles is not None:
                for article in articles:
                    if article.id not in seen_ids:
                        seen_ids.add(article.id)
                        all_articles.append(article)

        all_articles.sort(key=lambda a: a.published_at, reverse=True)
        return all_articles[:self._settings.sentiment.max_articles_per_symbol]

    async def _safe_fetch_market_news(
        self,
        provider: NewsProvider,
        category: str | None,
    ) -> list[NewsArticle] | None:
        """Safely fetch market news from a provider."""
        try:
            return await provider.get_market_news(category=category)
        except Exception as e:
            logger.warning(
                "Failed to fetch market news",
                provider=provider.name,
                error=str(e),
            )
            return None

    async def _analyze_articles(
        self,
        articles: list[NewsArticle],
    ) -> list[SentimentResult]:
        """Analyze sentiment of articles."""
        if not articles:
            return []

        # Extract text for batch analysis
        texts = [a.get_text_for_analysis() for a in articles]

        # Batch analyze
        try:
            scores = await self._analyzer.analyze_batch(texts)
        except Exception as e:
            logger.error(
                "Batch sentiment analysis failed",
                error=str(e),
            )
            # Fall back to individual analysis
            scores = []
            for text in texts:
                try:
                    score = await self._analyzer.analyze(text)
                    scores.append(score)
                except Exception:
                    scores.append(
                        SentimentScore.from_probabilities(
                            positive=0.33,
                            negative=0.33,
                            neutral=0.34,
                            model_name=self._analyzer.model_name,
                        )
                    )

        # Create results
        results = []
        for article, score in zip(articles, scores):
            result = SentimentResult(
                article=article,
                scores=[score],
                ensemble_score=score.score,
                ensemble_confidence=score.confidence,
            )
            results.append(result)

        return results

    async def close(self) -> None:
        """Close all provider connections."""
        for provider in self._providers:
            if hasattr(provider, "close"):
                await provider.close()

    async def __aenter__(self) -> SentimentService:
        """Async context manager entry."""
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        await self.close()


# Convenience function for quick access
async def get_symbol_sentiment(
    symbol: str,
    settings: Settings | None = None,
) -> AggregatedSentiment:
    """
    Quick function to get sentiment for a symbol.

    Args:
        symbol: Trading symbol
        settings: Application settings

    Returns:
        AggregatedSentiment with results
    """
    async with SentimentService(settings=settings) as service:
        return await service.get_sentiment(symbol)
