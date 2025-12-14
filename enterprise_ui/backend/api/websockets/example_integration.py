"""
Example integration of WebSocket handlers with FastAPI application.

This file demonstrates how to integrate the WebSocket handlers
into your FastAPI application and how to use them.
"""

import asyncio
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import the WebSocket router and handlers
from .router import (
    websocket_router,
    mcts_handler,
    market_handler,
    decision_handler,
    portfolio_handler,
    connection_manager,
)


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application with WebSocket support.

    Returns:
        Configured FastAPI application
    """
    app = FastAPI(
        title="Trading Platform API",
        description="Real-time trading platform with WebSocket streaming",
        version="1.0.0",
    )

    # Add CORS middleware for WebSocket support
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include WebSocket router
    app.include_router(websocket_router)

    # Add startup and shutdown event handlers
    @app.on_event("startup")
    async def startup_event():
        """Start background tasks on application startup."""
        # Start heartbeat loop
        asyncio.create_task(connection_manager.heartbeat_loop(interval=30))

        # You can start other background tasks here
        # For example, market data polling, MCTS processing, etc.

    @app.on_event("shutdown")
    async def shutdown_event():
        """Clean up on application shutdown."""
        await connection_manager.shutdown()

    return app


# Example usage in your application code
async def example_mcts_streaming():
    """
    Example: Stream MCTS search progress.

    This would be called from your MCTS search implementation.
    """
    search_id = "search-123"

    # Stream iteration updates
    for iteration in range(100):
        await mcts_handler.stream_iteration_update(
            search_id=search_id,
            iteration=iteration,
            total_iterations=100,
            best_action="BUY",
            best_value=0.85,
            nodes_explored=iteration * 10,
        )
        await asyncio.sleep(0.1)  # Simulate work

    # Stream completion
    await mcts_handler.stream_search_completion(
        search_id=search_id,
        best_action="BUY",
        best_value=0.95,
        total_iterations=100,
        duration_seconds=10.0,
        tree_size=1000,
    )


async def example_market_data_streaming():
    """
    Example: Stream real-time market data.

    This would be integrated with your market data source.
    """
    symbol = "AAPL"

    # Stream price updates
    while True:
        # Simulate getting market data
        price = 150.0  # Get from your data source
        volume = 1000.0

        await market_handler.stream_price_update(
            symbol=symbol,
            price=price,
            volume=volume,
            bid=149.95,
            ask=150.05,
        )

        # Stream indicator updates
        await market_handler.stream_indicator_update(
            symbol=symbol,
            indicators={
                "rsi": 65.5,
                "macd": 1.2,
                "sma_20": 148.5,
                "sma_50": 145.0,
            },
        )

        await asyncio.sleep(1)  # Update every second


async def example_decision_streaming():
    """
    Example: Stream trading decisions.

    This would be called when your trading algorithm makes decisions.
    """
    decision_id = "decision-456"

    # Stream a trading decision
    await decision_handler.stream_decision(
        decision_id=decision_id,
        symbol="AAPL",
        action="BUY",
        quantity=100.0,
        price=150.0,
        rationale="MCTS search suggests strong upward movement",
        confidence=0.85,
        regime="bullish",
        metadata={
            "mcts_search_id": "search-123",
            "expected_return": 0.05,
        },
    )

    # Stream execution update
    await decision_handler.stream_execution(
        execution_id="exec-789",
        decision_id=decision_id,
        symbol="AAPL",
        action="BUY",
        quantity=100.0,
        price=150.05,
        status="filled",
        fill_time=datetime.utcnow().isoformat(),
    )


async def example_portfolio_streaming():
    """
    Example: Stream portfolio updates.

    This would be called when portfolio state changes.
    """
    user_id = "user-123"

    # Stream position update
    await portfolio_handler.stream_position_update(
        user_id=user_id,
        symbol="AAPL",
        quantity=100.0,
        entry_price=150.0,
        current_price=152.0,
        pnl=200.0,
        pnl_percent=1.33,
    )

    # Stream P&L update
    await portfolio_handler.stream_pnl_update(
        user_id=user_id,
        total_pnl=1500.0,
        daily_pnl=200.0,
        unrealized_pnl=200.0,
        realized_pnl=1300.0,
    )

    # Stream risk alert
    await portfolio_handler.stream_risk_alert(
        user_id=user_id,
        alert_type="drawdown",
        severity="warning",
        message="Portfolio drawdown exceeds 5%",
        details={
            "current_drawdown": 5.2,
            "threshold": 5.0,
        },
    )


async def example_regime_change_workflow():
    """
    Example: Complete workflow when market regime changes.

    Demonstrates how different handlers work together.
    """
    symbol = "AAPL"
    old_regime = "ranging"
    new_regime = "bullish"

    # 1. Stream regime change via market handler
    await market_handler.stream_regime_change(
        symbol=symbol,
        old_regime=old_regime,
        new_regime=new_regime,
        confidence=0.92,
    )

    # 2. Stream regime-triggered decision
    decision_id = "decision-regime-123"
    await decision_handler.stream_regime_triggered_decision(
        decision_id=decision_id,
        symbol=symbol,
        old_regime=old_regime,
        new_regime=new_regime,
        action="BUY",
        rationale=f"Regime changed from {old_regime} to {new_regime}, increasing position",
    )

    # 3. Execute and update portfolio
    user_id = "user-123"
    await portfolio_handler.stream_trade_notification(
        user_id=user_id,
        symbol=symbol,
        action="BUY",
        quantity=50.0,
        price=150.0,
        status="filled",
    )


# Example: Custom background task for periodic updates
async def periodic_portfolio_summary(user_id: str, interval: int = 60):
    """
    Background task to periodically send portfolio summaries.

    Args:
        user_id: The user ID
        interval: Update interval in seconds
    """
    while True:
        try:
            # Calculate portfolio summary (this would use your actual data)
            total_value = 100000.0  # Get from your portfolio service
            cash = 50000.0
            positions_value = 50000.0
            num_positions = 5

            await portfolio_handler.stream_portfolio_summary(
                user_id=user_id,
                total_value=total_value,
                cash=cash,
                positions_value=positions_value,
                num_positions=num_positions,
            )

            await asyncio.sleep(interval)

        except Exception as e:
            # Log error and continue
            import logging
            logging.error(f"Error in portfolio summary task: {e}")
            await asyncio.sleep(interval)


# Example: Testing WebSocket connections
async def test_websocket_client():
    """
    Example client code for testing WebSocket connections.

    This shows how to connect and interact with the WebSocket endpoints
    from a Python client.
    """
    import websockets
    import json

    # Connect to MCTS stream
    async with websockets.connect("ws://localhost:8000/ws/mcts/AAPL") as ws:
        # Receive welcome message
        welcome = await ws.recv()
        print(f"Welcome: {welcome}")

        # Start a search
        await ws.send(json.dumps({
            "command": "start_search",
            "config": {
                "iterations": 100,
                "exploration": 1.4,
            }
        }))

        # Receive updates
        while True:
            message = await ws.recv()
            data = json.loads(message)
            print(f"Received: {data['type']}")

            if data["type"] == "search_completed":
                break


if __name__ == "__main__":
    """
    Example of running the FastAPI app with WebSocket support.
    """
    import uvicorn

    app = create_app()

    # Run the application
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
    )
