# Development Guide

Complete guide for developing, testing, and deploying the Reasoning Trading Enterprise UI.

## Table of Contents

- [Local Development Setup](#local-development-setup)
- [Project Structure](#project-structure)
- [Code Conventions](#code-conventions)
- [Development Workflow](#development-workflow)
- [Testing Strategy](#testing-strategy)
- [Debugging](#debugging)
- [API Development](#api-development)
- [Frontend Development](#frontend-development)
- [Database Management](#database-management)
- [Deployment Process](#deployment-process)
- [Troubleshooting](#troubleshooting)

## Local Development Setup

### Prerequisites

**Required:**
- Python 3.11+ with pip
- Node.js 18+ with npm
- Git
- Redis 7.0+ (optional but recommended)

**Optional:**
- Docker & Docker Compose (for containerized development)
- PostgreSQL (for production-like database)

### Initial Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/ianshank/Reasoning-Trading.git
   cd Reasoning-Trading/enterprise_ui
   ```

2. **Install Python dependencies:**
   ```bash
   cd ..
   pip install -e ".[dev,webui]"
   ```

3. **Install frontend dependencies:**
   ```bash
   cd enterprise_ui/frontend
   npm install
   ```

4. **Setup environment:**
   ```bash
   cd ..
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Start Redis (if installed):**
   ```bash
   # macOS
   brew services start redis

   # Linux
   sudo systemctl start redis

   # Or run in foreground
   redis-server
   ```

6. **Create necessary directories:**
   ```bash
   mkdir -p logs data
   ```

### Quick Start

**Option 1: Using the startup script (recommended)**
```bash
./scripts/dev.sh
```

**Option 2: Manual startup**
```bash
# Terminal 1 - Backend
cd enterprise_ui
python -m enterprise_ui.backend.main

# Terminal 2 - Frontend
cd enterprise_ui/frontend
npm run dev
```

### Access the Application

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Project Structure

```
enterprise_ui/
├── backend/                    # FastAPI backend
│   ├── api/                   # API endpoints
│   │   ├── v1/               # API v1 routes
│   │   │   ├── endpoints/    # REST endpoints
│   │   │   └── router.py     # Main router
│   │   └── websockets/       # WebSocket handlers
│   │       ├── handlers.py   # Connection manager
│   │       ├── router.py     # WebSocket router
│   │       └── *_stream.py   # Stream handlers
│   ├── core/                 # Core utilities
│   │   ├── logging.py        # Logging setup
│   │   └── debug.py          # Debug utilities
│   ├── middleware/           # Custom middleware
│   ├── models/              # Pydantic models
│   │   ├── requests.py      # Request models
│   │   ├── responses.py     # Response models
│   │   └── websocket.py     # WebSocket models
│   ├── services/            # Business logic
│   │   ├── trading_service.py
│   │   ├── mcts_service.py
│   │   ├── portfolio_service.py
│   │   ├── analytics_service.py
│   │   └── cache_service.py
│   ├── tests/               # Backend tests
│   │   ├── unit/           # Unit tests
│   │   ├── integration/    # Integration tests
│   │   └── conftest.py     # Pytest fixtures
│   ├── config.py           # Configuration
│   ├── dependencies.py     # Dependency injection
│   └── main.py            # Application entry
│
├── frontend/                  # React frontend
│   ├── public/               # Static assets
│   ├── src/
│   │   ├── components/      # React components
│   │   │   ├── layout/     # Layout components
│   │   │   ├── features/   # Feature components
│   │   │   └── ui/        # UI components
│   │   ├── hooks/          # Custom hooks
│   │   ├── lib/            # Utilities
│   │   ├── services/       # API services
│   │   ├── stores/         # Zustand stores
│   │   ├── types/          # TypeScript types
│   │   ├── App.tsx         # Main app component
│   │   └── main.tsx        # Entry point
│   ├── tests/              # Frontend tests
│   ├── package.json        # NPM dependencies
│   ├── tsconfig.json       # TypeScript config
│   ├── vite.config.ts      # Vite config
│   └── tailwind.config.js  # Tailwind config
│
├── scripts/                   # Utility scripts
│   ├── dev.sh                # Development startup
│   └── test.sh               # Test runner
│
├── .env.example              # Environment template
├── docker-compose.yml        # Docker orchestration
├── Dockerfile.backend        # Backend container
├── Dockerfile.frontend       # Frontend container
├── nginx.conf                # Nginx configuration
├── README.md                 # Main documentation
├── ARCHITECTURE.md           # Architecture docs
└── DEVELOPMENT.md            # This file
```

## Code Conventions

### Python (Backend)

**Style Guide:** PEP 8 with Ruff linting

```python
# Good: Type hints, docstrings, async/await
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status

router = APIRouter(prefix="/trading", tags=["trading"])

@router.post("/analyze", response_model=TradingAnalysis)
async def analyze_trading_opportunity(
    request: TradingRequest,
    service: TradingService = Depends(get_trading_service),
) -> TradingAnalysis:
    """
    Analyze a trading opportunity using MCTS.

    Args:
        request: Trading analysis parameters
        service: Injected trading service

    Returns:
        Analysis results with recommended actions

    Raises:
        HTTPException: If analysis fails
    """
    try:
        result = await service.analyze(request.symbol, request.timeframe)
        return result
    except Exception as e:
        logger.error("analysis_failed", symbol=request.symbol, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}",
        )
```

**Naming Conventions:**
- Classes: `PascalCase` (e.g., `TradingService`)
- Functions/methods: `snake_case` (e.g., `get_portfolio_summary`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `MAX_RETRIES`)
- Private: `_leading_underscore` (e.g., `_internal_method`)

**Imports:**
```python
# Standard library
from typing import Optional
import asyncio

# Third-party
from fastapi import FastAPI
from pydantic import BaseModel

# Local
from enterprise_ui.backend.config import get_backend_settings
from enterprise_ui.backend.services import TradingService
```

### TypeScript (Frontend)

**Style Guide:** Airbnb TypeScript guide

```typescript
// Good: Interfaces, type safety, async/await
interface TradingAnalysis {
  symbol: string;
  recommendation: 'buy' | 'sell' | 'hold';
  confidence: number;
  reasoning: string;
}

export const useTradingAnalysis = (symbol: string) => {
  return useQuery<TradingAnalysis>({
    queryKey: ['trading', 'analysis', symbol],
    queryFn: async () => {
      const response = await apiClient.post('/trading/analyze', { symbol });
      return response.data;
    },
    enabled: !!symbol,
    staleTime: 30000, // 30 seconds
  });
};
```

**Naming Conventions:**
- Components: `PascalCase` (e.g., `TradingDashboard`)
- Hooks: `camelCase` with `use` prefix (e.g., `useTradingData`)
- Utilities: `camelCase` (e.g., `formatCurrency`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `API_BASE_URL`)
- Types/Interfaces: `PascalCase` (e.g., `Portfolio`)

**File Organization:**
```typescript
// Component file structure
import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';

// Types
interface Props {
  symbol: string;
  onAnalyze: (result: Analysis) => void;
}

// Component
export const TradingAnalyzer: React.FC<Props> = ({ symbol, onAnalyze }) => {
  // Hooks
  const { data, isLoading, error } = useTradingAnalysis(symbol);

  // Event handlers
  const handleAnalyze = () => {
    if (data) {
      onAnalyze(data);
    }
  };

  // Render
  return (
    <div>
      {/* Component JSX */}
    </div>
  );
};
```

### Git Conventions

**Commit Messages:**
```bash
# Format: <type>(<scope>): <subject>

# Examples:
git commit -m "feat(mcts): add real-time search visualization"
git commit -m "fix(portfolio): correct P&L calculation"
git commit -m "docs(readme): update installation instructions"
git commit -m "refactor(api): simplify error handling"
git commit -m "test(trading): add integration tests for execution"
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `refactor`: Code refactoring
- `test`: Adding/updating tests
- `chore`: Maintenance tasks
- `perf`: Performance improvements
- `style`: Code style changes

**Branch Naming:**
```bash
feature/mcts-visualization
fix/portfolio-calculation
refactor/api-error-handling
docs/deployment-guide
```

## Development Workflow

### 1. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
```

### 2. Make Changes

Follow code conventions and write tests for new features.

### 3. Run Tests

```bash
# All tests
./scripts/test.sh

# Backend only
cd backend && pytest

# Frontend only
cd frontend && npm test

# With coverage
./scripts/test.sh --coverage
```

### 4. Lint and Format

**Backend:**
```bash
# Lint
ruff check .

# Fix automatically
ruff check --fix .

# Type checking
mypy enterprise_ui/backend
```

**Frontend:**
```bash
# Lint
npm run lint

# Fix automatically
npm run lint:fix

# Type checking
npm run type-check

# Format
npm run format
```

### 5. Commit Changes

```bash
git add .
git commit -m "feat(scope): description"
```

### 6. Push and Create PR

```bash
git push origin feature/your-feature-name
# Create pull request on GitHub
```

## Testing Strategy

### Backend Testing

**Test Structure:**
```
tests/
├── unit/                  # Fast, isolated tests
│   ├── test_services.py
│   ├── test_models.py
│   └── test_utils.py
├── integration/           # Tests with dependencies
│   ├── test_api.py
│   ├── test_websockets.py
│   └── test_cache.py
└── conftest.py           # Shared fixtures
```

**Writing Tests:**
```python
# tests/unit/test_trading_service.py
import pytest
from enterprise_ui.backend.services import TradingService

@pytest.fixture
def trading_service(mock_alpaca_client):
    """Create trading service with mocked dependencies."""
    return TradingService(client=mock_alpaca_client)

@pytest.mark.asyncio
async def test_analyze_trading_opportunity(trading_service):
    """Test trading analysis returns valid results."""
    # Arrange
    symbol = "AAPL"
    timeframe = "1D"

    # Act
    result = await trading_service.analyze(symbol, timeframe)

    # Assert
    assert result.symbol == symbol
    assert result.recommendation in ["buy", "sell", "hold"]
    assert 0 <= result.confidence <= 1
```

**Integration Tests:**
```python
# tests/integration/test_api.py
import pytest
from fastapi.testclient import TestClient
from enterprise_ui.backend.main import app

@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)

def test_trading_analysis_endpoint(client):
    """Test trading analysis API endpoint."""
    response = client.post(
        "/api/v1/trading/analyze",
        json={"symbol": "AAPL", "timeframe": "1D"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "symbol" in data
    assert "recommendation" in data
```

**Running Tests:**
```bash
# All tests
pytest

# Specific file
pytest tests/unit/test_trading_service.py

# Specific test
pytest tests/unit/test_trading_service.py::test_analyze_trading_opportunity

# With coverage
pytest --cov=enterprise_ui.backend --cov-report=html

# Verbose output
pytest -v

# Stop on first failure
pytest -x
```

### Frontend Testing

**Test Structure:**
```
tests/
├── unit/              # Component/hook tests
├── integration/       # Feature tests
└── setup.ts          # Test configuration
```

**Writing Tests:**
```typescript
// tests/unit/TradingAnalyzer.test.tsx
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { TradingAnalyzer } from '@/components/features/TradingAnalyzer';

describe('TradingAnalyzer', () => {
  it('renders symbol input', () => {
    render(<TradingAnalyzer onAnalyze={jest.fn()} />);
    expect(screen.getByLabelText(/symbol/i)).toBeInTheDocument();
  });

  it('calls onAnalyze when analyze button clicked', async () => {
    const onAnalyze = jest.fn();
    render(<TradingAnalyzer onAnalyze={onAnalyze} />);

    const input = screen.getByLabelText(/symbol/i);
    await userEvent.type(input, 'AAPL');

    const button = screen.getByRole('button', { name: /analyze/i });
    await userEvent.click(button);

    await waitFor(() => {
      expect(onAnalyze).toHaveBeenCalled();
    });
  });
});
```

**Running Tests:**
```bash
# All tests
npm test

# Watch mode
npm test -- --watch

# With UI
npm run test:ui

# Coverage
npm run test:coverage
```

## Debugging

### Backend Debugging

**Structured Logging:**
```python
from enterprise_ui.backend.core.logging import get_logger

logger = get_logger(__name__)

# Log levels
logger.debug("debug_message", extra_field="value")
logger.info("info_message", user_id=123)
logger.warning("warning_message", count=5)
logger.error("error_message", error=str(e), exc_info=True)
```

**Debug Mode:**
```python
# backend/core/debug.py
from enterprise_ui.backend.core.debug import enable_debug_mode

if settings.is_development:
    enable_debug_mode()  # Enables detailed error traces
```

**Interactive Debugging:**
```python
# Add breakpoint
import pdb; pdb.set_trace()

# Or use ipdb for better interface
import ipdb; ipdb.set_trace()
```

**Log Files:**
```bash
# Tail backend logs
tail -f logs/backend.log

# Filter by level
cat logs/backend.log | grep '"level":"error"'

# Pretty print JSON logs
cat logs/backend.log | jq '.'
```

### Frontend Debugging

**React DevTools:**
- Install React DevTools browser extension
- Inspect component tree and props
- Profile performance

**Browser Console:**
```typescript
// Debug logging
console.log('Data:', data);
console.table(array);
console.trace();

// Performance
console.time('operation');
// ... code ...
console.timeEnd('operation');
```

**Network Debugging:**
- Open browser DevTools (F12)
- Network tab for API calls
- WebSocket frames in WS tab
- Check request/response payloads

**Source Maps:**
Vite automatically generates source maps in development for debugging TypeScript.

## API Development

### Creating a New Endpoint

1. **Define models:**
```python
# backend/models/requests.py
class NewFeatureRequest(BaseModel):
    param1: str
    param2: int = Field(ge=0, le=100)

# backend/models/responses.py
class NewFeatureResponse(BaseModel):
    result: str
    metadata: dict
```

2. **Create endpoint:**
```python
# backend/api/v1/endpoints/new_feature.py
from fastapi import APIRouter, Depends
from enterprise_ui.backend.models import NewFeatureRequest, NewFeatureResponse

router = APIRouter(prefix="/new-feature", tags=["new-feature"])

@router.post("/action", response_model=NewFeatureResponse)
async def perform_action(request: NewFeatureRequest) -> NewFeatureResponse:
    # Implementation
    return NewFeatureResponse(result="success", metadata={})
```

3. **Register router:**
```python
# backend/api/v1/router.py
from enterprise_ui.backend.api.v1.endpoints import new_feature

api_router.include_router(new_feature.router)
```

4. **Add tests:**
```python
# backend/tests/integration/test_new_feature.py
def test_new_feature_endpoint(client):
    response = client.post(
        "/api/v1/new-feature/action",
        json={"param1": "value", "param2": 50},
    )
    assert response.status_code == 200
```

### Creating a WebSocket Handler

1. **Define models:**
```python
# backend/models/websocket.py
class NewStreamMessage(BaseModel):
    type: Literal["update", "error"]
    data: dict
```

2. **Create handler:**
```python
# backend/api/websockets/new_stream.py
from fastapi import WebSocket
from enterprise_ui.backend.api.websockets.handlers import BaseStreamHandler

class NewStreamHandler(BaseStreamHandler):
    async def handle_connection(self, websocket: WebSocket):
        await self.manager.connect(websocket, room="new_stream")
        try:
            while True:
                message = await websocket.receive_json()
                # Handle message
                await self.send_update(websocket, {"type": "update", "data": {}})
        except WebSocketDisconnect:
            self.manager.disconnect(websocket)
```

3. **Register route:**
```python
# backend/api/websockets/router.py
@websocket_router.websocket("/new-stream")
async def new_stream_websocket(websocket: WebSocket):
    await new_stream_handler.handle_connection(websocket)
```

## Frontend Development

### Creating a New Component

```typescript
// src/components/features/NewFeature.tsx
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card, Button } from '@/components/ui';

interface NewFeatureProps {
  param: string;
}

export const NewFeature: React.FC<NewFeatureProps> = ({ param }) => {
  const [value, setValue] = useState('');

  const { data, isLoading, error } = useQuery({
    queryKey: ['new-feature', param],
    queryFn: async () => {
      const response = await fetch(`/api/v1/new-feature/${param}`);
      return response.json();
    },
  });

  if (isLoading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;

  return (
    <Card>
      <h2>New Feature</h2>
      <p>{data.result}</p>
    </Card>
  );
};
```

### Creating a Custom Hook

```typescript
// src/hooks/useNewFeature.ts
import { useQuery, useMutation } from '@tanstack/react-query';
import { apiClient } from '@/lib/api';

export const useNewFeature = (param: string) => {
  const query = useQuery({
    queryKey: ['new-feature', param],
    queryFn: () => apiClient.get(`/new-feature/${param}`),
  });

  const mutation = useMutation({
    mutationFn: (data: NewFeatureData) =>
      apiClient.post('/new-feature/action', data),
    onSuccess: () => {
      queryClient.invalidateQueries(['new-feature']);
    },
  });

  return { ...query, performAction: mutation.mutate };
};
```

## Database Management

### Migrations (SQLAlchemy)

```bash
# Create migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

### Database Console

**SQLite:**
```bash
sqlite3 data/enterprise_ui.db
.tables
.schema tablename
SELECT * FROM tablename;
```

**PostgreSQL:**
```bash
psql reasoning_trading
\dt
\d tablename
SELECT * FROM tablename;
```

## Deployment Process

### Development Deployment

```bash
./scripts/dev.sh
```

### Docker Deployment

1. **Build images:**
```bash
docker-compose build
```

2. **Start services:**
```bash
docker-compose up -d
```

3. **View logs:**
```bash
docker-compose logs -f
```

4. **Stop services:**
```bash
docker-compose down
```

### Production Deployment

1. **Set environment to production:**
```bash
export ENVIRONMENT=production
```

2. **Update .env with production values:**
   - Strong JWT secret
   - Production CORS origins
   - Secure Redis password
   - Production database URL

3. **Build and deploy:**
```bash
docker-compose -f docker-compose.yml up -d --build
```

4. **Monitor:**
```bash
docker-compose logs -f
curl http://localhost/health
```

## Troubleshooting

### Backend Won't Start

**Problem:** ImportError or module not found

**Solution:**
```bash
pip install -e ".[dev,webui]"
```

**Problem:** Redis connection error

**Solution:**
```bash
# Check Redis is running
redis-cli ping

# Or disable Redis temporarily
export REDIS_HOST=localhost
```

### Frontend Build Fails

**Problem:** TypeScript errors

**Solution:**
```bash
npm run type-check  # See errors
# Fix type issues
```

**Problem:** Module not found

**Solution:**
```bash
rm -rf node_modules package-lock.json
npm install
```

### WebSocket Connection Issues

**Problem:** WebSocket disconnects immediately

**Solution:**
- Check CORS settings in backend
- Verify WebSocket URL in frontend (.env)
- Check browser console for errors
- Verify Nginx WebSocket proxy config

### Tests Failing

**Problem:** Import errors in tests

**Solution:**
```bash
# Backend
export PYTHONPATH=/path/to/Reasoning-Trading:$PYTHONPATH

# Or install in editable mode
pip install -e .
```

**Problem:** Async test errors

**Solution:**
```python
# Ensure pytest-asyncio is installed
pip install pytest-asyncio

# Use @pytest.mark.asyncio decorator
@pytest.mark.asyncio
async def test_async_function():
    result = await async_operation()
    assert result
```

### Performance Issues

**Problem:** Slow API responses

**Solution:**
- Check Redis connection
- Enable query caching
- Profile slow endpoints
- Add database indexes

**Problem:** High memory usage

**Solution:**
- Reduce worker count
- Check for memory leaks
- Monitor with `docker stats`

## Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev/)
- [TanStack Query](https://tanstack.com/query/latest)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)

## Getting Help

- Check [README.md](README.md) for quick start
- See [ARCHITECTURE.md](ARCHITECTURE.md) for system design
- Review [LOGGING_DEBUG_GUIDE.md](LOGGING_DEBUG_GUIDE.md) for debugging
- Open GitHub issue for bugs or feature requests
