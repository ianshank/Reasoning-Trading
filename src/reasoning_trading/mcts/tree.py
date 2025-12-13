"""
MCTS Tree implementation for trading decisions.

Provides the main tree search algorithm with configurable phases:
selection, expansion, simulation (rollout), and backpropagation.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, Callable

import structlog

from reasoning_trading.config import MCTSSettings, get_settings
from reasoning_trading.mcts.node import Node
from reasoning_trading.mcts.rollout import RolloutEngine, TradingRollout
from reasoning_trading.mcts.ucb import (
    SelectionStrategy,
    UCB1Selector,
    UCBSelector,
    create_selector,
)

if TYPE_CHECKING:
    from reasoning_trading.core.actions import ActionSpace, TradingAction
    from reasoning_trading.core.state import TradingState

logger = structlog.get_logger(__name__)


@dataclass
class MCTSConfig:
    """Configuration for MCTS algorithm."""

    max_simulations: int = 1000
    max_depth: int = 50
    exploration_weight: float = 1.414
    discount_factor: float = 0.99

    # Time budgets
    time_budget_ms: int | None = None  # None = no time limit
    per_simulation_timeout_ms: int = 5000

    # Selection strategy
    selection_strategy: SelectionStrategy = SelectionStrategy.RISK_ADJUSTED

    # Progressive widening
    progressive_widening_alpha: float = 0.5

    # Early termination
    confidence_threshold: float = 0.85
    min_simulations: int = 100

    # Rollout configuration
    rollout_horizon: int = 30

    @classmethod
    def from_settings(cls, settings: MCTSSettings | None = None) -> MCTSConfig:
        """Create config from settings."""
        if settings is None:
            settings = get_settings().mcts
        return cls(
            max_simulations=settings.max_simulations,
            exploration_weight=settings.exploration_weight,
            discount_factor=settings.discount_factor,
            time_budget_ms=settings.realtime_budget_ms,
            confidence_threshold=settings.confidence_threshold,
            progressive_widening_alpha=settings.progressive_widening_alpha,
            rollout_horizon=settings.rollout_horizon_days,
        )


@dataclass
class MCTSResult:
    """Result of MCTS search."""

    best_action: TradingAction | None = None
    best_node: Node | None = None
    root: Node | None = None

    # Statistics
    total_simulations: int = 0
    total_time_ms: float = 0.0
    simulations_per_second: float = 0.0

    # Confidence metrics
    best_value: float = 0.0
    best_visits: int = 0
    value_std: float = 0.0

    # Tree statistics
    max_depth_reached: int = 0
    total_nodes: int = 0
    leaf_nodes: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "best_action": self.best_action.to_dict() if self.best_action else None,
            "total_simulations": self.total_simulations,
            "total_time_ms": self.total_time_ms,
            "simulations_per_second": self.simulations_per_second,
            "best_value": self.best_value,
            "best_visits": self.best_visits,
            "value_std": self.value_std,
            "max_depth_reached": self.max_depth_reached,
            "total_nodes": self.total_nodes,
            "leaf_nodes": self.leaf_nodes,
        }


class MCTSTree:
    """
    Monte Carlo Tree Search implementation for trading.

    Implements the four MCTS phases:
    1. Selection: Use UCB to select promising nodes
    2. Expansion: Generate new child nodes
    3. Simulation: Run rollouts to estimate value
    4. Backpropagation: Update node statistics

    Usage:
        tree = MCTSTree(config)
        result = await tree.search(initial_state, action_space)
        best_action = result.best_action
    """

    def __init__(
        self,
        config: MCTSConfig | None = None,
        rollout_engine: RolloutEngine | None = None,
        selector: UCBSelector | None = None,
        expansion_callback: Callable[[Node, ActionSpace], list[TradingAction]] | None = None,
    ):
        """
        Initialize MCTS tree.

        Args:
            config: MCTS configuration
            rollout_engine: Engine for simulation rollouts
            selector: UCB selection strategy
            expansion_callback: Custom expansion function (e.g., LLM-based)
        """
        self.config = config or MCTSConfig()
        self.rollout_engine = rollout_engine or TradingRollout(
            horizon_days=self.config.rollout_horizon,
            discount_factor=self.config.discount_factor,
        )
        self.selector = selector or create_selector(
            self.config.selection_strategy,
            exploration_constant=self.config.exploration_weight,
        )
        self.expansion_callback = expansion_callback

        self.root: Node | None = None
        self._action_space: ActionSpace | None = None

    async def search(
        self,
        initial_state: TradingState,
        action_space: ActionSpace,
    ) -> MCTSResult:
        """
        Run MCTS search from initial state.

        Args:
            initial_state: Starting trading state
            action_space: Available actions

        Returns:
            MCTSResult with best action and statistics
        """
        self._action_space = action_space

        # Initialize root node
        self.root = Node(state=initial_state)

        start_time = time.time()
        simulation_count = 0
        deadline = None

        if self.config.time_budget_ms is not None:
            deadline = start_time + (self.config.time_budget_ms / 1000.0)

        logger.info(
            "Starting MCTS search",
            max_simulations=self.config.max_simulations,
            time_budget_ms=self.config.time_budget_ms,
        )

        while simulation_count < self.config.max_simulations:
            # Check time budget
            if deadline is not None and time.time() > deadline:
                logger.info("Time budget exceeded", simulations=simulation_count)
                break

            # Check early termination
            if simulation_count >= self.config.min_simulations:
                if self._should_terminate_early():
                    logger.info(
                        "Early termination due to confidence",
                        simulations=simulation_count,
                    )
                    break

            # Run one MCTS iteration
            await self._run_simulation()
            simulation_count += 1

        elapsed_ms = (time.time() - start_time) * 1000

        result = self._build_result(simulation_count, elapsed_ms)

        logger.info(
            "MCTS search completed",
            simulations=simulation_count,
            elapsed_ms=elapsed_ms,
            best_value=result.best_value,
            best_visits=result.best_visits,
        )

        return result

    async def _run_simulation(self) -> None:
        """Run one complete MCTS simulation (select, expand, simulate, backprop)."""
        if self.root is None:
            return

        # Phase 1: Selection - traverse tree using UCB
        node = self._select(self.root)

        # Phase 2: Expansion - add new child if not terminal
        if not node.is_terminal and not node.is_solved:
            expanded_node = await self._expand(node)
            if expanded_node is not None:
                node = expanded_node

        # Phase 3: Simulation - rollout to estimate value
        value = await self._simulate(node)

        # Phase 4: Backpropagation - update statistics up the tree
        self._backpropagate(node, value)

    def _select(self, node: Node) -> Node:
        """
        Select most promising node using UCB.

        Traverses from root to a leaf node using the configured
        selection strategy.
        """
        current = node
        depth = 0

        while not current.is_leaf and depth < self.config.max_depth:
            selected = self.selector.select(current)
            if selected is None:
                break
            current = selected
            depth += 1

        return current

    async def _expand(self, node: Node) -> Node | None:
        """
        Expand node with new children.

        Uses progressive widening for continuous action spaces.
        """
        if self._action_space is None or node.state is None:
            return None

        # Get existing child actions
        existing_actions = [c.action for c in node.children if c.action is not None]

        # Get candidate actions using progressive widening
        if self.expansion_callback is not None:
            # Use custom expansion (e.g., LLM-based)
            candidate_actions = self.expansion_callback(node, self._action_space)
        else:
            # Use action space's default expansion
            candidate_actions = self._action_space.get_candidate_actions(
                visit_count=max(node.visits, 1),
                existing_actions=existing_actions,
            )

        if not candidate_actions:
            return None

        # Select one action to expand
        action = candidate_actions[0]

        # Create new state by applying action
        new_state = self._apply_action(node.state, action)

        # Create child node
        child = node.expand(
            action=action,
            new_state=new_state,
            prior=action.confidence,  # Use confidence as prior
        )

        return child

    def _apply_action(self, state: TradingState, action: TradingAction) -> TradingState:
        """
        Apply action to state and return new state.

        This is a simplified state transition - the real transition
        happens during rollout simulation.
        """
        new_state = state.copy()
        new_state.simulation_step += 1

        # Simple state update based on action direction
        from reasoning_trading.core.actions import TradingDirection

        if action.direction == TradingDirection.BUY:
            position_value = action.position_size.size_fraction * state.portfolio.portfolio_value
            new_state.portfolio.positions[state.symbol] = (
                new_state.portfolio.get_position_size(state.symbol)
                + position_value / state.current_price
            )
        elif action.direction in (TradingDirection.SELL, TradingDirection.COVER):
            new_state.portfolio.positions[state.symbol] = 0.0

        return new_state

    async def _simulate(self, node: Node) -> float:
        """
        Run rollout simulation to estimate node value.

        Uses the configured rollout engine to simulate trading
        and return a risk-adjusted reward.
        """
        try:
            async with asyncio.timeout(self.config.per_simulation_timeout_ms / 1000):
                return await self.rollout_engine.rollout(
                    node, depth=self.config.rollout_horizon
                )
        except asyncio.TimeoutError:
            logger.warning("Rollout timeout", node_id=node.id)
            return 0.0
        except Exception as e:
            logger.error("Rollout error", error=str(e), node_id=node.id)
            return 0.0

    def _backpropagate(self, node: Node, value: float) -> None:
        """
        Backpropagate value up the tree.

        Updates visit counts and value statistics for all nodes
        from the given node to the root.
        """
        node.backpropagate(value, discount=self.config.discount_factor)

    def _should_terminate_early(self) -> bool:
        """Check if we should terminate search early based on confidence."""
        if self.root is None or not self.root.children:
            return False

        # Get top children by visits
        sorted_children = sorted(self.root.children, key=lambda c: c.visits, reverse=True)
        if len(sorted_children) < 2:
            return False

        best = sorted_children[0]
        second_best = sorted_children[1]

        # Terminate if best is significantly better than alternatives
        if best.visits == 0 or second_best.visits == 0:
            return False

        # Check visit ratio
        visit_ratio = best.visits / (best.visits + second_best.visits)
        if visit_ratio > self.config.confidence_threshold:
            return True

        # Check value difference
        value_diff = best.mean_value - second_best.mean_value
        if value_diff > 0.5 and best.visits > self.config.min_simulations:
            return True

        return False

    def _build_result(self, simulation_count: int, elapsed_ms: float) -> MCTSResult:
        """Build MCTSResult from current tree state."""
        result = MCTSResult(
            root=self.root,
            total_simulations=simulation_count,
            total_time_ms=elapsed_ms,
        )

        if elapsed_ms > 0:
            result.simulations_per_second = simulation_count / (elapsed_ms / 1000)

        if self.root is not None:
            # Get best action by visit count
            best_child = self.root.best_action_child()
            if best_child is not None:
                result.best_node = best_child
                result.best_action = best_child.action
                result.best_value = best_child.mean_value
                result.best_visits = best_child.visits

            # Calculate tree statistics
            result.total_nodes, result.leaf_nodes, result.max_depth_reached = (
                self._compute_tree_stats(self.root)
            )

            # Calculate value std across top children
            if len(self.root.children) > 1:
                import numpy as np

                values = [c.mean_value for c in self.root.children if c.visits > 0]
                if values:
                    result.value_std = float(np.std(values))

        return result

    def _compute_tree_stats(self, root: Node) -> tuple[int, int, int]:
        """Compute tree statistics (total nodes, leaf nodes, max depth)."""
        total = 0
        leaves = 0
        max_depth = 0

        stack = [root]
        while stack:
            node = stack.pop()
            total += 1
            max_depth = max(max_depth, node.depth)

            if node.is_leaf:
                leaves += 1
            else:
                stack.extend(node.children)

        return total, leaves, max_depth

    def get_action_distribution(self) -> dict[str, float]:
        """Get probability distribution over actions at root."""
        if self.root is None or not self.root.children:
            return {}

        total_visits = sum(c.visits for c in self.root.children)
        if total_visits == 0:
            return {}

        distribution = {}
        for child in self.root.children:
            if child.action is not None and child.visits > 0:
                key = f"{child.action.direction.value}_{child.action.time_horizon.value}"
                distribution[key] = child.visits / total_visits

        return distribution

    def get_top_actions(self, n: int = 5) -> list[tuple[TradingAction, float, int]]:
        """
        Get top N actions by visit count.

        Returns:
            List of (action, mean_value, visits) tuples
        """
        if self.root is None:
            return []

        sorted_children = sorted(
            [c for c in self.root.children if c.action is not None],
            key=lambda c: c.visits,
            reverse=True,
        )

        return [
            (c.action, c.mean_value, c.visits)
            for c in sorted_children[:n]
            if c.action is not None
        ]


class AsyncMCTSTree(MCTSTree):
    """
    Async-optimized MCTS tree with parallel simulations.

    Runs multiple simulations concurrently for improved throughput.
    """

    def __init__(self, *args: Any, num_parallel: int = 4, **kwargs: Any):
        """
        Initialize async MCTS tree.

        Args:
            num_parallel: Number of parallel simulations to run
            *args, **kwargs: Passed to MCTSTree
        """
        super().__init__(*args, **kwargs)
        self.num_parallel = num_parallel

    async def search(
        self,
        initial_state: TradingState,
        action_space: ActionSpace,
    ) -> MCTSResult:
        """Run parallelized MCTS search."""
        self._action_space = action_space
        self.root = Node(state=initial_state)

        start_time = time.time()
        simulation_count = 0
        deadline = None

        if self.config.time_budget_ms is not None:
            deadline = start_time + (self.config.time_budget_ms / 1000.0)

        logger.info(
            "Starting parallel MCTS search",
            max_simulations=self.config.max_simulations,
            num_parallel=self.num_parallel,
        )

        while simulation_count < self.config.max_simulations:
            if deadline is not None and time.time() > deadline:
                break

            if (
                simulation_count >= self.config.min_simulations
                and self._should_terminate_early()
            ):
                break

            # Run batch of parallel simulations
            batch_size = min(
                self.num_parallel,
                self.config.max_simulations - simulation_count,
            )

            tasks = [self._run_simulation() for _ in range(batch_size)]
            await asyncio.gather(*tasks)
            simulation_count += batch_size

        elapsed_ms = (time.time() - start_time) * 1000
        return self._build_result(simulation_count, elapsed_ms)
