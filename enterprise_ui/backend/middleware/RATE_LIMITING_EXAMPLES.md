# Rate Limiting Examples

This document provides examples of how to use the rate limiting middleware in the Enterprise UI backend.

## HTTP Endpoint Rate Limiting

The rate limiting middleware is automatically applied to all HTTP endpoints. No changes needed in endpoint code.

### Configuration

```python
from fastapi import FastAPI
from enterprise_ui.backend.middleware.rate_limiting import setup_rate_limiting

app = FastAPI()

# Set up rate limiting with custom limits
rate_limit_middleware = setup_rate_limiting(
    app,
    default_limit=60,      # 60 requests/minute for normal endpoints
    trading_limit=10,      # 10 requests/minute for trading endpoints
    websocket_limit=120,   # 120 messages/minute for WebSocket connections
    window_seconds=60,
)

# Start cleanup tasks on application startup
@app.on_event("startup")
async def startup():
    await rate_limit_middleware.startup()

# Stop cleanup tasks on application shutdown
@app.on_event("shutdown")
async def shutdown():
    await rate_limit_middleware.shutdown()
```

### Rate Limit Headers

All HTTP responses include rate limit headers:

```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1702656789
```

When rate limit is exceeded, a 429 response is returned:

```json
{
  "error": "Rate limit exceeded",
  "message": "Too many requests. Please try again in 42 seconds.",
  "limit": 60,
  "window_seconds": 60,
  "retry_after": 42
}
```

## WebSocket Rate Limiting

WebSocket rate limiting must be manually integrated into WebSocket handlers.

### Basic Usage

```python
from fastapi import WebSocket, WebSocketDisconnect
from enterprise_ui.backend.middleware.rate_limiting import check_websocket_rate_limit

@websocket_router.websocket("/ws/example")
async def example_websocket(websocket: WebSocket):
    await websocket.accept()

    try:
        while True:
            # Receive message
            data = await websocket.receive_json()

            # Check rate limit BEFORE processing
            if not await check_websocket_rate_limit(websocket, "/ws/example"):
                await websocket.send_json({
                    "type": "error",
                    "message": "Rate limit exceeded. Please slow down."
                })
                # Optionally close the connection
                # await websocket.close(code=1008, reason="Rate limit exceeded")
                continue

            # Process message normally
            await process_message(data)

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
```

### Advanced Usage with Custom Limits

```python
from enterprise_ui.backend.middleware.rate_limiting import (
    WebSocketRateLimiter,
    RateLimitConfig,
)

# Create a custom rate limiter for a specific WebSocket endpoint
custom_ws_limiter = WebSocketRateLimiter(
    messages_per_minute=30,  # More restrictive
    window_seconds=60,
)

@websocket_router.websocket("/ws/high-frequency")
async def high_frequency_websocket(websocket: WebSocket):
    await websocket.accept()

    # Start cleanup task
    await custom_ws_limiter.startup()

    try:
        while True:
            data = await websocket.receive_json()

            # Use custom rate limiter
            is_allowed, metadata = await custom_ws_limiter.check_message(
                websocket=websocket,
                endpoint="/ws/high-frequency",
            )

            if not is_allowed:
                await websocket.send_json({
                    "type": "rate_limit_exceeded",
                    "limit": metadata["limit"],
                    "retry_after": metadata["retry_after"],
                    "message": f"Rate limit exceeded. Try again in {metadata['retry_after']}s"
                })
                continue

            # Send rate limit info with response
            await websocket.send_json({
                "type": "response",
                "data": {"processed": True},
                "rate_limit": {
                    "limit": metadata["limit"],
                    "remaining": metadata["remaining"],
                    "reset": metadata["reset"],
                }
            })

    except WebSocketDisconnect:
        pass
    finally:
        await custom_ws_limiter.shutdown()
```

### Integration with Existing Handler

Here's how to add rate limiting to the existing MCTS stream handler:

```python
from enterprise_ui.backend.middleware.rate_limiting import check_websocket_rate_limit

class MCTSStreamHandler:
    async def handle_connection(self, websocket: WebSocket, symbol: str, token: str | None = None):
        # ... existing connection setup code ...

        try:
            # Message handling loop
            while True:
                try:
                    # Receive message from client
                    data = await websocket.receive_json()

                    # ✨ ADD RATE LIMITING HERE
                    if not await check_websocket_rate_limit(websocket, f"/ws/mcts/{symbol}"):
                        error_msg = create_message(
                            "rate_limit_exceeded",
                            {
                                "error": "Too many messages",
                                "message": "Please slow down your request rate",
                            }
                        )
                        await self.connection_manager.send_personal_message(
                            connection_id, error_msg
                        )
                        continue  # Skip processing this message

                    # Process message normally
                    await self._handle_client_message(connection_id, symbol, data)

                except WebSocketDisconnect:
                    break
                except Exception as e:
                    await handle_websocket_errors(websocket, connection_id, e)
        finally:
            await self.connection_manager.disconnect(connection_id)
```

