"""
Factory for creating sentiment analyzers.

Creates and configures analyzers based on application settings.
"""

from __future__ import annotations

import structlog

from reasoning_trading.config import SentimentModelType, Settings, get_settings
from reasoning_trading.sentiment.analyzers.base import SentimentAnalyzer
from reasoning_trading.sentiment.analyzers.finbert import FinBERTAnalyzer
from reasoning_trading.sentiment.analyzers.vader import VADERAnalyzer
from reasoning_trading.sentiment.analyzers.llm import LLMSentimentAnalyzer
from reasoning_trading.sentiment.analyzers.ensemble import EnsembleAnalyzer

logger = structlog.get_logger(__name__)


def create_sentiment_analyzer(
    settings: Settings | None = None,
    model_type: SentimentModelType | None = None,
) -> SentimentAnalyzer:
    """
    Create a sentiment analyzer based on settings.

    Args:
        settings: Application settings
        model_type: Override model type

    Returns:
        Configured sentiment analyzer
    """
    settings = settings or get_settings()
    requested_type = model_type or settings.sentiment.primary_model

    # If ensemble is requested or configured
    if requested_type == SentimentModelType.ENSEMBLE or settings.sentiment.use_ensemble:
        return _create_ensemble(settings)

    # Create single analyzer
    analyzer = _create_single_analyzer(requested_type, settings)

    if analyzer is not None and analyzer.is_available():
        logger.info(
            "Created sentiment analyzer",
            type=requested_type.value,
            model=analyzer.model_name,
        )
        return analyzer

    # Fall back to fallback model
    fallback_type = settings.sentiment.fallback_model
    logger.info(
        "Primary analyzer not available, using fallback",
        primary=requested_type.value,
        fallback=fallback_type.value,
    )

    analyzer = _create_single_analyzer(fallback_type, settings)
    if analyzer is not None and analyzer.is_available():
        return analyzer

    # Last resort: VADER (usually always available)
    logger.warning("Using VADER as last resort analyzer")
    return VADERAnalyzer(settings=settings)


def _create_single_analyzer(
    model_type: SentimentModelType,
    settings: Settings,
) -> SentimentAnalyzer | None:
    """Create a single analyzer by type."""
    if model_type == SentimentModelType.FINBERT:
        return FinBERTAnalyzer(settings=settings)
    elif model_type == SentimentModelType.VADER:
        return VADERAnalyzer(settings=settings)
    elif model_type == SentimentModelType.LLM:
        return LLMSentimentAnalyzer(settings=settings)
    else:
        logger.warning(f"Unknown model type: {model_type}")
        return None


def _create_ensemble(settings: Settings) -> EnsembleAnalyzer:
    """Create an ensemble analyzer with all available models."""
    ensemble = EnsembleAnalyzer(
        settings=settings,
        weights=settings.sentiment.ensemble_weights,
    )

    # Add analyzers in order of preference
    analyzers_to_try = [
        FinBERTAnalyzer(settings=settings),
        VADERAnalyzer(settings=settings),
        LLMSentimentAnalyzer(settings=settings),
    ]

    for analyzer in analyzers_to_try:
        if analyzer.is_available():
            ensemble.add_analyzer(analyzer)
            logger.debug(
                "Added analyzer to ensemble",
                analyzer=analyzer.name,
            )

    if not ensemble.is_available():
        logger.warning("No analyzers available for ensemble, using VADER only")
        ensemble.add_analyzer(VADERAnalyzer(settings=settings))

    logger.info(
        "Created ensemble analyzer",
        model=ensemble.model_name,
    )

    return ensemble


def get_available_analyzers(settings: Settings | None = None) -> list[str]:
    """
    Get list of available analyzer names.

    Returns:
        List of analyzer names that are available
    """
    settings = settings or get_settings()
    available = []

    # Check each analyzer type
    if FinBERTAnalyzer(settings=settings).is_available():
        available.append("finbert")

    if VADERAnalyzer(settings=settings).is_available():
        available.append("vader")

    if LLMSentimentAnalyzer(settings=settings).is_available():
        available.append("llm")

    return available
