"""
Real-time market data streaming.

Streams price updates, technical indicators, and market regime changes
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


class MarketStreamHandler:
    """
    Handler for streaming real-time market data to WebSocket clients.

    Features:
    - Real-time price updates
    - Technical indicator updates
    - Market regime change notifications
    - Symbol-based subscriptions
    """

    def __init__(self, connection_manager: ConnectionManager):
        """
        Initialize the market stream handler.

        Args:
            connection_manager: The connection manager instance
        """
        self.connection_manager = connection_manager

        # Subscription tracking (connection_id -> set of symbols)
        self.subscriptions: Dict[str, set] = {}

        logger.info("market_stream_handler_initialized")

    async def handle_connection(
        self,
        websocket: WebSocket,
        symbol: str,
        token: Optional[str] = None,
    ) -> None:
        """
        Handle a WebSocket connection for market data updates.

        Args:
            websocket: The WebSocket connection
            symbol: The trading symbol
            token: Optional authentication token
        """
        # Authenticate
        user_id = await authenticate_websocket(websocket, token)

        # Connect
        connection_id = await self.connection_manager.connect(
            websocket,
            user_id=user_id,
            metadata={"type": "market", "symbol": symbol},
        )

        # Join symbol-specific room
        room_id = f"market:{symbol}"
        self.connection_manager.join_room(connection_id, room_id)

        # Track subscription
        if connection_id not in self.subscriptions:
            self.subscriptions[connection_id] = set()
        self.subscriptions[connection_id].add(symbol)

        # Send welcome message
        welcome_message = create_message(
            "connected",
            {
                "connection_id": connection_id,
                "symbol": symbol,
                "message": "Connected to market data stream",
                "subscriptions": list(self.subscriptions[connection_id]),
            },
        )
        await self.connection_manager.send_personal_message(
            connection_id, welcome_message
        )

        logger.info(
            "market_stream_connected",
            connection_id=connection_id,
            symbol=symbol,
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
            # Clean up subscriptions
            self.subscriptions.pop(connection_id, None)
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

        if command == "subscribe":
            await self._handle_subscribe(connection_id, message)

        elif command == "unsubscribe":
            await self._handle_unsubscribe(connection_id, message)

        elif command == "get_subscriptions":
            await self._handle_get_subscriptions(connection_id)

        elif command == "get_snapshot":
            await self._handle_get_snapshot(connection_id, message)

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

    async def _handle_subscribe(
        self,
        connection_id: str,
        message: Dict[str, Any],
    ) -> None:
        """
        Handle subscribe command.

        Args:
            connection_id: The connection ID
            message: The command message
        """
        symbols = message.get("symbols", [])

        if not symbols:
            error_message = create_message(
                "error",
                {"error": "No symbols provided"},
            )
            await self.connection_manager.send_personal_message(
                connection_id, error_message
            )
            return

        # Add symbols to subscription
        if connection_id not in self.subscriptions:
            self.subscriptions[connection_id] = set()

        for symbol in symbols:
            self.subscriptions[connection_id].add(symbol)
            room_id = f"market:{symbol}"
            self.connection_manager.join_room(connection_id, room_id)

        logger.info(
            "market_subscribed",
            connection_id=connection_id,
            symbols=symbols,
        )

        # Send confirmation
        response = create_message(
            "subscribed",
            {
                "symbols": symbols,
                "all_subscriptions": list(self.subscriptions[connection_id]),
            },
        )
        await self.connection_manager.send_personal_message(
            connection_id, response
        )

    async def _handle_unsubscribe(
        self,
        connection_id: str,
        message: Dict[str, Any],
    ) -> None:
        """
        Handle unsubscribe command.

        Args:
            connection_id: The connection ID
            message: The command message
        """
        symbols = message.get("symbols", [])

        if not symbols or connection_id not in self.subscriptions:
            return

        # Remove symbols from subscription
        for symbol in symbols:
            self.subscriptions[connection_id].discard(symbol)
            room_id = f"market:{symbol}"
            self.connection_manager.leave_room(connection_id, room_id)

        logger.info(
            "market_unsubscribed",
            connection_id=connection_id,
            symbols=symbols,
        )

        # Send confirmation
        response = create_message(
            "unsubscribed",
            {
                "symbols": symbols,
                "remaining_subscriptions": list(self.subscriptions[connection_id]),
            },
        )
        await self.connection_manager.send_personal_message(
            connection_id, response
        )

    async def _handle_get_subscriptions(
        self,
        connection_id: str,
    ) -> None:
        """
        Handle get subscriptions command.

        Args:
            connection_id: The connection ID
        """
        subscriptions = list(self.subscriptions.get(connection_id, set()))

        response = create_message(
            "subscriptions",
            {"symbols": subscriptions},
        )
        await self.connection_manager.send_personal_message(
            connection_id, response
        )

    async def _handle_get_snapshot(
        self,
        connection_id: str,
        message: Dict[str, Any],
    ) -> None:
        """
        Handle get snapshot command.

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

        # TODO: Fetch current market snapshot from data source
        # This is a placeholder
        snapshot = {
            "symbol": symbol,
            "price": 0.0,
            "timestamp": datetime.utcnow().isoformat(),
            "indicators": {},
            "regime": "unknown",
        }

        response = create_message("snapshot", snapshot)
        await self.connection_manager.send_personal_message(
            connection_id, response
        )

    async def stream_price_update(
        self,
        symbol: str,
        price: float,
        volume: Optional[float] = None,
        timestamp: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """
        Stream a price update to subscribers.

        Args:
            symbol: The trading symbol
            price: The current price
            volume: Optional trade volume
            timestamp: Optional timestamp (defaults to now)
            **kwargs: Additional price data
        """
        room_id = f"market:{symbol}"

        message = create_message(
            "price_update",
            {
                "symbol": symbol,
                "price": price,
                "volume": volume,
                "timestamp": timestamp or datetime.utcnow().isoformat(),
                **kwargs,
            },
        )

        count = await self.connection_manager.broadcast_to_room(room_id, message)

        logger.debug(
            "price_update_streamed",
            symbol=symbol,
            price=price,
            subscribers=count,
        )

    async def stream_indicator_update(
        self,
        symbol: str,
        indicators: Dict[str, float],
        timestamp: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """
        Stream technical indicator updates.

        Args:
            symbol: The trading symbol
            indicators: Dictionary of indicator values
            timestamp: Optional timestamp (defaults to now)
            **kwargs: Additional indicator data
        """
        room_id = f"market:{symbol}"

        message = create_message(
            "indicator_update",
            {
                "symbol": symbol,
                "indicators": indicators,
                "timestamp": timestamp or datetime.utcnow().isoformat(),
                **kwargs,
            },
        )

        count = await self.connection_manager.broadcast_to_room(room_id, message)

        logger.debug(
            "indicator_update_streamed",
            symbol=symbol,
            indicators=list(indicators.keys()),
            subscribers=count,
        )

    async def stream_regime_change(
        self,
        symbol: str,
        old_regime: str,
        new_regime: str,
        confidence: Optional[float] = None,
        timestamp: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """
        Stream market regime change notification.

        Args:
            symbol: The trading symbol
            old_regime: The previous regime
            new_regime: The new regime
            confidence: Optional confidence score
            timestamp: Optional timestamp (defaults to now)
            **kwargs: Additional regime data
        """
        room_id = f"market:{symbol}"

        message = create_message(
            "regime_change",
            {
                "symbol": symbol,
                "old_regime": old_regime,
                "new_regime": new_regime,
                "confidence": confidence,
                "timestamp": timestamp or datetime.utcnow().isoformat(),
                **kwargs,
            },
        )

        count = await self.connection_manager.broadcast_to_room(room_id, message)

        logger.info(
            "regime_change_streamed",
            symbol=symbol,
            old_regime=old_regime,
            new_regime=new_regime,
            subscribers=count,
        )

    async def stream_ohlcv_update(
        self,
        symbol: str,
        open_price: float,
        high_price: float,
        low_price: float,
        close_price: float,
        volume: float,
        interval: str,
        timestamp: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """
        Stream OHLCV (candlestick) data update.

        Args:
            symbol: The trading symbol
            open_price: Opening price
            high_price: High price
            low_price: Low price
            close_price: Closing price
            volume: Trading volume
            interval: Time interval (e.g., "1m", "5m", "1h")
            timestamp: Optional timestamp (defaults to now)
            **kwargs: Additional OHLCV data
        """
        room_id = f"market:{symbol}"

        message = create_message(
            "ohlcv_update",
            {
                "symbol": symbol,
                "open": open_price,
                "high": high_price,
                "low": low_price,
                "close": close_price,
                "volume": volume,
                "interval": interval,
                "timestamp": timestamp or datetime.utcnow().isoformat(),
                **kwargs,
            },
        )

        await self.connection_manager.broadcast_to_room(room_id, message)

    async def stream_orderbook_update(
        self,
        symbol: str,
        bids: List[List[float]],
        asks: List[List[float]],
        timestamp: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """
        Stream order book update.

        Args:
            symbol: The trading symbol
            bids: List of [price, quantity] bid levels
            asks: List of [price, quantity] ask levels
            timestamp: Optional timestamp (defaults to now)
            **kwargs: Additional order book data
        """
        room_id = f"market:{symbol}"

        message = create_message(
            "orderbook_update",
            {
                "symbol": symbol,
                "bids": bids,
                "asks": asks,
                "timestamp": timestamp or datetime.utcnow().isoformat(),
                **kwargs,
            },
        )

        await self.connection_manager.broadcast_to_room(room_id, message)

    def get_subscriber_count(self, symbol: str) -> int:
        """
        Get the number of subscribers for a symbol.

        Args:
            symbol: The trading symbol

        Returns:
            Number of active subscribers
        """
        room_id = f"market:{symbol}"
        connections = self.connection_manager.get_room_connections(room_id)
        return len(connections)

    def get_all_subscribed_symbols(self) -> set:
        """
        Get all symbols that have active subscriptions.

        Returns:
            Set of subscribed symbols
        """
        all_symbols = set()
        for symbols in self.subscriptions.values():
            all_symbols.update(symbols)
        return all_symbols
