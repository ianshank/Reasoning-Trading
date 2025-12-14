# WebSocket Quick Reference Card

## Server-Side Usage

### Import Handlers
```python
from enterprise_ui.backend.api.websockets.router import (
    mcts_handler,
    market_handler,
    decision_handler,
    portfolio_handler,
    connection_manager,
)
```

### Stream MCTS Updates
```python
# Iteration update
await mcts_handler.stream_iteration_update(
    search_id="search-123",
    iteration=50,
    total_iterations=100,
    best_action="BUY",
    best_value=0.85
)

# Search completion
await mcts_handler.stream_search_completion(
    search_id="search-123",
    best_action="BUY",
    best_value=0.95,
    total_iterations=100,
    duration_seconds=10.0
)
```

### Stream Market Data
```python
# Price update
await market_handler.stream_price_update(
    symbol="AAPL",
    price=150.0,
    volume=1000.0
)

# Regime change
await market_handler.stream_regime_change(
    symbol="AAPL",
    old_regime="ranging",
    new_regime="bullish",
    confidence=0.92
)
```

### Stream Trading Decisions
```python
# Trading decision
await decision_handler.stream_decision(
    decision_id="decision-123",
    symbol="AAPL",
    action="BUY",
    quantity=100.0,
    price=150.0,
    rationale="Strong buy signal",
    confidence=0.85
)

# Execution
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

### Stream Portfolio Updates
```python
# Position update
await portfolio_handler.stream_position_update(
    user_id="user-123",
    symbol="AAPL",
    quantity=100.0,
    entry_price=150.0,
    current_price=152.0,
    pnl=200.0,
    pnl_percent=1.33
)

# Risk alert
await portfolio_handler.stream_risk_alert(
    user_id="user-123",
    alert_type="drawdown",
    severity="warning",
    message="Portfolio drawdown exceeds 5%"
)
```

## Client-Side Usage (JavaScript/TypeScript)

### Basic Connection
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/mcts/AAPL?token=your-token');

ws.onopen = () => console.log('Connected');

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Type:', data.type);
    console.log('Data:', data.data);
};

ws.onerror = (error) => console.error('Error:', error);
ws.onclose = () => console.log('Disconnected');
```

### Send Commands
```javascript
// MCTS: Start search
ws.send(JSON.stringify({
    command: 'start_search',
    config: { iterations: 100 }
}));

// Market: Subscribe to symbols
ws.send(JSON.stringify({
    command: 'subscribe',
    symbols: ['MSFT', 'GOOGL']
}));

// Decisions: Get recent
ws.send(JSON.stringify({
    command: 'get_recent',
    limit: 20
}));

// Portfolio: Get portfolio
ws.send(JSON.stringify({
    command: 'get_portfolio'
}));
```

### Using TypeScript Client
```typescript
import { MCTSWebSocketClient } from './client_example';

const client = new MCTSWebSocketClient('AAPL', 'your-token');

client.on('iteration_update', (data) => {
    console.log(`Progress: ${data.progress * 100}%`);
});

await client.connect();
client.startSearch({ iterations: 100 });
```

### React Hook
```typescript
function MyComponent() {
    const { isConnected, searchProgress, bestAction, startSearch } =
        useMCTSWebSocket('AAPL', 'your-token');

    return (
        <div>
            <p>Connected: {isConnected}</p>
            <p>Progress: {searchProgress * 100}%</p>
            <p>Best Action: {bestAction}</p>
            <button onClick={() => startSearch({ iterations: 100 })}>
                Start Search
            </button>
        </div>
    );
}
```

## FastAPI Integration

### Add to App
```python
from fastapi import FastAPI
from enterprise_ui.backend.api.websockets import websocket_router

app = FastAPI()
app.include_router(websocket_router)
```

### Add Startup Task
```python
import asyncio
from enterprise_ui.backend.api.websockets.router import connection_manager

@app.on_event("startup")
async def startup():
    asyncio.create_task(connection_manager.heartbeat_loop())
```

### Add Shutdown Handler
```python
@app.on_event("shutdown")
async def shutdown():
    await connection_manager.shutdown()
```

