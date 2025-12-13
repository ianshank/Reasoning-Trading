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
```

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
