# Reasoning Trading Enterprise UI

A production-ready enterprise user interface for the Reasoning Trading multi-agent trading system with MCTS (Monte Carlo Tree Search) planning capabilities.

## Overview

The Enterprise UI provides a comprehensive web-based interface for monitoring and controlling the Reasoning Trading system. It features real-time market data visualization, MCTS search progress tracking, portfolio management, and trading decision analysis.

### Key Features

- **Real-time Market Monitoring**: Live price updates, technical indicators, and market regime detection
- **MCTS Visualization**: Interactive tree search visualization with node expansion and backpropagation tracking
- **Portfolio Dashboard**: Real-time position tracking, P&L monitoring, and risk metrics
- **Trading Decisions**: Decision history, execution tracking, and performance analytics
- **WebSocket Streaming**: Low-latency real-time updates for all data streams
- **Production-Ready**: Docker containerization, Nginx reverse proxy, Redis caching, comprehensive logging

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Enterprise UI                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────┐         ┌──────────────┐         ┌─────────┐  │
│  │   Frontend   │◄───────►│   Nginx      │◄───────►│  Redis  │  │
│  │  (React +    │         │  (Reverse    │         │ (Cache) │  │
│  │   Vite)      │         │   Proxy)     │         └─────────┘  │
│  └──────────────┘         └──────────────┘                       │
│         │                         │                              │
│         │                         ▼                              │
│         │                 ┌──────────────┐                       │
│         └────────────────►│   Backend    │                       │
│                          │  (FastAPI +   │                       │
│                          │  WebSocket)   │                       │
│                          └──────────────┘                       │
│                                 │                                │
└─────────────────────────────────┼────────────────────────────────┘
                                  │
                                  ▼
                   ┌──────────────────────────────┐
                   │  Reasoning Trading Core      │
                   │  - MCTS Planning             │
                   │  - Multi-Agent System        │
                   │  - Alpaca Trading            │
                   │  - Market Regime Detection   │
                   └──────────────────────────────┘
