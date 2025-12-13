# Reasoning Trading: MCTS-Enhanced Multi-Agent Trading Framework

A production-ready framework integrating **AlpacaTradingAgent's** multi-agent LLM architecture with **LangGraph MCTS** (Monte Carlo Tree Search) to enable strategic exploration of trading strategies.

## Overview

This framework transforms trading decisions from reactive classification tasks into strategic planning problems. It combines:

- **Multi-Agent Analysis**: 5 specialized analysts (Market, News, Social Sentiment, Fundamentals, Macro) with Bull/Bear debate structure
- **MCTS Planning**: Systematic exploration of trading strategies using UCB-based selection, progressive widening for continuous actions, and risk-adjusted reward functions
- **Hybrid Architecture**: Lambda pattern combining batch planning (overnight) with real-time decisions

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    MCTS Planning Layer (LangGraph)                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                 │
│  │  Selection  │──│  Expansion  │──│ Simulation  │──┐              │
│  │   (UCB)     │  │  (LLM Gen)  │  │  (Rollout)  │  │              │
│  └─────────────┘  └─────────────┘  └──────┬──────┘  │              │
│                                           │         │              │
│                                    ┌──────▼──────┐  │              │
│                                    │Backpropagation│◄┘              │
│                                    └─────────────┘                  │
└────────────────────────────────────────────┬────────────────────────┘
                                             │ Tool Calls
                          ┌──────────────────▼───────────────────┐
                          │        Message Queue (Redis)          │
                          └──────────────────┬───────────────────┘
                                             │
┌────────────────────────────────────────────▼────────────────────────┐
│              AlpacaTradingAgent Service (Separate Process)           │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐        │
│  │5 Analysts │─▶│Researchers│─▶│Risk Mgmt  │─▶│Portfolio  │        │
│  │           │  │(Bull/Bear)│  │(3 profiles)│  │Manager    │        │
│  └───────────┘  └───────────┘  └───────────┘  └─────┬─────┘        │
│                                                      │              │
│                                              ┌───────▼───────┐      │
│                                              │  Alpaca API   │      │
│                                              └───────────────┘      │
└─────────────────────────────────────────────────────────────────────┘
```

## Installation

```bash
# Clone the repository
git clone https://github.com/ianshank/Reasoning-Trading.git
cd Reasoning-Trading

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Copy environment template
cp .env.example .env
# Edit .env with your API keys
```

## Configuration

All configuration is managed via environment variables (no hardcoded values). See `.env.example` for all available options:

```bash
# Required
OPENAI_API_KEY=your_openai_key
ALPACA_API_KEY=your_alpaca_key
ALPACA_SECRET_KEY=your_alpaca_secret

# Optional
MCTS_MAX_SIMULATIONS=1000
MCTS_EXPLORATION_WEIGHT=1.414
DEFAULT_RISK_PROFILE=moderate
```

## Usage

### CLI Commands

```bash
# Analyze a single symbol
reasoning-trading analyze AAPL

# Analyze with specific date
reasoning-trading analyze NVDA -d 2024-01-15

# Batch planning for multiple symbols
reasoning-trading batch AAPL NVDA TSLA GOOGL

# Real-time decision (uses cached policy if available)
reasoning-trading realtime AAPL

# Show configuration status
reasoning-trading config
```

### Python API

```python
import asyncio
from reasoning_trading.workflow.graph import build_trading_mcts_graph
from reasoning_trading.config import get_settings

async def main():
    settings = get_settings()
    graph = build_trading_mcts_graph(settings)

    result = await graph.run("AAPL", "2024-01-15")

    if result.best_action:
        print(f"Direction: {result.best_action.direction.value}")
        print(f"Confidence: {result.action_confidence:.1%}")
        print(f"Reasoning: {result.action_reasoning}")

    await graph.cleanup()

asyncio.run(main())
```

### Hybrid Architecture (Batch + Realtime)

```python
from reasoning_trading.workflow.hybrid import HybridTradingArchitecture

async def trading_system():
    hybrid = HybridTradingArchitecture()
    await hybrid.initialize()

    # Run overnight batch planning
    symbols = ["AAPL", "NVDA", "TSLA", "GOOGL", "MSFT"]
    await hybrid.nightly_planning(symbols)

    # Real-time decisions use cached policy
    action = await hybrid.realtime_decision("AAPL")

    await hybrid.cleanup()
