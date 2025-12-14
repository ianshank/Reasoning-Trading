"""
Performance analytics endpoints.

This module provides REST API endpoints for:
- Performance metrics and statistics
- Lambda architecture layer statistics
- Speed layer metrics
- Cache performance statistics
"""

import os
from datetime import datetime, timedelta
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from reasoning_trading.lambda_arch.coordinator import LambdaCoordinator
from reasoning_trading.services.portfolio import PortfolioService

from enterprise_ui.backend.core.errors import handle_error

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/analytics", tags=["analytics"])


# Request/Response Models
class PerformanceMetricsResponse(BaseModel):
    """Performance metrics response."""

    portfolio_value: float
    total_return: float
    total_return_pct: float
    sharpe_ratio: float
    max_drawdown: float
    current_drawdown: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    average_win: float
    average_loss: float
    profit_factor: float
    realized_pnl: float
    unrealized_pnl: float
    period_start: datetime
    period_end: datetime
    timestamp: datetime


class LambdaStatsResponse(BaseModel):
    """Lambda architecture statistics."""

    current_regime: str
    regime_confidence: float
    regime_since: datetime
    total_regime_changes: int
    recent_triggers: list[dict[str, Any]]
    batch_layer: dict[str, Any]
    speed_layer: dict[str, Any]
    serving_layer: dict[str, Any]
    timestamp: datetime


class SpeedLayerMetricsResponse(BaseModel):
    """Speed layer metrics."""

    total_decisions: int
    avg_decision_time_ms: float
    cache_hit_rate: float
    fallback_rate: float
    avg_confidence: float
    decisions_per_second: float
    fast_path_rate: float
    policy_network_calls: int
    timestamp: datetime


class CacheStatsResponse(BaseModel):
    """Cache statistics."""

    total_keys: int
    hit_rate: float
    miss_rate: float
    eviction_rate: float
    avg_get_time_ms: float
    avg_set_time_ms: float
    memory_used_mb: float
    memory_limit_mb: float
    ttl_seconds: int
    timestamp: datetime


# Dependency injection
async def get_portfolio_service() -> PortfolioService:
    """Get portfolio service instance."""
    return PortfolioService()


async def get_lambda_coordinator() -> LambdaCoordinator:
    """Get Lambda coordinator instance."""
    return LambdaCoordinator()


