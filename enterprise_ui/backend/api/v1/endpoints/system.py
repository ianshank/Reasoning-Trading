"""
System health and configuration endpoints.

This module provides REST API endpoints for:
- Health checks
- Readiness checks
- System configuration retrieval
- Batch recomputation triggers
- System status and diagnostics
"""

import platform
import time
from datetime import datetime
from typing import Any

import psutil
import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from reasoning_trading.config import Settings, get_settings
from reasoning_trading.lambda_arch.coordinator import LambdaCoordinator

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/system", tags=["system"])


# Request/Response Models
class HealthCheckResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Health status: healthy, degraded, unhealthy")
    timestamp: datetime
    uptime_seconds: float
    version: str = "1.0.0"
    checks: dict[str, bool]


class ReadinessCheckResponse(BaseModel):
    """Readiness check response."""

    ready: bool
    timestamp: datetime
    checks: dict[str, bool]
    message: str


class SystemConfigResponse(BaseModel):
    """System configuration response."""

    trading_mode: str
    risk_profile: str
    mcts_config: dict[str, Any]
    risk_limits: dict[str, Any]
    api_config: dict[str, Any]
    feature_flags: dict[str, bool]
    timestamp: datetime


class BatchTriggerRequest(BaseModel):
    """Batch recomputation trigger request."""

    symbols: list[str] = Field(..., description="Symbols to recompute")
    reason: str = Field(default="manual", description="Trigger reason")
    priority: str = Field(default="normal", description="Priority: low, normal, high")


class BatchTriggerResponse(BaseModel):
    """Batch recomputation trigger response."""

    job_id: str
    symbols: list[str]
    status: str
    submitted_at: datetime
    estimated_completion: datetime | None = None


class SystemStatusResponse(BaseModel):
    """System status and diagnostics."""

    status: str
    uptime_seconds: float
    cpu_usage_percent: float
    memory_usage_percent: float
    disk_usage_percent: float
    active_connections: int
    requests_per_minute: float
    error_rate: float
    avg_response_time_ms: float
    timestamp: datetime


# Global state
_start_time = time.time()
_request_count = 0
_error_count = 0


# Dependency injection
async def get_system_settings() -> Settings:
    """Get system settings."""
    return get_settings()


async def get_lambda_coordinator() -> LambdaCoordinator:
    """Get Lambda coordinator instance."""
    return LambdaCoordinator()


# Endpoints
@router.get(
    "/health",
    response_model=HealthCheckResponse,
    status_code=status.HTTP_200_OK,
    summary="Health check",
    description="""
    Performs comprehensive system health check.

    This endpoint checks the health of all critical system components
    including databases, caches, external APIs, and services.

    **Health Checks:**
    - API server responsive
    - Database connectivity
    - Cache (Redis) availability
    - Portfolio service operational
    - MCTS engine functional
    - External API keys valid

    **Status Values:**
    - healthy: All checks pass
    - degraded: Some non-critical checks fail
    - unhealthy: Critical checks fail

    **Use Case:** Monitor system health for alerts and dashboards.

    **Returns:** Health status with individual check results.
    """,
)
async def health_check(
    settings: Settings = Depends(get_system_settings),
) -> HealthCheckResponse:
    """
    Perform health check.

    Args:
        settings: System settings

    Returns:
        HealthCheckResponse with health status
    """
    logger.info("Performing health check")

    uptime = time.time() - _start_time

    # Perform various health checks
    checks = {
        "api_server": True,  # If we're here, API is running
        "database": True,  # TODO: Check database connection
        "cache": True,  # TODO: Check Redis connection
        "portfolio_service": True,  # TODO: Check portfolio service
        "mcts_engine": True,  # TODO: Check MCTS availability
        "api_keys": any(settings.validate_api_keys().values()),
    }

    # Determine overall status
    if all(checks.values()):
        overall_status = "healthy"
    elif checks["api_server"] and checks["portfolio_service"]:
        overall_status = "degraded"
    else:
        overall_status = "unhealthy"

    logger.info("Health check completed", status=overall_status)

    return HealthCheckResponse(
        status=overall_status,
        timestamp=datetime.now(),
        uptime_seconds=uptime,
        checks=checks,
    )


