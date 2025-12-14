"""
Unit tests for WebSocket handlers.

Tests connection management, message handling, and streaming functionality.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from .handlers import ConnectionManager, create_message
from .mcts_stream import MCTSStreamHandler
from .market_stream import MarketStreamHandler
from .decision_stream import DecisionStreamHandler
from .portfolio_stream import PortfolioStreamHandler


class TestConnectionManager:
    """Test ConnectionManager functionality."""

    @pytest.fixture
    def manager(self):
        """Create a ConnectionManager instance."""
        return ConnectionManager()

    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket."""
        ws = AsyncMock()
        ws.accept = AsyncMock()
        ws.send_json = AsyncMock()
        ws.close = AsyncMock()
        return ws

    @pytest.mark.asyncio
    async def test_connect(self, manager, mock_websocket):
        """Test connecting a WebSocket."""
        connection_id = await manager.connect(
            mock_websocket,
            user_id="test_user",
            metadata={"test": "data"}
        )

        assert connection_id in manager.active_connections
        assert manager.connection_metadata[connection_id]["user_id"] == "test_user"
        assert manager.connection_metadata[connection_id]["test"] == "data"
        mock_websocket.accept.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect(self, manager, mock_websocket):
        """Test disconnecting a WebSocket."""
        connection_id = await manager.connect(mock_websocket, user_id="test_user")
        await manager.disconnect(connection_id)

        assert connection_id not in manager.active_connections
        assert connection_id not in manager.connection_metadata

    @pytest.mark.asyncio
    async def test_join_leave_room(self, manager, mock_websocket):
        """Test joining and leaving rooms."""
        connection_id = await manager.connect(mock_websocket)
        room_id = "test_room"

        manager.join_room(connection_id, room_id)
        assert connection_id in manager.rooms[room_id]

        manager.leave_room(connection_id, room_id)
        assert connection_id not in manager.rooms.get(room_id, set())

    @pytest.mark.asyncio
    async def test_send_personal_message(self, manager, mock_websocket):
        """Test sending a personal message."""
        connection_id = await manager.connect(mock_websocket)
        message = {"type": "test", "data": "Hello"}

        result = await manager.send_personal_message(connection_id, message)

        assert result is True
        mock_websocket.send_json.assert_called_once_with(message)

    @pytest.mark.asyncio
    async def test_broadcast_to_room(self, manager, mock_websocket):
        """Test broadcasting to a room."""
        # Connect two clients
        ws1 = AsyncMock()
        ws1.accept = AsyncMock()
        ws1.send_json = AsyncMock()

        ws2 = AsyncMock()
        ws2.accept = AsyncMock()
        ws2.send_json = AsyncMock()

        conn1 = await manager.connect(ws1)
        conn2 = await manager.connect(ws2)

        room_id = "test_room"
        manager.join_room(conn1, room_id)
        manager.join_room(conn2, room_id)

        message = {"type": "test", "data": "Broadcast"}
        count = await manager.broadcast_to_room(room_id, message)

        assert count == 2
        ws1.send_json.assert_called_once_with(message)
        ws2.send_json.assert_called_once_with(message)

    @pytest.mark.asyncio
    async def test_broadcast_to_user(self, manager, mock_websocket):
        """Test broadcasting to all connections of a user."""
        ws1 = AsyncMock()
        ws1.accept = AsyncMock()
        ws1.send_json = AsyncMock()

        ws2 = AsyncMock()
        ws2.accept = AsyncMock()
        ws2.send_json = AsyncMock()

        user_id = "test_user"
        await manager.connect(ws1, user_id=user_id)
        await manager.connect(ws2, user_id=user_id)

        message = {"type": "test", "data": "User broadcast"}
        count = await manager.broadcast_to_user(user_id, message)

        assert count == 2


