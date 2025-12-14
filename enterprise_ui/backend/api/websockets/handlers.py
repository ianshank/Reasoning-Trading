"""
WebSocket connection management and utilities.

Provides centralized connection management, room-based subscriptions,
broadcast utilities, and heartbeat handling for all WebSocket endpoints.
"""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4

from fastapi import WebSocket, WebSocketDisconnect
from structlog import get_logger

logger = get_logger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections with room-based subscriptions.

    Features:
    - Connection lifecycle management
    - Room-based message broadcasting
    - Per-connection metadata
    - Heartbeat/ping-pong support
    - Graceful shutdown handling
    """

    def __init__(self):
        """Initialize the connection manager."""
        # Active connections by connection ID
        self.active_connections: Dict[str, WebSocket] = {}

        # Connection metadata
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}

        # Room subscriptions (room -> set of connection IDs)
        self.rooms: Dict[str, Set[str]] = {}

        # User connections (user_id -> set of connection IDs)
        self.user_connections: Dict[str, Set[str]] = {}

        # Heartbeat tracking
        self.last_heartbeat: Dict[str, float] = {}

        # Shutdown flag
        self._shutdown = False

        logger.info("connection_manager_initialized")

    async def connect(
        self,
        websocket: WebSocket,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Accept a new WebSocket connection.

        Args:
            websocket: The WebSocket connection
            user_id: Optional user identifier
            metadata: Optional connection metadata

        Returns:
            Connection ID
        """
        await websocket.accept()

        connection_id = str(uuid4())
        self.active_connections[connection_id] = websocket

        # Store metadata
        self.connection_metadata[connection_id] = {
            "user_id": user_id,
            "connected_at": datetime.utcnow().isoformat(),
            "last_message": None,
            **(metadata or {}),
        }

        # Track user connections
        if user_id:
            if user_id not in self.user_connections:
                self.user_connections[user_id] = set()
            self.user_connections[user_id].add(connection_id)

        logger.info(
            "websocket_connected",
            connection_id=connection_id,
            user_id=user_id,
            total_connections=len(self.active_connections),
        )

        return connection_id

    async def disconnect(self, connection_id: str) -> None:
        """
        Disconnect a WebSocket connection and clean up.

        Args:
            connection_id: The connection to disconnect
        """
        if connection_id not in self.active_connections:
            return

        # Remove from all rooms
        for room_id in list(self.rooms.keys()):
            self.leave_room(connection_id, room_id)

        # Get metadata before cleanup
        metadata = self.connection_metadata.get(connection_id, {})
        user_id = metadata.get("user_id")

        # Remove from user connections
        if user_id and user_id in self.user_connections:
            self.user_connections[user_id].discard(connection_id)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]

        # Clean up connection data
        del self.active_connections[connection_id]
        self.connection_metadata.pop(connection_id, None)
        self.last_heartbeat.pop(connection_id, None)

        logger.info(
            "websocket_disconnected",
            connection_id=connection_id,
            user_id=user_id,
            total_connections=len(self.active_connections),
        )

    def join_room(self, connection_id: str, room_id: str) -> None:
        """
        Add a connection to a room.

        Args:
            connection_id: The connection ID
            room_id: The room identifier
        """
        if room_id not in self.rooms:
            self.rooms[room_id] = set()

        self.rooms[room_id].add(connection_id)

        logger.debug(
            "joined_room",
            connection_id=connection_id,
            room_id=room_id,
            room_size=len(self.rooms[room_id]),
        )

    def leave_room(self, connection_id: str, room_id: str) -> None:
        """
        Remove a connection from a room.

        Args:
            connection_id: The connection ID
            room_id: The room identifier
        """
        if room_id in self.rooms:
            self.rooms[room_id].discard(connection_id)

            # Clean up empty rooms
            if not self.rooms[room_id]:
                del self.rooms[room_id]
                logger.debug("room_deleted", room_id=room_id)
            else:
                logger.debug(
                    "left_room",
                    connection_id=connection_id,
                    room_id=room_id,
                    room_size=len(self.rooms[room_id]),
                )

    async def send_personal_message(
        self,
        connection_id: str,
        message: Dict[str, Any],
    ) -> bool:
        """
        Send a message to a specific connection.

        Args:
            connection_id: The target connection
            message: The message to send

        Returns:
            True if sent successfully, False otherwise
        """
        if connection_id not in self.active_connections:
            logger.warning("connection_not_found", connection_id=connection_id)
            return False

        websocket = self.active_connections[connection_id]

        try:
            await websocket.send_json(message)

            # Update last message time
            if connection_id in self.connection_metadata:
                self.connection_metadata[connection_id]["last_message"] = (
                    datetime.utcnow().isoformat()
                )

            logger.debug(
                "message_sent",
                connection_id=connection_id,
                message_type=message.get("type"),
            )
            return True

        except Exception as e:
            logger.error(
                "send_message_failed",
                connection_id=connection_id,
                error=str(e),
                exc_info=True,
            )
            await self.disconnect(connection_id)
            return False

    async def broadcast_to_room(
        self,
        room_id: str,
        message: Dict[str, Any],
        exclude: Optional[Set[str]] = None,
    ) -> int:
        """
        Broadcast a message to all connections in a room.

        Args:
            room_id: The room to broadcast to
            message: The message to send
            exclude: Optional set of connection IDs to exclude

        Returns:
            Number of successful sends
        """
        if room_id not in self.rooms:
            logger.debug("room_not_found", room_id=room_id)
            return 0

        exclude = exclude or set()
        connections = self.rooms[room_id] - exclude

        success_count = 0
        failed_connections = []

        for connection_id in connections:
            if await self.send_personal_message(connection_id, message):
                success_count += 1
            else:
                failed_connections.append(connection_id)

        logger.debug(
            "broadcast_completed",
            room_id=room_id,
            total=len(connections),
            success=success_count,
            failed=len(failed_connections),
        )

        return success_count

    async def broadcast_to_user(
        self,
        user_id: str,
        message: Dict[str, Any],
    ) -> int:
        """
        Broadcast a message to all connections of a user.

        Args:
            user_id: The user ID
            message: The message to send

        Returns:
            Number of successful sends
        """
        if user_id not in self.user_connections:
            logger.debug("user_not_connected", user_id=user_id)
            return 0

        connections = self.user_connections[user_id].copy()
        success_count = 0

        for connection_id in connections:
            if await self.send_personal_message(connection_id, message):
                success_count += 1

        logger.debug(
            "user_broadcast_completed",
            user_id=user_id,
            connections=len(connections),
            success=success_count,
        )

        return success_count

    async def broadcast_all(
        self,
        message: Dict[str, Any],
        exclude: Optional[Set[str]] = None,
    ) -> int:
        """
        Broadcast a message to all active connections.

        Args:
            message: The message to send
            exclude: Optional set of connection IDs to exclude

        Returns:
            Number of successful sends
        """
        exclude = exclude or set()
        connections = set(self.active_connections.keys()) - exclude

        success_count = 0

        for connection_id in connections:
            if await self.send_personal_message(connection_id, message):
                success_count += 1

        logger.debug(
            "broadcast_all_completed",
            total=len(connections),
            success=success_count,
        )

        return success_count

    async def send_heartbeat(self, connection_id: str) -> bool:
        """
        Send a heartbeat ping to a connection.

        Args:
            connection_id: The connection to ping

        Returns:
            True if sent successfully
        """
        message = {
            "type": "ping",
            "timestamp": datetime.utcnow().isoformat(),
        }

        result = await self.send_personal_message(connection_id, message)

        if result:
            self.last_heartbeat[connection_id] = asyncio.get_event_loop().time()

        return result

    async def heartbeat_loop(
        self,
        interval: int = 30,
        timeout: int = 60,
    ) -> None:
        """
        Background task to send periodic heartbeats and detect stale connections.

        Args:
            interval: Seconds between heartbeats
            timeout: Seconds before considering a connection stale
        """
        logger.info("heartbeat_loop_started", interval=interval, timeout=timeout)

        while not self._shutdown:
            try:
                current_time = asyncio.get_event_loop().time()
                stale_connections = []

                for connection_id in list(self.active_connections.keys()):
                    # Check if connection is stale
                    last_hb = self.last_heartbeat.get(connection_id, 0)

                    if current_time - last_hb > timeout:
                        stale_connections.append(connection_id)
                    else:
                        # Send heartbeat
                        await self.send_heartbeat(connection_id)

                # Disconnect stale connections
                for connection_id in stale_connections:
                    logger.warning(
                        "stale_connection_detected",
                        connection_id=connection_id,
                    )
                    await self.disconnect(connection_id)

                await asyncio.sleep(interval)

            except Exception as e:
                logger.error(
                    "heartbeat_loop_error",
                    error=str(e),
                    exc_info=True,
                )
                await asyncio.sleep(interval)

        logger.info("heartbeat_loop_stopped")

    def get_connection_count(self) -> int:
        """Get the total number of active connections."""
        return len(self.active_connections)

    def get_room_count(self) -> int:
        """Get the total number of active rooms."""
        return len(self.rooms)

    def get_room_connections(self, room_id: str) -> List[str]:
        """
        Get all connection IDs in a room.

        Args:
            room_id: The room identifier

        Returns:
            List of connection IDs
        """
        return list(self.rooms.get(room_id, set()))

    def get_user_connections(self, user_id: str) -> List[str]:
        """
        Get all connection IDs for a user.

        Args:
            user_id: The user identifier

        Returns:
            List of connection IDs
        """
        return list(self.user_connections.get(user_id, set()))

    def get_metadata(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a connection.

        Args:
            connection_id: The connection identifier

        Returns:
            Connection metadata or None
        """
        return self.connection_metadata.get(connection_id)

    async def shutdown(self) -> None:
        """Gracefully shutdown all connections."""
        logger.info("shutdown_initiated", connections=len(self.active_connections))

        self._shutdown = True

        # Send shutdown message to all connections
        shutdown_message = {
            "type": "shutdown",
            "message": "Server is shutting down",
            "timestamp": datetime.utcnow().isoformat(),
        }

        await self.broadcast_all(shutdown_message)

        # Close all connections
        for connection_id in list(self.active_connections.keys()):
            try:
                websocket = self.active_connections[connection_id]
                await websocket.close()
            except Exception as e:
                logger.error(
                    "shutdown_connection_error",
                    connection_id=connection_id,
                    error=str(e),
                )

            await self.disconnect(connection_id)

        logger.info("shutdown_completed")


# Global connection manager instance
connection_manager = ConnectionManager()


async def handle_websocket_errors(
    websocket: WebSocket,
    connection_id: str,
    error: Exception,
) -> None:
    """
    Handle WebSocket errors and send error messages.

    Args:
        websocket: The WebSocket connection
        connection_id: The connection identifier
        error: The error that occurred
    """
    error_message = {
        "type": "error",
        "error": str(error),
        "timestamp": datetime.utcnow().isoformat(),
    }

    try:
        await websocket.send_json(error_message)
    except Exception as send_error:
        logger.error(
            "error_message_send_failed",
            connection_id=connection_id,
            original_error=str(error),
            send_error=str(send_error),
        )


async def authenticate_websocket(
    websocket: WebSocket,
    token: Optional[str] = None,
) -> Optional[str]:
    """
    Authenticate a WebSocket connection.

    This is a placeholder for actual authentication logic.
    In production, this should validate JWT tokens or session tokens.

    Args:
        websocket: The WebSocket connection
        token: Optional authentication token

    Returns:
        User ID if authenticated, None otherwise
    """
    # TODO: Implement actual authentication logic
    # For now, return a placeholder user ID

    if token:
        # In production, validate the token and extract user ID
        logger.debug("websocket_auth_attempted", token_length=len(token))
        return "user_placeholder"

    logger.debug("websocket_auth_skipped")
    return None


def create_message(
    message_type: str,
    data: Any,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Create a standardized WebSocket message.

    Args:
        message_type: The message type
        data: The message data
        metadata: Optional metadata

    Returns:
        Formatted message dictionary
    """
    message = {
        "type": message_type,
        "data": data,
        "timestamp": datetime.utcnow().isoformat(),
    }

    if metadata:
        message["metadata"] = metadata

    return message
