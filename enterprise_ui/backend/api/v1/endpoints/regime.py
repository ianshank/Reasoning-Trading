"""
Market regime detection endpoints.

This module provides REST API endpoints for:
- Current regime detection
- Regime history retrieval
- Regime probability distributions
- Regime-based strategy recommendations
"""

from datetime import datetime, timedelta
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from reasoning_trading.regime.detector import RegimeDetector, RegimeDetectorConfig

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/regime", tags=["regime"])


# Request/Response Models
class CurrentRegimeResponse(BaseModel):
    """Current regime response."""

    symbol: str
    regime: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    hmm_regime: str | None = None
    hmm_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    technical_regime: str | None = None
    technical_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    timestamp: datetime


class RegimeHistoryItem(BaseModel):
    """Single regime classification in history."""

    regime: str
    confidence: float
    timestamp: datetime


class RegimeHistoryResponse(BaseModel):
    """Regime history response."""

    symbol: str
    classifications: list[RegimeHistoryItem]
    current_regime: str
    regime_start: datetime
    regime_durations: dict[str, float]
    total_count: int
    timestamp: datetime


class RegimeProbabilitiesResponse(BaseModel):
    """Regime probability distribution."""

    symbol: str
    probabilities: dict[str, float]
    current_regime: str
    confidence: float
    timestamp: datetime


class RegimeStatisticsResponse(BaseModel):
    """Regime detection statistics."""

    current_regime: str
    regime_start: datetime
    total_classifications: int
    regime_frequency: dict[str, float]
    regime_durations: dict[str, float]
    average_confidence: float
    hmm_enabled: bool
    timestamp: datetime


# Dependency injection
async def get_regime_detector() -> RegimeDetector:
    """Get regime detector instance."""
    config = RegimeDetectorConfig()
    return RegimeDetector(config=config)


# Endpoints
@router.get(
    "/current/{symbol}",
    response_model=CurrentRegimeResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current market regime",
    description="""
    Detects and returns the current market regime for a symbol.

    This endpoint analyzes market conditions using both technical indicators
    and Hidden Markov Models (HMM) to classify the current regime.

    **Regime Types:**
    - bull: Strong upward trend
    - bear: Strong downward trend
    - neutral: Range-bound, no clear trend
    - high_volatility: High price fluctuations
    - low_volatility: Stable, low fluctuations

    **Detection Methods:**
    - Technical: ADX, volatility, moving averages, RSI
    - HMM: Statistical regime inference from returns
    - Combined: Weighted combination of both methods

    **Use Case:** Adapt trading strategy based on market conditions.

    **Returns:** Current regime with confidence scores.
    """,
)
async def get_current_regime(
    symbol: str,
    detector: RegimeDetector = Depends(get_regime_detector),
) -> CurrentRegimeResponse:
    """
    Get current market regime for a symbol.

    Args:
        symbol: Trading symbol
        detector: Regime detector

    Returns:
        CurrentRegimeResponse with current regime
    """
    logger.info("Detecting current regime", symbol=symbol)

    try:
        # TODO: Get current trading state from market data
        # For now, use mock data
        from reasoning_trading.core.state import TradingState

        state = TradingState(
            symbol=symbol,
            timestamp=datetime.now(),
            current_price=100.0,
        )

        # Detect regime
        classification = detector.detect(state)

        logger.info(
            "Regime detected",
            symbol=symbol,
            regime=classification.regime,
            confidence=classification.confidence,
        )

        return CurrentRegimeResponse(
            symbol=symbol,
            regime=classification.regime,
            confidence=classification.confidence,
            hmm_regime=classification.hmm_regime,
            hmm_confidence=classification.hmm_confidence,
            technical_regime=classification.technical_regime,
            technical_confidence=classification.technical_confidence,
            timestamp=classification.timestamp,
        )

    except Exception as e:
        logger.error("Regime detection failed", symbol=symbol, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Regime detection failed: {str(e)}",
        )


