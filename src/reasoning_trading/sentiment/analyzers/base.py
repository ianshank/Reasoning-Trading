"""
Base interface for sentiment analyzers.

Defines the protocol that all sentiment analyzers must implement.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Protocol, runtime_checkable

import structlog

from reasoning_trading.sentiment.models import NewsArticle, SentimentScore

logger = structlog.get_logger(__name__)


class AnalyzerError(Exception):
    """Exception raised by sentiment analyzers."""

    def __init__(
        self,
        message: str,
        analyzer: str,
        retriable: bool = True,
        original_error: Exception | None = None,
    ):
        super().__init__(message)
        self.analyzer = analyzer
        self.retriable = retriable
        self.original_error = original_error


@runtime_checkable
class SentimentAnalyzer(Protocol):
    """
    Protocol for sentiment analyzers.

    All analyzers must implement this interface.
    """

    @property
    def name(self) -> str:
        """Get analyzer name."""
        ...

    @property
    def model_name(self) -> str:
        """Get the underlying model name."""
        ...

    async def analyze(self, text: str) -> SentimentScore:
        """
        Analyze sentiment of text.

        Args:
            text: Text to analyze

        Returns:
            SentimentScore with results

        Raises:
            AnalyzerError: If analysis fails
        """
        ...

    async def analyze_batch(self, texts: list[str]) -> list[SentimentScore]:
        """
        Analyze sentiment of multiple texts.

        Args:
            texts: List of texts to analyze

        Returns:
            List of SentimentScore objects
        """
        ...

    async def analyze_article(self, article: NewsArticle) -> SentimentScore:
        """
        Analyze sentiment of a news article.

        Args:
            article: News article to analyze

        Returns:
            SentimentScore with results
        """
        ...

    def is_available(self) -> bool:
        """Check if the analyzer is available."""
        ...


class BaseSentimentAnalyzer(ABC):
    """
    Abstract base class for sentiment analyzers.

    Provides common functionality and enforces the SentimentAnalyzer protocol.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Get analyzer name."""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Get the underlying model name."""
        ...

    @abstractmethod
    async def analyze(self, text: str) -> SentimentScore:
        """Analyze sentiment of text."""
        ...

    async def analyze_batch(self, texts: list[str]) -> list[SentimentScore]:
        """
        Analyze sentiment of multiple texts.

        Default implementation processes sequentially.
        Subclasses can override for batch optimization.
        """
        results = []
        for text in texts:
            try:
                score = await self.analyze(text)
                results.append(score)
            except Exception as e:
                logger.warning(
                    "Failed to analyze text in batch",
                    analyzer=self.name,
                    error=str(e),
                )
                # Return neutral score on failure
                results.append(
                    SentimentScore.from_probabilities(
                        positive=0.33,
                        negative=0.33,
                        neutral=0.34,
                        model_name=self.model_name,
                    )
                )
        return results

    async def analyze_article(self, article: NewsArticle) -> SentimentScore:
        """
        Analyze sentiment of a news article.

        Uses the best available text from the article.
        """
        text = article.get_text_for_analysis()
        return await self.analyze(text)

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the analyzer is available."""
        ...

    def _truncate_text(self, text: str, max_length: int) -> str:
        """
        Truncate text to maximum length.

        Attempts to truncate at sentence boundaries.
        """
        if len(text) <= max_length:
            return text

        # Try to truncate at sentence boundary
        truncated = text[:max_length]
        last_period = truncated.rfind(".")
        last_question = truncated.rfind("?")
        last_exclaim = truncated.rfind("!")

        best_boundary = max(last_period, last_question, last_exclaim)

        if best_boundary > max_length * 0.5:
            return truncated[: best_boundary + 1]

        return truncated