```

### Multi-Agent Coordination

```python
from reasoning_trading.agents.coordinator import MultiAgentTradingMCTS

async def multi_agent_analysis():
    coordinator = MultiAgentTradingMCTS()

    # Analyze using all specialized agents
    action = await coordinator.analyze(trading_state)

    # Get agent statistics
    stats = coordinator.get_agent_stats()
```

## Key Components

### Core (`reasoning_trading.core`)
- `TradingState`: Complete state representation for MCTS nodes
- `TradingAction`: Action space with direction, sizing, stop-loss
- `ActionSpace`: Progressive widening for continuous actions

### MCTS (`reasoning_trading.mcts`)
- `MCTSTree`: Main tree search with configurable phases
- `Node`: Tree node with UCB statistics
- `TradingRollout`: Risk-adjusted reward simulation
- `UCBSelector`: Multiple selection strategies (UCB1, PUCT, Risk-Adjusted)

### Services (`reasoning_trading.services`)
- `TradingServiceAdapter`: LangGraph tools for trading operations
- `MarketDataService`: Historical data and indicators
- `PortfolioService`: Position and risk management

### Workflow (`reasoning_trading.workflow`)
- `MCTSTradingGraph`: Complete LangGraph StateGraph workflow
- `HybridTradingArchitecture`: Lambda pattern implementation

### Agents (`reasoning_trading.agents`)
- `MultiAgentTradingMCTS`: Specialized agent coordination
- Built-in agents: Momentum, Mean Reversion, Breakout

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=reasoning_trading --cov-report=html

# Run specific test file
pytest tests/test_mcts.py

# Run with verbose output
pytest -v

# Using Make commands
make test           # Run all tests
make test-unit      # Run unit tests only
make test-integration  # Run integration tests
make test-e2e       # Run E2E tests
make test-cov       # Run tests with coverage report
```

## CI/CD Pipeline

This project includes a comprehensive CI/CD pipeline using GitHub Actions.

### Workflows

| Workflow | Trigger | Description |
|----------|---------|-------------|
| **CI** | Push, PR | Linting, type checking, tests, build validation |
| **Release** | Tags (`v*.*.*`) | Build, test, publish to PyPI/Docker |
| **Security** | Push, Schedule | Dependency scanning, SAST, secret detection |

### CI Pipeline Stages

```
┌─────────────────────────────────────────────────────────────┐
│                         CI Pipeline                          │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────┐   ┌────────────┐   ┌─────────────┐            │
│  │  Lint   │   │ Type Check │   │    Build    │            │
│  │ (Ruff)  │   │  (MyPy)    │   │  (Package)  │            │
│  └────┬────┘   └─────┬──────┘   └──────┬──────┘            │
│       │              │                  │                   │
│       └──────────────┼──────────────────┘                   │
│                      │                                      │
│               ┌──────▼──────┐                               │
│               │ Unit Tests  │ (Python 3.11, 3.12, 3.13)    │
│               └──────┬──────┘                               │
│                      │                                      │
│               ┌──────▼──────┐                               │
│               │ Integration │                               │
│               │   Tests     │                               │
│               └──────┬──────┘                               │
│                      │                                      │
│               ┌──────▼──────┐                               │
│               │  E2E Tests  │                               │
│               └──────┬──────┘                               │
│                      │                                      │
│               ┌──────▼──────┐                               │
│               │  Coverage   │                               │
│               │   Report    │                               │
│               └─────────────┘                               │
└─────────────────────────────────────────────────────────────┘
```

### Running CI Locally

```bash
# Install pre-commit hooks
make pre-commit-install

# Run all code quality checks
make check

# Run CI-style tests
make ci-test

# Run security checks
make ci-security
```

## Docker

### Building Images

```bash
# Build production image
make docker-build

# Build development image
make docker-build-dev

# Or using docker directly
docker build -t reasoning-trading:latest .
docker build --target development -t reasoning-trading:dev .
```

### Running with Docker

```bash
# Run API server
docker run -it --rm --env-file .env -p 8000:8000 reasoning-trading:latest

# Run CLI commands
docker run -it --rm --env-file .env reasoning-trading:latest reasoning-trading analyze AAPL

# Run tests in container
docker run -it --rm reasoning-trading:dev pytest tests/ -v
```

