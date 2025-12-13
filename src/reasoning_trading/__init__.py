"""
Reasoning Trading: MCTS-Enhanced Multi-Agent Trading Framework

This package integrates AlpacaTradingAgent with LangGraph MCTS to enable
strategic exploration of trading strategies through Monte Carlo Tree Search.

Key Components:
    - mcts: Core MCTS implementation with trading-specific adaptations
    - agents: Multi-agent trading system with specialized analysts
    - core: State representations and action spaces
    - services: Trading service adapters and API tools
    - strategies: Position sizing and risk management strategies
"""

from reasoning_trading.config import Settings, get_settings
from reasoning_trading.core.state import TradingState
from reasoning_trading.mcts.node import Node
from reasoning_trading.mcts.tree import MCTSTree

__version__ = "0.1.0"

__all__ = [
    "Settings",
    "get_settings",
    "TradingState",
    "Node",
    "MCTSTree",
    "__version__",
]
