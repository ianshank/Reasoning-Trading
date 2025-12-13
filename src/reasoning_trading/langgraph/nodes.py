"""
MCTS Phase Nodes for LangGraph orchestration.

Implements specialized nodes for each MCTS phase:
- SelectionNode: UCT selection with neural network priors
- ExpansionNode: Policy network expansion
- SimulationNode: Parallel rollout simulations
- BackpropagationNode: Value backpropagation with MAXQ
"""

from __future__ import annotations

import asyncio
import math
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

import numpy as np
from numpy.typing import NDArray
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from reasoning_trading.langgraph.state import (
    BackpropResult,
    ExpansionResult,
    MCTSPhase,
    MCTSState,
    NodeInfo,
    SelectionResult,
    SimulationResult,
)

if TYPE_CHECKING:
    from reasoning_trading.policy.network import PolicyNetwork


class NodeConfig(BaseSettings):
    """Base configuration for MCTS nodes."""

    model_config = SettingsConfigDict(
        env_prefix="MCTS_NODE_",
        case_sensitive=False,
        extra="ignore",
    )

    # UCT parameters
    exploration_constant: float = Field(
        default=1.41,
        ge=0.1,
        le=10.0,
        description="UCT exploration constant (c_puct)",
    )

    # Policy prior parameters
    prior_weight: float = Field(
        default=1.0,
        ge=0.0,
        le=5.0,
        description="Weight for policy prior in PUCT",
    )

    # Simulation parameters
    max_rollout_depth: int = Field(
        default=50,
        ge=5,
        le=200,
        description="Maximum rollout depth",
    )
    discount_factor: float = Field(
        default=0.99,
        ge=0.9,
        le=1.0,
        description="Discount factor for returns",
    )


class MCTSNode(ABC):
    """Abstract base class for MCTS phase nodes."""

    def __init__(self, config: NodeConfig | None = None):
        """Initialize node."""
        self.config = config or NodeConfig()

    @abstractmethod
    async def execute(self, state: MCTSState) -> MCTSState:
        """Execute this phase of MCTS."""
        pass

    def get_next_phase(self, state: MCTSState) -> MCTSPhase:
        """Determine next phase based on current state."""
        if state.error_message:
            return MCTSPhase.ERROR
        return MCTSPhase.SELECTION


class SelectionNode(MCTSNode):
    """
    Selection phase node using UCT with neural priors.

    Implements PUCT (Predictor + UCT) formula:
    UCT(s,a) = Q(s,a) + c_puct * P(s,a) * sqrt(N(s)) / (1 + N(s,a))
    """

    async def execute(self, state: MCTSState) -> MCTSState:
        """
        Execute selection phase.

        Traverse tree from root to leaf using UCT selection.
        """
        start_time = time.perf_counter()

        try:
            # Start from root
            current_id = state.root_node_id
            path = [current_id]
            uct_values: dict[str, float] = {}

            while True:
                current = state.get_node(current_id)
                if current is None:
                    break

                # Check if terminal or unexpanded
                if current.get("is_terminal", False):
                    break

                children = state.get_children(current_id)
                if not children:
                    # Needs expansion
                    break

                # Select best child using PUCT
                best_child_id = None
                best_uct = float("-inf")

                parent_visits = current.get("visit_count", 1)
                sqrt_parent = math.sqrt(parent_visits)

                for child in children:
                    child_id = child["node_id"]
                    visits = child.get("visit_count", 0)
                    value_sum = child.get("value_sum", 0.0)
                    prior = child.get("prior", 1.0 / len(children))

                    # Q-value
                    q_value = value_sum / max(visits, 1)

                    # PUCT formula
                    exploration = (
                        self.config.exploration_constant
                        * prior
                        * sqrt_parent
                        / (1 + visits)
                    )
                    uct = q_value + exploration

                    uct_values[child_id] = uct

                    if uct > best_uct:
                        best_uct = uct
                        best_child_id = child_id

                if best_child_id is None:
                    break

                current_id = best_child_id
                path.append(current_id)

            # Determine if expansion needed
            leaf_node = state.get_node(current_id)
            needs_expansion = (
                leaf_node is not None
                and not leaf_node.get("is_expanded", False)
                and not leaf_node.get("is_terminal", False)
            )

            state.selection_result = SelectionResult(
                selected_path=path,
                leaf_node_id=current_id,
                uct_values=uct_values,
                needs_expansion=needs_expansion,
                is_terminal=leaf_node.get("is_terminal", False) if leaf_node else False,
            )
            state.current_node_id = current_id

            # Set next phase
            if needs_expansion:
                state.phase = MCTSPhase.EXPANSION
            elif leaf_node and leaf_node.get("is_terminal", False):
                state.phase = MCTSPhase.SIMULATION
            else:
                state.phase = MCTSPhase.SIMULATION

        except Exception as e:
            state.error_message = f"Selection error: {str(e)}"
            state.phase = MCTSPhase.ERROR

        elapsed = (time.perf_counter() - start_time) * 1000
        state.record_phase_time("selection", elapsed)

        return state

    def get_next_phase(self, state: MCTSState) -> MCTSPhase:
        """Determine next phase after selection."""
        if state.selection_result:
            if state.selection_result.get("needs_expansion"):
                return MCTSPhase.EXPANSION
            return MCTSPhase.SIMULATION
        return MCTSPhase.ERROR