# Endpoints
@router.get(
    "/performance",
    response_model=PerformanceMetricsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get performance metrics",
    description="""
    Retrieves comprehensive trading performance metrics.

    This endpoint calculates and returns key performance indicators (KPIs)
    for the trading system including returns, risk metrics, and trade statistics.

    **Performance Metrics:**
    - Total and percentage returns
    - Sharpe ratio (risk-adjusted returns)
    - Maximum and current drawdown
    - Win rate and profit factor
    - Average win/loss amounts
    - Trade count and success rate

    **Query Parameters:**
    - period_days: Lookback period in days (default: 30)

    **Use Case:** Monitor and evaluate trading system performance.

    **Returns:** Comprehensive performance metrics.
    """,
)
async def get_performance_metrics(
    period_days: int = Query(default=30, ge=1, le=365),
    portfolio: PortfolioService = Depends(get_portfolio_service),
) -> PerformanceMetricsResponse:
    """
    Get performance metrics.

    Args:
        period_days: Lookback period in days
        portfolio: Portfolio service

    Returns:
        PerformanceMetricsResponse with performance metrics
    """
    logger.info("Calculating performance metrics", period_days=period_days)

    try:
        state = portfolio.get_state()
        sharpe_ratio = portfolio.calculate_sharpe_ratio()

        # Calculate returns - get initial value from portfolio or environment config
        initial_value = float(os.environ.get("INITIAL_PORTFOLIO_VALUE", "0")) or state.initial_portfolio_value or state.portfolio_value
        total_return = state.portfolio_value - initial_value
        total_return_pct = (total_return / initial_value) * 100 if initial_value > 0 else 0.0

        # Get trade history
        since = datetime.now() - timedelta(days=period_days)
        trades = portfolio.get_trade_history(since=since)

        # Calculate trade statistics
        winning_trades = [t for t in trades if t.pnl > 0]
        losing_trades = [t for t in trades if t.pnl < 0]

        win_rate = len(winning_trades) / len(trades) if trades else 0.0
        avg_win = sum(t.pnl for t in winning_trades) / len(winning_trades) if winning_trades else 0.0
        avg_loss = sum(t.pnl for t in losing_trades) / len(losing_trades) if losing_trades else 0.0

        # Profit factor: total wins / total losses
        total_wins = sum(t.pnl for t in winning_trades)
        total_losses = abs(sum(t.pnl for t in losing_trades))
        profit_factor = total_wins / total_losses if total_losses > 0 else 0.0

        logger.info(
            "Performance metrics calculated",
            total_return=total_return,
            sharpe_ratio=sharpe_ratio,
        )

        return PerformanceMetricsResponse(
            portfolio_value=state.portfolio_value,
            total_return=total_return,
            total_return_pct=total_return_pct,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=state.max_drawdown,
            current_drawdown=state.current_drawdown,
            total_trades=len(trades),
            winning_trades=len(winning_trades),
            losing_trades=len(losing_trades),
            win_rate=win_rate,
            average_win=avg_win,
            average_loss=avg_loss,
            profit_factor=profit_factor,
            realized_pnl=state.realized_pnl_total,
            unrealized_pnl=state.unrealized_pnl,
            period_start=since,
            period_end=datetime.now(),
            timestamp=datetime.now(),
        )

    except Exception as e:
        raise handle_error(
            logger=logger,
            error=e,
            generic_message="Failed to calculate performance metrics",
            log_message="Failed to calculate performance metrics",
        )


@router.get(
    "/lambda-stats",
    response_model=LambdaStatsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Lambda architecture statistics",
    description="""
    Retrieves statistics from the Lambda architecture layers.

    This endpoint returns operational metrics from all three layers of the
    Lambda architecture: batch, speed, and serving layers.

    **Lambda Architecture:**
    - Batch Layer: Strategic overnight MCTS planning
    - Speed Layer: Real-time tactical decisions with fast policy networks
    - Serving Layer: Policy caching and retrieval

    **Statistics Include:**
    - Current market regime and confidence
    - Regime change triggers and history
    - Layer-specific performance metrics
    - Cache hit rates and latencies

    **Use Case:** Monitor Lambda architecture health and performance.

    **Returns:** Comprehensive Lambda architecture statistics.
    """,
)
async def get_lambda_stats(
    coordinator: LambdaCoordinator = Depends(get_lambda_coordinator),
) -> LambdaStatsResponse:
    """
    Get Lambda architecture statistics.

    Args:
        coordinator: Lambda coordinator

    Returns:
        LambdaStatsResponse with statistics
    """
    logger.info("Fetching Lambda architecture statistics")

    try:
        stats = coordinator.get_statistics()

        return LambdaStatsResponse(
            current_regime=stats["current_regime"],
            regime_confidence=stats["regime_confidence"],
            regime_since=datetime.fromisoformat(stats["regime_since"]),
            total_regime_changes=stats["total_triggers"],
            recent_triggers=stats["recent_triggers"],
            batch_layer=stats["batch_layer"],
            speed_layer=stats["speed_layer"],
            serving_layer=stats["serving_layer"],
            timestamp=datetime.now(),
        )

    except Exception as e:
        raise handle_error(
            logger=logger,
            error=e,
            generic_message="Failed to fetch Lambda stats",
            log_message="Failed to fetch Lambda stats",
        )


