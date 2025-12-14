"""
Rate limiting middleware for FastAPI using sliding window algorithm.

This middleware provides:
- Sliding window rate limiting with in-memory storage
- Configurable rate limits per endpoint type
- IP-based rate limiting for HTTP endpoints
- Connection-based rate limiting for WebSockets
- Automatic cleanup of expired entries
- Detailed logging with structlog
- 429 Too Many Requests responses with Retry-After headers

Architecture:
- Uses asyncio locks for thread-safe operations
- Implements sliding window counter algorithm
- Supports Redis backend upgrade path (currently in-memory)
- Efficient memory management with automatic cleanup
"""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Callable, Deque

from fastapi import Request, Response, WebSocket, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from ..core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class RateLimitConfig:
    """
    Configuration for rate limiting rules.

    Attributes:
        requests_per_window: Maximum number of requests allowed in the time window
        window_seconds: Time window in seconds for the rate limit
        burst_multiplier: Multiplier for burst allowance (default 1.5x)
    """
    requests_per_window: int
    window_seconds: int = 60
    burst_multiplier: float = 1.5

    @property
    def burst_limit(self) -> int:
        """Calculate burst limit based on multiplier."""
        return int(self.requests_per_window * self.burst_multiplier)


@dataclass
class RequestRecord:
    """
    Record of a single request for rate limiting.

    Attributes:
        timestamp: Unix timestamp of the request
        endpoint: Endpoint path that was accessed
    """
    timestamp: float
    endpoint: str


@dataclass
class ClientRateLimitState:
    """
    Rate limiting state for a single client (IP address or connection).

    Attributes:
        requests: Deque of recent request timestamps
        lock: Asyncio lock for thread-safe access
        last_cleanup: Timestamp of last cleanup operation
    """
    requests: Deque[RequestRecord] = field(default_factory=deque)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    last_cleanup: float = field(default_factory=time.time)


