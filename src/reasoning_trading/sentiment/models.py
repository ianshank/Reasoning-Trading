"""
Data models for sentiment analysis.

Defines the core data structures used throughout the sentiment
analysis pipeline, from raw news articles to aggregated scores.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

# Mathematical constant for exponential decay (ln(2))
LN_2 = math.log(2)

# Default thresholds for sentiment labeling
# These can be overridden by settings in analyzer classes
DEFAULT_BULLISH_THRESHOLD = 0.1
DEFAULT_BEARISH_THRESHOLD = -0.1

# Default reliability thresholds
DEFAULT_CONFIDENCE_THRESHOLD = 0.5
DEFAULT_MIN_ARTICLES_FOR_RELIABILITY = 3


class SentimentLabel(str, Enum):
    """Sentiment classification labels."""

    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class NewsSource(str, Enum):
    """News source types for tracking provenance."""

    FINNHUB = "finnhub"
    NEWSAPI = "newsapi"
    ALPACA = "alpaca"
    RSS = "rss"
    SOCIAL = "social"


class NewsArticle(BaseModel):
    """
    Represents a single news article.

    Captures all relevant metadata for sentiment analysis
    including source, timing, and relevance metrics.
    """

    id: str = Field(description="Unique identifier for the article")
    headline: str = Field(description="Article headline/title")
    summary: str = Field(default="", description="Article summary or snippet")
    content: str = Field(default="", description="Full article content if available")
    source: NewsSource = Field(description="News source provider")
    source_name: str = Field(default="", description="Original publication name")
    url: str = Field(default="", description="URL to the original article")
    published_at: datetime = Field(description="Publication timestamp")
    symbols: list[str] = Field(default_factory=list, description="Related trading symbols")
    category: str = Field(default="", description="News category")
    image_url: str = Field(default="", description="Article image URL")

    # Relevance metrics (populated by providers)
    relevance_score: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Relevance score to the target symbol",
    )

    # Metadata
    raw_data: dict[str, Any] = Field(
        default_factory=dict,
        description="Raw data from the provider",
    )

    def get_text_for_analysis(self) -> str:
        """Get the best available text for sentiment analysis."""
        if self.content:
            return f"{self.headline}. {self.content}"
        if self.summary:
            return f"{self.headline}. {self.summary}"
        return self.headline

    def age_hours(self) -> float:
        """Calculate the age of the article in hours."""
        delta = datetime.now() - self.published_at
        return delta.total_seconds() / 3600.0


class SentimentScore(BaseModel):
    """
    Sentiment score from a single analyzer.

    Captures the raw sentiment output from one model,
    with confidence and supporting metadata.
    """

    score: float = Field(
        ge=-1.0,
        le=1.0,
        description="Sentiment score (-1 bearish to +1 bullish)",
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence in the score",
    )
    label: SentimentLabel = Field(description="Categorical sentiment label")
    model_name: str = Field(description="Name of the model that produced this score")

    # Probability distribution (if available)
    probabilities: dict[str, float] = Field(
        default_factory=dict,
        description="Class probabilities (positive, negative, neutral)",
    )

    # Processing metadata
    processing_time_ms: float = Field(
        default=0.0,
        ge=0.0,
        description="Time taken to process in milliseconds",
    )

    @classmethod
    def from_probabilities(
        cls,
        positive: float,
        negative: float,
        neutral: float,
        model_name: str,
        bullish_threshold: float = DEFAULT_BULLISH_THRESHOLD,
        bearish_threshold: float = DEFAULT_BEARISH_THRESHOLD,
    ) -> SentimentScore:
        """Create score from probability distribution."""
        # Calculate score as weighted combination
        score = positive - negative

        # Determine label using configurable thresholds
        if score > bullish_threshold:
            label = SentimentLabel.BULLISH
        elif score < bearish_threshold:
            label = SentimentLabel.BEARISH
        else:
            label = SentimentLabel.NEUTRAL

        # Confidence is max probability
        confidence = max(positive, negative, neutral)

        return cls(
            score=score,
            confidence=confidence,
            label=label,
            model_name=model_name,
            probabilities={
                "positive": positive,
                "negative": negative,
                "neutral": neutral,
            },
        )


class SentimentResult(BaseModel):
    """
    Sentiment analysis result for a single article.

    Combines article with sentiment scores from one or more models.
    """

    article: NewsArticle = Field(description="The analyzed article")
    scores: list[SentimentScore] = Field(
        default_factory=list,
        description="Sentiment scores from different models",
    )
    ensemble_score: float = Field(
        default=0.0,
        ge=-1.0,
        le=1.0,
        description="Combined ensemble score",
    )
    ensemble_confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence in ensemble score",
    )
    analyzed_at: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp of analysis",
    )

    def get_time_weighted_score(self, decay_hours: float) -> float:
        """
        Get time-weighted sentiment score.

        Args:
            decay_hours: Half-life for exponential decay in hours

        Returns:
            Score weighted by time decay
        """
        age = self.article.age_hours()
        decay_factor = math.exp(-LN_2 * age / decay_hours)
        return self.ensemble_score * decay_factor

    def get_time_weighted_confidence(self, decay_hours: float) -> float:
        """Get time-weighted confidence."""
        age = self.article.age_hours()
        decay_factor = math.exp(-LN_2 * age / decay_hours)
        return self.ensemble_confidence * decay_factor


class AggregatedSentiment(BaseModel):
    """
    Aggregated sentiment for a trading symbol.

    Combines sentiment from multiple articles with time-decay
    weighting and confidence aggregation.
    """

    symbol: str = Field(description="Trading symbol")
    news_score: float = Field(
        default=0.0,
        ge=-1.0,
        le=1.0,
        description="Aggregated news sentiment score",
    )
    news_confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence in news score",
    )
    social_score: float = Field(
        default=0.0,
        ge=-1.0,
        le=1.0,
        description="Social media sentiment score",
    )
    social_confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence in social score",
    )
    combined_score: float = Field(
        default=0.0,
        ge=-1.0,
        le=1.0,
        description="Combined overall sentiment score",
    )
    combined_confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence in combined score",
    )

    # Statistics
    article_count: int = Field(default=0, ge=0, description="Number of articles analyzed")
    positive_count: int = Field(default=0, ge=0, description="Number of bullish articles")
    negative_count: int = Field(default=0, ge=0, description="Number of bearish articles")
    neutral_count: int = Field(default=0, ge=0, description="Number of neutral articles")

    # Time range
    oldest_article: datetime | None = Field(
        default=None,
        description="Timestamp of oldest article",
    )
    newest_article: datetime | None = Field(
        default=None,
        description="Timestamp of newest article",
    )

    # Analysis metadata
    analyzed_at: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp of aggregation",
    )
    providers_used: list[str] = Field(
        default_factory=list,
        description="News providers that contributed",
    )
    models_used: list[str] = Field(
        default_factory=list,
        description="Sentiment models that contributed",
    )

    # Evidence for debugging/transparency
    top_bullish_headlines: list[str] = Field(
        default_factory=list,
        description="Most bullish headlines",
    )
    top_bearish_headlines: list[str] = Field(
        default_factory=list,
        description="Most bearish headlines",
    )

    @property
    def sentiment_label(self) -> SentimentLabel:
        """Get categorical label for combined score."""
        if self.combined_score > DEFAULT_BULLISH_THRESHOLD:
            return SentimentLabel.BULLISH
        elif self.combined_score < DEFAULT_BEARISH_THRESHOLD:
            return SentimentLabel.BEARISH
        return SentimentLabel.NEUTRAL

    @property
    def is_reliable(self) -> bool:
        """Check if sentiment signal is reliable based on confidence and article count."""
        return (
            self.combined_confidence >= DEFAULT_CONFIDENCE_THRESHOLD
            and self.article_count >= DEFAULT_MIN_ARTICLES_FOR_RELIABILITY
        )

    def to_analyst_signals(self) -> dict[str, float]:
        """Convert to format expected by AnalystSignals."""
        return {
            "news_analyst_score": self.news_score,
            "news_analyst_confidence": self.news_confidence,
            "social_sentiment_score": self.social_score,
            "social_sentiment_confidence": self.social_confidence,
        }


@dataclass
class SentimentCache:
    """Cache entry for sentiment data."""

    sentiment: AggregatedSentiment
    cached_at: datetime = field(default_factory=datetime.now)
    ttl_minutes: int = 15

    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        from datetime import timedelta

        return datetime.now() - self.cached_at > timedelta(minutes=self.ttl_minutes)
