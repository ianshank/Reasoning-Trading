"""
WebSocket handlers for real-time data streaming.

This package provides WebSocket endpoints for streaming:
- MCTS search progress and updates
- Real-time market data
- Trading decisions
- Portfolio updates

All WebSocket handlers support:
- Connection lifecycle management
- Room-based subscriptions
- Authentication
- Error handling and reconnection
- Structured logging
"""

from .handlers import ConnectionManager
from .mcts_stream import MCTSStreamHandler
from .market_stream import MarketStreamHandler
from .decision_stream import DecisionStreamHandler
from .portfolio_stream import PortfolioStreamHandler
from .router import websocket_router

__all__ = [
    "ConnectionManager",
    "MCTSStreamHandler",
    "MarketStreamHandler",
    "DecisionStreamHandler",
    "PortfolioStreamHandler",
    "websocket_router",
]
