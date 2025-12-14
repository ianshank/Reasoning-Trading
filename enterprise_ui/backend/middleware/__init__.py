"""
Middleware components for the enterprise UI backend.

Available middleware:
- logging_middleware: Request/response logging with timing
- rate_limiting: Rate limiting with sliding window algorithm
- security_headers: Security headers middleware
"""

from .logging_middleware import setup_middleware
from .rate_limiting import (
    RateLimitConfig,
    RateLimitMiddleware,
    WebSocketRateLimiter,
    check_websocket_rate_limit,
    setup_rate_limiting,
    websocket_rate_limiter,
)

__all__ = [
    # Logging middleware
    "setup_middleware",
    # Rate limiting
    "RateLimitConfig",
    "RateLimitMiddleware",
    "WebSocketRateLimiter",
    "websocket_rate_limiter",
    "check_websocket_rate_limit",
    "setup_rate_limiting",
]