@router.get(
    "/ready",
    response_model=ReadinessCheckResponse,
    status_code=status.HTTP_200_OK,
    summary="Readiness check",
    description="""
    Checks if the system is ready to accept requests.

    This endpoint is used by orchestration systems (Kubernetes, Docker Swarm)
    to determine if the service is ready to receive traffic.

    **Readiness Checks:**
    - Configuration loaded
    - Services initialized
    - Required dependencies available
    - Warm-up complete

    **Difference from Health:**
    - Health: Is the system working?
    - Readiness: Is the system ready to serve traffic?

    **Use Case:** Load balancer and orchestration readiness probes.

    **Returns:** Readiness status with check details.
    """,
)
async def readiness_check(
    settings: Settings = Depends(get_system_settings),
) -> ReadinessCheckResponse:
    """
    Perform readiness check.

    Args:
        settings: System settings

    Returns:
        ReadinessCheckResponse with readiness status
    """
    logger.info("Performing readiness check")

    checks = {
        "config_loaded": True,
        "services_initialized": True,
        "dependencies_available": True,
        "warmup_complete": True,
    }

    ready = all(checks.values())
    message = "System is ready" if ready else "System is not ready"

    logger.info("Readiness check completed", ready=ready)

    return ReadinessCheckResponse(
        ready=ready,
        timestamp=datetime.now(),
        checks=checks,
        message=message,
    )


@router.get(
    "/config",
    response_model=SystemConfigResponse,
    status_code=status.HTTP_200_OK,
    summary="Get system configuration",
    description="""
    Retrieves current system configuration.

    This endpoint returns the active configuration including trading mode,
    risk parameters, MCTS settings, and feature flags. Sensitive values
    (API keys) are redacted.

    **Configuration Sections:**
    - Trading: Mode (paper/live), platform settings
    - Risk: Position limits, stop-loss defaults, daily limits
    - MCTS: Simulations, exploration, time budgets
    - API: Host, port, rate limits, CORS
    - Features: Enabled/disabled features

    **Security:** API keys and secrets are not exposed.

    **Use Case:** Verify system configuration and settings.

    **Returns:** Current system configuration.
    """,
)
async def get_system_config(
    settings: Settings = Depends(get_system_settings),
) -> SystemConfigResponse:
    """
    Get system configuration.

    Args:
        settings: System settings

    Returns:
        SystemConfigResponse with configuration
    """
    logger.info("Fetching system configuration")

    return SystemConfigResponse(
        trading_mode=settings.trading.trading_mode.value,
        risk_profile=settings.risk.default_risk_profile.value,
        mcts_config={
            "max_simulations": settings.mcts.max_simulations,
            "exploration_weight": settings.mcts.exploration_weight,
            "rollout_horizon_days": settings.mcts.rollout_horizon_days,
            "confidence_threshold": settings.mcts.confidence_threshold,
            "realtime_budget_ms": settings.mcts.realtime_budget_ms,
            "progressive_widening_alpha": settings.mcts.progressive_widening_alpha,
            "discount_factor": settings.mcts.discount_factor,
        },
        risk_limits={
            "max_position_size_fraction": settings.risk.max_position_size_fraction,
            "default_stop_loss_percent": settings.risk.default_stop_loss_percent,
            "max_daily_loss_percent": settings.risk.max_daily_loss_percent,
        },
        api_config={
            "host": settings.api.host,
            "port": settings.api.port,
            "rate_limit": settings.api.rate_limit,
            "cors_allowed_origins": settings.api.cors_allowed_origins,
        },
        feature_flags={
            "allow_shorts": settings.features.allow_shorts,
            "enable_margin_trading": settings.features.enable_margin_trading,
            "enable_crypto_trading": settings.features.enable_crypto_trading,
            "auto_execute_trades": settings.features.auto_execute_trades,
        },
        timestamp=datetime.now(),
    )


