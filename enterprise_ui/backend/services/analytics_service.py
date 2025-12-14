"""
Analytics service for performance metrics and Lambda architecture integration.

Integrates with LambdaCoordinator to provide performance metrics,
layer statistics, and cache analytics.
"""

from datetime import datetime, timedelta
from typing import Any, Optional

import structlog

from reasoning_trading.lambda_arch.coordinator import LambdaCoordinator

from .cache_service import CacheService
from .exceptions import AnalyticsServiceException

logger = structlog.get_logger(__name__)


class AnalyticsService:
    """
    Analytics and performance metrics service.

    Provides:
    - Lambda architecture statistics
    - Speed layer metrics
    - Batch layer statistics
    - Cache performance analytics
    - Aggregated performance metrics
    - Time-series metrics collection
    """

    def __init__(
        self,
        lambda_coordinator: Optional[LambdaCoordinator] = None,
        cache_service: Optional[CacheService] = None,
    ):
        """
        Initialize analytics service.

        Args:
            lambda_coordinator: Lambda architecture coordinator
            cache_service: Cache service for metrics storage
        """
        self.lambda_coordinator = lambda_coordinator
        self.cache = cache_service

        # Metrics storage (would be time-series database in production)
        self._metrics_history: list[dict[str, Any]] = []
        self._max_history_size = 1000

    async def get_lambda_statistics(self) -> dict[str, Any]:
        """
        Get Lambda architecture statistics.

        Returns:
            Dictionary with Lambda coordinator statistics

        Raises:
            AnalyticsServiceException: On retrieval errors
        """
        try:
            if self.lambda_coordinator is None:
                return {
                    "enabled": False,
                    "message": "Lambda coordinator not configured",
                }

            stats = self.lambda_coordinator.get_statistics()

            # Enhance with additional metadata
            stats["enabled"] = True
            stats["timestamp"] = datetime.now().isoformat()

            logger.debug(
                "lambda_statistics_retrieved",
                regime=stats.get("current_regime"),
                total_triggers=stats.get("total_triggers"),
            )

            return stats

        except Exception as e:
            logger.error("lambda_statistics_failed", error=str(e))
            raise AnalyticsServiceException(
                "Failed to get Lambda statistics",
                {"error": str(e)},
            )

    async def get_speed_layer_metrics(self) -> dict[str, Any]:
        """
        Get speed layer performance metrics.

        Returns:
            Dictionary with speed layer metrics

        Raises:
            AnalyticsServiceException: On retrieval errors
        """
        try:
            if self.lambda_coordinator is None:
                return {
                    "enabled": False,
                    "message": "Lambda coordinator not configured",
                }

            stats = self.lambda_coordinator.get_statistics()
            speed_metrics = stats.get("speed_layer", {})

            # Add timing analysis
            if isinstance(speed_metrics, dict):
                decisions = speed_metrics.get("total_decisions", 0)
                total_time = speed_metrics.get("total_decision_time_ms", 0)

                speed_metrics["avg_decision_time_ms"] = (
                    total_time / decisions if decisions > 0 else 0.0
                )
                speed_metrics["decisions_per_second"] = (
                    decisions / (total_time / 1000.0) if total_time > 0 else 0.0
                )

            speed_metrics["timestamp"] = datetime.now().isoformat()

            logger.debug(
                "speed_layer_metrics_retrieved",
                total_decisions=speed_metrics.get("total_decisions", 0),
            )

            return speed_metrics

        except Exception as e:
            logger.error("speed_layer_metrics_failed", error=str(e))
            raise AnalyticsServiceException(
                "Failed to get speed layer metrics",
                {"error": str(e)},
            )

    async def get_batch_layer_statistics(self) -> dict[str, Any]:
        """
        Get batch layer statistics.

        Returns:
            Dictionary with batch layer statistics

        Raises:
            AnalyticsServiceException: On retrieval errors
        """
        try:
            if self.lambda_coordinator is None:
                return {
                    "enabled": False,
                    "message": "Lambda coordinator not configured",
                }

            stats = self.lambda_coordinator.get_statistics()
            batch_stats = stats.get("batch_layer", {})

            batch_stats["timestamp"] = datetime.now().isoformat()

            logger.debug(
                "batch_layer_statistics_retrieved",
                total_jobs=batch_stats.get("total_jobs", 0),
            )

            return batch_stats

        except Exception as e:
            logger.error("batch_layer_statistics_failed", error=str(e))
            raise AnalyticsServiceException(
                "Failed to get batch layer statistics",
                {"error": str(e)},
            )

    async def get_cache_statistics(self) -> dict[str, Any]:
        """
        Get cache performance statistics.

        Returns:
            Dictionary with cache statistics

        Raises:
            AnalyticsServiceException: On retrieval errors
        """
        try:
            if self.cache is None:
                return {
                    "enabled": False,
                    "message": "Cache service not configured",
                }

            stats = self.cache.get_statistics()
            stats["enabled"] = True
            stats["timestamp"] = datetime.now().isoformat()

            # Add cache efficiency metrics
            if stats["total_requests"] > 0:
                stats["efficiency_score"] = stats["hit_rate"] * 100

            logger.debug(
                "cache_statistics_retrieved",
                hit_rate=stats.get("hit_rate", 0),
                total_requests=stats.get("total_requests", 0),
            )

            return stats

        except Exception as e:
            logger.error("cache_statistics_failed", error=str(e))
            raise AnalyticsServiceException(
                "Failed to get cache statistics",
                {"error": str(e)},
            )

    async def get_serving_layer_statistics(self) -> dict[str, Any]:
        """
        Get serving layer statistics.

        Returns:
            Dictionary with serving layer statistics

        Raises:
            AnalyticsServiceException: On retrieval errors
        """
        try:
            if self.lambda_coordinator is None:
                return {
                    "enabled": False,
                    "message": "Lambda coordinator not configured",
                }

            stats = self.lambda_coordinator.get_statistics()
            serving_stats = stats.get("serving_layer", {})

            serving_stats["timestamp"] = datetime.now().isoformat()

            logger.debug("serving_layer_statistics_retrieved")

            return serving_stats

        except Exception as e:
            logger.error("serving_layer_statistics_failed", error=str(e))
            raise AnalyticsServiceException(
                "Failed to get serving layer statistics",
                {"error": str(e)},
            )

    async def get_aggregated_metrics(self) -> dict[str, Any]:
        """
        Get aggregated metrics across all systems.

        Returns:
            Dictionary with aggregated metrics

        Raises:
            AnalyticsServiceException: On aggregation errors
        """
        try:
            # Gather all metrics
            lambda_stats = await self.get_lambda_statistics()
            speed_metrics = await self.get_speed_layer_metrics()
            batch_stats = await self.get_batch_layer_statistics()
            cache_stats = await self.get_cache_statistics()
            serving_stats = await self.get_serving_layer_statistics()

            aggregated = {
                "lambda": lambda_stats,
                "speed_layer": speed_metrics,
                "batch_layer": batch_stats,
                "cache": cache_stats,
                "serving_layer": serving_stats,
                "timestamp": datetime.now().isoformat(),
            }

            # Calculate overall health score
            health_score = self._calculate_health_score(aggregated)
            aggregated["health_score"] = health_score

            logger.debug(
                "aggregated_metrics_retrieved",
                health_score=health_score,
            )

            return aggregated

        except Exception as e:
            logger.error("aggregated_metrics_failed", error=str(e))
            raise AnalyticsServiceException(
                "Failed to get aggregated metrics",
                {"error": str(e)},
            )

    def _calculate_health_score(self, metrics: dict[str, Any]) -> float:
        """
        Calculate overall system health score (0-100).

        Args:
            metrics: Aggregated metrics

        Returns:
            Health score between 0 and 100
        """
        score = 100.0

        # Cache health (20 points)
        cache_stats = metrics.get("cache", {})
        if cache_stats.get("enabled"):
            hit_rate = cache_stats.get("hit_rate", 0)
            cache_score = hit_rate * 20
        else:
            cache_score = 10  # Partial score if cache not enabled

        # Speed layer health (30 points)
        speed_stats = metrics.get("speed_layer", {})
        if speed_stats.get("enabled") is not False:
            decisions = speed_stats.get("total_decisions", 0)
            avg_time = speed_stats.get("avg_decision_time_ms", 0)

            # Penalize slow decisions
            speed_score = 30
            if avg_time > 1000:  # > 1 second
                speed_score -= 10
            if decisions == 0:
                speed_score -= 10
        else:
            speed_score = 15

        # Lambda coordinator health (30 points)
        lambda_stats = metrics.get("lambda", {})
        if lambda_stats.get("enabled"):
            lambda_score = 30
            # Check for recent triggers
            total_triggers = lambda_stats.get("total_triggers", 0)
            if total_triggers > 0:
                lambda_score += 5
        else:
            lambda_score = 15

        # Serving layer health (20 points)
        serving_stats = metrics.get("serving_layer", {})
        if serving_stats.get("enabled") is not False:
            serving_score = 20
        else:
            serving_score = 10

        total_score = cache_score + speed_score + lambda_score + serving_score

        return min(100.0, max(0.0, total_score))

    async def record_metric(
        self,
        metric_type: str,
        value: float,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """
        Record a custom metric.

        Args:
            metric_type: Type of metric
            value: Metric value
            metadata: Additional metadata

        Raises:
            AnalyticsServiceException: On recording errors
        """
        try:
            metric = {
                "type": metric_type,
                "value": value,
                "metadata": metadata or {},
                "timestamp": datetime.now().isoformat(),
            }

            self._metrics_history.append(metric)

            # Trim history if too large
            if len(self._metrics_history) > self._max_history_size:
                self._metrics_history = self._metrics_history[-self._max_history_size :]

            logger.debug("metric_recorded", type=metric_type, value=value)

        except Exception as e:
            logger.error("metric_recording_failed", type=metric_type, error=str(e))
            raise AnalyticsServiceException(
                f"Failed to record metric '{metric_type}'",
                {"type": metric_type, "error": str(e)},
            )

    async def get_metrics_history(
        self,
        metric_type: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Get metrics history.

        Args:
            metric_type: Filter by metric type
            since: Get metrics since this timestamp
            limit: Maximum number of metrics to return

        Returns:
            List of metric records

        Raises:
            AnalyticsServiceException: On retrieval errors
        """
        try:
            filtered = self._metrics_history

            # Filter by type
            if metric_type is not None:
                filtered = [m for m in filtered if m["type"] == metric_type]

            # Filter by time
            if since is not None:
                filtered = [
                    m
                    for m in filtered
                    if datetime.fromisoformat(m["timestamp"]) >= since
                ]

            # Apply limit
            filtered = filtered[-limit:]

            logger.debug(
                "metrics_history_retrieved",
                count=len(filtered),
                type=metric_type,
            )

            return filtered

        except Exception as e:
            logger.error("metrics_history_failed", error=str(e))
            raise AnalyticsServiceException(
                "Failed to get metrics history",
                {"error": str(e)},
            )

    async def get_regime_history(self) -> list[dict[str, Any]]:
        """
        Get market regime change history.

        Returns:
            List of regime change events

        Raises:
            AnalyticsServiceException: On retrieval errors
        """
        try:
            if self.lambda_coordinator is None:
                return []

            history = self.lambda_coordinator.get_regime_history()

            logger.debug("regime_history_retrieved", count=len(history))

            return history

        except Exception as e:
            logger.error("regime_history_failed", error=str(e))
            raise AnalyticsServiceException(
                "Failed to get regime history",
                {"error": str(e)},
            )

    async def clear_metrics_history(self) -> int:
        """
        Clear metrics history.

        Returns:
            Number of metrics cleared

        Raises:
            AnalyticsServiceException: On clearing errors
        """
        try:
            count = len(self._metrics_history)
            self._metrics_history.clear()

            logger.info("metrics_history_cleared", count=count)

            return count

        except Exception as e:
            logger.error("metrics_history_clear_failed", error=str(e))
            raise AnalyticsServiceException(
                "Failed to clear metrics history",
                {"error": str(e)},
            )

    def get_statistics(self) -> dict[str, Any]:
        """
        Get analytics service statistics.

        Returns:
            Dictionary with service statistics
        """
        return {
            "metrics_history_size": len(self._metrics_history),
            "max_history_size": self._max_history_size,
            "lambda_enabled": self.lambda_coordinator is not None,
            "cache_enabled": self.cache is not None,
            "timestamp": datetime.now().isoformat(),
        }