### Docker Compose

```bash
# Start all services (API + Redis)
docker-compose up -d

# Start with development tools (Redis Commander)
docker-compose --profile dev up -d

# Run tests
docker-compose --profile test run --rm test

# View logs
docker-compose logs -f api

# Stop services
docker-compose down
```

### Services

| Service | Port | Description |
|---------|------|-------------|
| `api` | 8000 | Trading API server |
| `redis` | 6379 | Cache and message broker |
| `redis-commander` | 8081 | Redis web UI (dev profile) |

## Development Workflow

### Quick Start

```bash
# Complete development setup
make setup

# This will:
# 1. Create virtual environment
# 2. Install dev dependencies
# 3. Install pre-commit hooks
```

### Daily Development

```bash
# Before starting work
make lint          # Check for issues
make format        # Auto-format code
make type-check    # Run type checker

# Run tests frequently
make test-unit     # Fast feedback
make test-cov      # With coverage

# Before committing
make check         # All quality checks
make pre-commit-run  # Run all hooks
```

### Makefile Commands

```bash
make help          # Show all available commands

# Installation
make install       # Production dependencies
make install-dev   # Development dependencies
make install-all   # All dependencies

# Testing
make test          # All tests
make test-unit     # Unit tests only
make test-integration  # Integration tests
make test-e2e      # E2E tests
make test-cov      # With coverage

# Code Quality
make lint          # Run linter
make lint-fix      # Fix lint issues
make format        # Format code
make type-check    # Type checking
make check         # All checks

# Docker
make docker-build  # Build image
make docker-run    # Run container
make docker-compose-up    # Start services
make docker-compose-down  # Stop services

# Application
make run-api       # Start API server
make run-cli       # CLI help
make analyze SYMBOL=AAPL  # Analyze symbol
```

### Pre-commit Hooks

The project uses pre-commit hooks for code quality:

```bash
# Install hooks
pre-commit install
pre-commit install --hook-type commit-msg

# Run on all files
pre-commit run --all-files

# Update hooks
pre-commit autoupdate
```

**Included hooks:**
- Ruff (linting & formatting)
- MyPy (type checking)
- Bandit (security)
- detect-secrets (secret scanning)
- YAML/JSON/TOML validation
- Conventional commit messages

## Project Structure

```
reasoning_trading/
├── src/reasoning_trading/
│   ├── __init__.py
│   ├── config.py           # Configuration management
│   ├── cli.py              # Command-line interface
│   ├── core/               # State and action representations
│   │   ├── state.py
│   │   └── actions.py
│   ├── mcts/               # MCTS implementation
│   │   ├── node.py
│   │   ├── tree.py
│   │   ├── ucb.py
│   │   └── rollout.py
│   ├── services/           # Trading services
│   │   ├── adapter.py
│   │   ├── market_data.py
│   │   └── portfolio.py
│   ├── workflow/           # LangGraph workflows
│   │   ├── graph.py
│   │   └── hybrid.py
│   └── agents/             # Multi-agent coordination
│       └── coordinator.py
├── tests/                  # Comprehensive test suite
├── pyproject.toml          # Project configuration
├── .env.example            # Environment template
└── README.md
```

## Reward Functions

The framework supports multiple reward functions for MCTS rollouts:

| Function | Description | Best For |
|----------|-------------|----------|
| `RAW_RETURNS` | Simple profit/loss | Aggressive growth |
| `SHARPE_RATIO` | Risk-adjusted returns | Balanced performance |
| `SORTINO_RATIO` | Downside-only risk | Downside protection |
| `MAX_DRAWDOWN_PENALTY` | Returns with DD penalty | Capital preservation |

## License

MIT License - see LICENSE file for details.

## References

- [AlpacaTradingAgent](https://github.com/huygiatrng/AlpacaTradingAgent) - Multi-agent trading framework
- [LangGraph MCTS](https://github.com/ianshank/langgraph_multi_agent_mcts) - LATS implementation
- Vittori et al. (2021) - "MCTS for Trading" ACM ICAIF
- TradingAgents Framework (UCLA/MIT, 2024) - Multi-agent debate architecture