class SlidingWindowRateLimiter:
    """
    Sliding window rate limiter with automatic cleanup.

    Implements a sliding window counter algorithm that tracks requests
    in a time window and efficiently removes expired entries.

    Features:
    - O(1) rate limit check (amortized)
    - Automatic cleanup of old entries
    - Memory-efficient storage
    - Thread-safe operations with asyncio locks
    """

    def __init__(
        self,
        cleanup_interval_seconds: int = 300,  # Cleanup every 5 minutes
    ):
        """
        Initialize the rate limiter.

        Args:
            cleanup_interval_seconds: How often to run cleanup of expired entries
        """
        self.clients: dict[str, ClientRateLimitState] = {}
        self.cleanup_interval = cleanup_interval_seconds
        self.global_lock = asyncio.Lock()
        self._cleanup_task: asyncio.Task | None = None

        logger.info(
            "rate_limiter_initialized",
            cleanup_interval_seconds=cleanup_interval_seconds,
        )

    async def start_cleanup_task(self) -> None:
        """Start the background cleanup task."""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
            logger.info("rate_limiter_cleanup_task_started")

    async def stop_cleanup_task(self) -> None:
        """Stop the background cleanup task."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
            logger.info("rate_limiter_cleanup_task_stopped")

    async def _periodic_cleanup(self) -> None:
        """Periodically clean up expired entries to prevent memory leaks."""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self._cleanup_all_clients()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(
                    "rate_limiter_cleanup_error",
                    error=str(e),
                    exc_info=True,
                )

    async def _cleanup_all_clients(self) -> None:
        """Clean up expired entries for all clients."""
        async with self.global_lock:
            current_time = time.time()
            clients_to_remove = []

            for client_id, state in self.clients.items():
                async with state.lock:
                    # Remove requests older than 5 minutes (max window)
                    cutoff_time = current_time - 300

                    while state.requests and state.requests[0].timestamp < cutoff_time:
                        state.requests.popleft()

                    # Mark client for removal if no recent requests
                    if not state.requests:
                        clients_to_remove.append(client_id)

                    state.last_cleanup = current_time

            # Remove inactive clients
            for client_id in clients_to_remove:
                del self.clients[client_id]

            if clients_to_remove:
                logger.debug(
                    "rate_limiter_cleanup_completed",
                    clients_removed=len(clients_to_remove),
                    active_clients=len(self.clients),
                )

    async def _get_client_state(self, client_id: str) -> ClientRateLimitState:
        """
        Get or create rate limit state for a client.

        Args:
            client_id: Unique identifier for the client

        Returns:
            Rate limit state for the client
        """
        async with self.global_lock:
            if client_id not in self.clients:
                self.clients[client_id] = ClientRateLimitState()
            return self.clients[client_id]

    async def is_allowed(
        self,
        client_id: str,
        config: RateLimitConfig,
        endpoint: str,
    ) -> tuple[bool, dict[str, int | float]]:
        """
        Check if a request is allowed under the rate limit.

        Uses sliding window algorithm:
        1. Get current timestamp
        2. Remove requests outside the time window
        3. Count remaining requests
        4. Allow if count < limit, deny otherwise

        Args:
            client_id: Unique identifier for the client (IP or connection ID)
            config: Rate limit configuration to apply
            endpoint: Endpoint being accessed

        Returns:
            Tuple of (is_allowed, metadata) where metadata contains:
                - limit: The rate limit
                - remaining: Requests remaining in window
                - reset: Unix timestamp when the limit resets
                - retry_after: Seconds until retry (if blocked)
        """
        state = await self._get_client_state(client_id)

        async with state.lock:
            current_time = time.time()
            window_start = current_time - config.window_seconds

            # Remove requests outside the sliding window
            while state.requests and state.requests[0].timestamp < window_start:
                state.requests.popleft()

            # Count requests in current window
            request_count = len(state.requests)

            # Calculate metadata
            oldest_request_time = state.requests[0].timestamp if state.requests else current_time
            reset_time = oldest_request_time + config.window_seconds
            remaining = max(0, config.requests_per_window - request_count)

            metadata = {
                "limit": config.requests_per_window,
                "remaining": remaining,
                "reset": int(reset_time),
                "retry_after": max(0, int(reset_time - current_time)),
            }

            # Check if request is allowed
            is_allowed = request_count < config.requests_per_window

            if is_allowed:
                # Record the request
                state.requests.append(RequestRecord(
                    timestamp=current_time,
                    endpoint=endpoint,
                ))

                logger.debug(
                    "rate_limit_check_allowed",
                    client_id=client_id,
                    endpoint=endpoint,
                    request_count=request_count + 1,
                    limit=config.requests_per_window,
                    remaining=remaining - 1,
                )
            else:
                logger.warning(
                    "rate_limit_exceeded",
                    client_id=client_id,
                    endpoint=endpoint,
                    request_count=request_count,
                    limit=config.requests_per_window,
                    window_seconds=config.window_seconds,
                    retry_after=metadata["retry_after"],
                )

            return is_allowed, metadata

    async def get_stats(self) -> dict:
        """
        Get current rate limiter statistics.

        Returns:
            Dictionary with statistics about active clients and requests
        """
        async with self.global_lock:
            total_requests = sum(
                len(state.requests) for state in self.clients.values()
            )

            return {
                "active_clients": len(self.clients),
                "total_tracked_requests": total_requests,
                "cleanup_interval_seconds": self.cleanup_interval,
            }


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for HTTP request rate limiting.

    Applies different rate limits based on endpoint patterns:
    - Trading endpoints: Stricter limits (10 req/min)
    - Default endpoints: Standard limits (60 req/min)
    - Health/metrics: Excluded from rate limiting

    Uses client IP address as the identifier for rate limiting.
    """

    # Endpoint patterns for different rate limit tiers
    TRADING_ENDPOINTS = [
        "/api/v1/trading/",
        "/api/v1/portfolio/",
        "/api/v1/mcts/",
    ]

    EXCLUDED_PATHS = [
        "/health",
        "/metrics",
        "/api/health",
        "/docs",
        "/redoc",
        "/openapi.json",
    ]

    def __init__(
        self,
        app: ASGIApp,
        default_config: RateLimitConfig | None = None,
        trading_config: RateLimitConfig | None = None,
        exclude_paths: list[str] | None = None,
    ):
        """
        Initialize the rate limiting middleware.

        Args:
            app: The ASGI application
            default_config: Default rate limit configuration
            trading_config: Rate limit for trading endpoints
            exclude_paths: Paths to exclude from rate limiting
        """
        super().__init__(app)

        # Set default configurations
        self.default_config = default_config or RateLimitConfig(
            requests_per_window=60,
            window_seconds=60,
        )

        self.trading_config = trading_config or RateLimitConfig(
            requests_per_window=10,
            window_seconds=60,
        )

        self.exclude_paths = exclude_paths or self.EXCLUDED_PATHS
        self.rate_limiter = SlidingWindowRateLimiter()

        logger.info(
            "rate_limit_middleware_initialized",
            default_limit=self.default_config.requests_per_window,
            trading_limit=self.trading_config.requests_per_window,
            window_seconds=self.default_config.window_seconds,
            excluded_paths=len(self.exclude_paths),
        )

    async def startup(self) -> None:
        """Start background tasks."""
        await self.rate_limiter.start_cleanup_task()

    async def shutdown(self) -> None:
        """Stop background tasks."""
        await self.rate_limiter.stop_cleanup_task()

    def _get_client_id(self, request: Request) -> str:
        """
        Get client identifier from request.

        Uses X-Forwarded-For header if available (for proxies/load balancers),
        otherwise falls back to direct client IP.

        Args:
            request: The incoming request

        Returns:
            Client IP address
        """
        # Check for X-Forwarded-For header (from proxy/load balancer)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP in the chain (original client)
            return forwarded_for.split(",")[0].strip()

        # Fall back to direct client IP
        return request.client.host if request.client else "unknown"

    def _get_rate_limit_config(self, path: str) -> RateLimitConfig:
        """
        Determine which rate limit configuration to apply.

        Args:
            path: Request path

        Returns:
            Appropriate rate limit configuration
        """
        # Check if path matches trading endpoints
        for pattern in self.TRADING_ENDPOINTS:
            if path.startswith(pattern):
                return self.trading_config

        return self.default_config

    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        """
        Process request with rate limiting.

        Args:
            request: The incoming request
            call_next: The next middleware or route handler

        Returns:
            Response (potentially a 429 Too Many Requests)
        """
        # Skip rate limiting for excluded paths
        if request.url.path in self.exclude_paths:
            return await call_next(request)

        # Get client identifier
        client_id = self._get_client_id(request)

        # Get appropriate rate limit config
        config = self._get_rate_limit_config(request.url.path)

        # Check rate limit
        is_allowed, metadata = await self.rate_limiter.is_allowed(
            client_id=client_id,
            config=config,
            endpoint=request.url.path,
        )

        if not is_allowed:
            # Rate limit exceeded
            logger.warning(
                "request_rate_limited",
                client_id=client_id,
                path=request.url.path,
                method=request.method,
                limit=metadata["limit"],
                retry_after=metadata["retry_after"],
            )

            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "message": f"Too many requests. Please try again in {metadata['retry_after']} seconds.",
                    "limit": metadata["limit"],
                    "window_seconds": config.window_seconds,
                    "retry_after": metadata["retry_after"],
                },
                headers={
                    "X-RateLimit-Limit": str(metadata["limit"]),
                    "X-RateLimit-Remaining": str(metadata["remaining"]),
                    "X-RateLimit-Reset": str(metadata["reset"]),
                    "Retry-After": str(metadata["retry_after"]),
                },
            )

        # Request is allowed, process normally
        response = await call_next(request)

        # Add rate limit headers to response
        response.headers["X-RateLimit-Limit"] = str(metadata["limit"])
        response.headers["X-RateLimit-Remaining"] = str(metadata["remaining"])
        response.headers["X-RateLimit-Reset"] = str(metadata["reset"])

        return response


