"""
Sentiment analysis module for news and social media.

This module provides comprehensive sentiment analysis capabilities
for trading decisions, integrating multiple news providers and
sentiment analysis models.

Architecture:
- Providers: Fetch news from various sources (Finnhub, NewsAPI)
- Analyzers: Score sentiment using different models (FinBERT, VADER, LLM)
- Aggregator: Combine scores with time-decay and confidence weighting
- Service: Main interface for MCTS integration
"""

from reasoning_trading.sentiment.models import (
    NewsArticle,
    SentimentResult,
    SentimentScore,
    AggregatedSentiment,
)
from reasoning_trading.sentiment.service import SentimentService

__all__ = [
    "NewsArticle",
    "SentimentResult",
    "SentimentScore",
    "AggregatedSentiment",
    "SentimentService",
]
