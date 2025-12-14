"""
WebSocket router for mounting all WebSocket endpoints.

Provides centralized routing for all WebSocket streams:
- MCTS search progress
- Market data
- Trading decisions
- Portfolio updates
"""

from typing import Optional

from fastapi import APIRouter, WebSocket, Query
from structlog import get_logger

from .handlers import connection_manager
from .mcts_stream import MCTSStreamHandler
from .market_stream import MarketStreamHandler
from .decision_stream import DecisionStreamHandler
from .portfolio_stream import PortfolioStreamHandler

logger = get_logger(__name__)

# Create router
websocket_router = APIRouter(prefix="/ws", tags=["websockets"])

# Initialize handlers
mcts_handler = MCTSStreamHandler(connection_manager)
market_handler = MarketStreamHandler(connection_manager)
decision_handler = DecisionStreamHandler(connection_manager)
portfolio_handler = PortfolioStreamHandler(connection_manager)


@websocket_router.websocket("/mcts/{symbol}")
async def mcts_websocket(
    websocket: WebSocket,
    symbol: str,
    token: Optional[str] = Query(None),
):
    """
    WebSocket endpoint for MCTS search progress streaming.

    Streams real-time MCTS iteration updates, node expansions,
    backpropagation, and search completion events.

    Args:
        websocket: The WebSocket connection
        symbol: The trading symbol to monitor
        token: Optional authentication token

    Message format from client:
        {
            "command": "start_search" | "stop_search" | "update_config" | "get_status",
            "search_id": "...",  // for stop_search and update_config
            "config": {...}      // for start_search and update_config
        }

    Message types from server:
        - connected: Initial connection confirmation
        - search_started: Search initialization
        - iteration_update: MCTS iteration progress
        - node_expansion: Node expansion event
        - backpropagation: Backpropagation update
        - search_completed: Search completion
        - search_error: Error during search
        - error: General error
        - ping: Heartbeat ping
    """
    logger.info("mcts_websocket_connection_attempt", symbol=symbol)
    await mcts_handler.handle_connection(websocket, symbol, token)


@websocket_router.websocket("/market/{symbol}")
async def market_websocket(
    websocket: WebSocket,
    symbol: str,
    token: Optional[str] = Query(None),
):
    """
    WebSocket endpoint for real-time market data streaming.

    Streams price updates, technical indicators, OHLCV data,
    order book updates, and market regime changes.

    Args:
        websocket: The WebSocket connection
        symbol: The trading symbol to monitor
        token: Optional authentication token

    Message format from client:
        {
            "command": "subscribe" | "unsubscribe" | "get_subscriptions" | "get_snapshot",
            "symbols": ["AAPL", "MSFT"],  // for subscribe/unsubscribe
            "symbol": "AAPL"               // for get_snapshot
        }

    Message types from server:
        - connected: Initial connection confirmation
        - subscribed: Subscription confirmation
        - unsubscribed: Unsubscription confirmation
        - price_update: Real-time price update
        - indicator_update: Technical indicator update
        - ohlcv_update: OHLCV/candlestick data
        - orderbook_update: Order book update
        - regime_change: Market regime change notification
        - snapshot: Current market snapshot
        - error: General error
        - ping: Heartbeat ping
    """
    logger.info("market_websocket_connection_attempt", symbol=symbol)
    await market_handler.handle_connection(websocket, symbol, token)


@websocket_router.websocket("/decisions")
async def decisions_websocket(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
):
    """
    WebSocket endpoint for trading decision streaming.

    Streams real-time trading decisions, trade executions,
    regime-triggered decisions, and trading signals.

    Args:
        websocket: The WebSocket connection
        token: Optional authentication token

    Message format from client:
        {
            "command": "get_recent" | "get_decision" | "filter_by_symbol",
            "limit": 20,              // for get_recent
            "decision_id": "...",     // for get_decision
            "symbol": "AAPL"          // for filter_by_symbol
        }

    Message types from server:
        - connected: Initial connection confirmation with recent decisions
        - trading_decision: New trading decision
        - trade_execution: Trade execution notification
        - regime_triggered_decision: Decision triggered by regime change
        - trading_signal: Trading signal notification
        - recent_decisions: List of recent decisions
        - decision: Specific decision details
        - filtered_decisions: Filtered decision list
        - error: General error
        - ping: Heartbeat ping
    """
    logger.info("decisions_websocket_connection_attempt")
    await decision_handler.handle_connection(websocket, token)


@websocket_router.websocket("/portfolio")
async def portfolio_websocket(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
):
    """
    WebSocket endpoint for portfolio updates streaming.

    Streams real-time portfolio updates including positions,
    P&L, risk alerts, and performance metrics.

    Note: This endpoint requires authentication.

    Args:
        websocket: The WebSocket connection
        token: Authentication token (required)

    Message format from client:
        {
            "command": "get_portfolio" | "get_positions" | "get_performance" | "get_risk_metrics"
        }

    Message types from server:
        - connected: Initial connection confirmation with current portfolio
        - position_update: Position update
        - pnl_update: P&L update
        - portfolio_summary: Portfolio summary
        - trade_notification: Trade execution notification
        - performance_update: Performance metrics update
        - risk_alert: Risk alert notification
        - portfolio: Full portfolio data
        - positions: Position list
        - performance: Performance metrics
        - risk_metrics: Risk metrics
        - error: General error
        - ping: Heartbeat ping
    """
    logger.info("portfolio_websocket_connection_attempt")
    await portfolio_handler.handle_connection(websocket, token)


@websocket_router.get("/health")
async def websocket_health():
    """
    Health check endpoint for WebSocket service.

    Returns connection statistics and service status.
    """
    return {
        "status": "healthy",
        "active_connections": connection_manager.get_connection_count(),
        "active_rooms": connection_manager.get_room_count(),
        "handlers": {
            "mcts": "active",
            "market": "active",
            "decisions": "active",
            "portfolio": "active",
        },
    }


@websocket_router.get("/stats")
async def websocket_stats():
    """
    Get detailed WebSocket statistics.

    Returns detailed statistics about connections, rooms, and subscriptions.
    """
    return {
        "connections": {
            "total": connection_manager.get_connection_count(),
            "by_type": {
                "mcts": len([
                    c for c in connection_manager.connection_metadata.values()
                    if c.get("type") == "mcts"
                ]),
                "market": len([
                    c for c in connection_manager.connection_metadata.values()
                    if c.get("type") == "market"
                ]),
                "decision": len([
                    c for c in connection_manager.connection_metadata.values()
                    if c.get("type") == "decision"
                ]),
                "portfolio": len([
                    c for c in connection_manager.connection_metadata.values()
                    if c.get("type") == "portfolio"
                ]),
            },
        },
        "rooms": {
            "total": connection_manager.get_room_count(),
            "active": list(connection_manager.rooms.keys()),
        },
        "market": {
            "subscribed_symbols": list(market_handler.get_all_subscribed_symbols()),
            "total_subscriptions": sum(
                len(symbols) for symbols in market_handler.subscriptions.values()
            ),
        },
        "mcts": {
            "active_searches": len(mcts_handler.active_searches),
        },
        "decisions": {
            "cached_decisions": decision_handler.get_decision_count(),
        },
    }


# Export handlers for external use
__all__ = [
    "websocket_router",
    "mcts_handler",
    "market_handler",
    "decision_handler",
    "portfolio_handler",
    "connection_manager",
]
