"""
VADER sentiment analyzer implementation.

Uses NLTK's VADER (Valence Aware Dictionary and sEntiment Reasoner)
for rule-based sentiment analysis. Fast and effective for social
media and news text.
"""

from __future__ import annotations

import time
from typing import Any

import structlog

from reasoning_trading.config import Settings, get_settings
from reasoning_trading.sentiment.analyzers.base import (
    AnalyzerError,
    BaseSentimentAnalyzer,
)
from reasoning_trading.sentiment.models import SentimentLabel, SentimentScore

logger = structlog.get_logger(__name__)


class VADERAnalyzer(BaseSentimentAnalyzer):
    """
    VADER-based sentiment analyzer.

    Uses NLTK's VADER sentiment analyzer, which is specifically
    tuned for social media and news text. Very fast and doesn't
    require a GPU.
    """

    def __init__(self, settings: Settings | None = None):
        """
        Initialize VADER analyzer.

        Args:
            settings: Application settings
        """
        self._settings = settings or get_settings()
        self._analyzer: Any = None
        self._available: bool | None = None

    @property
    def name(self) -> str:
        """Get analyzer name."""
        return "VADER"

    @property
    def model_name(self) -> str:
        """Get the underlying model name."""
        return "nltk_vader"

    def is_available(self) -> bool:
        """Check if NLTK VADER is available."""
        if self._available is not None:
            return self._available

        try:
            from nltk.sentiment.vader import SentimentIntensityAnalyzer
            import nltk

            # Try to get the VADER lexicon
            try:
                nltk.data.find("sentiment/vader_lexicon.zip")
            except LookupError:
                logger.info("Downloading VADER lexicon")
                nltk.download("vader_lexicon", quiet=True)

            self._available = True
            logger.debug("VADER analyzer available")

        except ImportError:
            self._available = False
            logger.warning("VADER analyzer not available - nltk not installed")

        return self._available

    def _get_analyzer(self) -> Any:
        """Get or create the VADER analyzer."""
        if self._analyzer is None:
            if not self.is_available():
                raise AnalyzerError(
                    message="VADER not available - install nltk",
                    analyzer=self.name,
                    retriable=False,
                )

            from nltk.sentiment.vader import SentimentIntensityAnalyzer

            self._analyzer = SentimentIntensityAnalyzer()
            logger.debug("VADER analyzer initialized")

        return self._analyzer

    async def analyze(self, text: str) -> SentimentScore:
        """
        Analyze sentiment using VADER.

        Args:
            text: Text to analyze

        Returns:
            SentimentScore with results
        """
        if not text.strip():
            return SentimentScore.from_probabilities(
                positive=0.0,
                negative=0.0,
                neutral=1.0,
                model_name=self.model_name,
            )

        start_time = time.perf_counter()

        try:
            analyzer = self._get_analyzer()

            # VADER is fast, no need for thread pool
            scores = analyzer.polarity_scores(text)

            # VADER returns: pos, neg, neu, compound
            # compound is the normalized sum (-1 to 1)
            positive = scores["pos"]
            negative = scores["neg"]
            neutral = scores["neu"]
            compound = scores["compound"]

            # Determine label from compound score
            if compound >= 0.05:
                label = SentimentLabel.BULLISH
            elif compound <= -0.05:
                label = SentimentLabel.BEARISH
            else:
                label = SentimentLabel.NEUTRAL

            # Calculate confidence from extremity of compound
            confidence = min(abs(compound) + 0.5, 1.0)

            processing_time = (time.perf_counter() - start_time) * 1000

            result = SentimentScore(
                score=compound,
                confidence=confidence,
                label=label,
                model_name=self.model_name,
                probabilities={
                    "positive": positive,
                    "negative": negative,
                    "neutral": neutral,
                    "compound": compound,
                },
                processing_time_ms=processing_time,
            )

            logger.debug(
                "VADER analysis complete",
                score=result.score,
                label=result.label,
                processing_time_ms=processing_time,
            )

            return result

        except AnalyzerError:
            raise
        except Exception as e:
            raise AnalyzerError(
                message=f"VADER analysis failed: {str(e)}",
                analyzer=self.name,
                retriable=True,
                original_error=e,
            )

    async def analyze_batch(self, texts: list[str]) -> list[SentimentScore]:
        """
        Batch analyze multiple texts.

        VADER is very fast, so we just loop.
        """
        results = []
        for text in texts:
            result = await self.analyze(text)
            results.append(result)
        return results
