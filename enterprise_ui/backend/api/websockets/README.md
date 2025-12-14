# WebSocket Handlers for Real-Time Data Streaming

Comprehensive WebSocket implementation for real-time streaming of MCTS search progress, market data, trading decisions, and portfolio updates.

## Overview

This package provides a complete WebSocket infrastructure for the trading platform with the following features:

- **Connection Management**: Centralized connection lifecycle management with room-based subscriptions
- **MCTS Streaming**: Real-time MCTS search progress, node expansions, and results
- **Market Data**: Real-time price updates, indicators, and regime changes
- **Trading Decisions**: Real-time decision streaming and trade execution notifications
- **Portfolio Updates**: Real-time position, P&L, and risk updates

## Architecture

```
websockets/
├── __init__.py              # Package exports
├── handlers.py              # Core connection management
├── mcts_stream.py          # MCTS search streaming
├── market_stream.py        # Market data streaming
├── decision_stream.py      # Trading decision streaming
├── portfolio_stream.py     # Portfolio update streaming
├── router.py               # FastAPI WebSocket router
├── example_integration.py  # Integration examples
└── README.md               # This file
```

## Quick Start

### 1. Integration with FastAPI

```python
from fastapi import FastAPI
from enterprise_ui.backend.api.websockets import websocket_router

app = FastAPI()

# Include WebSocket router
app.include_router(websocket_router)

# Start heartbeat loop on startup
@app.on_event("startup")
async def startup():
    from enterprise_ui.backend.api.websockets.router import connection_manager
    asyncio.create_task(connection_manager.heartbeat_loop())
```

### 2. Client Connection (JavaScript/TypeScript)

```javascript
// Connect to MCTS stream
const ws = new WebSocket('ws://localhost:8000/ws/mcts/AAPL?token=your-token');

ws.onopen = () => {
    // Start a search
    ws.send(JSON.stringify({
        command: 'start_search',
        config: {
            iterations: 100,
            exploration: 1.4
        }
    }));
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Message type:', data.type);

    switch(data.type) {
        case 'iteration_update':
            console.log('Progress:', data.data.progress);
            break;
        case 'search_completed':
            console.log('Best action:', data.data.best_action);
            break;
    }
};
```

### 3. Server-Side Streaming

```python
from enterprise_ui.backend.api.websockets.router import mcts_handler

# Stream MCTS updates
await mcts_handler.stream_iteration_update(
    search_id="search-123",
    iteration=50,
    total_iterations=100,
    best_action="BUY",
    best_value=0.85
)
```

## WebSocket Endpoints

### `/ws/mcts/{symbol}`

Stream MCTS search progress for a trading symbol.

**Query Parameters:**
- `token` (optional): Authentication token

**Client Commands:**
- `start_search`: Start a new MCTS search
- `stop_search`: Stop an active search
- `update_config`: Update search configuration
- `get_status`: Get current search status

**Server Messages:**
- `connected`: Connection confirmation
- `search_started`: Search initialization
- `iteration_update`: Iteration progress
- `node_expansion`: Node expansion event
- `backpropagation`: Backpropagation update
- `search_completed`: Search completion
- `search_error`: Error notification
- `ping`: Heartbeat

**Example:**
```javascript
ws.send(JSON.stringify({
    command: 'start_search',
    config: {
        iterations: 100,
        exploration: 1.4,
        max_depth: 10
    }
}));
```

### `/ws/market/{symbol}`

Stream real-time market data for a trading symbol.

**Query Parameters:**
- `token` (optional): Authentication token

**Client Commands:**
- `subscribe`: Subscribe to additional symbols
- `unsubscribe`: Unsubscribe from symbols
- `get_subscriptions`: Get current subscriptions
- `get_snapshot`: Get current market snapshot

**Server Messages:**
- `connected`: Connection confirmation
- `price_update`: Real-time price update
- `indicator_update`: Technical indicator update
- `ohlcv_update`: OHLCV/candlestick data
- `orderbook_update`: Order book update
- `regime_change`: Market regime change
- `snapshot`: Market snapshot
- `ping`: Heartbeat

**Example:**
```javascript
ws.send(JSON.stringify({
    command: 'subscribe',
    symbols: ['MSFT', 'GOOGL']
}));
```

