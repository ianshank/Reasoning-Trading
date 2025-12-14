"""
Portfolio updates streaming.

Streams real-time portfolio updates including positions, P&L, and risk alerts
to connected clients.
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import WebSocket, WebSocketDisconnect
from structlog import get_logger

from .handlers import (
    ConnectionManager,
    authenticate_websocket,
    create_message,
    handle_websocket_errors,
)

logger = get_logger(__name__)


class PortfolioStreamHandler:
    """
    Handler for streaming portfolio updates to WebSocket clients.

    Features:
    - Real-time position updates
    - P&L tracking and notifications
    - Risk alerts
    - Portfolio performance metrics
    """

    def __init__(self, connection_manager: ConnectionManager):
        """
        Initialize the portfolio stream handler.

        Args:
            connection_manager: The connection manager instance
        """
        self.connection_manager = connection_manager

        # Cache current portfolio state for new connections
        self.portfolio_cache: Dict[str, Any] = {}

        logger.info("portfolio_stream_handler_initialized")

    async def handle_connection(
        self,
        websocket: WebSocket,
        token: Optional[str] = None,
    ) -> None:
        """
        Handle a WebSocket connection for portfolio updates.

        Args:
            websocket: The WebSocket connection
            token: Optional authentication token
        """
        # Authenticate
        user_id = await authenticate_websocket(websocket, token)

        if not user_id:
            # Portfolio stream requires authentication
            await websocket.close(code=1008, reason="Authentication required")
            logger.warning("portfolio_connection_rejected_no_auth")
            return

        # Connect
        connection_id = await self.connection_manager.connect(
            websocket,
            user_id=user_id,
            metadata={"type": "portfolio"},
        )

        # Join user-specific portfolio room
        room_id = f"portfolio:{user_id}"
        self.connection_manager.join_room(connection_id, room_id)

        # Also join global portfolio room for broadcast messages
        self.connection_manager.join_room(connection_id, "portfolio")

        # Send welcome message with current portfolio state
        current_portfolio = self.portfolio_cache.get(
            user_id,
            {
                "positions": [],
                "total_value": 0.0,
                "cash": 0.0,
                "pnl": 0.0,
            },
        )

        welcome_message = create_message(
            "connected",
            {
                "connection_id": connection_id,
                "message": "Connected to portfolio stream",
                "current_portfolio": current_portfolio,
            },
        )
        await self.connection_manager.send_personal_message(
            connection_id, welcome_message
        )

        logger.info(
            "portfolio_stream_connected",
            connection_id=connection_id,
            user_id=user_id,
        )

        try:
            # Message handling loop
            while True:
                try:
                    # Receive message from client
                    data = await websocket.receive_json()

                    await self._handle_client_message(
                        connection_id, user_id, data
                    )

                except WebSocketDisconnect:
                    logger.info(
                        "websocket_disconnected",
                        connection_id=connection_id,
                    )
                    break

                except Exception as e:
                    logger.error(
                        "message_handling_error",
                        connection_id=connection_id,
                        error=str(e),
                        exc_info=True,
                    )
                    await handle_websocket_errors(websocket, connection_id, e)

        finally:
            await self.connection_manager.disconnect(connection_id)

    async def _handle_client_message(
        self,
        connection_id: str,
        user_id: str,
        message: Dict[str, Any],
    ) -> None:
        """
        Handle messages from clients.

        Args:
            connection_id: The connection ID
            user_id: The user ID
            message: The message from client
        """
        command = message.get("command")

        if command == "get_portfolio":
            await self._handle_get_portfolio(connection_id, user_id)

        elif command == "get_positions":
            await self._handle_get_positions(connection_id, user_id)

        elif command == "get_performance":
            await self._handle_get_performance(connection_id, user_id)

        elif command == "get_risk_metrics":
            await self._handle_get_risk_metrics(connection_id, user_id)

        elif command == "pong":
            # Handle pong response to ping
            logger.debug("pong_received", connection_id=connection_id)

        else:
            logger.warning(
                "unknown_command",
                connection_id=connection_id,
                command=command,
            )
            error_message = create_message(
                "error",
                {"error": f"Unknown command: {command}"},
            )
            await self.connection_manager.send_personal_message(
                connection_id, error_message
            )

    async def _handle_get_portfolio(
        self,
        connection_id: str,
        user_id: str,
    ) -> None:
        """
        Handle get portfolio command.

        Args:
            connection_id: The connection ID
            user_id: The user ID
        """
        portfolio = self.portfolio_cache.get(
            user_id,
            {
                "positions": [],
                "total_value": 0.0,
                "cash": 0.0,
                "pnl": 0.0,
            },
        )

        response = create_message("portfolio", portfolio)
        await self.connection_manager.send_personal_message(
            connection_id, response
        )

    async def _handle_get_positions(
        self,
        connection_id: str,
        user_id: str,
    ) -> None:
        """
        Handle get positions command.

        Args:
            connection_id: The connection ID
            user_id: The user ID
        """
        portfolio = self.portfolio_cache.get(user_id, {})
        positions = portfolio.get("positions", [])

        response = create_message("positions", {"positions": positions})
        await self.connection_manager.send_personal_message(
            connection_id, response
        )

    async def _handle_get_performance(
        self,
        connection_id: str,
        user_id: str,
    ) -> None:
        """
        Handle get performance command.

        Args:
            connection_id: The connection ID
            user_id: The user ID
        """
        try:
            from reasoning_trading.services.portfolio import PortfolioService

            portfolio_service = PortfolioService()
            state = portfolio_service.get_state()
            sharpe_ratio = portfolio_service.calculate_sharpe_ratio()

            # Calculate returns from portfolio state
            initial_value = state.initial_portfolio_value or state.portfolio_value
            if initial_value > 0:
                total_return = (state.portfolio_value - initial_value) / initial_value
            else:
                total_return = 0.0

            # Daily return approximation from realized P&L
            daily_return = state.realized_pnl_today / state.portfolio_value if state.portfolio_value > 0 else 0.0

            performance = {
                "total_return": total_return,
                "daily_return": daily_return,
                "sharpe_ratio": sharpe_ratio,
                "max_drawdown": state.max_drawdown,
                "current_drawdown": state.current_drawdown,
                "unrealized_pnl": state.unrealized_pnl,
                "realized_pnl_today": state.realized_pnl_today,
                "realized_pnl_total": state.realized_pnl_total,
            }
        except Exception as e:
            logger.warning("performance_calculation_error", user_id=user_id, error=str(e))
            performance = {
                "total_return": 0.0,
                "daily_return": 0.0,
                "sharpe_ratio": 0.0,
                "max_drawdown": 0.0,
                "error": str(e),
            }

        response = create_message("performance", performance)
        await self.connection_manager.send_personal_message(
            connection_id, response
        )

    async def _handle_get_risk_metrics(
        self,
        connection_id: str,
        user_id: str,
    ) -> None:
        """
        Handle get risk metrics command.

        Args:
            connection_id: The connection ID
            user_id: The user ID
        """
        try:
            from reasoning_trading.services.portfolio import PortfolioService

            portfolio_service = PortfolioService()
            state = portfolio_service.get_state()

            # Calculate VaR (Value at Risk) at 95% confidence
            # Use daily_var_95 from state if available, otherwise estimate
            var_95 = getattr(state, 'daily_var_95', 0.0) or 0.0

            # Expected shortfall (CVaR) - estimate as 1.25x VaR for normal distribution
            expected_shortfall = var_95 * 1.25 if var_95 else 0.0

            # Beta estimate (default to 1.0 for market-neutral)
            beta = getattr(state, 'beta', 1.0)

            # Volatility from drawdown data
            max_drawdown = getattr(state, 'max_drawdown', 0.0) or 0.0
            volatility = max_drawdown * 2.0 if max_drawdown else 0.0

            risk_metrics = {
                "var": var_95,
                "expected_shortfall": expected_shortfall,
                "beta": beta,
                "volatility": volatility,
                "current_drawdown": getattr(state, 'current_drawdown', 0.0) or 0.0,
                "max_drawdown": max_drawdown,
                "largest_position_pct": getattr(state, 'largest_position_pct', 0.0) or 0.0,
                "position_count": getattr(state, 'position_count', 0),
                "margin_used": getattr(state, 'margin_used', 0.0) or 0.0,
                "margin_available": getattr(state, 'margin_available', 0.0) or 0.0,
            }
        except Exception as e:
            logger.warning("risk_metrics_calculation_error", user_id=user_id, error=str(e))
            risk_metrics = {
                "var": 0.0,
                "expected_shortfall": 0.0,
                "beta": 1.0,
                "volatility": 0.0,
                "error": str(e),
            }

        response = create_message("risk_metrics", risk_metrics)
        await self.connection_manager.send_personal_message(
            connection_id, response
        )

    async def stream_position_update(
        self,
        user_id: str,
        symbol: str,
        quantity: float,
        entry_price: float,
        current_price: float,
        pnl: float,
        pnl_percent: float,
        **kwargs: Any,
    ) -> None:
        """
        Stream a position update to user.

        Args:
            user_id: The user ID
            symbol: The trading symbol
            quantity: Current position quantity
            entry_price: Entry price
            current_price: Current market price
            pnl: Position P&L
            pnl_percent: Position P&L percentage
            **kwargs: Additional position data
        """
        position = {
            "symbol": symbol,
            "quantity": quantity,
            "entry_price": entry_price,
            "current_price": current_price,
            "pnl": pnl,
            "pnl_percent": pnl_percent,
            "timestamp": datetime.utcnow().isoformat(),
            **kwargs,
        }

        # Update cache
        if user_id not in self.portfolio_cache:
            self.portfolio_cache[user_id] = {"positions": []}

        positions = self.portfolio_cache[user_id].get("positions", [])
        # Update or add position
        existing_idx = next(
            (i for i, p in enumerate(positions) if p.get("symbol") == symbol),
            None,
        )
        if existing_idx is not None:
            positions[existing_idx] = position
        else:
            positions.append(position)
        self.portfolio_cache[user_id]["positions"] = positions

        # Stream to user
        room_id = f"portfolio:{user_id}"
        message = create_message("position_update", position)

        count = await self.connection_manager.broadcast_to_room(room_id, message)

        logger.debug(
            "position_update_streamed",
            user_id=user_id,
            symbol=symbol,
            pnl=pnl,
            subscribers=count,
        )

    async def stream_pnl_update(
        self,
        user_id: str,
        total_pnl: float,
        daily_pnl: float,
        unrealized_pnl: float,
        realized_pnl: float,
        **kwargs: Any,
    ) -> None:
        """
        Stream P&L update to user.

        Args:
            user_id: The user ID
            total_pnl: Total P&L
            daily_pnl: Daily P&L
            unrealized_pnl: Unrealized P&L
            realized_pnl: Realized P&L
            **kwargs: Additional P&L data
        """
        pnl_data = {
            "total_pnl": total_pnl,
            "daily_pnl": daily_pnl,
            "unrealized_pnl": unrealized_pnl,
            "realized_pnl": realized_pnl,
            "timestamp": datetime.utcnow().isoformat(),
            **kwargs,
        }

        # Update cache
        if user_id in self.portfolio_cache:
            self.portfolio_cache[user_id]["pnl"] = total_pnl

        # Stream to user
        room_id = f"portfolio:{user_id}"
        message = create_message("pnl_update", pnl_data)

        count = await self.connection_manager.broadcast_to_room(room_id, message)

        logger.debug(
            "pnl_update_streamed",
            user_id=user_id,
            total_pnl=total_pnl,
            daily_pnl=daily_pnl,
            subscribers=count,
        )

    async def stream_risk_alert(
        self,
        user_id: str,
        alert_type: str,
        severity: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """
        Stream a risk alert to user.

        Args:
            user_id: The user ID
            alert_type: Type of alert (drawdown, volatility, concentration, etc.)
            severity: Alert severity (info, warning, critical)
            message: Alert message
            details: Optional additional details
            **kwargs: Additional alert data
        """
        alert = {
            "alert_type": alert_type,
            "severity": severity,
            "message": message,
            "details": details or {},
            "timestamp": datetime.utcnow().isoformat(),
            **kwargs,
        }

        # Stream to user
        room_id = f"portfolio:{user_id}"
        message_obj = create_message("risk_alert", alert)

        count = await self.connection_manager.broadcast_to_room(
            room_id, message_obj
        )

        logger.warning(
            "risk_alert_streamed",
            user_id=user_id,
            alert_type=alert_type,
            severity=severity,
            subscribers=count,
        )

    async def stream_portfolio_summary(
        self,
        user_id: str,
        total_value: float,
        cash: float,
        positions_value: float,
        num_positions: int,
        **kwargs: Any,
    ) -> None:
        """
        Stream portfolio summary to user.

        Args:
            user_id: The user ID
            total_value: Total portfolio value
            cash: Cash balance
            positions_value: Total value of positions
            num_positions: Number of positions
            **kwargs: Additional summary data
        """
        summary = {
            "total_value": total_value,
            "cash": cash,
            "positions_value": positions_value,
            "num_positions": num_positions,
            "timestamp": datetime.utcnow().isoformat(),
            **kwargs,
        }

        # Update cache
        if user_id in self.portfolio_cache:
            self.portfolio_cache[user_id].update({
                "total_value": total_value,
                "cash": cash,
            })

        # Stream to user
        room_id = f"portfolio:{user_id}"
        message = create_message("portfolio_summary", summary)

        count = await self.connection_manager.broadcast_to_room(room_id, message)

        logger.debug(
            "portfolio_summary_streamed",
            user_id=user_id,
            total_value=total_value,
            subscribers=count,
        )

    async def stream_trade_notification(
        self,
        user_id: str,
        symbol: str,
        action: str,
        quantity: float,
        price: float,
        status: str,
        **kwargs: Any,
    ) -> None:
        """
        Stream trade notification to user.

        Args:
            user_id: The user ID
            symbol: The trading symbol
            action: Trade action (buy, sell)
            quantity: Trade quantity
            price: Trade price
            status: Trade status
            **kwargs: Additional trade data
        """
        trade = {
            "symbol": symbol,
            "action": action,
            "quantity": quantity,
            "price": price,
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
            **kwargs,
        }

        # Stream to user
        room_id = f"portfolio:{user_id}"
        message = create_message("trade_notification", trade)

        count = await self.connection_manager.broadcast_to_room(room_id, message)

        logger.info(
            "trade_notification_streamed",
            user_id=user_id,
            symbol=symbol,
            action=action,
            subscribers=count,
        )

    async def stream_performance_update(
        self,
        user_id: str,
        total_return: float,
        daily_return: float,
        sharpe_ratio: Optional[float] = None,
        max_drawdown: Optional[float] = None,
        **kwargs: Any,
    ) -> None:
        """
        Stream performance metrics update.

        Args:
            user_id: The user ID
            total_return: Total return percentage
            daily_return: Daily return percentage
            sharpe_ratio: Optional Sharpe ratio
            max_drawdown: Optional max drawdown percentage
            **kwargs: Additional performance data
        """
        performance = {
            "total_return": total_return,
            "daily_return": daily_return,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": max_drawdown,
            "timestamp": datetime.utcnow().isoformat(),
            **kwargs,
        }

        # Stream to user
        room_id = f"portfolio:{user_id}"
        message = create_message("performance_update", performance)

        await self.connection_manager.broadcast_to_room(room_id, message)

    def get_cached_portfolio(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get cached portfolio for a user.

        Args:
            user_id: The user ID

        Returns:
            Cached portfolio data or None
        """
        return self.portfolio_cache.get(user_id)

    def update_portfolio_cache(
        self,
        user_id: str,
        portfolio_data: Dict[str, Any],
    ) -> None:
        """
        Update the portfolio cache for a user.

        Args:
            user_id: The user ID
            portfolio_data: Portfolio data to cache
        """
        self.portfolio_cache[user_id] = portfolio_data
        logger.debug("portfolio_cache_updated", user_id=user_id)