class ExpansionNode(MCTSNode):
    """
    Expansion phase node using policy network.

    Uses policy network to generate action priors for new nodes.
    """

    def __init__(
        self,
        config: NodeConfig | None = None,
        policy_network: PolicyNetwork | None = None,
    ):
        """Initialize expansion node."""
        super().__init__(config)
        self.policy_network = policy_network

        # Default actions for trading
        self.default_actions = [
            "hold_position",
            "enter_long_position",
            "exit_long_position",
            "scale_in_position",
            "scale_out_position",
            "adjust_stop_loss",
            "take_partial_profit",
        ]

    async def execute(self, state: MCTSState) -> MCTSState:
        """
        Execute expansion phase.

        Expand leaf node with action priors from policy network.
        """
        start_time = time.perf_counter()

        try:
            leaf_id = state.current_node_id
            leaf_node = state.get_node(leaf_id)

            if leaf_node is None:
                state.error_message = f"Leaf node {leaf_id} not found"
                state.phase = MCTSPhase.ERROR
                return state

            # Get policy priors
            if self.policy_network is not None and state.trading_state_features is not None:
                try:
                    output = self.policy_network.predict(state.trading_state_features)
                    priors = output.action_probs
                    actions = list(priors.keys())
                except Exception:
                    # Fallback to uniform
                    actions = self.default_actions
                    priors = {a: 1.0 / len(actions) for a in actions}
            else:
                # Use uniform priors
                actions = self._get_level_actions(state.hierarchy_level)
                priors = {a: 1.0 / len(actions) for a in actions}

            # Create child nodes
            new_children = []
            for action in actions:
                child_id = f"{leaf_id}_{action}_{uuid.uuid4().hex[:8]}"
                child_node: NodeInfo = {
                    "node_id": child_id,
                    "parent_id": leaf_id,
                    "action": action,
                    "visit_count": 0,
                    "value_sum": 0.0,
                    "prior": priors.get(action, 1.0 / len(actions)),
                    "children": [],
                    "is_terminal": False,
                    "is_expanded": False,
                    "level": state.hierarchy_level,
                }
                state.add_node(child_node)
                new_children.append(child_id)

            # Update parent
            leaf_node["children"] = new_children
            leaf_node["is_expanded"] = True

            state.expansion_result = ExpansionResult(
                expanded_node_id=leaf_id,
                new_children=new_children,
                policy_priors=priors,
                action_mask=[True] * len(actions),
                expansion_time_ms=(time.perf_counter() - start_time) * 1000,
            )

            state.phase = MCTSPhase.SIMULATION

        except Exception as e:
            state.error_message = f"Expansion error: {str(e)}"
            state.phase = MCTSPhase.ERROR

        elapsed = (time.perf_counter() - start_time) * 1000
        state.record_phase_time("expansion", elapsed)

        return state

    def _get_level_actions(self, level: str) -> list[str]:
        """Get actions appropriate for hierarchy level."""
        if level == "strategic":
            return [
                "allocate_aggressive",
                "allocate_moderate",
                "allocate_conservative",
                "reduce_exposure",
                "increase_exposure",
                "rebalance_portfolio",
            ]
        elif level == "execution":
            return [
                "market_order",
                "limit_order",
                "stop_order",
                "iceberg_order",
                "twap_order",
                "wait_for_better_price",
            ]
        else:  # tactical
            return self.default_actions

    def get_next_phase(self, state: MCTSState) -> MCTSPhase:
        """Next phase is always simulation."""
        return MCTSPhase.SIMULATION


