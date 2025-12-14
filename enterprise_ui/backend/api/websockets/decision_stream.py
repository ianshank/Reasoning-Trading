"""
Trading decision streaming.

Streams real-time trading decisions, trade executions, and regime-triggered
updates to connected clients.
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


class DecisionStreamHandler:
    """
    Handler for streaming trading decisions to WebSocket clients.

    Features:
    - Real-time trading decisions
    - Trade execution notifications
    - Regime-triggered updates
    - Decision rationale and metadata
    """

    def __init__(self, connection_manager: ConnectionManager):
        """
        Initialize the decision stream handler.

        Args:
            connection_manager: The connection manager instance
        """
        self.connection_manager = connection_manager

        # Track decision history (for replay/catch-up)
        self.recent_decisions: List[Dict[str, Any]] = []
        self.max_history_size = 100

        logger.info("decision_stream_handler_initialized")

    async def handle_connection(
        self,
        websocket: WebSocket,
        token: Optional[str] = None,
    ) -> None:
        """
        Handle a WebSocket connection for trading decisions.

        Args:
            websocket: The WebSocket connection
            token: Optional authentication token
        """
        # Authenticate
        user_id = await authenticate_websocket(websocket, token)

        # Connect
        connection_id = await self.connection_manager.connect(
            websocket,
            user_id=user_id,
            metadata={"type": "decision"},
        )

        # Join decisions room
        room_id = "decisions"
        self.connection_manager.join_room(connection_id, room_id)

        # Send welcome message with recent decisions
        welcome_message = create_message(
            "connected",
            {
                "connection_id": connection_id,
                "message": "Connected to trading decisions stream",
                "recent_decisions": self.recent_decisions[-10:],  # Last 10
            },
        )
        await self.connection_manager.send_personal_message(
            connection_id, welcome_message
        )

        logger.info(
            "decision_stream_connected",
            connection_id=connection_id,
            user_id=user_id,
        )

        try:
            # Message handling loop
            while True:
                try:
                    # Receive message from client
                    data = await websocket.receive_json()

                    await self._handle_client_message(connection_id, data)

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
        message: Dict[str, Any],
    ) -> None:
        """
        Handle messages from clients.

        Args:
            connection_id: The connection ID
            message: The message from client
        """
        command = message.get("command")

        if command == "get_recent":
            await self._handle_get_recent(connection_id, message)

        elif command == "get_decision":
            await self._handle_get_decision(connection_id, message)

        elif command == "filter_by_symbol":
            await self._handle_filter_by_symbol(connection_id, message)

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

    async def _handle_get_recent(
        self,
        connection_id: str,
        message: Dict[str, Any],
    ) -> None:
        """
        Handle get recent decisions command.

        Args:
            connection_id: The connection ID
            message: The command message
        """
        limit = message.get("limit", 20)
        limit = min(limit, 100)  # Cap at 100

        response = create_message(
            "recent_decisions",
            {"decisions": self.recent_decisions[-limit:]},
        )
        await self.connection_manager.send_personal_message(
            connection_id, response
        )

    async def _handle_get_decision(
        self,
        connection_id: str,
        message: Dict[str, Any],
    ) -> None:
        """
        Handle get specific decision command.

        Args:
            connection_id: The connection ID
            message: The command message
        """
        decision_id = message.get("decision_id")

        if not decision_id:
            error_message = create_message(
                "error",
                {"error": "No decision_id provided"},
            )
            await self.connection_manager.send_personal_message(
                connection_id, error_message
            )
            return

        # Find decision in history
        decision = next(
            (d for d in self.recent_decisions if d.get("decision_id") == decision_id),
            None,
        )

        if decision:
            response = create_message("decision", decision)
        else:
            response = create_message(
                "error",
                {"error": f"Decision {decision_id} not found"},
            )

        await self.connection_manager.send_personal_message(
            connection_id, response
        )

    async def _handle_filter_by_symbol(
        self,
        connection_id: str,
        message: Dict[str, Any],
    ) -> None:
        """
        Handle filter decisions by symbol command.

        Args:
            connection_id: The connection ID
            message: The command message
        """
        symbol = message.get("symbol")

        if not symbol:
            error_message = create_message(
                "error",
                {"error": "No symbol provided"},
            )
            await self.connection_manager.send_personal_message(
                connection_id, error_message
            )
            return

        # Filter decisions by symbol
        filtered = [
            d for d in self.recent_decisions
            if d.get("symbol") == symbol
        ]

        response = create_message(
            "filtered_decisions",
            {
                "symbol": symbol,
                "decisions": filtered,
            },
        )
        await self.connection_manager.send_personal_message(
            connection_id, response
        )

    async def stream_decision(
        self,
        decision_id: str,
        symbol: str,
        action: str,
        quantity: Optional[float] = None,
        price: Optional[float] = None,
        rationale: Optional[str] = None,
        confidence: Optional[float] = None,
        regime: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """
        Stream a trading decision to subscribers.

        Args:
            decision_id: Unique decision identifier
            symbol: The trading symbol
            action: The trading action (buy, sell, hold)
            quantity: Optional quantity
            price: Optional target price
            rationale: Optional decision rationale
            confidence: Optional confidence score
            regime: Optional market regime
            metadata: Optional additional metadata
            **kwargs: Additional decision data
        """
        decision = {
            "decision_id": decision_id,
            "symbol": symbol,
            "action": action,
            "quantity": quantity,
            "price": price,
            "rationale": rationale,
            "confidence": confidence,
            "regime": regime,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {},
            **kwargs,
        }

        # Add to history
        self.recent_decisions.append(decision)
        if len(self.recent_decisions) > self.max_history_size:
            self.recent_decisions.pop(0)

        # Broadcast to all decision subscribers
        room_id = "decisions"
        message = create_message("trading_decision", decision)

        count = await self.connection_manager.broadcast_to_room(room_id, message)

        logger.info(
            "decision_streamed",
            decision_id=decision_id,
            symbol=symbol,
            action=action,
            subscribers=count,
        )

    async def stream_execution(
        self,
        execution_id: str,
        decision_id: str,
        symbol: str,
        action: str,
        quantity: float,
        price: float,
        status: str,
        error: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """
        Stream trade execution notification.

        Args:
            execution_id: Unique execution identifier
            decision_id: Associated decision ID
            symbol: The trading symbol
            action: The trading action
            quantity: Executed quantity
            price: Execution price
            status: Execution status (pending, filled, partial, failed, cancelled)
            error: Optional error message if failed
            **kwargs: Additional execution data
        """
        execution = {
            "execution_id": execution_id,
            "decision_id": decision_id,
            "symbol": symbol,
            "action": action,
            "quantity": quantity,
            "price": price,
            "status": status,
            "error": error,
            "timestamp": datetime.utcnow().isoformat(),
            **kwargs,
        }

        # Broadcast to all decision subscribers
        room_id = "decisions"
        message = create_message("trade_execution", execution)

        count = await self.connection_manager.broadcast_to_room(room_id, message)

        logger.info(
            "execution_streamed",
            execution_id=execution_id,
            decision_id=decision_id,
            symbol=symbol,
            status=status,
            subscribers=count,
        )

    async def stream_regime_triggered_decision(
        self,
        decision_id: str,
        symbol: str,
        old_regime: str,
        new_regime: str,
        action: str,
        rationale: str,
        **kwargs: Any,
    ) -> None:
        """
        Stream a regime-triggered trading decision.

        Args:
            decision_id: Unique decision identifier
            symbol: The trading symbol
            old_regime: Previous market regime
            new_regime: New market regime
            action: The trading action
            rationale: Decision rationale
            **kwargs: Additional decision data
        """
        decision = {
            "decision_id": decision_id,
            "symbol": symbol,
            "trigger": "regime_change",
            "old_regime": old_regime,
            "new_regime": new_regime,
            "action": action,
            "rationale": rationale,
            "timestamp": datetime.utcnow().isoformat(),
            **kwargs,
        }

        # Add to history
        self.recent_decisions.append(decision)
        if len(self.recent_decisions) > self.max_history_size:
            self.recent_decisions.pop(0)

        # Broadcast to all decision subscribers
        room_id = "decisions"
        message = create_message("regime_triggered_decision", decision)

        count = await self.connection_manager.broadcast_to_room(room_id, message)

        logger.info(
            "regime_decision_streamed",
            decision_id=decision_id,
            symbol=symbol,
            old_regime=old_regime,
            new_regime=new_regime,
            action=action,
            subscribers=count,
        )

    async def stream_signal(
        self,
        signal_id: str,
        symbol: str,
        signal_type: str,
        strength: float,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """
        Stream a trading signal.

        Args:
            signal_id: Unique signal identifier
            symbol: The trading symbol
            signal_type: Type of signal (bullish, bearish, neutral, etc.)
            strength: Signal strength (0-1)
            description: Optional signal description
            metadata: Optional additional metadata
            **kwargs: Additional signal data
        """
        signal = {
            "signal_id": signal_id,
            "symbol": symbol,
            "signal_type": signal_type,
            "strength": strength,
            "description": description,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {},
            **kwargs,
        }

        # Broadcast to all decision subscribers
        room_id = "decisions"
        message = create_message("trading_signal", signal)

        count = await self.connection_manager.broadcast_to_room(room_id, message)

        logger.debug(
            "signal_streamed",
            signal_id=signal_id,
            symbol=symbol,
            signal_type=signal_type,
            subscribers=count,
        )

    def get_decision_count(self) -> int:
        """
        Get the total number of decisions in history.

        Returns:
            Number of decisions in history
        """
        return len(self.recent_decisions)

    def clear_history(self) -> None:
        """Clear the decision history."""
        self.recent_decisions.clear()
        logger.info("decision_history_cleared")