### `/ws/decisions`

Stream trading decisions and executions.

**Query Parameters:**
- `token` (optional): Authentication token

**Client Commands:**
- `get_recent`: Get recent decisions
- `get_decision`: Get specific decision
- `filter_by_symbol`: Filter decisions by symbol

**Server Messages:**
- `connected`: Connection confirmation with recent decisions
- `trading_decision`: New trading decision
- `trade_execution`: Trade execution notification
- `regime_triggered_decision`: Regime-triggered decision
- `trading_signal`: Trading signal
- `ping`: Heartbeat

**Example:**
```javascript
ws.send(JSON.stringify({
    command: 'get_recent',
    limit: 20
}));
```

### `/ws/portfolio`

Stream portfolio updates (requires authentication).

**Query Parameters:**
- `token` (required): Authentication token

**Client Commands:**
- `get_portfolio`: Get current portfolio
- `get_positions`: Get current positions
- `get_performance`: Get performance metrics
- `get_risk_metrics`: Get risk metrics

**Server Messages:**
- `connected`: Connection confirmation with current portfolio
- `position_update`: Position update
- `pnl_update`: P&L update
- `portfolio_summary`: Portfolio summary
- `trade_notification`: Trade execution
- `performance_update`: Performance metrics
- `risk_alert`: Risk alert
- `ping`: Heartbeat

**Example:**
```javascript
ws.send(JSON.stringify({
    command: 'get_portfolio'
}));
```

## Message Format

All messages follow a consistent format:

```json
{
    "type": "message_type",
    "data": {
        // Message-specific data
    },
    "timestamp": "2025-12-13T10:30:00.000Z",
    "metadata": {
        // Optional metadata
    }
}
```

## Connection Management

### Room-Based Subscriptions

Connections are organized into rooms for efficient broadcasting:

- **Symbol Rooms**: `market:{symbol}`, `mcts:{symbol}`
- **User Rooms**: `portfolio:{user_id}`
- **Global Rooms**: `decisions`

### Heartbeat/Keep-Alive

The connection manager automatically:
- Sends ping messages every 30 seconds
- Expects pong responses from clients
- Disconnects stale connections after 60 seconds

### Error Handling

All errors are sent in a consistent format:

```json
{
    "type": "error",
    "data": {
        "error": "Error message"
    },
    "timestamp": "2025-12-13T10:30:00.000Z"
}
```

## Server-Side API

### Streaming Data

Each handler provides methods for streaming data:

#### MCTS Handler

```python
from enterprise_ui.backend.api.websockets.router import mcts_handler

# Stream iteration update
await mcts_handler.stream_iteration_update(
    search_id="search-123",
    iteration=50,
    total_iterations=100,
    best_action="BUY",
    best_value=0.85
)

# Stream node expansion
await mcts_handler.stream_node_expansion(
    search_id="search-123",
    node_id="node-456",
    state={"price": 150.0},
    action="BUY",
    parent_id="node-123"
)

# Stream completion
await mcts_handler.stream_search_completion(
    search_id="search-123",
    best_action="BUY",
    best_value=0.95,
    total_iterations=100,
    duration_seconds=10.0
)
```

#### Market Handler

```python
from enterprise_ui.backend.api.websockets.router import market_handler

# Stream price update
await market_handler.stream_price_update(
    symbol="AAPL",
    price=150.0,
    volume=1000.0
)

# Stream indicator update
await market_handler.stream_indicator_update(
    symbol="AAPL",
    indicators={"rsi": 65.5, "macd": 1.2}
)

# Stream regime change
await market_handler.stream_regime_change(
    symbol="AAPL",
    old_regime="ranging",
    new_regime="bullish",
    confidence=0.92
)
```

#### Decision Handler

```python
from enterprise_ui.backend.api.websockets.router import decision_handler

# Stream trading decision
await decision_handler.stream_decision(
    decision_id="decision-123",
    symbol="AAPL",
    action="BUY",
    quantity=100.0,
    price=150.0,
    rationale="MCTS suggests strong upward movement",
    confidence=0.85
)

# Stream execution
await decision_handler.stream_execution(
    execution_id="exec-456",
    decision_id="decision-123",
    symbol="AAPL",
    action="BUY",
    quantity=100.0,
    price=150.05,
    status="filled"
)
```

