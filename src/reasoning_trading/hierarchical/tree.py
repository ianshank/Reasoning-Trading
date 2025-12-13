"""
Hierarchical MCTS Tree implementation.

Implements H-UCT (Hierarchical UCT) algorithm that integrates task hierarchies
from the MAXQ framework into MCTS, achieving complexity reduction from
O(|A|^T) to O(|Ã|^(T/L)).
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, Callable

import numpy as np
import structlog
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from reasoning_trading.hierarchical.levels import (
    HierarchyLevel,
    HierarchyLevelConfig,
    HierarchyLevelType,
    LevelAction,
    StrategicLevel,
    TacticalLevel,
    ExecutionLevel,
    create_hierarchy_level,
)
from reasoning_trading.hierarchical.maxq import MAXQValueDecomposition, MAXQConfig
from reasoning_trading.hierarchical.node import HierarchicalNode
from reasoning_trading.hierarchical.state import StateAbstraction, StateAbstractionConfig

if TYPE_CHECKING:
    from reasoning_trading.core.actions import ActionSpace, TradingAction
    from reasoning_trading.core.state import TradingState

logger = structlog.get_logger(__name__)


class HierarchicalMCTSConfig(BaseSettings):
    """Configuration for Hierarchical MCTS."""

    model_config = SettingsConfigDict(
        env_prefix="H_MCTS_",
        case_sensitive=False,
        extra="ignore",
    )

    # Simulation budgets per level
    strategic_simulations: int = Field(
        default=800,
        ge=100,
        le=10000,
        description="MCTS simulations for strategic level",
    )
    tactical_simulations: int = Field(
        default=200,
        ge=50,
        le=5000,
        description="MCTS simulations for tactical level",
    )
    execution_simulations: int = Field(
        default=50,
        ge=10,
        le=1000,
        description="MCTS simulations for execution level",
    )

    # Tree parameters
    max_depth: int = Field(
        default=30,
        ge=5,
        le=100,
        description="Maximum tree depth",
    )
    exploration_weight: float = Field(
        default=1.414,
        ge=0.1,
        le=5.0,
        description="UCB exploration weight",
    )
    discount_factor: float = Field(
        default=0.99,
        ge=0.0,
        le=1.0,
        description="Discount factor for future rewards",
    )

    # Time budgets
    total_time_budget_ms: int = Field(
        default=5000,
        ge=100,
        le=60000,
        description="Total time budget for hierarchical search",
    )
    per_level_timeout_ms: int = Field(
        default=2000,
        ge=100,
        le=30000,
        description="Timeout per hierarchy level",
    )

    # Early termination
    confidence_threshold: float = Field(
        default=0.85,
        ge=0.5,
        le=0.99,
        description="Confidence threshold for early termination",
    )
    min_simulations_per_level: int = Field(
        default=20,
        ge=5,
        le=100,
        description="Minimum simulations before early termination",
    )

    # MAXQ decomposition
    use_maxq: bool = Field(
        default=True,
        description="Use MAXQ value decomposition",
    )

    # Policy network integration
    use_policy_prior: bool = Field(
        default=True,
        description="Use policy network priors in selection",
    )
    c_puct: float = Field(
        default=1.5,
        ge=0.1,
        le=5.0,
        description="PUCT exploration constant",
    )


@dataclass
class HierarchicalMCTSResult:
    """Result of hierarchical MCTS search."""

    # Best actions at each level
    strategic_action: LevelAction | None = None
    tactical_actions: list[LevelAction] = field(default_factory=list)
    execution_actions: list[LevelAction] = field(default_factory=list)

    # Best nodes
    strategic_node: HierarchicalNode | None = None
    root: HierarchicalNode | None = None

    # Statistics
    total_simulations: int = 0
    simulations_per_level: dict[str, int] = field(default_factory=dict)
    total_time_ms: float = 0.0
    time_per_level: dict[str, float] = field(default_factory=dict)

    # Value estimates
    strategic_value: float = 0.0
    tactical_value: float = 0.0
    execution_value: float = 0.0

    # Tree statistics
    max_depth_reached: int = 0
    total_nodes: int = 0
    nodes_per_level: dict[str, int] = field(default_factory=dict)

    def get_full_action_sequence(self) -> list[LevelAction]:
        """Get complete action sequence from strategic to execution."""
        sequence = []
        if self.strategic_action:
            sequence.append(self.strategic_action)
        sequence.extend(self.tactical_actions)
        sequence.extend(self.execution_actions)
        return sequence

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "strategic_action": self.strategic_action.to_dict() if self.strategic_action else None,
            "tactical_actions": [a.to_dict() for a in self.tactical_actions],
            "execution_actions": [a.to_dict() for a in self.execution_actions],
            "total_simulations": self.total_simulations,
            "simulations_per_level": self.simulations_per_level,
            "total_time_ms": self.total_time_ms,
            "time_per_level": self.time_per_level,
            "strategic_value": self.strategic_value,
            "tactical_value": self.tactical_value,
            "execution_value": self.execution_value,
            "max_depth_reached": self.max_depth_reached,
            "total_nodes": self.total_nodes,
            "nodes_per_level": self.nodes_per_level,
        }


class HierarchicalMCTSTree:
    """
    Hierarchical Monte Carlo Tree Search for trading.

    Implements the H-UCT algorithm with MAXQ value decomposition:
    1. Strategic level: Portfolio allocation (days/weeks)
    2. Tactical level: Asset selection (hours/days)
    3. Execution level: Order execution (seconds/minutes)

    Complexity reduction: O(|A|^T) → O(|Ã|^(T/L)) where L is the number of levels.
    """

    def __init__(
        self,
        config: HierarchicalMCTSConfig | None = None,
        level_config: HierarchyLevelConfig | None = None,
        maxq_config: MAXQConfig | None = None,
        state_config: StateAbstractionConfig | None = None,
        policy_network: Callable[[Any], dict[str, float]] | None = None,
    ):
        """
        Initialize hierarchical MCTS tree.

        Args:
            config: MCTS configuration
            level_config: Hierarchy level configuration
            maxq_config: MAXQ decomposition configuration
            state_config: State abstraction configuration
            policy_network: Optional policy network for action priors
        """
        self.config = config or HierarchicalMCTSConfig()
        self.level_config = level_config or HierarchyLevelConfig()
        self.maxq_config = maxq_config or MAXQConfig()
        self.state_config = state_config or StateAbstractionConfig()

        # Initialize hierarchy levels
        self.strategic_level = StrategicLevel(self.level_config)
        self.tactical_level = TacticalLevel(self.level_config)
        self.execution_level = ExecutionLevel(self.level_config)

        self.levels: dict[str, HierarchyLevel] = {
            "strategic": self.strategic_level,
            "tactical": self.tactical_level,
            "execution": self.execution_level,
        }

        # Initialize MAXQ decomposition
        self.maxq = MAXQValueDecomposition(self.maxq_config)

        # Initialize state abstraction
        self.state_abstraction = StateAbstraction(self.state_config)

        # Policy network for priors
        self.policy_network = policy_network

        # Tree state
        self.root: HierarchicalNode | None = None

    async def search(
        self,
        initial_state: TradingState,
        target_level: str = "execution",
    ) -> HierarchicalMCTSResult:
        """
        Run hierarchical MCTS search.

        Args:
            initial_state: Initial trading state
            target_level: Lowest level to plan to ("strategic", "tactical", "execution")

        Returns:
            HierarchicalMCTSResult with best actions at each level
        """
        start_time = time.time()

        # Create hierarchical state representation
        hierarchical_state = self.state_abstraction.create_hierarchical_state(initial_state)

        # Initialize root at strategic level
        strategic_state = self.strategic_level.abstract_state(initial_state)
        self.root = HierarchicalNode(
            level="strategic",
            task_id="root",
            level_state=strategic_state,
            raw_state=initial_state,
        )

        # Track statistics
        simulations_per_level: dict[str, int] = {"strategic": 0, "tactical": 0, "execution": 0}
        time_per_level: dict[str, float] = {"strategic": 0.0, "tactical": 0.0, "execution": 0.0}

        # Phase 1: Strategic search
        logger.info("Starting strategic level search")
        level_start = time.time()
        await self._search_level(
            self.root,
            self.strategic_level,
            self.config.strategic_simulations,
            initial_state,
        )
        time_per_level["strategic"] = (time.time() - level_start) * 1000
        simulations_per_level["strategic"] = self._count_simulations(self.root)

        # Get best strategic action
        best_strategic = self.root.best_child_hierarchical(
            c_puct=self.config.c_puct,
            use_prior=self.config.use_policy_prior,
        )

        if best_strategic is None or target_level == "strategic":
            return self._build_result(
                start_time,
                simulations_per_level,
                time_per_level,
                best_strategic,
            )

        # Phase 2: Tactical search (if needed)
        logger.info("Starting tactical level search")
        level_start = time.time()

        # Expand tactical subtasks from strategic action
        tactical_nodes = await self._expand_tactical(
            best_strategic,
            initial_state,
        )

        for tactical_node in tactical_nodes:
            await self._search_level(
                tactical_node,
                self.tactical_level,
                self.config.tactical_simulations // max(len(tactical_nodes), 1),
                initial_state,
            )

        time_per_level["tactical"] = (time.time() - level_start) * 1000
        simulations_per_level["tactical"] = sum(
            self._count_simulations(n) for n in tactical_nodes
        )

        if target_level == "tactical":
            return self._build_result(
                start_time,
                simulations_per_level,
                time_per_level,
                best_strategic,
            )

        # Phase 3: Execution search
        logger.info("Starting execution level search")
        level_start = time.time()

        for tactical_node in tactical_nodes:
            best_tactical = tactical_node.best_child_hierarchical(
                c_puct=self.config.c_puct,
                use_prior=self.config.use_policy_prior,
            )

            if best_tactical is not None:
                execution_nodes = await self._expand_execution(
                    best_tactical,
                    initial_state,
                )

                for exec_node in execution_nodes:
                    await self._search_level(
                        exec_node,
                        self.execution_level,
                        self.config.execution_simulations // max(len(execution_nodes), 1),
                        initial_state,
                    )

        time_per_level["execution"] = (time.time() - level_start) * 1000
        simulations_per_level["execution"] = self._count_execution_simulations()

        return self._build_result(
            start_time,
            simulations_per_level,
            time_per_level,
            best_strategic,
        )

    async def _search_level(
        self,
        root: HierarchicalNode,
        level: HierarchyLevel,
        max_simulations: int,
        raw_state: TradingState,
    ) -> None:
        """
        Run MCTS search at a specific hierarchy level.

        Args:
            root: Root node for this level's search
            level: Hierarchy level to search
            max_simulations: Maximum simulations at this level
            raw_state: Raw trading state
        """
        simulation_count = 0
        deadline = time.time() + (self.config.per_level_timeout_ms / 1000.0)

        while simulation_count < max_simulations:
            if time.time() > deadline:
                logger.debug(
                    "Level timeout",
                    level=level.level_type.value,
                    simulations=simulation_count,
                )
                break

            # Check early termination
            if (
                simulation_count >= self.config.min_simulations_per_level
                and self._should_terminate_level(root)
            ):
                break

            # Run one simulation
            await self._run_level_simulation(root, level, raw_state)
            simulation_count += 1

    async def _run_level_simulation(
        self,
        root: HierarchicalNode,
        level: HierarchyLevel,
        raw_state: TradingState,
    ) -> None:
        """
        Run one MCTS simulation at a hierarchy level.

        Args:
            root: Root node
            level: Hierarchy level
            raw_state: Raw trading state
        """
        # Selection
        node = self._select_hierarchical(root)

        # Expansion
        if not node.is_terminal and not node.is_primitive:
            expanded = await self._expand_level(node, level, raw_state)
            if expanded is not None:
                node = expanded

        # Simulation (rollout)
        value = await self._simulate_level(node, level, raw_state)

        # Backpropagation
        self._backpropagate_hierarchical(node, value)

        # Update MAXQ tables
        if self.config.use_maxq and node.action is not None:
            self._update_maxq(node, value)

    def _select_hierarchical(self, root: HierarchicalNode) -> HierarchicalNode:
        """
        Hierarchical selection using UCB with MAXQ Q-values.

        Args:
            root: Root node to select from

        Returns:
            Selected leaf node
        """
        current = root
        depth = 0

        while not current.is_leaf and depth < self.config.max_depth:
            selected = current.best_child_hierarchical(
                c_puct=self.config.c_puct,
                use_prior=self.config.use_policy_prior,
            )
            if selected is None:
                break
            current = selected
            depth += 1

        return current

    async def _expand_level(
        self,
        node: HierarchicalNode,
        level: HierarchyLevel,
        raw_state: TradingState,
    ) -> HierarchicalNode | None:
        """
        Expand node with actions from the hierarchy level.

        Args:
            node: Node to expand
            level: Hierarchy level providing actions
            raw_state: Raw trading state

        Returns:
            Newly expanded child node
        """
        if node.level_state is None:
            return None

        # Get candidate actions for this level
        candidate_actions = self._get_level_actions(level, node)

        if not candidate_actions:
            return None

        # Get policy priors if available
        priors = await self._get_action_priors(node.level_state, candidate_actions)

        # Expand with first unexpanded action
        existing_action_types = {
            c.action.action_type for c in node.children if c.action is not None
        }

        for action in candidate_actions:
            if action.action_type not in existing_action_types:
                # Create level state for child
                child_level_state = level.abstract_state(raw_state)

                # Get prior for this action
                prior = priors.get(action.action_type, 0.0)

                # Expand
                child = node.expand_with_subtask(
                    action=action,
                    level_state=child_level_state,
                    raw_state=raw_state,
                    prior=prior,
                )

                return child

        return None

    def _get_level_actions(
        self,
        level: HierarchyLevel,
        node: HierarchicalNode,
    ) -> list[LevelAction]:
        """Get available actions at a hierarchy level."""
        actions = []

        for action_type in level.action_types:
            actions.append(LevelAction(
                level=level.level_type,
                action_type=action_type,
                confidence=0.5,
            ))

        return actions

    async def _get_action_priors(
        self,
        level_state: Any,
        actions: list[LevelAction],
    ) -> dict[str, float]:
        """
        Get action priors from policy network.

        Args:
            level_state: State at current level
            actions: Available actions

        Returns:
            Dictionary mapping action types to prior probabilities
        """
        if self.policy_network is None:
            # Uniform priors
            return {a.action_type: 1.0 / len(actions) for a in actions}

        try:
            priors = self.policy_network(level_state)
            return priors
        except Exception as e:
            logger.warning("Policy network error", error=str(e))
            return {a.action_type: 1.0 / len(actions) for a in actions}

    async def _simulate_level(
        self,
        node: HierarchicalNode,
        level: HierarchyLevel,
        raw_state: TradingState,
    ) -> float:
        """
        Simulate (rollout) at a hierarchy level.

        Args:
            node: Node to simulate from
            level: Hierarchy level
            raw_state: Raw trading state

        Returns:
            Estimated value from simulation
        """
        if node.level_state is None:
            return 0.0

        # Use MAXQ if enabled
        if self.config.use_maxq and node.action is not None:
            parent_task_id = node.parent.task_id if node.parent else "root"
            subtask_id = node.action.subtask_id or node.action.action_type

            q_value = self.maxq.get_q_value(
                parent_task_id,
                subtask_id,
                node.level_state,
            )

            # Add noise for exploration
            noise = np.random.normal(0, 0.1)
            return q_value + noise

        # Default: simple heuristic based on state
        # Higher RSI in bullish = positive, lower in bearish = positive
        if node.raw_state is not None:
            rsi = node.raw_state.technical_indicators.rsi_14 or 50
            consensus = node.raw_state.analyst_signals.weighted_consensus()

            if node.action is not None:
                if "buy" in node.action.action_type.lower() or "long" in node.action.action_type.lower():
                    return consensus * 0.5 + (rsi - 50) / 100
                elif "sell" in node.action.action_type.lower() or "short" in node.action.action_type.lower():
                    return -consensus * 0.5 + (50 - rsi) / 100

            return consensus * 0.3

        return 0.0

    def _backpropagate_hierarchical(
        self,
        node: HierarchicalNode,
        value: float,
    ) -> None:
        """
        Backpropagate value through hierarchy.

        Args:
            node: Leaf node
            value: Value to backpropagate
        """
        node.backpropagate_hierarchical(value, discount=self.config.discount_factor)

    def _update_maxq(self, node: HierarchicalNode, value: float) -> None:
        """
        Update MAXQ value tables.

        Args:
            node: Node that was simulated
            value: Observed value
        """
        if node.action is None or node.level_state is None:
            return

        subtask_id = node.action.subtask_id or node.action.action_type

        # Update subtask value
        self.maxq.update_subtask_value(subtask_id, node.level_state, value)

        # Update completion function if parent exists
        if node.parent is not None:
            parent_task_id = node.parent.task_id
            self.maxq.update_completion_function(
                parent_task_id,
                subtask_id,
                node.level_state,
                value,
            )

    async def _expand_tactical(
        self,
        strategic_node: HierarchicalNode,
        raw_state: TradingState,
    ) -> list[HierarchicalNode]:
        """
        Expand tactical subtasks from strategic node.

        Args:
            strategic_node: Best strategic node
            raw_state: Raw trading state

        Returns:
            List of tactical nodes
        """
        if strategic_node.action is None:
            return []

        # Get subtasks from strategic action
        subtasks = self.strategic_level.get_subtasks(
            strategic_node.action,
            strategic_node.level_state or self.strategic_level.abstract_state(raw_state),
        )

        tactical_nodes = []
        for subtask in subtasks:
            tactical_state = self.tactical_level.abstract_state(raw_state)
            node = strategic_node.expand_with_subtask(
                action=subtask,
                level_state=tactical_state,
                raw_state=raw_state,
            )
            tactical_nodes.append(node)

        return tactical_nodes

    async def _expand_execution(
        self,
        tactical_node: HierarchicalNode,
        raw_state: TradingState,
    ) -> list[HierarchicalNode]:
        """
        Expand execution subtasks from tactical node.

        Args:
            tactical_node: Best tactical node
            raw_state: Raw trading state

        Returns:
            List of execution nodes
        """
        if tactical_node.action is None:
            return []

        # Get subtasks from tactical action
        subtasks = self.tactical_level.get_subtasks(
            tactical_node.action,
            tactical_node.level_state or self.tactical_level.abstract_state(raw_state),
        )

        execution_nodes = []
        for subtask in subtasks:
            exec_state = self.execution_level.abstract_state(raw_state)
            node = tactical_node.expand_with_subtask(
                action=subtask,
                level_state=exec_state,
                raw_state=raw_state,
                is_primitive=True,  # Execution actions are primitive
            )
            node.is_primitive = True
            execution_nodes.append(node)

        return execution_nodes

    def _should_terminate_level(self, root: HierarchicalNode) -> bool:
        """Check if we should terminate search at this level early."""
        if not root.children:
            return False

        sorted_children = sorted(root.children, key=lambda c: c.visits, reverse=True)
        if len(sorted_children) < 2:
            return False

        best = sorted_children[0]
        second_best = sorted_children[1]

        if best.visits == 0 or second_best.visits == 0:
            return False

        visit_ratio = best.visits / (best.visits + second_best.visits)
        return visit_ratio > self.config.confidence_threshold

    def _count_simulations(self, root: HierarchicalNode) -> int:
        """Count total simulations under a node."""
        return root.visits

    def _count_execution_simulations(self) -> int:
        """Count execution-level simulations."""
        if self.root is None:
            return 0

        count = 0

        def count_recursive(node: HierarchicalNode) -> None:
            nonlocal count
            if node.level == "execution":
                count += node.visits
            for child in node.children:
                count_recursive(child)

        count_recursive(self.root)
        return count

    def _build_result(
        self,
        start_time: float,
        simulations_per_level: dict[str, int],
        time_per_level: dict[str, float],
        best_strategic: HierarchicalNode | None,
    ) -> HierarchicalMCTSResult:
        """Build result from search."""
        result = HierarchicalMCTSResult(
            root=self.root,
            total_time_ms=(time.time() - start_time) * 1000,
            simulations_per_level=simulations_per_level,
            time_per_level=time_per_level,
            total_simulations=sum(simulations_per_level.values()),
        )

        if best_strategic is not None:
            result.strategic_node = best_strategic
            result.strategic_action = best_strategic.action
            result.strategic_value = best_strategic.hierarchical_q_value

            # Collect tactical actions
            for child in best_strategic.children:
                if child.action is not None:
                    result.tactical_actions.append(child.action)

                # Collect execution actions
                for exec_child in child.children:
                    if exec_child.action is not None:
                        result.execution_actions.append(exec_child.action)

        # Compute tree statistics
        if self.root is not None:
            total_nodes, nodes_per_level, max_depth = self._compute_tree_stats()
            result.total_nodes = total_nodes
            result.nodes_per_level = nodes_per_level
            result.max_depth_reached = max_depth

        return result

    def _compute_tree_stats(self) -> tuple[int, dict[str, int], int]:
        """Compute tree statistics."""
        if self.root is None:
            return 0, {}, 0

        total = 0
        nodes_per_level: dict[str, int] = {"strategic": 0, "tactical": 0, "execution": 0}
        max_depth = 0

        stack = [self.root]
        while stack:
            node = stack.pop()
            total += 1
            max_depth = max(max_depth, node.depth)

            if node.level in nodes_per_level:
                nodes_per_level[node.level] += 1

            stack.extend(node.children)

        return total, nodes_per_level, max_depth

    def get_action_distribution(self, level: str = "strategic") -> dict[str, float]:
        """Get probability distribution over actions at a level."""
        if self.root is None:
            return {}

        if level == "strategic":
            return self.root.get_subtask_distribution()

        # Find nodes at target level
        level_nodes = []
        stack = [self.root]
        while stack:
            node = stack.pop()
            if node.level == level:
                level_nodes.append(node)
            stack.extend(node.children)

        if not level_nodes:
            return {}

        # Aggregate visits
        action_visits: dict[str, int] = {}
        for node in level_nodes:
            for child in node.children:
                if child.action is not None:
                    key = child.action.action_type
                    action_visits[key] = action_visits.get(key, 0) + child.visits

        total_visits = sum(action_visits.values())
        if total_visits == 0:
            return {}

        return {k: v / total_visits for k, v in action_visits.items()}
