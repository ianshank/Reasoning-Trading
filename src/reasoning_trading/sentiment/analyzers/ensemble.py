"""
Ensemble sentiment analyzer implementation.

Combines multiple sentiment models for more robust predictions.
"""

from __future__ import annotations

import asyncio
import time

import structlog

from reasoning_trading.config import Settings, get_settings
from reasoning_trading.sentiment.analyzers.base import (
    AnalyzerError,
    BaseSentimentAnalyzer,
    SentimentAnalyzer,
)
from reasoning_trading.sentiment.models import SentimentLabel, SentimentScore

logger = structlog.get_logger(__name__)


class EnsembleAnalyzer(BaseSentimentAnalyzer):
    """
    Ensemble sentiment analyzer.

    Combines predictions from multiple models using weighted averaging.
    Provides more robust sentiment scores than any single model.
    """

    def __init__(
        self,
        analyzers: list[SentimentAnalyzer] | None = None,
        weights: dict[str, float] | None = None,
        settings: Settings | None = None,
    ):
        """
        Initialize ensemble analyzer.

        Args:
            analyzers: List of analyzers to use (creates defaults if None)
            weights: Model name to weight mapping
            settings: Application settings
        """
        self._settings = settings or get_settings()
        self._weights = weights or self._settings.sentiment.ensemble_weights
        self._analyzers = analyzers or []

    @property
    def name(self) -> str:
        """Get analyzer name."""
        return "Ensemble"

    @property
    def model_name(self) -> str:
        """Get the underlying model name."""
        names = [a.model_name for a in self._analyzers if a.is_available()]
        return f"ensemble({','.join(names)})"

    def add_analyzer(self, analyzer: SentimentAnalyzer) -> None:
        """Add an analyzer to the ensemble."""
        self._analyzers.append(analyzer)

    def _create_neutral_fallback(self) -> SentimentScore:
        """Create a neutral fallback score when analysis fails."""
        return SentimentScore.from_probabilities(
            positive=self._settings.sentiment.neutral_fallback_positive,
            negative=self._settings.sentiment.neutral_fallback_negative,
            neutral=self._settings.sentiment.neutral_fallback_neutral,
            model_name=self.model_name,
        )

    def set_weight(self, model_name: str, weight: float) -> None:
        """Set weight for a specific model."""
        self._weights[model_name] = weight

    def is_available(self) -> bool:
        """Check if at least one analyzer is available."""
        return any(a.is_available() for a in self._analyzers)

    def _get_weight(self, model_name: str) -> float:
        """Get weight for a model, with fallback to equal weighting."""
        # Try exact match
        if model_name in self._weights:
            return self._weights[model_name]

        # Try partial match (e.g., "finbert" matches "ProsusAI/finbert")
        model_lower = model_name.lower()
        for key, weight in self._weights.items():
            if key.lower() in model_lower or model_lower in key.lower():
                return weight

        # Default equal weight
        return 1.0

    async def analyze(self, text: str) -> SentimentScore:
        """
        Analyze sentiment using ensemble of models.

        Args:
            text: Text to analyze

        Returns:
            Combined SentimentScore
        """
        if not text.strip():
            return SentimentScore.from_probabilities(
                positive=0.0,
                negative=0.0,
                neutral=1.0,
                model_name=self.model_name,
            )

        start_time = time.perf_counter()

        # Get available analyzers
        available = [a for a in self._analyzers if a.is_available()]

        if not available:
            raise AnalyzerError(
                message="No analyzers available in ensemble",
                analyzer=self.name,
                retriable=False,
            )

        # Run all analyzers in parallel
        results = await asyncio.gather(
            *[self._safe_analyze(a, text) for a in available],
            return_exceptions=False,
        )

        # Filter out None results (failed analyzers)
        valid_results = [
            (available[i], results[i])
            for i in range(len(results))
            if results[i] is not None
        ]

        if not valid_results:
            raise AnalyzerError(
                message="All ensemble analyzers failed",
                analyzer=self.name,
                retriable=True,
            )

        # Combine results with weighted averaging
        combined = self._combine_results(valid_results)

        processing_time = (time.perf_counter() - start_time) * 1000
        combined.processing_time_ms = processing_time

        logger.debug(
            "Ensemble analysis complete",
            analyzers_used=len(valid_results),
            score=combined.score,
            label=combined.label,
            processing_time_ms=processing_time,
        )

        return combined

    async def _safe_analyze(
        self,
        analyzer: SentimentAnalyzer,
        text: str,
    ) -> SentimentScore | None:
        """Safely analyze text, returning None on failure."""
        try:
            return await analyzer.analyze(text)
        except Exception as e:
            logger.warning(
                "Analyzer failed in ensemble",
                analyzer=analyzer.name,
                error=str(e),
            )
            return None

    def _combine_results(
        self,
        results: list[tuple[SentimentAnalyzer, SentimentScore]],
    ) -> SentimentScore:
        """Combine multiple results with weighted averaging."""
        total_weight = 0.0
        weighted_score = 0.0
        weighted_confidence = 0.0
        weighted_positive = 0.0
        weighted_negative = 0.0
        weighted_neutral = 0.0

        for analyzer, score in results:
            weight = self._get_weight(analyzer.model_name)

            # Weight by both configured weight and model confidence
            effective_weight = weight * score.confidence
            total_weight += effective_weight

            weighted_score += score.score * effective_weight
            weighted_confidence += score.confidence * weight

            probs = score.probabilities
            # Use settings for fallback probabilities
            fallback_pos = self._settings.sentiment.neutral_fallback_positive
            fallback_neg = self._settings.sentiment.neutral_fallback_negative
            fallback_neu = self._settings.sentiment.neutral_fallback_neutral
            weighted_positive += probs.get("positive", fallback_pos) * effective_weight
            weighted_negative += probs.get("negative", fallback_neg) * effective_weight
            weighted_neutral += probs.get("neutral", fallback_neu) * effective_weight

        if total_weight == 0:
            total_weight = 1.0

        # Normalize
        final_score = weighted_score / total_weight
        total_raw_weight = sum(self._get_weight(a.model_name) for a, _ in results)
        final_confidence = weighted_confidence / total_raw_weight if total_raw_weight > 0 else 0.5

        final_positive = weighted_positive / total_weight
        final_negative = weighted_negative / total_weight
        final_neutral = weighted_neutral / total_weight

        # Normalize probabilities
        prob_total = final_positive + final_negative + final_neutral
        if prob_total > 0:
            final_positive /= prob_total
            final_negative /= prob_total
            final_neutral /= prob_total

        # Determine label using configurable thresholds
        bullish_threshold = self._settings.sentiment.bullish_threshold
        bearish_threshold = self._settings.sentiment.bearish_threshold
        if final_score > bullish_threshold:
            label = SentimentLabel.BULLISH
        elif final_score < bearish_threshold:
            label = SentimentLabel.BEARISH
        else:
            label = SentimentLabel.NEUTRAL

        return SentimentScore(
            score=final_score,
            confidence=final_confidence,
            label=label,
            model_name=self.model_name,
            probabilities={
                "positive": final_positive,
                "negative": final_negative,
                "neutral": final_neutral,
            },
        )

    async def analyze_batch(self, texts: list[str]) -> list[SentimentScore]:
        """
        Batch analyze using ensemble.

        Runs each analyzer's batch method in parallel.
        """
        if not texts:
            return []

        available = [a for a in self._analyzers if a.is_available()]

        if not available:
            raise AnalyzerError(
                message="No analyzers available in ensemble",
                analyzer=self.name,
                retriable=False,
            )

        # Run batch analysis for each analyzer in parallel
        all_results = await asyncio.gather(
            *[self._safe_batch_analyze(a, texts) for a in available],
            return_exceptions=False,
        )

        # Filter out None results
        valid_results = [
            (available[i], all_results[i])
            for i in range(len(all_results))
            if all_results[i] is not None
        ]

        if not valid_results:
            raise AnalyzerError(
                message="All ensemble analyzers failed in batch",
                analyzer=self.name,
                retriable=True,
            )

        # Combine results for each text
        combined_results = []
        for i in range(len(texts)):
            text_results = [
                (analyzer, scores[i])
                for analyzer, scores in valid_results
                if len(scores) > i
            ]
            if text_results:
                combined_results.append(self._combine_results(text_results))
            else:
                combined_results.append(self._create_neutral_fallback())

        return combined_results

    async def _safe_batch_analyze(
        self,
        analyzer: SentimentAnalyzer,
        texts: list[str],
    ) -> list[SentimentScore] | None:
        """Safely batch analyze, returning None on failure."""
        try:
            return await analyzer.analyze_batch(texts)
        except Exception as e:
            logger.warning(
                "Analyzer batch failed in ensemble",
                analyzer=analyzer.name,
                error=str(e),
            )
            return None