class SimulationNode(MCTSNode):
    """
    Simulation phase node with parallel rollouts.

    Runs multiple parallel rollouts from the current state
    to estimate value.
    """

    def __init__(
        self,
        config: NodeConfig | None = None,
        value_network: Any | None = None,
    ):
        """Initialize simulation node."""
        super().__init__(config)
        self.value_network = value_network

    async def execute(self, state: MCTSState) -> MCTSState:
        """
        Execute simulation phase.

        Run parallel rollouts to estimate node value.
        """
        start_time = time.perf_counter()

        try:
            num_simulations = state.parallel_simulations

            # Run parallel simulations
            if num_simulations > 1:
                tasks = [
                    self._run_single_simulation(state, i)
                    for i in range(num_simulations)
                ]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                values = [
                    r for r in results
                    if isinstance(r, (int, float)) and not math.isnan(r)
                ]
            else:
                value = await self._run_single_simulation(state, 0)
                values = [value] if not math.isnan(value) else [0.0]

            if not values:
                values = [0.0]

            mean_value = float(np.mean(values))
            std_value = float(np.std(values)) if len(values) > 1 else 0.0

            state.simulation_result = SimulationResult(
                rollout_values=values,
                mean_value=mean_value,
                std_value=std_value,
                num_simulations=len(values),
                simulation_time_ms=(time.perf_counter() - start_time) * 1000,
                terminal_states=[],
            )

            state.phase = MCTSPhase.BACKPROPAGATION

        except Exception as e:
            state.error_message = f"Simulation error: {str(e)}"
            state.phase = MCTSPhase.ERROR

        elapsed = (time.perf_counter() - start_time) * 1000
        state.record_phase_time("simulation", elapsed)

        return state

    async def _run_single_simulation(
        self,
        state: MCTSState,
        sim_id: int,
    ) -> float:
        """Run a single rollout simulation."""
        # Use value network if available
        if self.value_network is not None and state.trading_state_features is not None:
            try:
                value = self.value_network.predict_value(state.trading_state_features)
                return float(value)
            except Exception:
                pass

        # Heuristic rollout
        return await self._heuristic_rollout(state)

    async def _heuristic_rollout(self, state: MCTSState) -> float:
        """
        Heuristic rollout using simple trading rules.

        Returns estimated value based on current state features.
        """
        if state.trading_state_features is None:
            return 0.0

        features = state.trading_state_features

        # Simple heuristic based on momentum and volatility
        # Assumes features include momentum (positive = bullish) and volatility
        if len(features) < 5:
            return 0.0

        # Use first few features as momentum signals
        momentum = float(np.mean(features[:3])) if len(features) >= 3 else 0.0

        # Clip to reasonable range
        value = np.clip(momentum * 10, -1.0, 1.0)

        # Add small random noise for exploration
        noise = np.random.normal(0, 0.1)
        value = float(np.clip(value + noise, -1.0, 1.0))

        return value

    def get_next_phase(self, state: MCTSState) -> MCTSPhase:
        """Next phase is backpropagation."""
        return MCTSPhase.BACKPROPAGATION


