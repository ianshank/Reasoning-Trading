"""
Unit tests for sentiment analysis module.

Tests the individual components of the sentiment analysis system
including models, analyzers, providers, and aggregation.
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
from reasoning_trading.sentiment.models import (
    AggregatedSentiment,
    NewsArticle,
    NewsSource,
    SentimentCache,
    SentimentLabel,
    SentimentResult,
    SentimentScore,
)
from reasoning_trading.sentiment.aggregator import SentimentAggregator
from reasoning_trading.sentiment.analyzers.base import AnalyzerError
from reasoning_trading.sentiment.analyzers.vader import VADERAnalyzer
from reasoning_trading.sentiment.analyzers.ensemble import EnsembleAnalyzer
from reasoning_trading.sentiment.providers.base import NewsProviderError

from tests.config import TestConfig, get_test_config


# =============================================================================
# Test Configuration
# =============================================================================


@pytest.fixture(scope="module")
def test_config() -> TestConfig:
    """Get test configuration."""
    return get_test_config()


@pytest.fixture
def sentiment_settings() -> SentimentSettings:
    """Create sentiment settings for testing."""
    return SentimentSettings(
        enabled_providers=[NewsProviderType.FINNHUB],
        primary_model=SentimentModelType.VADER,
        fallback_model=SentimentModelType.VADER,
        use_ensemble=False,
        sentiment_score_decay_hours=24.0,
        min_articles_for_signal=3,
        confidence_threshold=0.5,
        news_lookback_hours=48,
        max_articles_per_symbol=50,
        cache_ttl_minutes=15,
    )


# =============================================================================
# Model Tests
# =============================================================================


class TestSentimentScore:
    """Tests for SentimentScore model."""

    def test_from_probabilities_bullish(self) -> None:
        """Test creating score from bullish probabilities."""
        score = SentimentScore.from_probabilities(
            positive=0.7,
            negative=0.1,
            neutral=0.2,
            model_name="test_model",
        )

        assert score.score == pytest.approx(0.6, abs=0.01)  # 0.7 - 0.1
        assert score.label == SentimentLabel.BULLISH
        assert score.confidence == pytest.approx(0.7, abs=0.01)
        assert score.model_name == "test_model"

    def test_from_probabilities_bearish(self) -> None:
        """Test creating score from bearish probabilities."""
        score = SentimentScore.from_probabilities(
            positive=0.1,
            negative=0.8,
            neutral=0.1,
            model_name="test_model",
        )

        assert score.score == pytest.approx(-0.7, abs=0.01)
        assert score.label == SentimentLabel.BEARISH
        assert score.confidence == pytest.approx(0.8, abs=0.01)

    def test_from_probabilities_neutral(self) -> None:
        """Test creating score from neutral probabilities."""
        score = SentimentScore.from_probabilities(
            positive=0.3,
            negative=0.3,
            neutral=0.4,
            model_name="test_model",
        )

        assert score.score == pytest.approx(0.0, abs=0.01)
        assert score.label == SentimentLabel.NEUTRAL


class TestNewsArticle:
    """Tests for NewsArticle model."""

    def test_get_text_for_analysis_with_content(self) -> None:
        """Test text extraction with full content."""
        article = NewsArticle(
            id="test1",
            headline="Breaking: Stock Rises",
            summary="Short summary",
            content="Full article content here",
            source=NewsSource.FINNHUB,
            published_at=datetime.now(),
        )

        text = article.get_text_for_analysis()
        assert "Breaking: Stock Rises" in text
        assert "Full article content" in text

    def test_get_text_for_analysis_headline_only(self) -> None:
        """Test text extraction with headline only."""
        article = NewsArticle(
            id="test2",
            headline="Breaking News",
            source=NewsSource.FINNHUB,
            published_at=datetime.now(),
        )

        text = article.get_text_for_analysis()
        assert text == "Breaking News"

    def test_age_hours(self) -> None:
        """Test article age calculation."""
        old_article = NewsArticle(
            id="test3",
            headline="Old News",
            source=NewsSource.FINNHUB,
            published_at=datetime.now() - timedelta(hours=24),
        )

        age = old_article.age_hours()
        assert age == pytest.approx(24.0, abs=0.1)


class TestAggregatedSentiment:
    """Tests for AggregatedSentiment model."""

    def test_sentiment_label_bullish(self) -> None:
        """Test bullish sentiment label."""
        sentiment = AggregatedSentiment(
            symbol="AAPL",
            combined_score=0.5,
            combined_confidence=0.8,
        )
        assert sentiment.sentiment_label == SentimentLabel.BULLISH

    def test_sentiment_label_bearish(self) -> None:
        """Test bearish sentiment label."""
        sentiment = AggregatedSentiment(
            symbol="AAPL",
            combined_score=-0.5,
            combined_confidence=0.8,
        )
        assert sentiment.sentiment_label == SentimentLabel.BEARISH

    def test_sentiment_label_neutral(self) -> None:
        """Test neutral sentiment label."""
        sentiment = AggregatedSentiment(
            symbol="AAPL",
            combined_score=0.05,
            combined_confidence=0.8,
        )
        assert sentiment.sentiment_label == SentimentLabel.NEUTRAL

    def test_is_reliable_true(self) -> None:
        """Test reliable sentiment check."""
        sentiment = AggregatedSentiment(
            symbol="AAPL",
            combined_score=0.5,
            combined_confidence=0.7,
            article_count=5,
        )
        assert sentiment.is_reliable is True

    def test_is_reliable_low_confidence(self) -> None:
        """Test unreliable sentiment with low confidence."""
        sentiment = AggregatedSentiment(
            symbol="AAPL",
            combined_score=0.5,
            combined_confidence=0.3,
            article_count=5,
        )
        assert sentiment.is_reliable is False

    def test_is_reliable_few_articles(self) -> None:
        """Test unreliable sentiment with few articles."""
        sentiment = AggregatedSentiment(
            symbol="AAPL",
            combined_score=0.5,
            combined_confidence=0.7,
            article_count=1,
        )
        assert sentiment.is_reliable is False

    def test_to_analyst_signals(self) -> None:
        """Test conversion to analyst signals format."""
        sentiment = AggregatedSentiment(
            symbol="AAPL",
            news_score=0.6,
            news_confidence=0.8,
            social_score=0.4,
            social_confidence=0.6,
        )

        signals = sentiment.to_analyst_signals()

        assert signals["news_analyst_score"] == 0.6
        assert signals["news_analyst_confidence"] == 0.8
        assert signals["social_sentiment_score"] == 0.4
        assert signals["social_sentiment_confidence"] == 0.6


class TestSentimentCache:
    """Tests for SentimentCache."""

    def test_is_expired_fresh(self) -> None:
        """Test fresh cache is not expired."""
        cache = SentimentCache(
            sentiment=AggregatedSentiment(symbol="AAPL"),
            ttl_minutes=15,
        )
        assert cache.is_expired() is False

    def test_is_expired_old(self) -> None:
        """Test old cache is expired."""
        cache = SentimentCache(
            sentiment=AggregatedSentiment(symbol="AAPL"),
            cached_at=datetime.now() - timedelta(minutes=20),
            ttl_minutes=15,
        )
        assert cache.is_expired() is True


# =============================================================================
# Analyzer Tests
# =============================================================================


class TestVADERAnalyzer:
    """Tests for VADER sentiment analyzer."""

    @pytest.fixture
    def analyzer(self) -> VADERAnalyzer:
        """Create VADER analyzer."""
        return VADERAnalyzer()

    @pytest.mark.asyncio
    async def test_analyze_positive_text(self, analyzer: VADERAnalyzer) -> None:
        """Test analysis of positive text."""
        if not analyzer.is_available():
            pytest.skip("VADER not available")

        score = await analyzer.analyze(
            "The company reported excellent earnings, beating all expectations!"
        )

        assert score.score > 0.0
        assert score.label == SentimentLabel.BULLISH
        assert score.confidence > 0.0

    @pytest.mark.asyncio
    async def test_analyze_negative_text(self, analyzer: VADERAnalyzer) -> None:
        """Test analysis of negative text."""
        if not analyzer.is_available():
            pytest.skip("VADER not available")

        score = await analyzer.analyze(
            "The stock crashed after terrible earnings and massive losses."
        )

        assert score.score < 0.0
        assert score.label == SentimentLabel.BEARISH

    @pytest.mark.asyncio
    async def test_analyze_neutral_text(self, analyzer: VADERAnalyzer) -> None:
        """Test analysis of neutral text."""
        if not analyzer.is_available():
            pytest.skip("VADER not available")

        score = await analyzer.analyze(
            "The company released its quarterly report today."
        )

        # Should be close to neutral
        assert abs(score.score) < 0.5

    @pytest.mark.asyncio
    async def test_analyze_empty_text(self, analyzer: VADERAnalyzer) -> None:
        """Test analysis of empty text returns neutral."""
        if not analyzer.is_available():
            pytest.skip("VADER not available")

        score = await analyzer.analyze("")

        assert score.score == 0.0
        assert score.label == SentimentLabel.NEUTRAL

    @pytest.mark.asyncio
    async def test_analyze_batch(self, analyzer: VADERAnalyzer) -> None:
        """Test batch analysis."""
        if not analyzer.is_available():
            pytest.skip("VADER not available")

        texts = [
            "Great news! Stock soaring!",
            "Terrible results, stock plunging.",
            "No major changes reported.",
        ]

        scores = await analyzer.analyze_batch(texts)

        assert len(scores) == 3
        assert scores[0].score > 0.0  # Positive
        assert scores[1].score < 0.0  # Negative


class TestEnsembleAnalyzer:
    """Tests for ensemble sentiment analyzer."""

    @pytest.fixture
    def ensemble(self) -> EnsembleAnalyzer:
        """Create ensemble with VADER (always available)."""
        ensemble = EnsembleAnalyzer()
        ensemble.add_analyzer(VADERAnalyzer())
        return ensemble

    @pytest.mark.asyncio
    async def test_analyze_with_single_analyzer(self, ensemble: EnsembleAnalyzer) -> None:
        """Test ensemble with single analyzer."""
        if not ensemble.is_available():
            pytest.skip("No analyzers available")

        score = await ensemble.analyze("Great earnings report!")

        assert score.score != 0.0
        assert score.confidence > 0.0
        assert "ensemble" in score.model_name

    @pytest.mark.asyncio
    async def test_is_available(self, ensemble: EnsembleAnalyzer) -> None:
        """Test availability check."""
        assert ensemble.is_available() is True

    @pytest.mark.asyncio
    async def test_empty_ensemble_not_available(self) -> None:
        """Test empty ensemble is not available."""
        empty_ensemble = EnsembleAnalyzer()
        assert empty_ensemble.is_available() is False


# =============================================================================
# Aggregator Tests
# =============================================================================


class TestSentimentAggregator:
    """Tests for sentiment aggregation."""

    @pytest.fixture
    def aggregator(self, sentiment_settings: SentimentSettings) -> SentimentAggregator:
        """Create aggregator with test settings."""
        settings = Settings()
        settings.sentiment = sentiment_settings
        return SentimentAggregator(settings=settings)

    def _create_article(
        self,
        headline: str,
        hours_ago: float = 0,
        relevance: float = 1.0,
    ) -> NewsArticle:
        """Helper to create test articles."""
        return NewsArticle(
            id=f"test_{hash(headline)}",
            headline=headline,
            source=NewsSource.FINNHUB,
            published_at=datetime.now() - timedelta(hours=hours_ago),
            relevance_score=relevance,
        )

    def _create_result(
        self,
        article: NewsArticle,
        score: float,
        confidence: float = 0.8,
    ) -> SentimentResult:
        """Helper to create test results."""
        label = (
            SentimentLabel.BULLISH if score > 0.1
            else SentimentLabel.BEARISH if score < -0.1
            else SentimentLabel.NEUTRAL
        )
        sentiment_score = SentimentScore(
            score=score,
            confidence=confidence,
            label=label,
            model_name="test",
        )
        return SentimentResult(
            article=article,
            scores=[sentiment_score],
            ensemble_score=score,
            ensemble_confidence=confidence,
        )

    def test_aggregate_bullish_articles(
        self,
        aggregator: SentimentAggregator,
    ) -> None:
        """Test aggregation of bullish articles."""
        results = [
            self._create_result(
                self._create_article("Stock surges on great news", hours_ago=1),
                score=0.8,
            ),
            self._create_result(
                self._create_article("Earnings beat expectations", hours_ago=2),
                score=0.6,
            ),
            self._create_result(
                self._create_article("Analysts upgrade rating", hours_ago=3),
                score=0.7,
            ),
        ]

        aggregated = aggregator.aggregate("AAPL", results)

        assert aggregated.symbol == "AAPL"
        assert aggregated.news_score > 0.5
        assert aggregated.combined_score > 0.5
        assert aggregated.article_count == 3
        assert aggregated.positive_count == 3

    def test_aggregate_bearish_articles(
        self,
        aggregator: SentimentAggregator,
    ) -> None:
        """Test aggregation of bearish articles."""
        results = [
            self._create_result(
                self._create_article("Stock crashes on bad news", hours_ago=1),
                score=-0.8,
            ),
            self._create_result(
                self._create_article("Earnings miss expectations", hours_ago=2),
                score=-0.6,
            ),
            self._create_result(
                self._create_article("Analysts downgrade rating", hours_ago=3),
                score=-0.7,
            ),
        ]

        aggregated = aggregator.aggregate("AAPL", results)

        assert aggregated.news_score < -0.5
        assert aggregated.combined_score < -0.5
        assert aggregated.negative_count == 3

    def test_aggregate_mixed_articles(
        self,
        aggregator: SentimentAggregator,
    ) -> None:
        """Test aggregation of mixed sentiment articles."""
        results = [
            self._create_result(
                self._create_article("Good news!", hours_ago=1),
                score=0.7,
            ),
            self._create_result(
                self._create_article("Bad news!", hours_ago=1),
                score=-0.7,
            ),
            self._create_result(
                self._create_article("No news", hours_ago=1),
                score=0.0,
            ),
        ]

        aggregated = aggregator.aggregate("AAPL", results)

        # Should be close to neutral with mixed signals
        assert abs(aggregated.news_score) < 0.3
        assert aggregated.positive_count == 1
        assert aggregated.negative_count == 1
        assert aggregated.neutral_count == 1

    def test_aggregate_time_decay(
        self,
        aggregator: SentimentAggregator,
    ) -> None:
        """Test that newer articles have more weight."""
        # Recent bullish article
        recent_result = self._create_result(
            self._create_article("Recent positive news", hours_ago=1),
            score=0.8,
        )

        # Old bearish article
        old_result = self._create_result(
            self._create_article("Old negative news", hours_ago=48),
            score=-0.8,
        )

        aggregated = aggregator.aggregate("AAPL", [recent_result, old_result])

        # Recent bullish should outweigh old bearish
        assert aggregated.news_score > 0.0

    def test_aggregate_empty_results(
        self,
        aggregator: SentimentAggregator,
    ) -> None:
        """Test aggregation with no results."""
        aggregated = aggregator.aggregate("AAPL", [])

        assert aggregated.symbol == "AAPL"
        assert aggregated.news_score == 0.0
        assert aggregated.combined_score == 0.0
        assert aggregated.article_count == 0

    def test_aggregate_filters_low_confidence(
        self,
        aggregator: SentimentAggregator,
    ) -> None:
        """Test that low confidence results are filtered."""
        results = [
            self._create_result(
                self._create_article("High confidence bullish", hours_ago=1),
                score=0.8,
                confidence=0.9,
            ),
            self._create_result(
                self._create_article("Low confidence bearish", hours_ago=1),
                score=-0.8,
                confidence=0.3,  # Below threshold
            ),
        ]

        aggregated = aggregator.aggregate("AAPL", results)

        # Should only count high confidence article
        assert aggregated.news_score > 0.5


# =============================================================================
# Provider Tests
# =============================================================================


class TestNewsProviderError:
    """Tests for NewsProviderError."""

    def test_error_attributes(self) -> None:
        """Test error has correct attributes."""
        error = NewsProviderError(
            message="API rate limit exceeded",
            provider="finnhub",
            retriable=True,
        )

        assert str(error) == "API rate limit exceeded"
        assert error.provider == "finnhub"
        assert error.retriable is True

    def test_non_retriable_error(self) -> None:
        """Test non-retriable error."""
        error = NewsProviderError(
            message="Invalid API key",
            provider="finnhub",
            retriable=False,
        )

        assert error.retriable is False


# =============================================================================
# SentimentResult Tests
# =============================================================================


class TestSentimentResult:
    """Tests for SentimentResult model."""

    def test_time_weighted_score(self) -> None:
        """Test time-weighted score calculation."""
        article = NewsArticle(
            id="test",
            headline="Test",
            source=NewsSource.FINNHUB,
            published_at=datetime.now() - timedelta(hours=24),
        )
        result = SentimentResult(
            article=article,
            ensemble_score=1.0,
            ensemble_confidence=0.8,
        )

        # After 24 hours (decay half-life), score should be ~0.5
        weighted = result.get_time_weighted_score(decay_hours=24.0)
        assert weighted == pytest.approx(0.5, abs=0.1)

    def test_time_weighted_score_fresh(self) -> None:
        """Test time-weighted score for fresh article."""
        article = NewsArticle(
            id="test",
            headline="Test",
            source=NewsSource.FINNHUB,
            published_at=datetime.now(),
        )
        result = SentimentResult(
            article=article,
            ensemble_score=1.0,
            ensemble_confidence=0.8,
        )

        # Fresh article should have minimal decay
        weighted = result.get_time_weighted_score(decay_hours=24.0)
        assert weighted == pytest.approx(1.0, abs=0.05)