## Endpoints

- **MCTS**: `ws://localhost:8000/ws/mcts/{symbol}`
- **Market**: `ws://localhost:8000/ws/market/{symbol}`
- **Decisions**: `ws://localhost:8000/ws/decisions`
- **Portfolio**: `ws://localhost:8000/ws/portfolio` (requires auth)
- **Health**: `http://localhost:8000/ws/health`
- **Stats**: `http://localhost:8000/ws/stats`

## Message Types

### MCTS Messages
- `connected`, `search_started`, `iteration_update`, `node_expansion`, `backpropagation`, `search_completed`, `search_error`, `ping`

### Market Messages
- `connected`, `price_update`, `indicator_update`, `ohlcv_update`, `orderbook_update`, `regime_change`, `snapshot`, `ping`

### Decision Messages
- `connected`, `trading_decision`, `trade_execution`, `regime_triggered_decision`, `trading_signal`, `recent_decisions`, `ping`

### Portfolio Messages
- `connected`, `position_update`, `pnl_update`, `portfolio_summary`, `trade_notification`, `risk_alert`, `performance_update`, `ping`

## Monitoring

### Check Health
```bash
curl http://localhost:8000/ws/health
```

### Get Statistics
```bash
curl http://localhost:8000/ws/stats
```

## Connection Manager API

```python
# Get connection count
count = connection_manager.get_connection_count()

# Get room connections
connections = connection_manager.get_room_connections("market:AAPL")

# Get user connections
connections = connection_manager.get_user_connections("user-123")

# Broadcast to room
await connection_manager.broadcast_to_room("market:AAPL", message)

# Broadcast to user
await connection_manager.broadcast_to_user("user-123", message)

# Send personal message
await connection_manager.send_personal_message("conn-id", message)
```

## Testing

### Run Tests
```bash
pytest enterprise_ui/backend/api/websockets/test_websockets.py -v
```

### Test Connection (Python)
```python
import asyncio
import websockets
import json

async def test():
    async with websockets.connect('ws://localhost:8000/ws/mcts/AAPL') as ws:
        msg = await ws.recv()
        print(json.loads(msg))

asyncio.run(test())
```

## Common Patterns

### Workflow: Regime Change
```python
# 1. Detect regime change
await market_handler.stream_regime_change(...)

# 2. Make trading decision
await decision_handler.stream_regime_triggered_decision(...)

# 3. Update portfolio
await portfolio_handler.stream_trade_notification(...)
```

### Workflow: MCTS Search
```python
# 1. Start search (client sends command)
# 2. Stream iterations
for i in range(iterations):
    await mcts_handler.stream_iteration_update(...)

# 3. Stream completion
await mcts_handler.stream_search_completion(...)
```

### Periodic Updates
```python
async def periodic_portfolio_updates():
    while True:
        await portfolio_handler.stream_portfolio_summary(...)
        await asyncio.sleep(60)

asyncio.create_task(periodic_portfolio_updates())
```

## Error Handling

### Server-Side
```python
try:
    await handler.stream_something(...)
except Exception as e:
    logger.error("stream_error", error=str(e))
    await handler.stream_error(search_id, str(e))
```

### Client-Side
```javascript
ws.onerror = (error) => {
    console.error('WebSocket error:', error);
    // Implement reconnection logic
};

ws.onclose = () => {
    console.log('Connection closed, reconnecting...');
    setTimeout(() => connect(), 1000);
};
```

## Files

- `handlers.py` - Connection management
- `mcts_stream.py` - MCTS streaming
- `market_stream.py` - Market data streaming
- `decision_stream.py` - Decision streaming
- `portfolio_stream.py` - Portfolio streaming
- `router.py` - FastAPI router
- `example_integration.py` - Examples
- `client_example.ts` - Client library
- `test_websockets.py` - Tests
- `README.md` - Full documentation

## Support

For full documentation, see `README.md`.
For integration examples, see `example_integration.py`.
For client examples, see `client_example.ts`.
For implementation details, see `IMPLEMENTATION_SUMMARY.md`.