class WebSocketRateLimiter:
    """
    Rate limiter for WebSocket connections.

    Tracks message rates per WebSocket connection to prevent abuse.
    Each connection gets its own rate limit counter.
    """

    def __init__(
        self,
        messages_per_minute: int = 120,
        window_seconds: int = 60,
    ):
        """
        Initialize WebSocket rate limiter.

        Args:
            messages_per_minute: Maximum messages allowed per minute
            window_seconds: Time window for rate limiting
        """
        self.config = RateLimitConfig(
            requests_per_window=messages_per_minute,
            window_seconds=window_seconds,
        )
        self.rate_limiter = SlidingWindowRateLimiter()

        logger.info(
            "websocket_rate_limiter_initialized",
            messages_per_minute=messages_per_minute,
            window_seconds=window_seconds,
        )

    async def check_message(
        self,
        websocket: WebSocket,
        endpoint: str,
    ) -> tuple[bool, dict[str, int | float]]:
        """
        Check if a WebSocket message is allowed.

        Args:
            websocket: The WebSocket connection
            endpoint: WebSocket endpoint path

        Returns:
            Tuple of (is_allowed, metadata)
        """
        # Use WebSocket connection as unique identifier
        # In production, you might use authenticated user ID
        connection_id = f"ws_{id(websocket)}_{websocket.client.host if websocket.client else 'unknown'}"

        return await self.rate_limiter.is_allowed(
            client_id=connection_id,
            config=self.config,
            endpoint=endpoint,
        )

    async def startup(self) -> None:
        """Start background cleanup tasks."""
        await self.rate_limiter.start_cleanup_task()

    async def shutdown(self) -> None:
        """Stop background cleanup tasks."""
        await self.rate_limiter.stop_cleanup_task()


