"""
Integration tests for sentiment analysis system.

Tests the complete sentiment analysis pipeline including:
- News provider integration
- Analyzer orchestration
- Service coordination
- TradingState integration
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from reasoning_trading.config import (
    NewsProviderType,
    SentimentModelType,
    SentimentSettings,
    Settings,
)
from reasoning_trading.sentiment import (
    AggregatedSentiment,
    NewsArticle,
    SentimentService,
)
from reasoning_trading.sentiment.models import NewsSource, SentimentScore
from reasoning_trading.sentiment.providers import FinnhubNewsProvider, create_news_providers
from reasoning_trading.sentiment.analyzers import VADERAnalyzer, create_sentiment_analyzer
from reasoning_trading.sentiment.aggregator import SentimentAggregator

from tests.config import TestConfig, get_test_config


@pytest.fixture(scope="module")
def test_config() -> TestConfig:
    """Get test configuration."""
    return get_test_config()


@pytest.fixture
def mock_settings() -> Settings:
    """Create mock settings for testing."""
    settings = Settings()
    settings.sentiment = SentimentSettings(
        enabled_providers=[NewsProviderType.FINNHUB],
        primary_model=SentimentModelType.VADER,
        use_ensemble=False,
        sentiment_score_decay_hours=24.0,
        min_articles_for_signal=2,
        confidence_threshold=0.5,
        news_lookback_hours=48,
        max_articles_per_symbol=20,
        cache_ttl_minutes=5,
    )
    return settings


@pytest.fixture
def mock_articles() -> list[NewsArticle]:
    """Create mock news articles."""
    return [
        NewsArticle(
            id="article1",
            headline="Apple reports record-breaking iPhone sales",
            summary="Apple Inc. announced exceptional quarterly results driven by iPhone demand.",
            source=NewsSource.FINNHUB,
            source_name="Reuters",
            published_at=datetime.now() - timedelta(hours=2),
            symbols=["AAPL"],
            relevance_score=1.0,
        ),
        NewsArticle(
            id="article2",
            headline="Tech sector shows strong momentum",
            summary="Technology stocks rally as earnings exceed expectations.",
            source=NewsSource.FINNHUB,
            source_name="Bloomberg",
            published_at=datetime.now() - timedelta(hours=5),
            symbols=["AAPL", "MSFT", "GOOGL"],
            relevance_score=0.8,
        ),
        NewsArticle(
            id="article3",
            headline="Apple faces supply chain challenges",
            summary="Manufacturing delays may impact production schedules.",
            source=NewsSource.FINNHUB,
            source_name="WSJ",
            published_at=datetime.now() - timedelta(hours=8),
            symbols=["AAPL"],
            relevance_score=0.9,
        ),
    ]


class TestSentimentServiceIntegration:
    """Integration tests for SentimentService."""

    @pytest.mark.asyncio
    async def test_service_with_mock_provider(
        self,
        mock_settings: Settings,
        mock_articles: list[NewsArticle],
    ) -> None:
        """Test sentiment service with mocked news provider."""
        # Create mock provider
        mock_provider = AsyncMock()
        mock_provider.source = NewsSource.FINNHUB
        mock_provider.name = "MockFinnhub"
        mock_provider.is_available.return_value = True
        mock_provider.get_news = AsyncMock(return_value=mock_articles)

        # Create service with mock provider
        service = SentimentService(
            settings=mock_settings,
            providers=[mock_provider],
            analyzer=VADERAnalyzer(),
        )

        # Get sentiment
        sentiment = await service.get_sentiment("AAPL")

        assert sentiment.symbol == "AAPL"
        assert sentiment.article_count == 3
        assert sentiment.analyzed_at is not None
        # Mixed articles should give moderate sentiment
        assert -0.5 <= sentiment.combined_score <= 0.5

    @pytest.mark.asyncio
    async def test_service_caching(
        self,
        mock_settings: Settings,
        mock_articles: list[NewsArticle],
    ) -> None:
        """Test that sentiment results are cached."""
        mock_provider = AsyncMock()
        mock_provider.source = NewsSource.FINNHUB
        mock_provider.name = "MockFinnhub"
        mock_provider.is_available.return_value = True
        mock_provider.get_news = AsyncMock(return_value=mock_articles)

        service = SentimentService(
            settings=mock_settings,
            providers=[mock_provider],
            analyzer=VADERAnalyzer(),
        )

        # First call
        sentiment1 = await service.get_sentiment("AAPL")

        # Second call should use cache
        sentiment2 = await service.get_sentiment("AAPL")

        # Provider should only be called once
        assert mock_provider.get_news.call_count == 1
        assert sentiment1.symbol == sentiment2.symbol

    @pytest.mark.asyncio
    async def test_service_force_refresh(
        self,
        mock_settings: Settings,
        mock_articles: list[NewsArticle],
    ) -> None:
        """Test force refresh bypasses cache."""
        mock_provider = AsyncMock()
        mock_provider.source = NewsSource.FINNHUB
        mock_provider.name = "MockFinnhub"
        mock_provider.is_available.return_value = True
        mock_provider.get_news = AsyncMock(return_value=mock_articles)

        service = SentimentService(
            settings=mock_settings,
            providers=[mock_provider],
            analyzer=VADERAnalyzer(),
        )

        # First call
        await service.get_sentiment("AAPL")

        # Force refresh
        await service.get_sentiment("AAPL", force_refresh=True)

        # Provider should be called twice
        assert mock_provider.get_news.call_count == 2

    @pytest.mark.asyncio
    async def test_service_batch_analysis(
        self,
        mock_settings: Settings,
        mock_articles: list[NewsArticle],
    ) -> None:
        """Test batch sentiment analysis."""
        mock_provider = AsyncMock()
        mock_provider.source = NewsSource.FINNHUB
        mock_provider.name = "MockFinnhub"
        mock_provider.is_available.return_value = True
        mock_provider.get_news = AsyncMock(return_value=mock_articles)

        service = SentimentService(
            settings=mock_settings,
            providers=[mock_provider],
            analyzer=VADERAnalyzer(),
        )

        symbols = ["AAPL", "MSFT", "GOOGL"]
        results = await service.get_sentiment_batch(symbols)

        assert len(results) == 3
        assert all(sym in results for sym in symbols)

    @pytest.mark.asyncio
    async def test_service_analyze_text(
        self,
        mock_settings: Settings,
    ) -> None:
        """Test direct text analysis."""
        service = SentimentService(
            settings=mock_settings,
            providers=[],
            analyzer=VADERAnalyzer(),
        )

        score = await service.analyze_text(
            "The company announced excellent quarterly results!"
        )

        assert score.score > 0.0
        assert score.confidence > 0.0

    @pytest.mark.asyncio
    async def test_service_handles_provider_failure(
        self,
        mock_settings: Settings,
    ) -> None:
        """Test service handles provider failures gracefully."""
        mock_provider = AsyncMock()
        mock_provider.source = NewsSource.FINNHUB
        mock_provider.name = "MockFinnhub"
        mock_provider.is_available.return_value = True
        mock_provider.get_news = AsyncMock(side_effect=Exception("API Error"))

        service = SentimentService(
            settings=mock_settings,
            providers=[mock_provider],
            analyzer=VADERAnalyzer(),
        )

        # Should not raise, returns empty sentiment
        sentiment = await service.get_sentiment("AAPL")

        assert sentiment.symbol == "AAPL"
        assert sentiment.article_count == 0

    @pytest.mark.asyncio
    async def test_service_context_manager(
        self,
        mock_settings: Settings,
    ) -> None:
        """Test service can be used as context manager."""
        async with SentimentService(settings=mock_settings) as service:
            assert service is not None

    @pytest.mark.asyncio
    async def test_service_clear_cache(
        self,
        mock_settings: Settings,
        mock_articles: list[NewsArticle],
    ) -> None:
        """Test cache clearing."""
        mock_provider = AsyncMock()
        mock_provider.source = NewsSource.FINNHUB
        mock_provider.name = "MockFinnhub"
        mock_provider.is_available.return_value = True
        mock_provider.get_news = AsyncMock(return_value=mock_articles)

        service = SentimentService(
            settings=mock_settings,
            providers=[mock_provider],
            analyzer=VADERAnalyzer(),
        )

        # Populate cache
        await service.get_sentiment("AAPL")
        assert mock_provider.get_news.call_count == 1

        # Clear cache
        service.clear_cache()

        # Should fetch again
        await service.get_sentiment("AAPL")
        assert mock_provider.get_news.call_count == 2


class TestAnalyzerIntegration:
    """Integration tests for sentiment analyzers."""

    @pytest.mark.asyncio
    async def test_vader_processes_articles(
        self,
        mock_articles: list[NewsArticle],
    ) -> None:
        """Test VADER can process news articles."""
        analyzer = VADERAnalyzer()

        if not analyzer.is_available():
            pytest.skip("VADER not available")

        for article in mock_articles:
            score = await analyzer.analyze_article(article)
            assert -1.0 <= score.score <= 1.0
            assert 0.0 <= score.confidence <= 1.0

    @pytest.mark.asyncio
    async def test_analyzer_factory_creates_working_analyzer(
        self,
        mock_settings: Settings,
    ) -> None:
        """Test analyzer factory creates functional analyzer."""
        analyzer = create_sentiment_analyzer(
            settings=mock_settings,
            model_type=SentimentModelType.VADER,
        )

        score = await analyzer.analyze("Great news for investors!")

        assert score is not None
        assert score.score > 0.0


class TestAggregatorIntegration:
    """Integration tests for sentiment aggregation."""

    @pytest.fixture
    def aggregator(self, mock_settings: Settings) -> SentimentAggregator:
        """Create aggregator."""
        return SentimentAggregator(settings=mock_settings)

    @pytest.mark.asyncio
    async def test_full_aggregation_pipeline(
        self,
        aggregator: SentimentAggregator,
        mock_articles: list[NewsArticle],
    ) -> None:
        """Test complete aggregation pipeline."""
        analyzer = VADERAnalyzer()

        if not analyzer.is_available():
            pytest.skip("VADER not available")

        # Analyze all articles
        from reasoning_trading.sentiment.models import SentimentResult

        results = []
        for article in mock_articles:
            score = await analyzer.analyze_article(article)
            result = SentimentResult(
                article=article,
                scores=[score],
                ensemble_score=score.score,
                ensemble_confidence=score.confidence,
            )
            results.append(result)

        # Aggregate
        aggregated = aggregator.aggregate("AAPL", results)

        assert aggregated.symbol == "AAPL"
        assert aggregated.article_count == len(mock_articles)
        assert len(aggregated.providers_used) > 0
        assert len(aggregated.models_used) > 0


class TestProviderIntegration:
    """Integration tests for news providers."""

    @pytest.mark.asyncio
    async def test_provider_factory_respects_settings(
        self,
        mock_settings: Settings,
    ) -> None:
        """Test provider factory creates providers based on settings."""
        # Without API keys, no providers should be available
        providers = create_news_providers(settings=mock_settings)

        # Check that factory attempted to create requested providers
        assert isinstance(providers, list)

    @pytest.mark.asyncio
    async def test_finnhub_provider_requires_api_key(self) -> None:
        """Test Finnhub provider checks for API key."""
        settings = Settings()
        settings.data_apis.finnhub_api_key = None

        provider = FinnhubNewsProvider(settings=settings)

        assert provider.is_available() is False


class TestEndToEndSentiment:
    """End-to-end tests for sentiment analysis."""

    @pytest.mark.asyncio
    async def test_complete_sentiment_flow(
        self,
        mock_settings: Settings,
        mock_articles: list[NewsArticle],
    ) -> None:
        """Test complete flow from news to aggregated sentiment."""
        # Setup mock provider
        mock_provider = AsyncMock()
        mock_provider.source = NewsSource.FINNHUB
        mock_provider.name = "MockFinnhub"
        mock_provider.is_available.return_value = True
        mock_provider.get_news = AsyncMock(return_value=mock_articles)

        # Create service
        service = SentimentService(
            settings=mock_settings,
            providers=[mock_provider],
            analyzer=VADERAnalyzer(),
        )

        # Get sentiment
        sentiment = await service.get_sentiment("AAPL")

        # Verify complete result
        assert sentiment.symbol == "AAPL"
        assert sentiment.article_count == len(mock_articles)
        assert sentiment.analyzed_at is not None
        assert -1.0 <= sentiment.combined_score <= 1.0
        assert 0.0 <= sentiment.combined_confidence <= 1.0

        # Should have time range
        assert sentiment.newest_article is not None
        assert sentiment.oldest_article is not None
        assert sentiment.newest_article >= sentiment.oldest_article

        # Should categorize articles
        total_categorized = (
            sentiment.positive_count +
            sentiment.negative_count +
            sentiment.neutral_count
        )
        assert total_categorized == sentiment.article_count

    @pytest.mark.asyncio
    async def test_sentiment_affects_trading_signals(
        self,
        mock_settings: Settings,
        mock_articles: list[NewsArticle],
        test_config: TestConfig,
    ) -> None:
        """Test that sentiment integrates with trading signals."""
        # Create strongly bullish articles
        bullish_articles = [
            NewsArticle(
                id=f"bullish_{i}",
                headline="Massive gains! Stock skyrockets on incredible news!",
                summary="Outstanding performance exceeds all expectations.",
                source=NewsSource.FINNHUB,
                published_at=datetime.now() - timedelta(hours=i),
                symbols=[test_config.primary_symbol],
                relevance_score=1.0,
            )
            for i in range(5)
        ]

        mock_provider = AsyncMock()
        mock_provider.source = NewsSource.FINNHUB
        mock_provider.name = "MockFinnhub"
        mock_provider.is_available.return_value = True
        mock_provider.get_news = AsyncMock(return_value=bullish_articles)

        service = SentimentService(
            settings=mock_settings,
            providers=[mock_provider],
            analyzer=VADERAnalyzer(),
        )

        sentiment = await service.get_sentiment(test_config.primary_symbol)

        # Should be strongly bullish
        assert sentiment.combined_score > 0.3
        assert sentiment.is_reliable

        # Convert to analyst signals format
        signals = sentiment.to_analyst_signals()
        assert signals["news_analyst_score"] > 0.0
