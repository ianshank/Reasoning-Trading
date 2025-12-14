"""
FinBERT sentiment analyzer implementation.

Uses the ProsusAI/finbert model for financial sentiment analysis.
This is a BERT-based model fine-tuned on financial text.
"""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

import structlog

from reasoning_trading.config import Settings, get_settings
from reasoning_trading.sentiment.analyzers.base import (
    AnalyzerError,
    BaseSentimentAnalyzer,
)
from reasoning_trading.sentiment.models import SentimentLabel, SentimentScore

if TYPE_CHECKING:
    from transformers import Pipeline


@runtime_checkable
class TransformerPipeline(Protocol):
    """Protocol for transformer pipeline objects."""

    def __call__(self, text: str | list[str]) -> list[dict[str, Any]]:
        """Run the pipeline on text."""
        ...


logger = structlog.get_logger(__name__)


class FinBERTAnalyzer(BaseSentimentAnalyzer):
    """
    FinBERT-based sentiment analyzer.

    Uses the transformers library with ProsusAI/finbert model.
    Falls back gracefully if transformers is not installed.
    """

    # Default model - can be overridden in settings
    DEFAULT_MODEL = "ProsusAI/finbert"
    MAX_TEXT_LENGTH = 512  # BERT's max sequence length

    def __init__(
        self,
        settings: Settings | None = None,
        model_name: str | None = None,
    ):
        """
        Initialize FinBERT analyzer.

        Args:
            settings: Application settings
            model_name: Override model name
        """
        self._settings = settings or get_settings()
        self._model_name = model_name or self.DEFAULT_MODEL
        self._pipeline: TransformerPipeline | None = None
        self._available: bool | None = None

    @property
    def name(self) -> str:
        """Get analyzer name."""
        return "FinBERT"

    @property
    def model_name(self) -> str:
        """Get the underlying model name."""
        return self._model_name

    def is_available(self) -> bool:
        """Check if transformers and the model are available."""
        if self._available is not None:
            return self._available

        try:
            from transformers import pipeline

            # Just check if we can import - don't load model yet
            self._available = True
            logger.debug("FinBERT analyzer available")
        except ImportError:
            self._available = False
            logger.warning(
                "FinBERT analyzer not available - transformers not installed"
            )

        return self._available

    def _get_pipeline(self) -> TransformerPipeline:
        """Get or create the sentiment pipeline."""
        if self._pipeline is None:
            if not self.is_available():
                raise AnalyzerError(
                    message="FinBERT not available - install transformers",
                    analyzer=self.name,
                    retriable=False,
                )

            try:
                from transformers import pipeline

                logger.info("Loading FinBERT model", model=self._model_name)
                self._pipeline = pipeline(
                    "sentiment-analysis",
                    model=self._model_name,
                    tokenizer=self._model_name,
                    device=-1,  # CPU; use 0 for GPU
                )
                logger.info("FinBERT model loaded successfully")
            except Exception as e:
                raise AnalyzerError(
                    message=f"Failed to load FinBERT model: {str(e)}",
                    analyzer=self.name,
                    retriable=False,
                    original_error=e,
                )

        return self._pipeline

    async def analyze(self, text: str) -> SentimentScore:
        """
        Analyze sentiment using FinBERT.

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
            # Truncate text to model's max length
            truncated = self._truncate_text(text, self.MAX_TEXT_LENGTH)

            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._analyze_sync,
                truncated,
            )

            processing_time = (time.perf_counter() - start_time) * 1000
            result.processing_time_ms = processing_time

            logger.debug(
                "FinBERT analysis complete",
                score=result.score,
                label=result.label,
                processing_time_ms=processing_time,
            )

            return result

        except AnalyzerError:
            raise
        except Exception as e:
            raise AnalyzerError(
                message=f"FinBERT analysis failed: {str(e)}",
                analyzer=self.name,
                retriable=True,
                original_error=e,
            )

    def _map_result_to_score(self, result: dict[str, Any]) -> SentimentScore:
        """
        Map a single pipeline result to a SentimentScore.

        Extracted to avoid code duplication between sync and batch methods.
        """
        label = result["label"].lower()
        score_value = result["score"]

        # Get probability factors from settings
        secondary_factor = self._settings.sentiment.secondary_probability_factor
        neutral_factor = self._settings.sentiment.neutral_probability_factor

        # Map to our probability format
        if label == "positive":
            positive = score_value
            negative = (1 - score_value) * secondary_factor
            neutral = (1 - score_value) * neutral_factor
        elif label == "negative":
            negative = score_value
            positive = (1 - score_value) * secondary_factor
            neutral = (1 - score_value) * neutral_factor
        else:  # neutral
            neutral = score_value
            # Equal split for non-dominant sentiment
            positive = (1 - score_value) * 0.5
            negative = (1 - score_value) * 0.5

        # Normalize
        total = positive + negative + neutral
        positive /= total
        negative /= total
        neutral /= total

        return SentimentScore.from_probabilities(
            positive=positive,
            negative=negative,
            neutral=neutral,
            model_name=self.model_name,
        )

    def _analyze_sync(self, text: str) -> SentimentScore:
        """Synchronous analysis for thread pool execution."""
        pipeline = self._get_pipeline()
        result = pipeline(text)[0]
        return self._map_result_to_score(result)

    async def analyze_batch(self, texts: list[str]) -> list[SentimentScore]:
        """
        Batch analyze multiple texts.

        FinBERT supports efficient batch processing.
        """
        if not texts:
            return []

        start_time = time.perf_counter()

        try:
            # Truncate all texts
            truncated = [self._truncate_text(t, self.MAX_TEXT_LENGTH) for t in texts]

            # Run batch in thread pool
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None,
                self._analyze_batch_sync,
                truncated,
            )

            processing_time = (time.perf_counter() - start_time) * 1000
            avg_time = processing_time / len(texts)

            for result in results:
                result.processing_time_ms = avg_time

            logger.debug(
                "FinBERT batch analysis complete",
                count=len(texts),
                total_time_ms=processing_time,
            )

            return results

        except AnalyzerError:
            raise
        except Exception as e:
            raise AnalyzerError(
                message=f"FinBERT batch analysis failed: {str(e)}",
                analyzer=self.name,
                retriable=True,
                original_error=e,
            )

    def _analyze_batch_sync(self, texts: list[str]) -> list[SentimentScore]:
        """Synchronous batch analysis."""
        pipeline = self._get_pipeline()
        results = pipeline(texts)
        return [self._map_result_to_score(result) for result in results]