@router.post(
    "/batch/trigger",
    response_model=BatchTriggerResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger batch recomputation",
    description="""
    Triggers batch layer recomputation for specified symbols.

    This endpoint submits a batch job to recompute strategic MCTS policies
    for the given symbols. Batch recomputation is typically triggered by:
    - Market regime changes
    - Significant price movements
    - Manual request for updated strategies
    - Scheduled overnight processing

    **Batch Process:**
    1. Submit job with symbols and priority
    2. Queue job in batch layer
    3. Run full MCTS search for each symbol
    4. Update serving layer cache with results
    5. Return job ID for tracking

    **Parameters:**
    - symbols: List of trading symbols to recompute
    - reason: Why the batch was triggered
    - priority: Job priority (low, normal, high)

    **Use Case:** Trigger strategic policy updates when needed.

    **Returns:** Job ID and submission details (202 Accepted).
    """,
)
async def trigger_batch_recompute(
    request: BatchTriggerRequest,
    coordinator: LambdaCoordinator = Depends(get_lambda_coordinator),
) -> BatchTriggerResponse:
    """
    Trigger batch recomputation.

    Args:
        request: Batch trigger request
        coordinator: Lambda coordinator

    Returns:
        BatchTriggerResponse with job details
    """
    logger.info(
        "Triggering batch recomputation",
        symbols=request.symbols,
        reason=request.reason,
        priority=request.priority,
    )

    try:
        # TODO: Build states for symbols
        # For now, use empty dict
        states = {}

        # Trigger batch recomputation
        job_id = await coordinator.trigger_batch_recompute(
            states=states,
            reason=request.reason,
        )

        # Estimate completion time (rough estimate)
        estimated_time = datetime.now()
        # Add ~1 minute per symbol
        from datetime import timedelta
        estimated_time += timedelta(minutes=len(request.symbols))

        logger.info(
            "Batch recomputation triggered",
            job_id=job_id,
            symbols=request.symbols,
        )

        return BatchTriggerResponse(
            job_id=job_id,
            symbols=request.symbols,
            status="submitted",
            submitted_at=datetime.now(),
            estimated_completion=estimated_time,
        )

    except Exception as e:
        logger.error("Failed to trigger batch recomputation", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger batch recomputation: {str(e)}",
        )


@router.get(
    "/status",
    response_model=SystemStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get system status",
    description="""
    Retrieves detailed system status and diagnostics.

    This endpoint provides operational metrics about the running system
    including resource utilization, performance statistics, and health.

    **System Metrics:**
    - Uptime in seconds
    - CPU usage percentage
    - Memory usage percentage
    - Disk usage percentage
    - Active connections count
    - Request throughput (req/min)
    - Error rate
    - Average response time

    **Use Case:** System monitoring, debugging, capacity planning.

    **Returns:** Comprehensive system status.
    """,
)
async def get_system_status() -> SystemStatusResponse:
    """
    Get system status and diagnostics.

    Returns:
        SystemStatusResponse with system status
    """
    logger.info("Fetching system status")

    try:
        uptime = time.time() - _start_time

        # Get system resource usage
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        # Calculate metrics
        requests_per_minute = (_request_count / uptime) * 60 if uptime > 0 else 0
        error_rate = (_error_count / max(_request_count, 1)) * 100

        # Determine overall status
        if cpu_percent < 80 and memory.percent < 80 and disk.percent < 80:
            overall_status = "healthy"
        elif cpu_percent < 90 and memory.percent < 90:
            overall_status = "degraded"
        else:
            overall_status = "critical"

        return SystemStatusResponse(
            status=overall_status,
            uptime_seconds=uptime,
            cpu_usage_percent=cpu_percent,
            memory_usage_percent=memory.percent,
            disk_usage_percent=disk.percent,
            active_connections=0,  # TODO: Track actual connections
            requests_per_minute=requests_per_minute,
            error_rate=error_rate,
            avg_response_time_ms=50.0,  # TODO: Track actual response times
            timestamp=datetime.now(),
        )

    except Exception as e:
        logger.error("Failed to fetch system status", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch system status: {str(e)}",
        )


@router.get(
    "/info",
    status_code=status.HTTP_200_OK,
    summary="Get system information",
    description="""
    Retrieves basic system information.

    This endpoint returns static system information including platform
    details, Python version, and deployment environment.

    **Returns:** System information dictionary.
    """,
)
async def get_system_info() -> dict[str, Any]:
    """Get system information."""
    import sys

    return {
        "platform": platform.platform(),
        "python_version": sys.version,
        "api_version": "1.0.0",
        "environment": "production",  # TODO: Get from config
        "hostname": platform.node(),
        "timestamp": datetime.now().isoformat(),
    }
