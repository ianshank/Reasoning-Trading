# Enterprise UI Backend - FastAPI Implementation

Complete FastAPI backend for the Reasoning-Trading enterprise UI.

## Quick Start

```bash
# Install dependencies
pip install fastapi uvicorn pydantic pydantic-settings redis sqlalchemy aiosqlite asyncpg

# Set environment variables
export JWT_SECRET_KEY="$(openssl rand -hex 32)"
export ENVIRONMENT=development
export API_PORT=8000

# Run the server
python -m uvicorn enterprise_ui.backend.main:app --reload --host 0.0.0.0 --port 8000
```

## API Documentation

Once running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## Architecture

### Core Files

1. **config.py** - Backend configuration extending `reasoning_trading.config`
   - JWT authentication settings
   - Rate limiting configuration
   - CORS settings
   - WebSocket configuration
   - Database settings

2. **dependencies.py** - FastAPI dependency injection
   - Service singletons (MCTS coordinator, action space)
   - Database sessions
   - Redis client
   - Authentication dependencies

3. **main.py** - FastAPI application
   - Lifespan management (startup/shutdown)
   - Middleware setup (CORS, logging)
   - Exception handlers
   - Router inclusion

4. **api/v1/router.py** - Main API router
   - Aggregates all endpoint routers
   - `/api/v1/trading/*`
   - `/api/v1/mcts/*`
   - `/api/v1/portfolio/*`
   - `/api/v1/regime/*`
   - `/api/v1/analytics/*`
   - `/api/v1/system/*`

### Models

**Request Models** (`models/requests.py`):
- `TradingAnalysisRequest` - Multi-agent analysis
- `TradingDecisionRequest` - MCTS decision making
- `TradeExecutionRequest` - Trade execution
- `MCTSSearchRequest` - MCTS search
- `RiskCheckRequest` - Risk assessment
- `BatchTriggerRequest` - Batch operations
- `PortfolioQueryRequest` - Portfolio queries

**Response Models** (`models/responses.py`):
- `TradingAnalysisResponse` - Analysis results
- `TradingDecisionResponse` - Decision results
- `PortfolioStateResponse` - Portfolio state
- `RiskCheckResponse` - Risk assessment
- `HealthCheckResponse` - Health status

**WebSocket Models** (`models/websocket.py`):
- `WSMessage` - Base message structure
- `WSMessageType` - Message type enum
- Payload models for all message types
- Helper functions for creating messages

## Environment Variables

### Backend Settings

```bash
# Server
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=true
ENVIRONMENT=development

# JWT Authentication
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# CORS
CORS_ENABLED=true
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:7860

# Redis
REDIS_URL=redis://localhost:6379/0

# Database
DATABASE_URL=sqlite:///./data/enterprise_ui.db
# Or PostgreSQL:
# DATABASE_URL=postgresql+asyncpg://user:pass@localhost/dbname
```

### Core Trading Settings

All `reasoning_trading` settings are also available:

```bash
# Alpaca Trading
ALPACA_API_KEY=your-alpaca-key
ALPACA_SECRET_KEY=your-alpaca-secret
ALPACA_BASE_URL=https://paper-api.alpaca.markets
ALPACA_TRADING_MODE=paper

# LLM
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key

# Data APIs
FINNHUB_API_KEY=your-finnhub-key
FRED_API_KEY=your-fred-key

# MCTS
MCTS_MAX_SIMULATIONS=1000
MCTS_EXPLORATION_WEIGHT=1.414
MCTS_CONFIDENCE_THRESHOLD=0.85

# Risk Management
MAX_POSITION_SIZE_FRACTION=0.25
DEFAULT_STOP_LOSS_PERCENT=0.05
MAX_DAILY_LOSS_PERCENT=0.10
```

## Usage Examples

### Python Client

```python
import httpx

async with httpx.AsyncClient() as client:
    # Health check
    response = await client.get("http://localhost:8000/health")
    print(response.json())
    
    # Trading analysis
    response = await client.post(
        "http://localhost:8000/api/v1/analysis/trading",
        json={
            "symbol": "AAPL",
            "include_news": True,
            "include_social": True,
            "enable_debate": True
        }
    )
    analysis = response.json()
    print(f"Consensus: {analysis['consensus_score']}")
    
    # Trading decision
    response = await client.post(
        "http://localhost:8000/api/v1/analysis/decision",
        json={
            "symbol": "AAPL",
            "current_price": 150.25,
            "portfolio_value": 100000.0,
            "cash_balance": 50000.0,
            "risk_profile": "moderate",
            "max_simulations": 1000
        }
    )
    decision = response.json()
    print(f"Action: {decision['action']['direction']}")
    print(f"Confidence: {decision['action']['confidence']}")
```

