"""
FastAPI middleware for request/response logging and timing.

This middleware provides:
- Automatic request/response logging
- Request timing information
- Error tracking with stack traces
- Request ID generation and propagation
"""

import time
import traceback
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from ..core.logging import (
    clear_request_id,
    get_logger,
    set_request_id,
)

logger = get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging HTTP requests and responses.

    This middleware:
    - Generates or extracts request IDs
    - Logs all incoming requests
    - Tracks request timing
    - Logs responses with status codes
    - Captures and logs errors with full stack traces
    """

    def __init__(
        self,
        app: ASGIApp,
        exclude_paths: list[str] | None = None,
        log_request_body: bool = False,
        log_response_body: bool = False,
    ):
        """
        Initialize the logging middleware.

        Args:
            app: The ASGI application
            exclude_paths: List of paths to exclude from logging (e.g., health checks)
            log_request_body: Whether to log request bodies (use with caution)
            log_response_body: Whether to log response bodies (use with caution)
        """
        super().__init__(app)
        self.exclude_paths = exclude_paths or ["/health", "/metrics"]
        self.log_request_body = log_request_body
        self.log_response_body = log_response_body

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        """
        Process the request and add logging.

        Args:
            request: The incoming request
            call_next: The next middleware or route handler

        Returns:
            The response
        """
        # Skip logging for excluded paths
        if request.url.path in self.exclude_paths:
            return await call_next(request)

        # Generate or extract request ID
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        set_request_id(request_id)

        # Record start time
        start_time = time.time()

        # Extract request information
        request_info = {
            "method": request.method,
            "url": str(request.url),
            "path": request.url.path,
            "client": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
        }

        # Log request body if enabled
        if self.log_request_body and request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                request_info["body"] = body.decode("utf-8")[:1000]  # Limit size
            except Exception as e:
                logger.warning("failed_to_read_request_body", error=str(e))

        # Log incoming request
        logger.info("request_started", **request_info)

        try:
            # Process the request
            response = await call_next(request)

            # Calculate duration
            duration = time.time() - start_time

            # Log successful response
            logger.info(
                "request_completed",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=round(duration * 1000, 2),
            )

            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id

            return response

        except Exception as e:
            # Calculate duration
            duration = time.time() - start_time

            # Log error with full details
            logger.error(
                "request_failed",
                method=request.method,
                path=request.url.path,
                error_type=type(e).__name__,
                error_message=str(e),
                duration_ms=round(duration * 1000, 2),
                traceback=traceback.format_exc(),
                exc_info=True,
            )

            # Re-raise the exception to be handled by FastAPI
            raise

        finally:
            # Clear request ID from context
            clear_request_id()


class PerformanceLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for detailed performance logging.

    Logs warnings for slow requests based on configurable thresholds.
    """

    def __init__(
        self,
        app: ASGIApp,
        slow_request_threshold_ms: float = 1000.0,
        very_slow_threshold_ms: float = 5000.0,
    ):
        """
        Initialize the performance logging middleware.

        Args:
            app: The ASGI application
            slow_request_threshold_ms: Threshold in ms for slow request warnings
            very_slow_threshold_ms: Threshold in ms for very slow request errors
        """
        super().__init__(app)
        self.slow_threshold = slow_request_threshold_ms
        self.very_slow_threshold = very_slow_threshold_ms

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        """
        Process the request and log performance metrics.

        Args:
            request: The incoming request
            call_next: The next middleware or route handler

        Returns:
            The response
        """
        start_time = time.time()

        try:
            response = await call_next(request)
            duration_ms = (time.time() - start_time) * 1000

            # Log based on performance thresholds
            if duration_ms >= self.very_slow_threshold:
                logger.error(
                    "very_slow_request",
                    method=request.method,
                    path=request.url.path,
                    duration_ms=round(duration_ms, 2),
                    threshold_ms=self.very_slow_threshold,
                )
            elif duration_ms >= self.slow_threshold:
                logger.warning(
                    "slow_request",
                    method=request.method,
                    path=request.url.path,
                    duration_ms=round(duration_ms, 2),
                    threshold_ms=self.slow_threshold,
                )

            return response

        except Exception:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                "request_error_with_timing",
                method=request.method,
                path=request.url.path,
                duration_ms=round(duration_ms, 2),
            )
            raise


class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add contextual information to all log entries.

    Automatically adds request metadata to the logging context.
    """

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        """
        Process the request and add context.

        Args:
            request: The incoming request
            call_next: The next middleware or route handler

        Returns:
            The response
        """
        import structlog

        # Bind request context
        structlog.contextvars.bind_contextvars(
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host if request.client else None,
        )

        try:
            response = await call_next(request)
            return response
        finally:
            # Clear context
            structlog.contextvars.clear_contextvars()


def setup_middleware(app: ASGIApp, config: dict | None = None) -> None:
    """
    Set up all logging middleware for a FastAPI application.

    Example:
        from fastapi import FastAPI
        from enterprise_ui.backend.middleware.logging_middleware import setup_middleware

        app = FastAPI()
        setup_middleware(app)

    Args:
        app: FastAPI application instance
        config: Optional configuration dictionary with middleware settings
    """
    from fastapi import FastAPI

    if not isinstance(app, FastAPI):
        raise ValueError("App must be a FastAPI instance")

    config = config or {}

    # Add request context middleware (innermost)
    app.add_middleware(RequestContextMiddleware)

    # Add performance logging middleware
    app.add_middleware(
        PerformanceLoggingMiddleware,
        slow_request_threshold_ms=config.get("slow_request_threshold_ms", 1000.0),
        very_slow_threshold_ms=config.get("very_slow_threshold_ms", 5000.0),
    )

    # Add main logging middleware (outermost)
    app.add_middleware(
        LoggingMiddleware,
        exclude_paths=config.get("exclude_paths", ["/health", "/metrics"]),
        log_request_body=config.get("log_request_body", False),
        log_response_body=config.get("log_response_body", False),
    )

    logger.info("logging_middleware_configured", middleware_config=config)