class TestMCTSStreamHandler:
    """Test MCTSStreamHandler functionality."""

    @pytest.fixture
    def manager(self):
        """Create a ConnectionManager instance."""
        return ConnectionManager()

    @pytest.fixture
    def handler(self, manager):
        """Create an MCTSStreamHandler instance."""
        return MCTSStreamHandler(manager)

    @pytest.mark.asyncio
    async def test_stream_iteration_update(self, handler, manager):
        """Test streaming iteration updates."""
        # Setup
        search_id = "test_search"
        room_id = f"mcts:search:{search_id}"
        handler.search_rooms[search_id] = room_id

        ws = AsyncMock()
        ws.accept = AsyncMock()
        ws.send_json = AsyncMock()

        conn_id = await manager.connect(ws)
        manager.join_room(conn_id, room_id)

        # Stream update
        await handler.stream_iteration_update(
            search_id=search_id,
            iteration=50,
            total_iterations=100,
            best_action="BUY",
            best_value=0.85
        )

        # Verify message was sent
        assert ws.send_json.called
        call_args = ws.send_json.call_args[0][0]
        assert call_args["type"] == "iteration_update"
        assert call_args["data"]["iteration"] == 50
        assert call_args["data"]["best_action"] == "BUY"

    @pytest.mark.asyncio
    async def test_stream_search_completion(self, handler, manager):
        """Test streaming search completion."""
        search_id = "test_search"
        room_id = f"mcts:search:{search_id}"
        handler.search_rooms[search_id] = room_id
        handler.active_searches[search_id] = {"status": "running"}

        ws = AsyncMock()
        ws.accept = AsyncMock()
        ws.send_json = AsyncMock()

        conn_id = await manager.connect(ws)
        manager.join_room(conn_id, room_id)

        await handler.stream_search_completion(
            search_id=search_id,
            best_action="BUY",
            best_value=0.95,
            total_iterations=100,
            duration_seconds=10.0
        )

        assert ws.send_json.called
        assert handler.active_searches[search_id]["status"] == "completed"


class TestMarketStreamHandler:
    """Test MarketStreamHandler functionality."""

    @pytest.fixture
    def manager(self):
        """Create a ConnectionManager instance."""
        return ConnectionManager()

    @pytest.fixture
    def handler(self, manager):
        """Create a MarketStreamHandler instance."""
        return MarketStreamHandler(manager)

    @pytest.mark.asyncio
    async def test_stream_price_update(self, handler, manager):
        """Test streaming price updates."""
        symbol = "AAPL"
        room_id = f"market:{symbol}"

        ws = AsyncMock()
        ws.accept = AsyncMock()
        ws.send_json = AsyncMock()

        conn_id = await manager.connect(ws)
        manager.join_room(conn_id, room_id)

        await handler.stream_price_update(
            symbol=symbol,
            price=150.0,
            volume=1000.0
        )

        assert ws.send_json.called
        call_args = ws.send_json.call_args[0][0]
        assert call_args["type"] == "price_update"
        assert call_args["data"]["symbol"] == symbol
        assert call_args["data"]["price"] == 150.0

    @pytest.mark.asyncio
    async def test_stream_regime_change(self, handler, manager):
        """Test streaming regime changes."""
        symbol = "AAPL"
        room_id = f"market:{symbol}"

        ws = AsyncMock()
        ws.accept = AsyncMock()
        ws.send_json = AsyncMock()

        conn_id = await manager.connect(ws)
        manager.join_room(conn_id, room_id)

        await handler.stream_regime_change(
            symbol=symbol,
            old_regime="ranging",
            new_regime="bullish",
            confidence=0.92
        )

        assert ws.send_json.called
        call_args = ws.send_json.call_args[0][0]
        assert call_args["type"] == "regime_change"
        assert call_args["data"]["new_regime"] == "bullish"


