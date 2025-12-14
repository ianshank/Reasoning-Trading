# Enterprise UI Architecture

This document describes the architecture of the Reasoning Trading Enterprise UI system, including component design, data flow, integration points, and scalability considerations.

## Table of Contents

- [System Overview](#system-overview)
- [Architecture Diagram](#architecture-diagram)
- [Component Architecture](#component-architecture)
- [Data Flow](#data-flow)
- [Integration with Core](#integration-with-core)
- [State Management](#state-management)
- [Communication Patterns](#communication-patterns)
- [Security Architecture](#security-architecture)
- [Scalability & Performance](#scalability--performance)
- [Deployment Architecture](#deployment-architecture)

## System Overview

The Enterprise UI is a full-stack web application that provides a real-time interface for the Reasoning Trading multi-agent trading system. It consists of:

- **Frontend**: React-based SPA with real-time visualization
- **Backend**: FastAPI server with REST and WebSocket APIs
- **Cache Layer**: Redis for caching and pub/sub messaging
- **Reverse Proxy**: Nginx for routing and load balancing
- **Core Integration**: Deep integration with `reasoning_trading` package

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Client Browser                                   │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                      React Application                            │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │  │
│  │  │  Zustand │  │  React   │  │  React   │  │   WebSocket      │  │  │
│  │  │  Global  │  │  Query   │  │  Router  │  │   Client         │  │  │
│  │  │  State   │  │  (API)   │  │          │  │                  │  │  │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────────────┘  │  │
│  │       │             │              │                 │            │  │
│  └───────┼─────────────┼──────────────┼─────────────────┼────────────┘  │
│          │             │              │                 │               │
└──────────┼─────────────┼──────────────┼─────────────────┼───────────────┘
           │             │              │                 │
           │  HTTP/REST  │              │                 │  WebSocket
           └─────────────┴──────────────┴─────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          Nginx Reverse Proxy                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                  │
│  │   Static     │  │   API        │  │  WebSocket   │                  │
│  │   Files      │  │   Proxy      │  │  Upgrade     │                  │
│  └──────────────┘  └──────────────┘  └──────────────┘                  │
│         │                 │                   │                          │
│         │                 └───────┬───────────┘                          │
└─────────┼─────────────────────────┼──────────────────────────────────────┘
          │                         ▼
          │         ┌─────────────────────────────────┐
          │         │   FastAPI Backend Server        │
          │         │  ┌───────────────────────────┐  │
          │         │  │   Lifespan Manager        │  │
          │         │  │  (Startup/Shutdown)       │  │
          │         │  └───────────────────────────┘  │
          │         │  ┌───────────────────────────┐  │
          │         │  │   Middleware Stack        │  │
          │         │  │  - CORS                   │  │
          │         │  │  - Logging                │  │
          │         │  │  - Exception Handling     │  │
          │         │  └───────────────────────────┘  │
          │         │  ┌───────────────────────────┐  │
          │         │  │   API Routers             │  │
          │         │  │  ┌────────────────────┐   │  │
          │         │  │  │ REST Endpoints     │   │  │
          │         │  │  │ - Trading          │   │  │
          │         │  │  │ - MCTS             │   │  │
          │         │  │  │ - Portfolio        │   │  │
          │         │  │  │ - Regime           │   │  │
          │         │  │  │ - Analytics        │   │  │
          │         │  │  │ - System           │   │  │
          │         │  │  └────────────────────┘   │  │
          │         │  │  ┌────────────────────┐   │  │
          │         │  │  │ WebSocket Streams  │   │  │
          │         │  │  │ - MCTS Stream      │   │  │
          │         │  │  │ - Market Stream    │   │  │
          │         │  │  │ - Decision Stream  │   │  │
          │         │  │  │ - Portfolio Stream │   │  │
          │         │  │  └────────────────────┘   │  │
          │         │  └───────────────────────────┘  │
          │         │  ┌───────────────────────────┐  │
          │         │  │   Business Logic Layer    │  │
          │         │  │  - Services               │  │
          │         │  │  - Models                 │  │
          │         │  │  - Dependencies           │  │
          │         │  └───────────────────────────┘  │
          │         └──────────┬──────────────────────┘
          │                    │
          │         ┌──────────┼──────────┐
          │         │          │          │
          │         ▼          ▼          ▼
          │    ┌────────┐ ┌────────┐ ┌─────────┐
          │    │ Redis  │ │SQLite/ │ │ Reasoning│
          │    │ Cache  │ │Postgres│ │ Trading  │
          │    │        │ │   DB   │ │  Core    │
          │    └────────┘ └────────┘ └─────────┘
          │                               │
          │                               ▼
          │                    ┌──────────────────────┐
          │                    │  External Services   │
          │                    │  - Alpaca API        │
          │                    │  - OpenAI/Anthropic  │
          │                    │  - Finnhub           │
          │                    │  - LangSmith         │
          │                    └──────────────────────┘
          │
          ▼
    ┌──────────────┐
    │  Frontend    │
    │  Static      │
    │  Assets      │
    └──────────────┘
```

## Component Architecture

### Frontend Architecture

#### Component Hierarchy

```
App
├── DashboardLayout
│   ├── Header
│   │   ├── UserMenu
│   │   └── NotificationCenter
│   ├── Sidebar
│   │   └── Navigation
│   ├── MainContent
│   │   ├── Routes
│   │   │   ├── Dashboard (/)
│   │   │   │   ├── MarketOverview
│   │   │   │   ├── PortfolioSummary
│   │   │   │   ├── RecentDecisions
│   │   │   │   └── RegimeIndicator
│   │   │   ├── MCTS (/mcts)
│   │   │   │   ├── MCTSVisualizer
│   │   │   │   ├── SearchControls
│   │   │   │   └── SearchHistory
│   │   │   ├── Portfolio (/portfolio)
│   │   │   │   ├── PortfolioDashboard
│   │   │   │   ├── PositionsTable
│   │   │   │   ├── PerformanceChart
│   │   │   │   └── RiskMetrics
│   │   │   ├── Trading (/trading)
│   │   │   │   ├── TradingDecisions
│   │   │   │   ├── ExecutionHistory
│   │   │   │   └── TradingSignals
│   │   │   └── Analytics (/analytics)
│   │   │       ├── PerformanceAnalytics
│   │   │       ├── AttributionAnalysis
│   │   │       └── RiskAnalysis
│   │   └── ErrorBoundary
│   └── Footer
└── Providers
    ├── QueryClientProvider (TanStack Query)
    ├── RouterProvider (React Router)
    └── ThemeProvider
```

#### State Management Layers

1. **Server State** (TanStack Query)
   - API data caching
   - Automatic refetching
   - Optimistic updates
   - Request deduplication

2. **Global State** (Zustand)
   - User preferences
   - UI state (theme, sidebar)
   - WebSocket connection state
   - Real-time data streams

3. **Local State** (React useState/useReducer)
   - Form inputs
   - Component-specific UI state
   - Temporary data

### Backend Architecture

#### Layer Structure

```
┌─────────────────────────────────────────────┐
│         Presentation Layer (API)            │
│  - REST Endpoints (FastAPI routers)        │
│  - WebSocket Handlers                       │
│  - Request/Response Models (Pydantic)       │
└─────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────┐
│         Business Logic Layer                │
│  - Services (trading, MCTS, portfolio)      │
│  - Domain Models                            │
│  - Business Rules                           │
└─────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────┐
│         Data Access Layer                   │
│  - Cache Service (Redis)                    │
│  - Database Service (SQLAlchemy)            │
│  - External API Clients                     │
└─────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────┐
│         Core Integration Layer              │
│  - reasoning_trading package                │
│  - MCTS Engine                              │
│  - Multi-Agent System                       │
│  - Alpaca Trading Client                    │
└─────────────────────────────────────────────┘
```

#### Service Architecture

**TradingService**
- Analyzes trading opportunities
- Executes trades via Alpaca
- Manages trade history
- Integrates with MCTS for decision optimization

**MCTSService**
- Manages MCTS search sessions
- Streams search progress via WebSocket
- Caches search results
- Provides search analytics

**PortfolioService**
- Fetches portfolio data from Alpaca
- Calculates performance metrics
- Manages position tracking
- Streams real-time updates

**AnalyticsService**
- Computes performance analytics
- Attribution analysis
- Risk metrics calculation
- Historical analysis

**CacheService**
- Redis integration
- TTL-based caching
- Pub/sub for real-time updates
- Cache invalidation strategies

## Data Flow

### REST API Flow

```
Client Request
    │
    ▼
Nginx (Reverse Proxy)
    │
    ▼
FastAPI Middleware Stack
    │
    ├─► CORS Middleware
    ├─► Logging Middleware
    └─► Exception Handler
    │
    ▼
Router (Endpoint)
    │
    ▼
Pydantic Validation
    │
    ▼
Dependency Injection
    │
    ├─► Authentication
    ├─► Rate Limiting
    └─► Service Dependencies
    │
    ▼
Service Layer
    │
    ├─► Check Cache (Redis)
    │   └─► Cache Hit? Return
    │
    ├─► Core Integration
    │   └─► reasoning_trading
    │       ├─► MCTS Engine
    │       ├─► Multi-Agent
    │       └─► Alpaca API
    │
    └─► Update Cache
    │
    ▼
Response Model
    │
    ▼
JSON Response
    │
    ▼
Client
```

### WebSocket Flow

```
Client Connection
    │
    ▼
WebSocket Upgrade (Nginx)
    │
    ▼
WebSocket Handler
    │
    ├─► Validate Token (optional)
    ├─► Accept Connection
    └─► Register in ConnectionManager
    │
    ▼
Message Loop
    │
    ├─► Receive Client Message
    │   └─► Parse Command
    │       ├─► start_search
    │       ├─► subscribe
    │       ├─► get_portfolio
    │       └─► ...
    │
    ├─► Process Command
    │   └─► Call Service Layer
    │       └─► Core Integration
    │
    └─► Stream Updates
        │
        ├─► Generate Events
        │   ├─► MCTS iteration
        │   ├─► Price update
        │   ├─► Decision made
        │   └─► Portfolio change
        │
        ├─► Serialize to JSON
        │
        └─► Send to Client(s)
            ├─► Specific connection
            └─► Broadcast to room
```

### Real-time Update Flow

```
External Event
(Market data, Trade execution)
    │
    ▼
Core System Detection
    │
    ▼
Publish to Redis Channel
    │
    ▼
Backend Subscriber
    │
    ▼
ConnectionManager
    │
    ├─► Find relevant connections
    │   └─► By symbol, user, type
    │
    └─► Broadcast update
        │
        ▼
WebSocket Send
        │
        ▼
Client Receives
        │
        └─► Update UI State
```

## Integration with Core

### reasoning_trading Package Integration

The backend deeply integrates with the `reasoning_trading` package:

```python
# Service Layer Integration
from reasoning_trading.mcts import MCTSPlanner
from reasoning_trading.agents import AlpacaTradingAgent
from reasoning_trading.regime import RegimeDetector
from reasoning_trading.config import Settings as CoreSettings

class MCTSService:
    def __init__(self):
        self.core_settings = CoreSettings()
        self.planner = MCTSPlanner(config=self.core_settings.mcts)
        self.agent = AlpacaTradingAgent(config=self.core_settings.alpaca)

    async def start_search(self, symbol: str) -> SearchSession:
        # Use core MCTS engine
        result = await self.planner.search(symbol)
        # Stream progress via WebSocket
        # Cache results in Redis
        return result
```

### Integration Points

1. **Configuration Sharing**
   - Backend extends core configuration
   - Inherits all core trading settings
   - Adds UI-specific settings (JWT, CORS, etc.)

2. **Service Wrapping**
   - Backend services wrap core functionality
   - Add caching layer
   - Provide REST/WebSocket interface
   - Handle async orchestration

3. **Data Model Alignment**
   - Backend models extend core models
   - Consistent data structures
   - Type-safe integration

4. **Event Propagation**
   - Core system events → Backend events
   - Backend events → WebSocket streams
   - Real-time UI updates

## State Management

### Backend State

1. **Application State**
   - Settings (singleton, cached)
   - Service instances (dependency injection)
   - Connection manager (WebSocket connections)

2. **Session State**
   - Active MCTS searches
   - WebSocket subscriptions
   - Rate limit counters

3. **Persistent State**
   - Database (user data, history)
   - Redis cache (temporary data)
   - Core system state (reasoning_trading)

### Frontend State

1. **Server State (TanStack Query)**
   - Cached API responses
   - Query invalidation
   - Optimistic updates
   - Background refetching

2. **WebSocket State (Zustand)**
   - Connection status
   - Real-time data streams
   - Subscription management

3. **UI State (Zustand + Local)**
   - Theme preferences
   - Sidebar state
   - Active tab/route
   - Form values

## Communication Patterns

### Request-Response (REST)

**Use Cases:**
- One-time data fetching
- CRUD operations
- Synchronous operations

**Endpoints:**
- GET: Fetch data
- POST: Create/trigger action
- PUT/PATCH: Update
- DELETE: Remove

### Streaming (WebSocket)

**Use Cases:**
- Real-time updates
- Long-running operations (MCTS)
- Pub/sub patterns

**Patterns:**
- Command: Client → Server
- Event: Server → Client
- Broadcast: Server → Multiple clients
- Request-Response: Over WebSocket

### Pub/Sub (Redis)

**Use Cases:**
- Inter-service communication
- Event distribution
- Cache invalidation

**Channels:**
- `market:{symbol}` - Market data updates
- `decisions` - Trading decisions
- `portfolio:{user}` - Portfolio updates
- `mcts:{search_id}` - MCTS progress

## Security Architecture

### Authentication & Authorization

```
Client Request
    │
    ▼
JWT Token (Optional)
    │
    ├─► Extract from Authorization header
    ├─► Validate signature (JWT_SECRET_KEY)
    ├─► Check expiration
    └─► Extract user claims
    │
    ▼
Dependency Injection
    │
    └─► get_current_user()
    │
    ▼
Endpoint Handler
```

### Security Measures

1. **Transport Security**
   - HTTPS in production (TLS 1.2+)
   - WSS (WebSocket Secure)
   - HTTP Strict Transport Security (HSTS)

2. **API Security**
   - JWT token authentication
   - Rate limiting (60 req/min default)
   - CORS restrictions
   - Input validation (Pydantic)

3. **Data Security**
   - Secrets via environment variables
   - Never log sensitive data
   - Redis password protection
   - Database encryption at rest

4. **Application Security**
   - No hardcoded credentials
   - Parameterized queries (SQLAlchemy)
   - XSS protection headers
   - CSRF protection

## Scalability & Performance

### Horizontal Scaling

**Backend:**
```yaml
# Scale backend workers
docker-compose up -d --scale backend=4
```

**Stateless Design:**
- No server-side sessions
- JWT for authentication
- Redis for shared state

### Vertical Scaling

**Gunicorn Workers:**
```
workers = (2 x CPU cores) + 1
```

**Resource Limits:**
- Memory: ~200MB per worker
- CPU: Async I/O bound
- Connections: ~1000 per worker

### Caching Strategy

**Layers:**
1. Browser cache (static assets)
2. Redis cache (API data)
3. Application cache (in-memory)

**TTL Strategy:**
- Static data: 1 hour
- Market data: 30 seconds
- Portfolio: 1 minute
- MCTS results: 5 minutes

### Performance Optimizations

1. **Frontend**
   - Code splitting
   - Lazy loading
   - Virtual scrolling
   - Debounced updates
   - Memoization

2. **Backend**
   - Connection pooling
   - Async I/O (asyncio)
   - Batch operations
   - Query optimization
   - Response compression (gzip)

3. **Database**
   - Indexed queries
   - Connection pooling
   - Query result caching

## Deployment Architecture

### Development

```
localhost:3000 (Frontend dev server)
    ↓
localhost:8000 (Backend uvicorn)
    ↓
localhost:6379 (Redis)
```

### Production (Docker)

```
Client
    ↓
:80/:443 (Nginx)
    ↓
backend:8000 (Gunicorn + 4 workers)
    ↓
redis:6379 (Redis)
```

### High Availability (Future)

```
Client
    ↓
Load Balancer (HAProxy/ALB)
    ↓
Nginx (x2, redundant)
    ↓
Backend (x4+, auto-scaling)
    ↓
Redis Cluster (master + replicas)
    ↓
PostgreSQL (primary + read replicas)
```

### Monitoring & Observability

**Metrics:**
- Request latency (p50, p95, p99)
- Error rates
- WebSocket connections
- Cache hit rates
- System resources

**Logging:**
- Structured JSON logs
- Request tracing
- Error tracking (Sentry)
- LangSmith tracing (LLM calls)

**Health Checks:**
- `/health` - Application health
- `/api/v1/ws/health` - WebSocket health
- `/api/v1/system/metrics` - Detailed metrics

## Conclusion

This architecture provides:

- **Scalability**: Horizontal and vertical scaling capabilities
- **Performance**: Multi-layer caching, async I/O, optimized queries
- **Reliability**: Health checks, error handling, graceful degradation
- **Security**: Authentication, authorization, encryption, validation
- **Maintainability**: Clean architecture, type safety, comprehensive logging
- **Real-time**: WebSocket streaming, pub/sub messaging, low latency

The design balances simplicity for development with production-readiness for deployment.
