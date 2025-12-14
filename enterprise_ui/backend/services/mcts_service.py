"""
MCTS service for tree search operations.

Integrates with MCTSTree and HierarchicalMCTSTree to provide
search capabilities with result caching and configuration management.
"""

import asyncio
import hashlib
import json
from datetime import datetime
from typing import Any, Optional

import numpy as np
import structlog

from reasoning_trading.core.actions import ActionSpace
from reasoning_trading.core.state import TradingState
from reasoning_trading.hierarchical.tree import (
    HierarchicalMCTSConfig,
    HierarchicalMCTSResult,
    HierarchicalMCTSTree,
)
from reasoning_trading.mcts.tree import MCTSConfig, MCTSResult, MCTSTree

from .cache_service import CacheService
from .exceptions import MCTSServiceException, TimeoutException, ValidationException

logger = structlog.get_logger(__name__)


class MCTSService:
    """
    MCTS search service.

    Provides:
    - Standard MCTS search
    - Hierarchical MCTS search
    - Search result caching
    - Tree visualization
    - Action distribution analysis
    - Configuration management
    """

    def __init__(
        self,
        cache_service: Optional[CacheService] = None,
        mcts_config: Optional[MCTSConfig] = None,
        hierarchical_config: Optional[HierarchicalMCTSConfig] = None,
    ):
        """
        Initialize MCTS service.

        Args:
            cache_service: Cache service for results
            mcts_config: Standard MCTS configuration
            hierarchical_config: Hierarchical MCTS configuration
        """
        self.cache = cache_service
        self.mcts_config = mcts_config or MCTSConfig()
        self.hierarchical_config = hierarchical_config or HierarchicalMCTSConfig()

        # Active searches by ID
        self._active_searches: dict[str, dict[str, Any]] = {}

    def _generate_search_id(self, state: TradingState, search_type: str) -> str:
        """Generate unique search ID based on state and type."""
        state_hash = self._hash_state(state)
        timestamp = datetime.now().isoformat()
        unique_str = f"{search_type}:{state_hash}:{timestamp}"
        return hashlib.md5(unique_str.encode()).hexdigest()[:16]

    def _hash_state(self, state: TradingState) -> str:
        """Hash trading state for caching."""
        # Use key state features for hash
        features = state.to_feature_vector()
        discretized = np.round(features, 2)
        return hashlib.md5(discretized.tobytes()).hexdigest()[:16]

    async def run_search(
        self,
        state: TradingState,
        action_space: ActionSpace,
        config: Optional[MCTSConfig] = None,
        cache_ttl: int = 600,
    ) -> tuple[str, MCTSResult]:
        """
        Run standard MCTS search.

        Args:
            state: Initial trading state
            action_space: Available actions
            config: MCTS configuration (uses default if None)
            cache_ttl: Cache TTL in seconds

        Returns:
            Tuple of (search_id, MCTSResult)

        Raises:
            ValidationException: On invalid inputs
            MCTSServiceException: On search errors
            TimeoutException: On search timeout
        """
        if state is None:
            raise ValidationException("State cannot be None", field="state")

        if action_space is None:
            raise ValidationException("Action space cannot be None", field="action_space")

        # Generate search ID
        search_id = self._generate_search_id(state, "standard")

        # Check cache
        cache_key = f"mcts:{self._hash_state(state)}"
        if self.cache:
            cached = await self.cache.get(cache_key, use_pickle=True)
            if cached is not None:
                logger.info("mcts_cache_hit", search_id=search_id)
                return search_id, cached

        try:
            # Create MCTS tree
            config = config or self.mcts_config
            tree = MCTSTree(config=config)

            # Store in active searches
            self._active_searches[search_id] = {
                "type": "standard",
                "state": state,
                "started_at": datetime.now(),
                "status": "running",
            }

            logger.info(
                "mcts_search_started",
                search_id=search_id,
                symbol=state.symbol,
                max_simulations=config.max_simulations,
            )

            # Run search with timeout
            try:
                if config.time_budget_ms:
                    timeout_seconds = config.time_budget_ms / 1000.0 + 5.0  # Add buffer
                    result = await asyncio.wait_for(
                        tree.search(state, action_space),
                        timeout=timeout_seconds,
                    )
                else:
                    result = await tree.search(state, action_space)

            except asyncio.TimeoutError:
                logger.error("mcts_search_timeout", search_id=search_id)
                raise TimeoutException("MCTS search", config.time_budget_ms or 0)

            # Update search status
            self._active_searches[search_id]["status"] = "completed"
            self._active_searches[search_id]["completed_at"] = datetime.now()
            self._active_searches[search_id]["result"] = result

            # Cache result
            if self.cache:
                await self.cache.set(cache_key, result, ttl=cache_ttl, use_pickle=True)

            logger.info(
                "mcts_search_completed",
                search_id=search_id,
                simulations=result.total_simulations,
                time_ms=result.total_time_ms,
                best_value=result.best_value,
            )

            return search_id, result

        except TimeoutException:
            raise
        except Exception as e:
            logger.error("mcts_search_failed", search_id=search_id, error=str(e))
            if search_id in self._active_searches:
                self._active_searches[search_id]["status"] = "failed"
                self._active_searches[search_id]["error"] = str(e)
            raise MCTSServiceException(
                "MCTS search failed",
                {"search_id": search_id, "error": str(e)},
            )

    async def run_hierarchical_search(
        self,
        state: TradingState,
        target_level: str = "execution",
        config: Optional[HierarchicalMCTSConfig] = None,
        cache_ttl: int = 600,
    ) -> tuple[str, HierarchicalMCTSResult]:
        """
        Run hierarchical MCTS search.

        Args:
            state: Initial trading state
            target_level: Lowest level to plan ("strategic", "tactical", "execution")
            config: Hierarchical MCTS configuration
            cache_ttl: Cache TTL in seconds

        Returns:
            Tuple of (search_id, HierarchicalMCTSResult)

        Raises:
            ValidationException: On invalid inputs
            MCTSServiceException: On search errors
            TimeoutException: On search timeout
        """
        if state is None:
            raise ValidationException("State cannot be None", field="state")

        if target_level not in ["strategic", "tactical", "execution"]:
            raise ValidationException(
                "Target level must be 'strategic', 'tactical', or 'execution'",
                field="target_level",
            )

        # Generate search ID
        search_id = self._generate_search_id(state, f"hierarchical_{target_level}")

        # Check cache
        cache_key = f"h_mcts:{self._hash_state(state)}:{target_level}"
        if self.cache:
            cached = await self.cache.get(cache_key, use_pickle=True)
            if cached is not None:
                logger.info("hierarchical_mcts_cache_hit", search_id=search_id)
                return search_id, cached

        try:
            # Create hierarchical MCTS tree
            config = config or self.hierarchical_config
            tree = HierarchicalMCTSTree(config=config)

            # Store in active searches
            self._active_searches[search_id] = {
                "type": "hierarchical",
                "state": state,
                "target_level": target_level,
                "started_at": datetime.now(),
                "status": "running",
            }

            logger.info(
                "hierarchical_mcts_search_started",
                search_id=search_id,
                symbol=state.symbol,
                target_level=target_level,
            )

            # Run search with timeout
            try:
                if config.total_time_budget_ms:
                    timeout_seconds = config.total_time_budget_ms / 1000.0 + 5.0
                    result = await asyncio.wait_for(
                        tree.search(state, target_level),
                        timeout=timeout_seconds,
                    )
                else:
                    result = await tree.search(state, target_level)

            except asyncio.TimeoutError:
                logger.error("hierarchical_mcts_search_timeout", search_id=search_id)
                raise TimeoutException("Hierarchical MCTS search", config.total_time_budget_ms or 0)

            # Update search status
            self._active_searches[search_id]["status"] = "completed"
            self._active_searches[search_id]["completed_at"] = datetime.now()
            self._active_searches[search_id]["result"] = result

            # Cache result
            if self.cache:
                await self.cache.set(cache_key, result, ttl=cache_ttl, use_pickle=True)

            logger.info(
                "hierarchical_mcts_search_completed",
                search_id=search_id,
                total_simulations=result.total_simulations,
                time_ms=result.total_time_ms,
                strategic_value=result.strategic_value,
            )

            return search_id, result

        except TimeoutException:
            raise
        except Exception as e:
            logger.error("hierarchical_mcts_search_failed", search_id=search_id, error=str(e))
            if search_id in self._active_searches:
                self._active_searches[search_id]["status"] = "failed"
                self._active_searches[search_id]["error"] = str(e)
            raise MCTSServiceException(
                "Hierarchical MCTS search failed",
                {"search_id": search_id, "error": str(e)},
            )

    def get_search_status(self, search_id: str) -> Optional[dict[str, Any]]:
        """
        Get status of a search.

        Args:
            search_id: Search identifier

        Returns:
            Dictionary with search status or None if not found
        """
        search = self._active_searches.get(search_id)
        if search is None:
            return None

        status = {
            "search_id": search_id,
            "type": search["type"],
            "status": search["status"],
            "started_at": search["started_at"].isoformat(),
        }

        if "target_level" in search:
            status["target_level"] = search["target_level"]

        if "completed_at" in search:
            status["completed_at"] = search["completed_at"].isoformat()
            duration = (search["completed_at"] - search["started_at"]).total_seconds()
            status["duration_seconds"] = duration

        if "error" in search:
            status["error"] = search["error"]

        return status

    def get_tree_visualization(
        self,
        search_id: str,
        max_depth: int = 5,
    ) -> Optional[dict[str, Any]]:
        """
        Get tree visualization data.

        Args:
            search_id: Search identifier
            max_depth: Maximum depth to visualize

        Returns:
            Dictionary with tree visualization or None if not found
        """
        search = self._active_searches.get(search_id)
        if search is None or "result" not in search:
            logger.warning("search_not_found_for_visualization", search_id=search_id)
            return None

        try:
            result = search["result"]

            if isinstance(result, MCTSResult):
                return self._visualize_mcts_tree(result, max_depth)
            elif isinstance(result, HierarchicalMCTSResult):
                return self._visualize_hierarchical_tree(result, max_depth)
            else:
                logger.error("unknown_result_type", search_id=search_id)
                return None

        except Exception as e:
            logger.error("tree_visualization_failed", search_id=search_id, error=str(e))
            return None

    def _visualize_mcts_tree(self, result: MCTSResult, max_depth: int) -> dict[str, Any]:
        """Visualize standard MCTS tree."""
        if result.root is None:
            return {"nodes": [], "edges": []}

        nodes = []
        edges = []

        def traverse(node: Any, depth: int = 0) -> None:
            if depth > max_depth:
                return

            node_data = {
                "id": node.id,
                "visits": node.visits,
                "value": node.mean_value,
                "depth": depth,
                "is_terminal": node.is_terminal,
                "action": node.action.to_dict() if node.action else None,
            }
            nodes.append(node_data)

            for child in node.children:
                edges.append({"from": node.id, "to": child.id})
                traverse(child, depth + 1)

        traverse(result.root)

        return {
            "nodes": nodes,
            "edges": edges,
            "total_nodes": len(nodes),
            "max_depth": max_depth,
        }

    def _visualize_hierarchical_tree(
        self, result: HierarchicalMCTSResult, max_depth: int
    ) -> dict[str, Any]:
        """Visualize hierarchical MCTS tree."""
        if result.root is None:
            return {"nodes": [], "edges": [], "levels": {}}

        nodes = []
        edges = []
        levels = {"strategic": 0, "tactical": 0, "execution": 0}

        def traverse(node: Any, depth: int = 0) -> None:
            if depth > max_depth:
                return

            if node.level in levels:
                levels[node.level] += 1

            node_data = {
                "id": node.id,
                "level": node.level,
                "visits": node.visits,
                "value": node.hierarchical_q_value,
                "depth": depth,
                "is_terminal": node.is_terminal,
                "is_primitive": node.is_primitive,
                "action": node.action.to_dict() if node.action else None,
            }
            nodes.append(node_data)

            for child in node.children:
                edges.append({"from": node.id, "to": child.id})
                traverse(child, depth + 1)

        traverse(result.root)

        return {
            "nodes": nodes,
            "edges": edges,
            "levels": levels,
            "total_nodes": len(nodes),
            "max_depth": max_depth,
        }

    def get_action_distribution(
        self,
        search_id: str,
        level: str = "strategic",
    ) -> Optional[dict[str, float]]:
        """
        Get action probability distribution.

        Args:
            search_id: Search identifier
            level: Level for hierarchical search ("strategic", "tactical", "execution")

        Returns:
            Dictionary mapping action types to probabilities
        """
        search = self._active_searches.get(search_id)
        if search is None or "result" not in search:
            logger.warning("search_not_found_for_distribution", search_id=search_id)
            return None

        try:
            result = search["result"]

            if isinstance(result, MCTSResult) and result.root:
                tree = MCTSTree()
                tree.root = result.root
                return tree.get_action_distribution()
            elif isinstance(result, HierarchicalMCTSResult) and result.root:
                tree = HierarchicalMCTSTree()
                tree.root = result.root
                return tree.get_action_distribution(level)
            else:
                return None

        except Exception as e:
            logger.error("action_distribution_failed", search_id=search_id, error=str(e))
            return None

    def clear_search(self, search_id: str) -> bool:
        """
        Clear search from active searches.

        Args:
            search_id: Search identifier

        Returns:
            True if search was cleared
        """
        if search_id in self._active_searches:
            del self._active_searches[search_id]
            logger.debug("search_cleared", search_id=search_id)
            return True
        return False

    def clear_all_searches(self) -> int:
        """
        Clear all active searches.

        Returns:
            Number of searches cleared
        """
        count = len(self._active_searches)
        self._active_searches.clear()
        logger.info("all_searches_cleared", count=count)
        return count

    def get_statistics(self) -> dict[str, Any]:
        """
        Get service statistics.

        Returns:
            Dictionary with statistics
        """
        total_searches = len(self._active_searches)
        completed = sum(1 for s in self._active_searches.values() if s["status"] == "completed")
        running = sum(1 for s in self._active_searches.values() if s["status"] == "running")
        failed = sum(1 for s in self._active_searches.values() if s["status"] == "failed")

        return {
            "total_searches": total_searches,
            "completed": completed,
            "running": running,
            "failed": failed,
            "mcts_config": {
                "max_simulations": self.mcts_config.max_simulations,
                "exploration_weight": self.mcts_config.exploration_weight,
                "time_budget_ms": self.mcts_config.time_budget_ms,
            },
            "hierarchical_config": {
                "strategic_simulations": self.hierarchical_config.strategic_simulations,
                "tactical_simulations": self.hierarchical_config.tactical_simulations,
                "execution_simulations": self.hierarchical_config.execution_simulations,
                "total_time_budget_ms": self.hierarchical_config.total_time_budget_ms,
            },
        }