#### Portfolio Handler

```python
from enterprise_ui.backend.api.websockets.router import portfolio_handler

# Stream position update
await portfolio_handler.stream_position_update(
    user_id="user-123",
    symbol="AAPL",
    quantity=100.0,
    entry_price=150.0,
    current_price=152.0,
    pnl=200.0,
    pnl_percent=1.33
)

# Stream P&L update
await portfolio_handler.stream_pnl_update(
    user_id="user-123",
    total_pnl=1500.0,
    daily_pnl=200.0,
    unrealized_pnl=200.0,
    realized_pnl=1300.0
)

# Stream risk alert
await portfolio_handler.stream_risk_alert(
    user_id="user-123",
    alert_type="drawdown",
    severity="warning",
    message="Portfolio drawdown exceeds 5%"
)
```

## Authentication

Authentication can be implemented via:

1. **Query Parameter**: Pass token in WebSocket URL
   ```
   ws://localhost:8000/ws/portfolio?token=your-jwt-token
   ```

2. **First Message**: Send authentication in first message
   ```javascript
   ws.send(JSON.stringify({
       type: 'auth',
       token: 'your-jwt-token'
   }));
   ```

Update the `authenticate_websocket()` function in `handlers.py` to implement your authentication logic.

## Monitoring

### Health Check

```bash
curl http://localhost:8000/ws/health
```

Response:
```json
{
    "status": "healthy",
    "active_connections": 15,
    "active_rooms": 8,
    "handlers": {
        "mcts": "active",
        "market": "active",
        "decisions": "active",
        "portfolio": "active"
    }
}
```

### Statistics

```bash
curl http://localhost:8000/ws/stats
```

Response:
```json
{
    "connections": {
        "total": 15,
        "by_type": {
            "mcts": 3,
            "market": 5,
            "decision": 4,
            "portfolio": 3
        }
    },
    "rooms": {
        "total": 8,
        "active": ["market:AAPL", "mcts:MSFT", ...]
    },
    "market": {
        "subscribed_symbols": ["AAPL", "MSFT", "GOOGL"],
        "total_subscriptions": 12
    },
    "mcts": {
        "active_searches": 2
    },
    "decisions": {
        "cached_decisions": 45
    }
}
```

## Best Practices

1. **Error Handling**: Always handle connection errors and reconnect logic on the client
2. **Heartbeat**: Respond to ping messages with pong to maintain connection
3. **Authentication**: Use secure tokens and validate on server-side
4. **Rate Limiting**: Implement rate limiting for high-frequency updates
5. **Graceful Shutdown**: Always close connections properly
6. **Logging**: Monitor WebSocket logs for debugging and performance

## Testing

### Python Client Example

```python
import asyncio
import websockets
import json

async def test_mcts_stream():
    async with websockets.connect('ws://localhost:8000/ws/mcts/AAPL') as ws:
        # Receive welcome
        welcome = await ws.recv()
        print(json.loads(welcome))

        # Start search
        await ws.send(json.dumps({
            'command': 'start_search',
            'config': {'iterations': 100}
        }))

        # Receive updates
        while True:
            message = await ws.recv()
            data = json.loads(message)
            print(f"Type: {data['type']}")

            if data['type'] == 'search_completed':
                break

asyncio.run(test_mcts_stream())
```

### JavaScript/TypeScript Client Example

See `example_integration.py` for complete examples.

## Production Considerations

1. **Scaling**: Use Redis for pub/sub across multiple server instances
2. **Load Balancing**: Configure sticky sessions for WebSocket connections
3. **Rate Limiting**: Implement per-connection rate limits
4. **Monitoring**: Add metrics for connection count, message throughput, latency
5. **Security**: Implement proper authentication and authorization
6. **CORS**: Configure CORS appropriately for your deployment

## Troubleshooting

### Connection Drops

- Check heartbeat configuration
- Verify network stability
- Check server logs for errors

### High Latency

- Monitor message queue sizes
- Check server CPU/memory usage
- Consider implementing message throttling

### Authentication Failures

- Verify token format and expiration
- Check authentication logic in `handlers.py`
- Review server logs for auth errors

## License

Part of the Reasoning-Trading platform.