@router.get(
    "/history/{symbol}",
    response_model=RegimeHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get regime history",
    description="""
    Retrieves historical regime classifications for a symbol.

    This endpoint returns the time series of regime classifications,
    showing how the market regime has evolved over time.

    **History Components:**
    - Chronological list of regime classifications
    - Duration statistics per regime
    - Current regime and start time
    - Regime transition frequency

    **Query Parameters:**
    - limit: Maximum number of classifications to return
    - since: Filter classifications after this timestamp

    **Use Case:** Analyze regime stability and transition patterns.

    **Returns:** Historical regime classifications with statistics.
    """,
)
async def get_regime_history(
    symbol: str,
    limit: int = Query(default=100, ge=1, le=1000),
    since: datetime | None = Query(default=None),
    detector: RegimeDetector = Depends(get_regime_detector),
) -> RegimeHistoryResponse:
    """
    Get regime history for a symbol.

    Args:
        symbol: Trading symbol
        limit: Maximum number of classifications to return
        since: Filter classifications after this timestamp
        detector: Regime detector

    Returns:
        RegimeHistoryResponse with historical classifications
    """
    logger.info("Fetching regime history", symbol=symbol, limit=limit)

    try:
        history = detector.history

        # Filter by timestamp if provided
        classifications = history.classifications
        if since is not None:
            classifications = [
                c for c in classifications if c.timestamp >= since
            ]

        # Apply limit
        classifications = classifications[-limit:]

        # Build history items
        history_items = [
            RegimeHistoryItem(
                regime=c.regime,
                confidence=c.confidence,
                timestamp=c.timestamp,
            )
            for c in classifications
        ]

        logger.info(
            "Regime history retrieved",
            symbol=symbol,
            count=len(history_items),
        )

        return RegimeHistoryResponse(
            symbol=symbol,
            classifications=history_items,
            current_regime=history.current_regime,
            regime_start=history.current_regime_start,
            regime_durations=history.regime_durations,
            total_count=len(classifications),
            timestamp=datetime.now(),
        )

    except Exception as e:
        logger.error("Failed to fetch regime history", symbol=symbol, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch regime history: {str(e)}",
        )


@router.get(
    "/probabilities/{symbol}",
    response_model=RegimeProbabilitiesResponse,
    status_code=status.HTTP_200_OK,
    summary="Get regime probabilities",
    description="""
    Returns probability distribution over all possible regimes.

    This endpoint provides the detector's confidence distribution across
    all regime types, useful for understanding uncertainty and alternative
    regime interpretations.

    **Probability Distribution:**
    - Probability for each regime type (sum to 1.0)
    - Current most-likely regime
    - Overall confidence measure

    **Use Case:**
    - Assess regime detection uncertainty
    - Consider alternative regime scenarios
    - Risk management based on regime ambiguity

    **Returns:** Probability distribution over regimes.
    """,
)
async def get_regime_probabilities(
    symbol: str,
    detector: RegimeDetector = Depends(get_regime_detector),
) -> RegimeProbabilitiesResponse:
    """
    Get regime probability distribution.

    Args:
        symbol: Trading symbol
        detector: Regime detector

    Returns:
        RegimeProbabilitiesResponse with probabilities
    """
    logger.info("Fetching regime probabilities", symbol=symbol)

    try:
        # Get current regime and probabilities
        current_regime, confidence = detector.get_current_regime()
        probabilities = detector.get_regime_probabilities()

        logger.info(
            "Regime probabilities retrieved",
            symbol=symbol,
            regime=current_regime,
        )

        return RegimeProbabilitiesResponse(
            symbol=symbol,
            probabilities=probabilities,
            current_regime=current_regime,
            confidence=confidence,
            timestamp=datetime.now(),
        )

    except Exception as e:
        logger.error("Failed to fetch probabilities", symbol=symbol, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch probabilities: {str(e)}",
        )


@router.get(
    "/statistics",
    response_model=RegimeStatisticsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get regime detection statistics",
    description="""
    Returns comprehensive statistics about regime detection.

    This endpoint provides aggregate statistics about the regime detector's
    operation including classification counts, regime frequencies, average
    durations, and confidence metrics.

    **Statistics:**
    - Total classifications performed
    - Frequency of each regime type
    - Average duration per regime
    - Average confidence scores
    - Detection method (HMM enabled/disabled)

    **Use Case:** Monitor detector performance and regime patterns.

    **Returns:** Comprehensive detector statistics.
    """,
)
async def get_regime_statistics(
    detector: RegimeDetector = Depends(get_regime_detector),
) -> RegimeStatisticsResponse:
    """
    Get regime detection statistics.

    Args:
        detector: Regime detector

    Returns:
        RegimeStatisticsResponse with statistics
    """
    logger.info("Fetching regime statistics")

    try:
        stats = detector.get_statistics()

        # Calculate average confidence
        classifications = detector.history.classifications
        avg_confidence = (
            sum(c.confidence for c in classifications) / len(classifications)
            if classifications
            else 0.0
        )

        return RegimeStatisticsResponse(
            current_regime=stats["current_regime"],
            regime_start=datetime.fromisoformat(stats["regime_start"]),
            total_classifications=stats["total_classifications"],
            regime_frequency=stats["regime_frequency"],
            regime_durations=stats["regime_durations"],
            average_confidence=avg_confidence,
            hmm_enabled=stats["hmm_enabled"],
            timestamp=datetime.now(),
        )

    except Exception as e:
        logger.error("Failed to fetch statistics", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch statistics: {str(e)}",
        )
