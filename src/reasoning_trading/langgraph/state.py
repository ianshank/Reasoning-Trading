"""
MCTS State definitions for LangGraph orchestration.

Defines the state that flows through MCTS phase nodes:
- Selection state with UCT values
- Expansion state with policy priors
- Simulation state with rollout results
- Backpropagation state with value updates
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, TypedDict

import numpy as np
from numpy.typing import NDArray


class MCTSPhase(str, Enum):
    """MCTS execution phases."""

    SELECTION = "selection"
    EXPANSION = "expansion"
    SIMULATION = "simulation"
    BACKPROPAGATION = "backpropagation"
    COMPLETE = "complete"
    ERROR = "error"


class NodeInfo(TypedDict, total=False):
    """Information about an MCTS tree node."""

    node_id: str
    parent_id: str | None
    action: str
    visit_count: int
    value_sum: float
    prior: float
    children: list[str]
    is_terminal: bool
    is_expanded: bool
    level: str


class SelectionResult(TypedDict, total=False):
    """Result from selection phase."""

    selected_path: list[str]
    leaf_node_id: str
    uct_values: dict[str, float]
    needs_expansion: bool
    is_terminal: bool


class ExpansionResult(TypedDict, total=False):
    """Result from expansion phase."""

    expanded_node_id: str
    new_children: list[str]
    policy_priors: dict[str, float]
    action_mask: list[bool]
    expansion_time_ms: float


class SimulationResult(TypedDict, total=False):
    """Result from simulation phase."""

    rollout_values: list[float]
    mean_value: float
    std_value: float
    num_simulations: int
    simulation_time_ms: float
    terminal_states: list[dict[str, Any]]


class BackpropResult(TypedDict, total=False):
    """Result from backpropagation phase."""

    updated_nodes: list[str]
    value_deltas: dict[str, float]
    visit_increments: dict[str, int]
    backprop_time_ms: float


@dataclass
class MCTSState:
    """
    State for LangGraph MCTS orchestration.

    Contains all information needed for MCTS phase transitions.
    """

    # Current phase
    phase: MCTSPhase = MCTSPhase.SELECTION
    iteration: int = 0
    max_iterations: int = 100

    # Tree structure
    root_node_id: str = ""
    nodes: dict[str, NodeInfo] = field(default_factory=dict)
    current_node_id: str = ""

    # Trading state
    trading_state_features: NDArray[np.float64] | None = None
    symbol: str = ""
    hierarchy_level: str = "tactical"

    # Phase results
    selection_result: SelectionResult | None = None
    expansion_result: ExpansionResult | None = None
    simulation_result: SimulationResult | None = None
    backprop_result: BackpropResult | None = None

    # Search configuration
    exploration_constant: float = 1.41
    temperature: float = 1.0
    use_policy_prior: bool = True
    parallel_simulations: int = 4

    # Timing
    start_time: datetime = field(default_factory=datetime.now)
    phase_times: dict[str, float] = field(default_factory=dict)

    # Error handling
    error_message: str | None = None
    retry_count: int = 0
    max_retries: int = 3

    # Results
    best_action: str | None = None
    action_probabilities: dict[str, float] = field(default_factory=dict)
    root_value: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "phase": self.phase.value,
            "iteration": self.iteration,
            "max_iterations": self.max_iterations,
            "root_node_id": self.root_node_id,
            "current_node_id": self.current_node_id,
            "symbol": self.symbol,
            "hierarchy_level": self.hierarchy_level,
            "selection_result": self.selection_result,
            "expansion_result": self.expansion_result,
            "simulation_result": self.simulation_result,
            "backprop_result": self.backprop_result,
            "exploration_constant": self.exploration_constant,
            "temperature": self.temperature,
            "use_policy_prior": self.use_policy_prior,
            "parallel_simulations": self.parallel_simulations,
            "phase_times": self.phase_times,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "best_action": self.best_action,
            "action_probabilities": self.action_probabilities,
            "root_value": self.root_value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MCTSState:
        """Create from dictionary."""
        state = cls()
        state.phase = MCTSPhase(data.get("phase", "selection"))
        state.iteration = data.get("iteration", 0)
        state.max_iterations = data.get("max_iterations", 100)
        state.root_node_id = data.get("root_node_id", "")
        state.current_node_id = data.get("current_node_id", "")
        state.symbol = data.get("symbol", "")
        state.hierarchy_level = data.get("hierarchy_level", "tactical")
        state.selection_result = data.get("selection_result")
        state.expansion_result = data.get("expansion_result")
        state.simulation_result = data.get("simulation_result")
        state.backprop_result = data.get("backprop_result")
        state.exploration_constant = data.get("exploration_constant", 1.41)
        state.temperature = data.get("temperature", 1.0)
        state.use_policy_prior = data.get("use_policy_prior", True)
        state.parallel_simulations = data.get("parallel_simulations", 4)
        state.phase_times = data.get("phase_times", {})
        state.error_message = data.get("error_message")
        state.retry_count = data.get("retry_count", 0)
        state.best_action = data.get("best_action")
        state.action_probabilities = data.get("action_probabilities", {})
        state.root_value = data.get("root_value", 0.0)
        return state

    def get_node(self, node_id: str) -> NodeInfo | None:
        """Get node by ID."""
        return self.nodes.get(node_id)

    def add_node(self, node: NodeInfo) -> None:
        """Add node to tree."""
        self.nodes[node["node_id"]] = node

    def update_node(
        self,
        node_id: str,
        visit_delta: int = 0,
        value_delta: float = 0.0,
    ) -> None:
        """Update node statistics."""
        if node_id in self.nodes:
            self.nodes[node_id]["visit_count"] += visit_delta
            self.nodes[node_id]["value_sum"] += value_delta

    def get_children(self, node_id: str) -> list[NodeInfo]:
        """Get children of a node."""
        node = self.nodes.get(node_id)
        if node is None:
            return []
        return [self.nodes[cid] for cid in node.get("children", []) if cid in self.nodes]

    def get_path_to_root(self, node_id: str) -> list[str]:
        """Get path from node to root."""
        path = [node_id]
        current = self.nodes.get(node_id)

        while current and current.get("parent_id"):
            path.append(current["parent_id"])
            current = self.nodes.get(current["parent_id"])

        return list(reversed(path))

    def is_search_complete(self) -> bool:
        """Check if search should terminate."""
        return (
            self.iteration >= self.max_iterations
            or self.phase == MCTSPhase.COMPLETE
            or self.phase == MCTSPhase.ERROR
        )

    def record_phase_time(self, phase: str, time_ms: float) -> None:
        """Record time for a phase."""
        if phase not in self.phase_times:
            self.phase_times[phase] = 0.0
        self.phase_times[phase] += time_ms

    def get_total_time_ms(self) -> float:
        """Get total search time in ms."""
        return sum(self.phase_times.values())


class MCTSStateDict(TypedDict, total=False):
    """TypedDict version of MCTSState for LangGraph compatibility."""

    phase: str
    iteration: int
    max_iterations: int
    root_node_id: str
    nodes: dict[str, NodeInfo]
    current_node_id: str
    trading_state_features: list[float] | None
    symbol: str
    hierarchy_level: str
    selection_result: SelectionResult | None
    expansion_result: ExpansionResult | None
    simulation_result: SimulationResult | None
    backprop_result: BackpropResult | None
    exploration_constant: float
    temperature: float
    use_policy_prior: bool
    parallel_simulations: int
    phase_times: dict[str, float]
    error_message: str | None
    retry_count: int
    max_retries: int
    best_action: str | None
    action_probabilities: dict[str, float]
    root_value: float