### cURL Examples

```bash
# Health check
curl http://localhost:8000/health

# Trading analysis
curl -X POST http://localhost:8000/api/v1/analysis/trading \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "AAPL",
    "include_news": true,
    "enable_debate": true
  }'

# Portfolio state
curl -X POST http://localhost:8000/api/v1/portfolio/state \
  -H "Content-Type: application/json" \
  -d '{
    "include_positions": true,
    "calculate_metrics": true
  }'
```

## Key Features

### Configuration Management
- Extends core `reasoning_trading.config.Settings`
- Environment variable based configuration
- No hardcoded values
- Cached singletons for performance
- Type-safe with Pydantic v2

### Dependency Injection
- Singleton service instances
- Database connection pooling
- Redis client management
- JWT authentication
- Type-safe dependencies

### Logging
- Structured logging with `structlog`
- Request/response logging
- Performance tracking
- Error tracking with stack traces
- Request ID correlation

### API Documentation
- Auto-generated OpenAPI schema
- Swagger UI and ReDoc
- All models have examples
- Comprehensive descriptions

### Security
- JWT authentication
- Rate limiting
- CORS configuration
- Optional authentication for public endpoints
- Proper error handling

### WebSocket Support
- Real-time price updates
- Portfolio change notifications
- Analysis progress updates
- MCTS search progress
- Connection heartbeat

## Development

### Running Tests

```bash
pytest enterprise_ui/backend/tests/
```

### Code Quality

```bash
# Type checking
mypy enterprise_ui/backend/

# Linting
ruff check enterprise_ui/backend/

# Formatting
ruff format enterprise_ui/backend/
```

### Project Structure

```
enterprise_ui/backend/
├── __init__.py              # Package initializer
├── config.py                # Backend configuration
├── dependencies.py          # Dependency injection
├── main.py                  # FastAPI application
├── api/
│   └── v1/
│       ├── router.py        # Main router
│       └── endpoints/       # Endpoint implementations
├── models/
│   ├── requests.py          # Request models
│   ├── responses.py         # Response models
│   └── websocket.py         # WebSocket models
├── core/
│   └── logging.py           # Logging configuration
└── middleware/
    └── logging_middleware.py # HTTP logging
```

## Integration

### With Core Trading System

The backend integrates seamlessly with the core `reasoning_trading` package:

```python
from reasoning_trading.agents.coordinator import MultiAgentTradingMCTS
from reasoning_trading.core.state import TradingState
from reasoning_trading.core.actions import ActionSpace

# These are available as dependencies in endpoints
coordinator = MultiAgentTradingMCTS()
action_space = ActionSpace()
```

### With Frontend

The backend exposes:
- REST API for trading operations
- WebSocket for real-time updates
- OpenAPI schema for client generation

Frontend clients can be auto-generated from the OpenAPI schema:

```bash
# Generate TypeScript client
npx openapi-typescript-codegen \
  --input http://localhost:8000/openapi.json \
  --output ./src/api-client
```

## Production Deployment

### Environment Setup

```bash
# Set production environment
export ENVIRONMENT=production

# Use secure JWT secret
export JWT_SECRET_KEY="$(openssl rand -hex 32)"

# Disable API docs in production
export API_DOCS_URL=
export API_REDOC_URL=

# Use production Redis
export REDIS_URL=redis://prod-redis:6379/0

# Use production database
export DATABASE_URL=postgresql+asyncpg://user:pass@prod-db/trading
```

### Running with Gunicorn

```bash
gunicorn enterprise_ui.backend.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 300
```

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "enterprise_ui.backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Support

For issues or questions:
1. Check the OpenAPI documentation at `/docs`
2. Review logs for detailed error messages
3. Check environment variable configuration
4. Verify API keys are properly set

## License

Same as parent Reasoning-Trading project.
