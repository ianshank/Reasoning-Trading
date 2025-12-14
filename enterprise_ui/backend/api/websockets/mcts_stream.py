"""
Real-time MCTS search progress streaming.

Streams MCTS iteration progress, node expansion events, backpropagation updates,
and search completion notifications to connected clients.
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import uuid4

from fastapi import WebSocket, WebSocketDisconnect
from structlog import get_logger

from .handlers import (
    ConnectionManager,
    authenticate_websocket,
    create_message,
    handle_websocket_errors,
)

logger = get_logger(__name__)


class MCTSStreamHandler:
    """
    Handler for streaming MCTS search progress to WebSocket clients.

    Features:
    - Real-time iteration updates
    - Node expansion events
    - Backpropagation tracking
    - Search completion notifications
    - Client control commands (start, stop, configure)
    """

    def __init__(self, connection_manager: ConnectionManager):
        """
        Initialize the MCTS stream handler.

        Args:
            connection_manager: The connection manager instance
        """
        self.connection_manager = connection_manager

        # Active searches (search_id -> search metadata)
        self.active_searches: Dict[str, Dict[str, Any]] = {}

        # Search room mapping (search_id -> room_id)
        self.search_rooms: Dict[str, str] = {}

        # Search tasks (search_id -> asyncio.Task)
        self.search_tasks: Dict[str, asyncio.Task] = {}

        logger.info("mcts_stream_handler_initialized")

    async def handle_connection(
        self,
        websocket: WebSocket,
        symbol: str,
        token: Optional[str] = None,
    ) -> None:
        """
        Handle a WebSocket connection for MCTS updates.

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
            metadata={"type": "mcts", "symbol": symbol},
        )

        # Join symbol-specific room
        room_id = f"mcts:{symbol}"
        self.connection_manager.join_room(connection_id, room_id)

        # Send welcome message
        welcome_message = create_message(
            "connected",
            {
                "connection_id": connection_id,
                "symbol": symbol,
                "message": "Connected to MCTS stream",
            },
        )
        await self.connection_manager.send_personal_message(
            connection_id, welcome_message
        )

        try:
            # Message handling loop
            while True:
                try:
                    # Receive message from client
                    data = await websocket.receive_json()

                    await self._handle_client_message(
                        connection_id, symbol, data
                    )

                except WebSocketDisconnect:
                    logger.info(
                        "websocket_disconnected",
                        connection_id=connection_id,
                        symbol=symbol,
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
        symbol: str,
        message: Dict[str, Any],
    ) -> None:
        """
        Handle messages from clients.

        Args:
            connection_id: The connection ID
            symbol: The trading symbol
            message: The message from client
        """
        command = message.get("command")

        if command == "start_search":
            await self._handle_start_search(connection_id, symbol, message)

        elif command == "stop_search":
            await self._handle_stop_search(connection_id, symbol, message)

        elif command == "update_config":
            await self._handle_update_config(connection_id, symbol, message)

        elif command == "get_status":
            await self._handle_get_status(connection_id, symbol)

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

    async def _handle_start_search(
        self,
        connection_id: str,
        symbol: str,
        message: Dict[str, Any],
    ) -> None:
        """
        Handle start search command.

        Args:
            connection_id: The connection ID
            symbol: The trading symbol
            message: The command message
        """
        config = message.get("config", {})
        search_id = str(uuid4())

        # Store search metadata
        self.active_searches[search_id] = {
            "symbol": symbol,
            "connection_id": connection_id,
            "config": config,
            "started_at": datetime.utcnow().isoformat(),
            "status": "running",
        }

        # Create search-specific room
        room_id = f"mcts:search:{search_id}"
        self.search_rooms[search_id] = room_id
        self.connection_manager.join_room(connection_id, room_id)

        logger.info(
            "mcts_search_started",
            search_id=search_id,
            symbol=symbol,
            connection_id=connection_id,
            config=config,
        )

        # Send confirmation
        response = create_message(
            "search_started",
            {
                "search_id": search_id,
                "symbol": symbol,
                "config": config,
            },
        )
        await self.connection_manager.send_personal_message(
            connection_id, response
        )

        # Start MCTS search process in background task
        task = asyncio.create_task(
            self._run_mcts_search(connection_id, search_id, symbol, config)
        )
        self.search_tasks[search_id] = task

    async def _run_mcts_search(
        self,
        connection_id: str,
        search_id: str,
        symbol: str,
        config: Dict[str, Any],
    ) -> None:
        """
        Run the actual MCTS search process.

        Args:
            connection_id: The connection ID to send updates to
            search_id: The search ID
            symbol: The trading symbol
            config: Search configuration
        """
        try:
            from reasoning_trading.mcts.tree import MCTSTree, MCTSConfig
            from reasoning_trading.core.actions import ActionSpace
            from reasoning_trading.core.state import TradingState

            # Build MCTS configuration
            mcts_config = MCTSConfig(
                max_simulations=config.get("max_simulations", 1000),
                exploration_weight=config.get("exploration_weight", 1.414),
                time_budget_ms=config.get("time_budget_ms"),
            )

            # Create tree and action space
            tree = MCTSTree(config=mcts_config)
            action_space = ActionSpace()

            # Build initial state (simplified - in production, fetch real data)
            initial_state = TradingState(
                symbol=symbol,
                timestamp=datetime.utcnow(),
                current_price=config.get("current_price", 100.0),
            )

            # Run search with progress callbacks
            iteration = 0
            max_iterations = config.get("max_simulations", 1000)

            while iteration < max_iterations:
                # Check if search was stopped
                if search_id in self.active_searches and self.active_searches[search_id].get("status") == "stopped":
                    logger.info("mcts_search_stopped", search_id=search_id)
                    break

                # Run one iteration
                tree.iterate(initial_state, action_space)
                iteration += 1

                # Send progress update every 10 iterations
                if iteration % 10 == 0:
                    await self.stream_iteration_update(
                        search_id=search_id,
                        iteration=iteration,
                        total_iterations=max_iterations,
                        best_action=str(tree.get_best_action()) if tree.root else "none",
                        best_value=tree.root.mean_value if tree.root else 0.0,
                        total_nodes=tree.total_nodes if hasattr(tree, "total_nodes") else iteration,
                    )

            # Send completion
            await self.stream_search_complete(
                search_id=search_id,
                best_action=tree.get_best_action().to_dict() if tree.root and tree.get_best_action() else {},
                best_value=tree.root.mean_value if tree.root else 0.0,
                total_simulations=iteration,
            )

        except asyncio.CancelledError:
            logger.info("mcts_search_cancelled", search_id=search_id)
            # Update search status
            if search_id in self.active_searches:
                self.active_searches[search_id]["status"] = "cancelled"
                self.active_searches[search_id]["cancelled_at"] = datetime.utcnow().isoformat()
            # Re-raise to properly propagate cancellation
            raise

        except Exception as e:
            logger.error("mcts_search_error", search_id=search_id, error=str(e))
            error_message = create_message("error", {"error": str(e), "search_id": search_id})
            await self.connection_manager.send_personal_message(connection_id, error_message)

        finally:
            # Clean up task reference
            self.search_tasks.pop(search_id, None)

    async def _handle_stop_search(
        self,
        connection_id: str,
        symbol: str,
        message: Dict[str, Any],
    ) -> None:
        """
        Handle stop search command.

        Args:
            connection_id: The connection ID
            symbol: The trading symbol
            message: The command message
        """
        search_id = message.get("search_id")

        if not search_id or search_id not in self.active_searches:
            error_message = create_message(
                "error",
                {"error": "Invalid or inactive search ID"},
            )
            await self.connection_manager.send_personal_message(
                connection_id, error_message
            )
            return

        # Update search status
        self.active_searches[search_id]["status"] = "stopped"
        self.active_searches[search_id]["stopped_at"] = (
            datetime.utcnow().isoformat()
        )

        logger.info(
            "mcts_search_stopped",
            search_id=search_id,
            symbol=symbol,
            connection_id=connection_id,
        )

        # Cancel the running task if it exists
        task = self.search_tasks.get(search_id)
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass  # Expected when task is cancelled

        # Send confirmation
        response = create_message(
            "search_stopped",
            {
                "search_id": search_id,
                "symbol": symbol,
            },
        )
        await self.connection_manager.send_personal_message(
            connection_id, response
        )

    async def _handle_update_config(
        self,
        connection_id: str,
        symbol: str,
        message: Dict[str, Any],
    ) -> None:
        """
        Handle update config command.

        Args:
            connection_id: The connection ID
            symbol: The trading symbol
            message: The command message
        """
        search_id = message.get("search_id")
        config = message.get("config", {})

        if not search_id or search_id not in self.active_searches:
            error_message = create_message(
                "error",
                {"error": "Invalid or inactive search ID"},
            )
            await self.connection_manager.send_personal_message(
                connection_id, error_message
            )
            return

        # Update configuration
        self.active_searches[search_id]["config"].update(config)

        logger.info(
            "mcts_config_updated",
            search_id=search_id,
            symbol=symbol,
            config=config,
        )

        # Send confirmation
        response = create_message(
            "config_updated",
            {
                "search_id": search_id,
                "config": self.active_searches[search_id]["config"],
            },
        )
        await self.connection_manager.send_personal_message(
            connection_id, response
        )

    async def _handle_get_status(
        self,
        connection_id: str,
        symbol: str,
    ) -> None:
        """
        Handle get status command.

        Args:
            connection_id: The connection ID
            symbol: The trading symbol
        """
        # Get all active searches for this symbol
        symbol_searches = {
            sid: meta
            for sid, meta in self.active_searches.items()
            if meta["symbol"] == symbol
        }

        response = create_message(
            "status",
            {
                "symbol": symbol,
                "active_searches": len(symbol_searches),
                "searches": symbol_searches,
            },
        )
        await self.connection_manager.send_personal_message(
            connection_id, response
        )

    async def stream_iteration_update(
        self,
        search_id: str,
        iteration: int,
        total_iterations: int,
        best_action: Optional[str] = None,
        best_value: Optional[float] = None,
        **kwargs: Any,
    ) -> None:
        """
        Stream an iteration update to subscribers.

        Args:
            search_id: The search identifier
            iteration: Current iteration number
            total_iterations: Total iterations planned
            best_action: Current best action
            best_value: Current best value
            **kwargs: Additional iteration data
        """
        if search_id not in self.search_rooms:
            logger.warning("search_room_not_found", search_id=search_id)
            return

        room_id = self.search_rooms[search_id]

        message = create_message(
            "iteration_update",
            {
                "search_id": search_id,
                "iteration": iteration,
                "total_iterations": total_iterations,
                "progress": iteration / total_iterations if total_iterations > 0 else 0,
                "best_action": best_action,
                "best_value": best_value,
                **kwargs,
            },
        )

        await self.connection_manager.broadcast_to_room(room_id, message)

    async def stream_node_expansion(
        self,
        search_id: str,
        node_id: str,
        state: Dict[str, Any],
        action: Optional[str] = None,
        parent_id: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """
        Stream a node expansion event.

        Args:
            search_id: The search identifier
            node_id: The expanded node ID
            state: The node state
            action: Action that led to this node
            parent_id: Parent node ID
            **kwargs: Additional node data
        """
        if search_id not in self.search_rooms:
            return

        room_id = self.search_rooms[search_id]

        message = create_message(
            "node_expansion",
            {
                "search_id": search_id,
                "node_id": node_id,
                "state": state,
                "action": action,
                "parent_id": parent_id,
                **kwargs,
            },
        )

        await self.connection_manager.broadcast_to_room(room_id, message)

    async def stream_backpropagation(
        self,
        search_id: str,
        node_path: list[str],
        value: float,
        **kwargs: Any,
    ) -> None:
        """
        Stream a backpropagation update.

        Args:
            search_id: The search identifier
            node_path: Path of nodes being updated
            value: The value being backpropagated
            **kwargs: Additional backpropagation data
        """
        if search_id not in self.search_rooms:
            return

        room_id = self.search_rooms[search_id]

        message = create_message(
            "backpropagation",
            {
                "search_id": search_id,
                "node_path": node_path,
                "value": value,
                **kwargs,
            },
        )

        await self.connection_manager.broadcast_to_room(room_id, message)

    async def stream_search_complete(
        self,
        search_id: str,
        best_action: Any,
        best_value: float,
        total_simulations: int,
        **kwargs: Any,
    ) -> None:
        """
        Stream search completion notification.

        Args:
            search_id: The search identifier
            best_action: The best action found (dict or str)
            best_value: The best value found
            total_simulations: Total simulations performed
            **kwargs: Additional completion data
        """
        if search_id not in self.search_rooms:
            return

        room_id = self.search_rooms[search_id]

        # Update search status
        if search_id in self.active_searches:
            self.active_searches[search_id].update({
                "status": "completed",
                "completed_at": datetime.utcnow().isoformat(),
                "result": {
                    "best_action": best_action,
                    "best_value": best_value,
                    "total_simulations": total_simulations,
                },
            })

        message = create_message(
            "search_completed",
            {
                "search_id": search_id,
                "best_action": best_action,
                "best_value": best_value,
                "total_simulations": total_simulations,
                **kwargs,
            },
        )

        await self.connection_manager.broadcast_to_room(room_id, message)

        logger.info(
            "mcts_search_completed",
            search_id=search_id,
            best_action=best_action,
            best_value=best_value,
            total_simulations=total_simulations,
        )

    async def stream_error(
        self,
        search_id: str,
        error: str,
        **kwargs: Any,
    ) -> None:
        """
        Stream an error event.

        Args:
            search_id: The search identifier
            error: The error message
            **kwargs: Additional error data
        """
        if search_id not in self.search_rooms:
            return

        room_id = self.search_rooms[search_id]

        # Update search status
        if search_id in self.active_searches:
            self.active_searches[search_id].update({
                "status": "error",
                "error": error,
                "error_at": datetime.utcnow().isoformat(),
            })

        message = create_message(
            "search_error",
            {
                "search_id": search_id,
                "error": error,
                **kwargs,
            },
        )

        await self.connection_manager.broadcast_to_room(room_id, message)

        logger.error(
            "mcts_search_error",
            search_id=search_id,
            error=error,
        )