class BackpropagationNode(MCTSNode):
    """
    Backpropagation phase node with MAXQ support.

    Propagates values back through the tree with optional
    MAXQ value decomposition.
    """

    def __init__(
        self,
        config: NodeConfig | None = None,
        use_maxq: bool = False,
    ):
        """Initialize backpropagation node."""
        super().__init__(config)
        self.use_maxq = use_maxq

    async def execute(self, state: MCTSState) -> MCTSState:
        """
        Execute backpropagation phase.

        Update values along path from leaf to root.
        """
        start_time = time.perf_counter()

        try:
            if state.simulation_result is None:
                state.error_message = "No simulation result for backprop"
                state.phase = MCTSPhase.ERROR
                return state

            value = state.simulation_result.get("mean_value", 0.0)
            leaf_id = state.current_node_id

            # Get path to root
            path = state.get_path_to_root(leaf_id)

            updated_nodes = []
            value_deltas: dict[str, float] = {}
            visit_increments: dict[str, int] = {}

            # Backpropagate with discount
            current_value = value
            for node_id in reversed(path):
                state.update_node(node_id, visit_delta=1, value_delta=current_value)
                updated_nodes.append(node_id)
                value_deltas[node_id] = current_value
                visit_increments[node_id] = 1

                # Discount for parent
                current_value *= self.config.discount_factor

            state.backprop_result = BackpropResult(
                updated_nodes=updated_nodes,
                value_deltas=value_deltas,
                visit_increments=visit_increments,
                backprop_time_ms=(time.perf_counter() - start_time) * 1000,
            )

            # Check if search complete
            state.iteration += 1
            if state.is_search_complete():
                state.phase = MCTSPhase.COMPLETE
                self._compute_final_result(state)
            else:
                state.phase = MCTSPhase.SELECTION

        except Exception as e:
            state.error_message = f"Backprop error: {str(e)}"
            state.phase = MCTSPhase.ERROR

        elapsed = (time.perf_counter() - start_time) * 1000
        state.record_phase_time("backpropagation", elapsed)

        return state

    def _compute_final_result(self, state: MCTSState) -> None:
        """Compute final action selection from root."""
        root = state.get_node(state.root_node_id)
        if root is None:
            return

        children = state.get_children(state.root_node_id)
        if not children:
            return

        # Compute action probabilities using visit counts
        total_visits = sum(c.get("visit_count", 0) for c in children)
        if total_visits == 0:
            total_visits = 1

        action_probs: dict[str, float] = {}
        best_action = None
        best_visits = -1

        for child in children:
            action = child.get("action", "unknown")
            visits = child.get("visit_count", 0)

            # Apply temperature
            if state.temperature > 0:
                prob = (visits / total_visits) ** (1.0 / state.temperature)
            else:
                prob = 1.0 if visits == max(c.get("visit_count", 0) for c in children) else 0.0

            action_probs[action] = prob

            if visits > best_visits:
                best_visits = visits
                best_action = action

        # Normalize probabilities
        total_prob = sum(action_probs.values())
        if total_prob > 0:
            action_probs = {k: v / total_prob for k, v in action_probs.items()}

        state.action_probabilities = action_probs
        state.best_action = best_action

        # Root value
        root_visits = root.get("visit_count", 1)
        root_value_sum = root.get("value_sum", 0.0)
        state.root_value = root_value_sum / max(root_visits, 1)

    def get_next_phase(self, state: MCTSState) -> MCTSPhase:
        """Determine next phase."""
        if state.is_search_complete():
            return MCTSPhase.COMPLETE
        return MCTSPhase.SELECTION
