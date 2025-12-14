"""
FastAPI application entry point for Reasoning Trading Enterprise UI.

This module creates and configures the FastAPI application with:
- Lifespan context management for startup/shutdown
- CORS middleware
- Logging middleware
- Rate limiting
- API routers (REST and WebSocket)
- OpenAPI documentation
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from enterprise_ui.backend.config import get_backend_settings
from enterprise_ui.backend.core.errors import ErrorCode, ProblemDetail
from enterprise_ui.backend.core.logging import configure_logging, get_logger
from enterprise_ui.backend.dependencies import close_redis_client
from enterprise_ui.backend.middleware.logging_middleware import setup_middleware
from enterprise_ui.backend.middleware.rate_limiting import (
    setup_rate_limiting,
    websocket_rate_limiter,
)
from enterprise_ui.backend.middleware.security_headers import setup_security_headers

logger = get_logger(__name__)

# Global reference to rate limit middleware for startup/shutdown
_rate_limit_middleware = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan context manager.

    Handles startup and shutdown events:
    - Startup: Initialize logging, validate configuration, warm up services
    - Shutdown: Close database connections, Redis client, cleanup resources

    Args:
        app: FastAPI application instance

    Yields:
        None (application is running)
    """
    # --- Startup ---
    settings = get_backend_settings()

    logger.info(
        "application_starting",
        environment=settings.environment,
        version=settings.version,
        host=settings.host,
        port=settings.port,
    )

    # Configure structured logging
    configure_logging(
        json_logs=settings.is_production,
        log_level=None,  # Use environment-based default
    )

    # Validate API keys
    api_keys_status = settings.core.validate_api_keys()
    logger.info("api_keys_validated", **api_keys_status)

    # Warn if critical keys are missing
    if not api_keys_status["alpaca"]:
        logger.warning("alpaca_api_key_missing", message="Trading will not work without Alpaca credentials")

    # Disable docs in production
    if settings.is_production:
        settings.disable_docs_in_production()
        logger.info("api_documentation_disabled", reason="production_environment")

    logger.info("application_started", message="Ready to accept requests")

    # Start rate limiting cleanup tasks
    global _rate_limit_middleware
    if _rate_limit_middleware:
        await _rate_limit_middleware.startup()
        logger.info("rate_limiting_cleanup_tasks_started")

    # Start WebSocket rate limiter cleanup
    await websocket_rate_limiter.startup()
    logger.info("websocket_rate_limiter_cleanup_started")

    yield

    # --- Shutdown ---
    logger.info("application_shutting_down")

    # Stop rate limiting cleanup tasks
    if _rate_limit_middleware:
        await _rate_limit_middleware.shutdown()
        logger.info("rate_limiting_cleanup_tasks_stopped")

    # Stop WebSocket rate limiter cleanup
    await websocket_rate_limiter.shutdown()
    logger.info("websocket_rate_limiter_cleanup_stopped")

    # Close Redis connection
    await close_redis_client()

    logger.info("application_stopped")


def create_application() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance

    Example:
        app = create_application()
        uvicorn.run(app, host="0.0.0.0", port=8000)
    """
    settings = get_backend_settings()

    # Create FastAPI app
    app = FastAPI(
        title=settings.title,
        description=settings.description,
        version=settings.version,
        openapi_url=settings.openapi_url,
        docs_url=settings.docs_url,
        redoc_url=settings.redoc_url,
        lifespan=lifespan,
    )

    # --- Security Headers Middleware ---
    setup_security_headers(
        app,
        enable_hsts=settings.is_production,  # Only enable HSTS in production with HTTPS
        hsts_max_age=31536000,  # 1 year
        hsts_include_subdomains=True,
        hsts_preload=True,
    )

    # --- CORS Middleware ---
    if settings.cors.enabled:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors.allowed_origins,
            allow_credentials=settings.cors.allow_credentials,
            allow_methods=settings.cors.allowed_methods,
            allow_headers=settings.cors.allowed_headers,
        )
        logger.info(
            "cors_middleware_configured",
            origins=settings.cors.allowed_origins,
        )

    # --- Rate Limiting Middleware ---
    # Add rate limiting before logging to reject requests early
    global _rate_limit_middleware
    _rate_limit_middleware = setup_rate_limiting(
        app,
        default_limit=60,  # 60 requests/minute for normal endpoints
        trading_limit=10,  # 10 requests/minute for trading endpoints
        websocket_limit=120,  # 120 messages/minute for WebSocket connections
        window_seconds=60,
    )

    # --- Logging Middleware ---
    setup_middleware(
        app,
        config={
            "exclude_paths": ["/health", "/metrics", "/api/health"],
            "log_request_body": settings.is_development,
            "log_response_body": False,
            "slow_request_threshold_ms": 1000.0,
            "very_slow_threshold_ms": 5000.0,
        },
    )

    # --- Exception Handlers ---

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """
        Handle request validation errors with RFC 7807 compliant error messages.

        Args:
            request: The incoming request
            exc: Validation error exception

        Returns:
            RFC 7807 JSON response with validation error details
        """
        logger.warning(
            "validation_error",
            path=request.url.path,
            errors=exc.errors(),
        )

        # Create RFC 7807 Problem Details response
        problem = ProblemDetail(
            type="about:blank",
            title="Validation Error",
            status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Request validation failed. Please check the provided data.",
            instance=str(request.url.path),
        )

        # Convert to dict and add validation errors
        problem_dict = problem.model_dump(exclude_none=True)
        problem_dict["errors"] = exc.errors()

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=problem_dict,
            media_type="application/problem+json",
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """
        Handle uncaught exceptions with RFC 7807 compliant error messages.

        Args:
            request: The incoming request
            exc: The exception

        Returns:
            RFC 7807 JSON response with error details
        """
        logger.error(
            "uncaught_exception",
            path=request.url.path,
            error_type=type(exc).__name__,
            error_message=str(exc),
            exc_info=True,
        )

        # In production, return generic message
        # In development, return detailed error for debugging
        detail = (
            f"Internal server error: {str(exc)}"
            if settings.is_development
            else "An internal server error occurred"
        )

        # Create RFC 7807 Problem Details response
        problem = ProblemDetail(
            type="about:blank",
            title="Internal Server Error",
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
            instance=str(request.url.path),
        )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=problem.model_dump(exclude_none=True),
            media_type="application/problem+json",
        )

    # --- Health Check Endpoint ---

    @app.get("/health", tags=["Health"])
    async def health_check() -> dict:
        """
        Health check endpoint for monitoring and load balancers.

        Returns:
            Health status information
        """
        return {
            "status": "healthy",
            "environment": settings.environment,
            "version": settings.version,
        }

    # --- API Routers ---
    # Import routers here to avoid circular imports
    from enterprise_ui.backend.api.v1.router import api_router
    from enterprise_ui.backend.api.websockets.router import websocket_router

    # Include REST API router
    app.include_router(api_router, prefix="/api/v1")

    # Include WebSocket router
    app.include_router(websocket_router, prefix="/api/v1")

    logger.info("api_routers_registered", prefix="/api/v1", routers=["rest", "websocket"])

    return app


# Create application instance
app = create_application()


if __name__ == "__main__":
    import uvicorn

    settings = get_backend_settings()

    uvicorn.run(
        "enterprise_ui.backend.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload and settings.is_development,
        log_level="info",
        access_log=False,  # We have our own logging middleware
    )