@router.get(
    "/speed-layer-metrics",
    response_model=SpeedLayerMetricsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get speed layer metrics",
    description="""
    Retrieves detailed metrics from the speed layer.

    The speed layer handles real-time trading decisions using fast policy
    networks and cached strategies. This endpoint returns performance
    metrics specific to the speed layer.

    **Speed Layer Metrics:**
    - Total decisions made
    - Average decision latency
    - Cache hit rate (fast path vs computation)
    - Fallback rate (when cache misses)
    - Average confidence scores
    - Throughput (decisions per second)
    - Policy network utilization

    **Performance Targets:**
    - Decision latency: <100ms (p95)
    - Cache hit rate: >80%
    - Average confidence: >0.7

    **Use Case:** Monitor real-time decision-making performance.

    **Returns:** Speed layer performance metrics.
    """,
)
async def get_speed_layer_metrics(
    coordinator: LambdaCoordinator = Depends(get_lambda_coordinator),
) -> SpeedLayerMetricsResponse:
    """
    Get speed layer metrics.

    Args:
        coordinator: Lambda coordinator

    Returns:
        SpeedLayerMetricsResponse with metrics
    """
    logger.info("Fetching speed layer metrics")

    try:
        speed_layer = coordinator.speed_layer
        metrics = speed_layer.get_metrics()

        return SpeedLayerMetricsResponse(
            total_decisions=metrics.total_decisions,
            avg_decision_time_ms=metrics.avg_decision_time_ms,
            cache_hit_rate=metrics.cache_hit_rate,
            fallback_rate=metrics.fallback_rate,
            avg_confidence=metrics.avg_confidence,
            decisions_per_second=metrics.decisions_per_second,
            fast_path_rate=metrics.fast_path_rate,
            policy_network_calls=metrics.policy_network_calls,
            timestamp=datetime.now(),
        )

    except Exception as e:
        raise handle_error(
            logger=logger,
            error=e,
            generic_message="Failed to fetch speed layer metrics",
            log_message="Failed to fetch speed layer metrics",
        )


@router.get(
    "/cache-stats",
    response_model=CacheStatsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get cache statistics",
    description="""
    Retrieves cache performance statistics.

    The serving layer uses caching to store computed policies for fast
    retrieval. This endpoint returns detailed cache statistics.

    **Cache Metrics:**
    - Total keys stored
    - Hit rate (successful lookups)
    - Miss rate (cache misses)
    - Eviction rate (key removals)
    - Get/Set operation latencies
    - Memory utilization
    - TTL configuration

    **Cache Strategy:**
    - LRU eviction policy
    - State-based key hashing
    - Regime-aware invalidation
    - Configurable TTL

    **Performance Targets:**
    - Hit rate: >75%
    - Get latency: <5ms
    - Memory usage: <80% of limit

    **Use Case:** Monitor cache effectiveness and optimize hit rate.

    **Returns:** Cache performance statistics.
    """,
)
async def get_cache_stats(
    coordinator: LambdaCoordinator = Depends(get_lambda_coordinator),
) -> CacheStatsResponse:
    """
    Get cache statistics.

    Args:
        coordinator: Lambda coordinator

    Returns:
        CacheStatsResponse with cache statistics
    """
    logger.info("Fetching cache statistics")

    try:
        serving_layer = coordinator.serving_layer
        stats = serving_layer.get_statistics()

        # Extract cache-specific stats
        cache_stats = stats.get("cache", {})

        return CacheStatsResponse(
            total_keys=cache_stats.get("total_keys", 0),
            hit_rate=cache_stats.get("hit_rate", 0.0),
            miss_rate=cache_stats.get("miss_rate", 0.0),
            eviction_rate=cache_stats.get("eviction_rate", 0.0),
            avg_get_time_ms=cache_stats.get("avg_get_time_ms", 0.0),
            avg_set_time_ms=cache_stats.get("avg_set_time_ms", 0.0),
            memory_used_mb=cache_stats.get("memory_used_mb", 0.0),
            memory_limit_mb=cache_stats.get("memory_limit_mb", float(os.environ.get("CACHE_MEMORY_LIMIT_MB", "1024"))),
            ttl_seconds=cache_stats.get("ttl_seconds", 3600),
            timestamp=datetime.now(),
        )

    except Exception as e:
        raise handle_error(
            logger=logger,
            error=e,
            generic_message="Failed to fetch cache stats",
            log_message="Failed to fetch cache stats",
        )