class TestDecisionStreamHandler:
    """Test DecisionStreamHandler functionality."""

    @pytest.fixture
    def manager(self):
        """Create a ConnectionManager instance."""
        return ConnectionManager()

    @pytest.fixture
    def handler(self, manager):
        """Create a DecisionStreamHandler instance."""
        return DecisionStreamHandler(manager)

    @pytest.mark.asyncio
    async def test_stream_decision(self, handler, manager):
        """Test streaming trading decisions."""
        room_id = "decisions"

        ws = AsyncMock()
        ws.accept = AsyncMock()
        ws.send_json = AsyncMock()

        conn_id = await manager.connect(ws)
        manager.join_room(conn_id, room_id)

        await handler.stream_decision(
            decision_id="decision-123",
            symbol="AAPL",
            action="BUY",
            quantity=100.0,
            price=150.0,
            confidence=0.85
        )

        assert ws.send_json.called
        call_args = ws.send_json.call_args[0][0]
        assert call_args["type"] == "trading_decision"
        assert call_args["data"]["action"] == "BUY"
        assert len(handler.recent_decisions) == 1

    @pytest.mark.asyncio
    async def test_stream_execution(self, handler, manager):
        """Test streaming trade executions."""
        room_id = "decisions"

        ws = AsyncMock()
        ws.accept = AsyncMock()
        ws.send_json = AsyncMock()

        conn_id = await manager.connect(ws)
        manager.join_room(conn_id, room_id)

        await handler.stream_execution(
            execution_id="exec-456",
            decision_id="decision-123",
            symbol="AAPL",
            action="BUY",
            quantity=100.0,
            price=150.05,
            status="filled"
        )

        assert ws.send_json.called
        call_args = ws.send_json.call_args[0][0]
        assert call_args["type"] == "trade_execution"
        assert call_args["data"]["status"] == "filled"


class TestPortfolioStreamHandler:
    """Test PortfolioStreamHandler functionality."""

    @pytest.fixture
    def manager(self):
        """Create a ConnectionManager instance."""
        return ConnectionManager()

    @pytest.fixture
    def handler(self, manager):
        """Create a PortfolioStreamHandler instance."""
        return PortfolioStreamHandler(manager)

    @pytest.mark.asyncio
    async def test_stream_position_update(self, handler, manager):
        """Test streaming position updates."""
        user_id = "user-123"
        room_id = f"portfolio:{user_id}"

        ws = AsyncMock()
        ws.accept = AsyncMock()
        ws.send_json = AsyncMock()

        conn_id = await manager.connect(ws, user_id=user_id)
        manager.join_room(conn_id, room_id)

        await handler.stream_position_update(
            user_id=user_id,
            symbol="AAPL",
            quantity=100.0,
            entry_price=150.0,
            current_price=152.0,
            pnl=200.0,
            pnl_percent=1.33
        )

        assert ws.send_json.called
        call_args = ws.send_json.call_args[0][0]
        assert call_args["type"] == "position_update"
        assert call_args["data"]["pnl"] == 200.0

    @pytest.mark.asyncio
    async def test_stream_risk_alert(self, handler, manager):
        """Test streaming risk alerts."""
        user_id = "user-123"
        room_id = f"portfolio:{user_id}"

        ws = AsyncMock()
        ws.accept = AsyncMock()
        ws.send_json = AsyncMock()

        conn_id = await manager.connect(ws, user_id=user_id)
        manager.join_room(conn_id, room_id)

        await handler.stream_risk_alert(
            user_id=user_id,
            alert_type="drawdown",
            severity="warning",
            message="Portfolio drawdown exceeds 5%"
        )

        assert ws.send_json.called
        call_args = ws.send_json.call_args[0][0]
        assert call_args["type"] == "risk_alert"
        assert call_args["data"]["severity"] == "warning"


class TestMessageFormat:
    """Test message formatting utilities."""

    def test_create_message(self):
        """Test create_message utility."""
        message = create_message(
            "test_type",
            {"key": "value"},
            metadata={"meta": "data"}
        )

        assert message["type"] == "test_type"
        assert message["data"]["key"] == "value"
        assert message["metadata"]["meta"] == "data"
        assert "timestamp" in message


# Run tests with: pytest test_websockets.py -v
