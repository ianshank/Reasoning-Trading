"""
Sentiment aggregation module.

Combines sentiment from multiple articles with time-decay weighting
and confidence-based aggregation.
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import Callable

import structlog

from reasoning_trading.config import Settings, get_settings
from reasoning_trading.sentiment.models import (
    AggregatedSentiment,
    NewsArticle,
    SentimentLabel,
    SentimentResult,
)

logger = structlog.get_logger(__name__)


class SentimentAggregator:
    """
    Aggregates sentiment from multiple articles.

    Features:
    - Time-decay weighting (newer articles have more impact)
    - Relevance-based weighting
    - Confidence-based combination
    - Separate news and social sentiment tracks
    """

    def __init__(self, settings: Settings | None = None):
        """
        Initialize the aggregator.

        Args:
            settings: Application settings
        """
        self._settings = settings or get_settings()

    @property
    def decay_hours(self) -> float:
        """Get the decay half-life in hours."""
        return self._settings.sentiment.sentiment_score_decay_hours

    @property
    def min_articles(self) -> int:
        """Get minimum articles for reliable signal."""
        return self._settings.sentiment.min_articles_for_signal

    @property
    def confidence_threshold(self) -> float:
        """Get confidence threshold for inclusion."""
        return self._settings.sentiment.confidence_threshold

    @property
    def social_weight(self) -> float:
        """Get weight for social sentiment."""
        return self._settings.sentiment.social_weight

    def aggregate(
        self,
        symbol: str,
        results: list[SentimentResult],
        social_results: list[SentimentResult] | None = None,
    ) -> AggregatedSentiment:
        """
        Aggregate sentiment results for a symbol.

        Args:
            symbol: Trading symbol
            results: News sentiment results
            social_results: Social media sentiment results

        Returns:
            AggregatedSentiment with combined scores
        """
        # Filter results by confidence
        filtered_news = self._filter_by_confidence(results)
        filtered_social = self._filter_by_confidence(social_results or [])

        # Calculate news sentiment
        news_score, news_confidence = self._calculate_weighted_sentiment(
            filtered_news,
            weight_fn=self._news_weight,
        )

        # Calculate social sentiment
        social_score, social_confidence = self._calculate_weighted_sentiment(
            filtered_social,
            weight_fn=self._social_weight_fn,
        )

        # Combine news and social
        combined_score, combined_confidence = self._combine_news_social(
            news_score,
            news_confidence,
            social_score,
            social_confidence,
        )

        # Count sentiments
        positive_count = sum(
            1 for r in filtered_news if r.ensemble_score > 0.1
        )
        negative_count = sum(
            1 for r in filtered_news if r.ensemble_score < -0.1
        )
        neutral_count = len(filtered_news) - positive_count - negative_count

        # Get time range
        all_results = filtered_news + filtered_social
        timestamps = [r.article.published_at for r in all_results]
        oldest = min(timestamps) if timestamps else None
        newest = max(timestamps) if timestamps else None

        # Get providers and models used
        providers = list(set(r.article.source.value for r in all_results))
        models = list(set(
            score.model_name
            for r in all_results
            for score in r.scores
        ))

        # Extract top headlines
        top_bullish = self._get_top_headlines(
            filtered_news,
            positive=True,
            limit=3,
        )
        top_bearish = self._get_top_headlines(
            filtered_news,
            positive=False,
            limit=3,
        )

        aggregated = AggregatedSentiment(
            symbol=symbol,
            news_score=news_score,
            news_confidence=news_confidence,
            social_score=social_score,
            social_confidence=social_confidence,
            combined_score=combined_score,
            combined_confidence=combined_confidence,
            article_count=len(filtered_news),
            positive_count=positive_count,
            negative_count=negative_count,
            neutral_count=neutral_count,
            oldest_article=oldest,
            newest_article=newest,
            analyzed_at=datetime.now(),
            providers_used=providers,
            models_used=models,
            top_bullish_headlines=top_bullish,
            top_bearish_headlines=top_bearish,
        )

        logger.info(
            "Aggregated sentiment",
            symbol=symbol,
            combined_score=combined_score,
            combined_confidence=combined_confidence,
            article_count=len(filtered_news),
        )

        return aggregated

    def _filter_by_confidence(
        self,
        results: list[SentimentResult],
    ) -> list[SentimentResult]:
        """Filter results by confidence threshold."""
        return [
            r for r in results
            if r.ensemble_confidence >= self.confidence_threshold
        ]

    def _calculate_weighted_sentiment(
        self,
        results: list[SentimentResult],
        weight_fn: Callable[[SentimentResult], float],
    ) -> tuple[float, float]:
        """
        Calculate weighted sentiment score and confidence.

        Args:
            results: Sentiment results
            weight_fn: Function to calculate weight for each result

        Returns:
            Tuple of (score, confidence)
        """
        if not results:
            return 0.0, 0.0

        total_weight = 0.0
        weighted_score = 0.0
        weighted_confidence = 0.0

        for result in results:
            weight = weight_fn(result)
            total_weight += weight
            weighted_score += result.ensemble_score * weight
            weighted_confidence += result.ensemble_confidence * weight

        if total_weight == 0:
            return 0.0, 0.0

        final_score = weighted_score / total_weight
        final_confidence = weighted_confidence / total_weight

        # Adjust confidence based on article count
        count_factor = min(len(results) / self.min_articles, 1.0)
        final_confidence *= count_factor

        return final_score, final_confidence

    def _news_weight(self, result: SentimentResult) -> float:
        """
        Calculate weight for a news article.

        Combines time decay and relevance.
        """
        # Time decay
        age_hours = result.article.age_hours()
        time_weight = math.exp(-0.693 * age_hours / self.decay_hours)

        # Relevance weight
        relevance_weight = result.article.relevance_score

        # Confidence weight
        confidence_weight = result.ensemble_confidence

        return time_weight * relevance_weight * confidence_weight

    def _social_weight_fn(self, result: SentimentResult) -> float:
        """
        Calculate weight for social media content.

        Social content decays faster than news.
        """
        # Faster decay for social content
        age_hours = result.article.age_hours()
        social_decay_hours = self.decay_hours / 2  # Half the decay time
        time_weight = math.exp(-0.693 * age_hours / social_decay_hours)

        # Lower base weight for social
        base_weight = 0.7

        # Confidence weight
        confidence_weight = result.ensemble_confidence

        return time_weight * base_weight * confidence_weight

    def _combine_news_social(
        self,
        news_score: float,
        news_confidence: float,
        social_score: float,
        social_confidence: float,
    ) -> tuple[float, float]:
        """
        Combine news and social sentiment.

        Uses configured social weight when both are available.
        """
        if news_confidence == 0 and social_confidence == 0:
            return 0.0, 0.0

        if news_confidence == 0:
            return social_score, social_confidence * 0.8  # Lower confidence for social-only

        if social_confidence == 0:
            return news_score, news_confidence

        # Combine with configured weights
        news_weight = 1.0 - self.social_weight
        social_weight = self.social_weight

        # Adjust weights by confidence
        total_confidence = news_confidence + social_confidence
        adjusted_news_weight = news_weight * (news_confidence / total_confidence)
        adjusted_social_weight = social_weight * (social_confidence / total_confidence)

        total_weight = adjusted_news_weight + adjusted_social_weight
        if total_weight == 0:
            return 0.0, 0.0

        combined_score = (
            news_score * adjusted_news_weight +
            social_score * adjusted_social_weight
        ) / total_weight

        # Combined confidence is weighted average
        combined_confidence = (
            news_confidence * news_weight +
            social_confidence * social_weight
        )

        return combined_score, combined_confidence

    def _get_top_headlines(
        self,
        results: list[SentimentResult],
        positive: bool,
        limit: int,
    ) -> list[str]:
        """Get top headlines by sentiment direction."""
        if positive:
            sorted_results = sorted(
                results,
                key=lambda r: r.ensemble_score,
                reverse=True,
            )
        else:
            sorted_results = sorted(
                results,
                key=lambda r: r.ensemble_score,
            )

        headlines = []
        for result in sorted_results[:limit]:
            score = result.ensemble_score
            if positive and score > 0.1:
                headlines.append(result.article.headline)
            elif not positive and score < -0.1:
                headlines.append(result.article.headline)

        return headlines


def calculate_sentiment_impact(
    sentiment: AggregatedSentiment,
    impact_multiplier: float = 1.0,
) -> float:
    """
    Calculate the trading impact of sentiment.

    Maps sentiment score to a trading signal adjustment.

    Args:
        sentiment: Aggregated sentiment data
        impact_multiplier: Scale factor for impact

    Returns:
        Impact value between -1 and 1
    """
    if not sentiment.is_reliable:
        # Low confidence = low impact
        return sentiment.combined_score * 0.3 * impact_multiplier

    # Scale by confidence
    impact = sentiment.combined_score * sentiment.combined_confidence * impact_multiplier

    # Clamp to valid range
    return max(-1.0, min(1.0, impact))