# Global WebSocket rate limiter instance
# This can be imported and used in WebSocket handlers
websocket_rate_limiter = WebSocketRateLimiter(
    messages_per_minute=120,
    window_seconds=60,
)


async def check_websocket_rate_limit(
    websocket: WebSocket,
    endpoint: str,
) -> bool:
    """
    Convenience function to check WebSocket rate limits.

    Usage in WebSocket handlers:
        from enterprise_ui.backend.middleware.rate_limiting import check_websocket_rate_limit

        if not await check_websocket_rate_limit(websocket, "/ws/mcts"):
            await websocket.close(code=1008, reason="Rate limit exceeded")
            return

    Args:
        websocket: The WebSocket connection
        endpoint: WebSocket endpoint path

    Returns:
        True if message is allowed, False if rate limit exceeded
    """
    is_allowed, metadata = await websocket_rate_limiter.check_message(
        websocket=websocket,
        endpoint=endpoint,
    )

    if not is_allowed:
        logger.warning(
            "websocket_rate_limit_exceeded",
            endpoint=endpoint,
            client=websocket.client.host if websocket.client else "unknown",
            retry_after=metadata["retry_after"],
        )

    return is_allowed


def setup_rate_limiting(
    app: ASGIApp,
    default_limit: int = 60,
    trading_limit: int = 10,
    websocket_limit: int = 120,
    window_seconds: int = 60,
) -> RateLimitMiddleware:
    """
    Set up rate limiting middleware for a FastAPI application.

    Example:
        from fastapi import FastAPI
        from enterprise_ui.backend.middleware.rate_limiting import setup_rate_limiting

        app = FastAPI()
        rate_limit_middleware = setup_rate_limiting(app)

        # Don't forget to start/stop cleanup tasks
        @app.on_event("startup")
        async def startup():
            await rate_limit_middleware.startup()

        @app.on_event("shutdown")
        async def shutdown():
            await rate_limit_middleware.shutdown()

    Args:
        app: FastAPI application instance
        default_limit: Default requests per window
        trading_limit: Rate limit for trading endpoints
        websocket_limit: Messages per minute for WebSocket connections
        window_seconds: Time window in seconds

    Returns:
        Configured RateLimitMiddleware instance
    """
    from fastapi import FastAPI

    if not isinstance(app, FastAPI):
        raise ValueError("App must be a FastAPI instance")

    # Create configurations
    default_config = RateLimitConfig(
        requests_per_window=default_limit,
        window_seconds=window_seconds,
    )

    trading_config = RateLimitConfig(
        requests_per_window=trading_limit,
        window_seconds=window_seconds,
    )

    # Add middleware
    middleware = RateLimitMiddleware(
        app=app,
        default_config=default_config,
        trading_config=trading_config,
    )
    app.add_middleware(
        RateLimitMiddleware,
        default_config=default_config,
        trading_config=trading_config,
    )

    # Update WebSocket rate limiter config
    websocket_rate_limiter.config = RateLimitConfig(
        requests_per_window=websocket_limit,
        window_seconds=window_seconds,
    )

    logger.info(
        "rate_limiting_configured",
        default_limit=default_limit,
        trading_limit=trading_limit,
        websocket_limit=websocket_limit,
        window_seconds=window_seconds,
    )

    return middleware


__all__ = [
    "RateLimitConfig",
    "SlidingWindowRateLimiter",
    "RateLimitMiddleware",
    "WebSocketRateLimiter",
    "websocket_rate_limiter",
    "check_websocket_rate_limit",
    "setup_rate_limiting",
]