## Custom Rate Limiting Logic

### Per-User Rate Limiting

```python
from enterprise_ui.backend.middleware.rate_limiting import SlidingWindowRateLimiter, RateLimitConfig

# Create a custom rate limiter for per-user limits
user_rate_limiter = SlidingWindowRateLimiter()

async def check_user_rate_limit(user_id: str, endpoint: str) -> bool:
    """Check rate limit for a specific user."""
    config = RateLimitConfig(
        requests_per_window=100,  # 100 requests per user
        window_seconds=60,
    )

    is_allowed, metadata = await user_rate_limiter.is_allowed(
        client_id=f"user:{user_id}",
        config=config,
        endpoint=endpoint,
    )

    return is_allowed
```

### Multi-Tier Rate Limiting

```python
from enterprise_ui.backend.middleware.rate_limiting import RateLimitConfig

# Different limits for different user tiers
RATE_LIMITS = {
    "free": RateLimitConfig(requests_per_window=10, window_seconds=60),
    "pro": RateLimitConfig(requests_per_window=100, window_seconds=60),
    "enterprise": RateLimitConfig(requests_per_window=1000, window_seconds=60),
}

async def check_tiered_rate_limit(user_id: str, tier: str, endpoint: str) -> tuple[bool, dict]:
    """Check rate limit based on user tier."""
    config = RATE_LIMITS.get(tier, RATE_LIMITS["free"])

    return await user_rate_limiter.is_allowed(
        client_id=f"user:{user_id}",
        config=config,
        endpoint=endpoint,
    )
```

## Monitoring and Statistics

```python
from enterprise_ui.backend.middleware.rate_limiting import websocket_rate_limiter

# Get rate limiter statistics
@app.get("/admin/rate-limit-stats")
async def get_rate_limit_stats():
    stats = await websocket_rate_limiter.rate_limiter.get_stats()
    return {
        "websocket": stats,
        "message": "Rate limiter statistics",
    }
```

## Testing Rate Limits

```python
import pytest
from fastapi.testclient import TestClient

def test_rate_limiting():
    """Test that rate limiting works correctly."""
    client = TestClient(app)

    # Make requests up to the limit
    for i in range(60):
        response = client.get("/api/v1/portfolio/summary")
        assert response.status_code == 200
        assert "X-RateLimit-Limit" in response.headers

    # 61st request should be rate limited
    response = client.get("/api/v1/portfolio/summary")
    assert response.status_code == 429
    assert "retry_after" in response.json()

def test_trading_endpoint_stricter_limit():
    """Test that trading endpoints have stricter limits."""
    client = TestClient(app)

    # Trading endpoints limited to 10 req/min
    for i in range(10):
        response = client.post("/api/v1/trading/execute", json={...})
        assert response.status_code in [200, 201]

    # 11th request should be rate limited
    response = client.post("/api/v1/trading/execute", json={...})
    assert response.status_code == 429
```

## Upgrading to Redis Backend

The current implementation uses in-memory storage. To upgrade to Redis for distributed rate limiting:

```python
# Future implementation (not yet available)
from enterprise_ui.backend.middleware.rate_limiting import RedisRateLimiter

redis_limiter = RedisRateLimiter(
    redis_url="redis://localhost:6379",
    key_prefix="rate_limit:",
)

# Use the same API as the in-memory version
is_allowed, metadata = await redis_limiter.is_allowed(
    client_id=client_ip,
    config=config,
    endpoint=endpoint,
)
```

## Best Practices

1. **Apply rate limiting early**: Add rate limiting middleware before logging middleware to reject requests quickly

2. **Use appropriate limits**:
   - Public endpoints: 60-100 req/min
   - Trading/write operations: 10-20 req/min
   - WebSocket messages: 60-120 msg/min

3. **Provide clear feedback**: Always include `retry_after` in error messages

4. **Monitor rate limits**: Track 429 responses to identify potential abuse or need for limit adjustments

5. **Exclude health checks**: Don't rate limit `/health` and `/metrics` endpoints

6. **Use connection pooling**: For WebSockets, limit messages per connection, not per IP

7. **Consider user tiers**: Implement different limits for different user subscription levels

8. **Handle burst traffic**: The `burst_multiplier` allows temporary spikes (default 1.5x)

9. **Clean up resources**: Always start/stop cleanup tasks in application lifecycle events

10. **Test thoroughly**: Include rate limiting tests in your test suite