```

### Technology Stack

**Backend:**
- FastAPI 0.115+ (REST API & WebSocket)
- Python 3.11+
- Redis 7.0+ (Caching & pub/sub)
- Structlog (Structured logging)
- Pydantic (Configuration & validation)

**Frontend:**
- React 18.3+
- TypeScript 5.6+
- Vite 5.4+ (Build tool)
- TanStack Query (State management)
- Zustand (Global state)
- Recharts + D3.js (Visualization)
- Tailwind CSS (Styling)

**Infrastructure:**
- Docker & Docker Compose
- Nginx (Reverse proxy & static files)
- Multi-stage builds (Optimized images)

## Quick Start

### Prerequisites

- Docker 24.0+ and Docker Compose 2.0+
- Node.js 18+ and npm 9+ (for local development)
- Python 3.11+ (for local development)
- Alpaca API credentials (for trading)

### Production Deployment (Docker)

1. **Clone and configure:**
   ```bash
   cd enterprise_ui
   cp .env.example .env
   # Edit .env with your configuration
   ```

2. **Start all services:**
   ```bash
   docker-compose up -d
   ```

3. **Access the UI:**
   - Frontend: http://localhost:80
   - Backend API: http://localhost:80/api/v1
   - API Documentation: http://localhost:80/docs

4. **View logs:**
   ```bash
   docker-compose logs -f
   ```

5. **Stop services:**
   ```bash
   docker-compose down
   ```

### Local Development

1. **Install dependencies:**
   ```bash
   # Backend
   cd backend
   pip install -e "../../[dev]"  # Install reasoning-trading with dev dependencies

   # Frontend
   cd ../frontend
   npm install
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your local configuration
   ```

3. **Start services:**
   ```bash
   # Quick start with script
   ./scripts/dev.sh

   # Or manually:
   # Terminal 1 - Backend
   cd backend
   python -m enterprise_ui.backend.main

   # Terminal 2 - Frontend
   cd frontend
   npm run dev
   ```

4. **Access locally:**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

## API Documentation

### REST Endpoints

The backend provides comprehensive REST endpoints under `/api/v1`:

- **Trading**: `/api/v1/trading/*`
  - `POST /analyze` - Analyze trading opportunities
  - `POST /execute` - Execute trades
  - `GET /history` - Trading history

- **MCTS**: `/api/v1/mcts/*`
  - `POST /search` - Start MCTS search
  - `GET /search/{id}` - Get search status
  - `GET /tree/{id}` - Get search tree

- **Portfolio**: `/api/v1/portfolio/*`
  - `GET /summary` - Portfolio summary
  - `GET /positions` - Current positions
  - `GET /performance` - Performance metrics

- **Regime**: `/api/v1/regime/*`
  - `GET /current` - Current market regime
  - `GET /history` - Regime history
  - `GET /probabilities` - Regime probabilities

- **Analytics**: `/api/v1/analytics/*`
  - `GET /performance` - Performance analytics
  - `GET /risk` - Risk metrics
  - `GET /attribution` - Return attribution

- **System**: `/api/v1/system/*`
  - `GET /health` - System health
  - `GET /config` - Configuration
  - `GET /metrics` - System metrics

### WebSocket Endpoints

Real-time data streams available under `/api/v1/ws`:

- **MCTS Search**: `/api/v1/ws/mcts/{symbol}`
  - Real-time search progress, node expansions, backpropagation

- **Market Data**: `/api/v1/ws/market/{symbol}`
  - Live price updates, indicators, order book, regime changes

- **Trading Decisions**: `/api/v1/ws/decisions`
  - Decision stream, trade executions, signals

- **Portfolio Updates**: `/api/v1/ws/portfolio`
  - Position updates, P&L, risk alerts, performance metrics

See `/docs` for complete API documentation with examples.

## Component Library

### Frontend Components

**Layout Components:**
- `DashboardLayout` - Main application layout with navigation
- `Header` - Application header with user info
- `Sidebar` - Navigation sidebar
- `Footer` - Application footer

**Feature Components:**
- `MarketOverview` - Real-time market data display
- `MCTSVisualizer` - Interactive MCTS tree visualization
- `PortfolioDashboard` - Portfolio summary and positions
- `TradingDecisions` - Decision history and analysis
- `RegimeIndicator` - Market regime display
- `PerformanceChart` - Performance visualization

**UI Components:**
- `Card`, `Button`, `Input`, `Select` - Base UI components
- `Chart`, `Table`, `Badge`, `Alert` - Data display components
- `Modal`, `Dropdown`, `Tabs` - Interactive components

### Backend Services

**Core Services:**
- `TradingService` - Trading operations and execution
- `MCTSService` - MCTS search management
- `PortfolioService` - Portfolio management
- `AnalyticsService` - Analytics and metrics
- `CacheService` - Redis caching layer

**WebSocket Handlers:**
- `MCTSStreamHandler` - MCTS search streaming
- `MarketStreamHandler` - Market data streaming
- `DecisionStreamHandler` - Decision streaming
- `PortfolioStreamHandler` - Portfolio streaming

## Configuration

Configuration is managed through environment variables. See `.env.example` for all available options.

**Key Configuration Groups:**

- **API Server**: Host, port, workers, reload
- **JWT Authentication**: Secret key, algorithm, token expiration
- **CORS**: Allowed origins, methods, headers
- **Rate Limiting**: Requests per minute, burst size
- **WebSocket**: Heartbeat interval, message size, timeout
- **Redis**: Host, port, database, password
- **Database**: URL, pool size, echo mode
- **Trading (Core)**: Alpaca credentials, trading mode
- **Logging**: Level, format, destinations

## Development

See [DEVELOPMENT.md](DEVELOPMENT.md) for detailed development guidelines including:
- Local setup and configuration
- Code style and conventions
- Testing strategy and coverage
- Debugging and troubleshooting
- Deployment process

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed system architecture including:
- Component design and interactions
- Data flow and state management
- Integration with reasoning_trading core
- Security and authentication
- Scalability considerations

## Testing

Run the comprehensive test suite:

```bash
# Run all tests
./scripts/test.sh

# Backend tests only
cd backend
pytest

# Frontend tests only
cd frontend
npm test

# With coverage
./scripts/test.sh --coverage
```

Test coverage targets:
- Backend: 80%+ line coverage
- Frontend: 70%+ line coverage
- Integration tests for all critical paths

## Production Deployment

### Docker Deployment (Recommended)

1. Configure production environment variables in `.env`
2. Build and start services: `docker-compose up -d --build`
3. Monitor logs: `docker-compose logs -f`
4. Scale backend workers: `docker-compose up -d --scale backend=3`

### Manual Deployment

1. **Backend:**
   ```bash
   pip install -e .[webui]
   gunicorn enterprise_ui.backend.main:app \
     --workers 4 \
     --worker-class uvicorn.workers.UvicornWorker \
     --bind 0.0.0.0:8000
   ```

2. **Frontend:**
   ```bash
   npm run build
   # Serve dist/ with Nginx or static file server
   ```

3. **Nginx:**
   ```bash
   cp nginx.conf /etc/nginx/sites-available/reasoning-trading
   ln -s /etc/nginx/sites-available/reasoning-trading /etc/nginx/sites-enabled/
   nginx -t && systemctl reload nginx
   ```

## Monitoring

### Health Checks

- Application: `GET /health`
- WebSocket: `GET /api/v1/ws/health`
- Detailed metrics: `GET /api/v1/system/metrics`

### Logs

Structured JSON logs in production:
```bash
# View application logs
docker-compose logs -f backend

# Filter by level
docker-compose logs backend | grep '"level":"error"'

# Follow specific component
docker-compose logs -f backend | grep '"component":"mcts"'
```

### Metrics

Monitor key metrics:
- Request latency (p50, p95, p99)
- Error rates and types
- WebSocket connection count
- Active MCTS searches
- Cache hit rates
- Database pool usage

## Troubleshooting

### Common Issues

**Backend won't start:**
- Check Redis connection: `redis-cli ping`
- Verify environment variables in `.env`
- Check logs: `docker-compose logs backend`

**Frontend can't connect:**
- Verify CORS settings match frontend URL
- Check network connectivity to backend
- Inspect browser console for errors

**WebSocket disconnects:**
- Check firewall settings
- Verify heartbeat configuration
- Monitor connection limits

**Trading not working:**
- Verify Alpaca API credentials
- Check API key permissions
- Ensure correct trading mode (paper/live)

See [LOGGING_DEBUG_GUIDE.md](LOGGING_DEBUG_GUIDE.md) for detailed debugging instructions.

## Security

**Production Checklist:**

- [ ] Change default JWT secret key
- [ ] Use strong Redis password
- [ ] Enable HTTPS with SSL certificates
- [ ] Configure CORS for specific origins
- [ ] Set up authentication for API endpoints
- [ ] Enable rate limiting
- [ ] Disable API documentation in production
- [ ] Use read-only Alpaca API keys when possible
- [ ] Set up firewall rules
- [ ] Enable log monitoring and alerts

## License

This project is part of the Reasoning Trading system. See main project LICENSE for details.

## Support

For issues, questions, or contributions:
- GitHub Issues: https://github.com/ianshank/Reasoning-Trading/issues
- Documentation: https://github.com/ianshank/Reasoning-Trading#readme

## Changelog

### Version 1.0.0 (Current)
- Initial enterprise UI release
- Real-time WebSocket streaming
- MCTS visualization
- Portfolio dashboard
- Trading decision analytics
- Docker deployment
- Comprehensive testing
