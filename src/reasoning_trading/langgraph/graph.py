"""
LangGraph MCTS Graph Builder.

Builds and compiles the MCTS workflow graph using LangGraph patterns:
- State-based routing between phases
- Conditional edges for phase transitions
- Checkpoint support for resumable search
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable, Literal

import numpy as np
from numpy.typing import NDArray
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from reasoning_trading.langgraph.nodes import (
    BackpropagationNode,
    ExpansionNode,
    NodeConfig,
    SelectionNode,
    SimulationNode,
)
from reasoning_trading.langgraph.state import (
    MCTSPhase,
    MCTSState,
    NodeInfo,
)

if TYPE_CHECKING:
    from reasoning_trading.policy.network import PolicyNetwork


class MCTSGraphConfig(BaseSettings):
    """Configuration for MCTS graph."""

    model_config = SettingsConfigDict(
        env_prefix="MCTS_GRAPH_",
        case_sensitive=False,
        extra="ignore",
    )

    # Search parameters
    max_iterations: int = Field(
        default=100,
        ge=10,
        le=10000,
        description="Maximum MCTS iterations",
    )
    exploration_constant: float = Field(
        default=1.41,
        ge=0.1,
        le=10.0,
        description="UCT exploration constant",
    )
    temperature: float = Field(
        default=1.0,
        ge=0.0,
        le=10.0,
        description="Action selection temperature",
    )

    # Parallelism
    parallel_simulations: int = Field(
        default=4,
        ge=1,
        le=32,
        description="Number of parallel simulations",
    )

    # Policy settings
    use_policy_prior: bool = Field(
        default=True,
        description="Use policy network for priors",
    )

    # Hierarchy
    default_level: str = Field(
        default="tactical",
        description="Default hierarchy level",
    )

    # Error handling
    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum retries on error",
    )


@dataclass
class MCTSGraphResult:
    """Result from MCTS graph execution."""

    best_action: str | None
    action_probabilities: dict[str, float]
    root_value: float
    iterations_completed: int
    total_time_ms: float
    phase_times: dict[str, float]
    tree_size: int
    success: bool
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "best_action": self.best_action,
            "action_probabilities": self.action_probabilities,
            "root_value": self.root_value,
            "iterations_completed": self.iterations_completed,
            "total_time_ms": self.total_time_ms,
            "phase_times": self.phase_times,
            "tree_size": self.tree_size,
            "success": self.success,
            "error_message": self.error_message,
        }


class MCTSGraph:
    """
    MCTS Graph using LangGraph patterns.

    Implements a state machine for MCTS phases:
    Selection -> Expansion -> Simulation -> Backprop -> (loop or complete)
    """

    def __init__(
        self,
        config: MCTSGraphConfig | None = None,
        node_config: NodeConfig | None = None,
        policy_network: PolicyNetwork | None = None,
    ):
        """Initialize MCTS graph."""
        self.config = config or MCTSGraphConfig()
        self.node_config = node_config or NodeConfig()

        # Create phase nodes
        self.selection_node = SelectionNode(self.node_config)
        self.expansion_node = ExpansionNode(self.node_config, policy_network)
        self.simulation_node = SimulationNode(self.node_config)
        self.backprop_node = BackpropagationNode(self.node_config)

        # Phase handlers
        self._phase_handlers: dict[MCTSPhase, Callable] = {
            MCTSPhase.SELECTION: self._handle_selection,
            MCTSPhase.EXPANSION: self._handle_expansion,
            MCTSPhase.SIMULATION: self._handle_simulation,
            MCTSPhase.BACKPROPAGATION: self._handle_backprop,
        }

    async def run(
        self,
        trading_state_features: NDArray[np.float64],
        symbol: str = "",
        level: str = "tactical",
        max_iterations: int | None = None,
    ) -> MCTSGraphResult:
        """
        Run MCTS search on the given state.

        Args:
            trading_state_features: Feature vector for current state
            symbol: Trading symbol
            level: Hierarchy level
            max_iterations: Override max iterations

        Returns:
            MCTSGraphResult with best action and statistics
        """
        # Initialize state
        state = self._initialize_state(
            trading_state_features,
            symbol,
            level,
            max_iterations or self.config.max_iterations,
        )

        # Run graph until completion
        while not state.is_search_complete():
            handler = self._phase_handlers.get(state.phase)
            if handler is None:
                break
            state = await handler(state)

            # Handle errors
            if state.phase == MCTSPhase.ERROR:
                if state.retry_count < state.max_retries:
                    state.retry_count += 1
                    state.error_message = None
                    state.phase = MCTSPhase.SELECTION
                else:
                    break

        return self._build_result(state)

    def _initialize_state(
        self,
        features: NDArray[np.float64],
        symbol: str,
        level: str,
        max_iterations: int,
    ) -> MCTSState:
        """Initialize MCTS state with root node."""
        root_id = f"root_{uuid.uuid4().hex[:8]}"

        root_node: NodeInfo = {
            "node_id": root_id,
            "parent_id": None,
            "action": "root",
            "visit_count": 0,
            "value_sum": 0.0,
            "prior": 1.0,
            "children": [],
            "is_terminal": False,
            "is_expanded": False,
            "level": level,
        }

        state = MCTSState(
            phase=MCTSPhase.SELECTION,
            iteration=0,
            max_iterations=max_iterations,
            root_node_id=root_id,
            current_node_id=root_id,
            trading_state_features=features,
            symbol=symbol,
            hierarchy_level=level,
            exploration_constant=self.config.exploration_constant,
            temperature=self.config.temperature,
            use_policy_prior=self.config.use_policy_prior,
            parallel_simulations=self.config.parallel_simulations,
            max_retries=self.config.max_retries,
        )

        state.add_node(root_node)

        return state

    async def _handle_selection(self, state: MCTSState) -> MCTSState:
        """Handle selection phase."""
        return await self.selection_node.execute(state)

    async def _handle_expansion(self, state: MCTSState) -> MCTSState:
        """Handle expansion phase."""
        return await self.expansion_node.execute(state)

    async def _handle_simulation(self, state: MCTSState) -> MCTSState:
        """Handle simulation phase."""
        return await self.simulation_node.execute(state)

    async def _handle_backprop(self, state: MCTSState) -> MCTSState:
        """Handle backpropagation phase."""
        return await self.backprop_node.execute(state)

    def _build_result(self, state: MCTSState) -> MCTSGraphResult:
        """Build result from final state."""
        return MCTSGraphResult(
            best_action=state.best_action,
            action_probabilities=state.action_probabilities,
            root_value=state.root_value,
            iterations_completed=state.iteration,
            total_time_ms=state.get_total_time_ms(),
            phase_times=state.phase_times,
            tree_size=len(state.nodes),
            success=state.phase == MCTSPhase.COMPLETE,
            error_message=state.error_message,
        )

    def get_phase_stats(self) -> dict[str, Any]:
        """Get statistics about phase execution."""
        return {
            "selection_config": {
                "exploration_constant": self.node_config.exploration_constant,
            },
            "simulation_config": {
                "max_rollout_depth": self.node_config.max_rollout_depth,
                "discount_factor": self.node_config.discount_factor,
            },
        }


def build_mcts_graph(
    config: MCTSGraphConfig | None = None,
    node_config: NodeConfig | None = None,
    policy_network: PolicyNetwork | None = None,
) -> MCTSGraph:
    """
    Build an MCTS graph with the given configuration.

    This is the main factory function for creating MCTS graphs.

    Args:
        config: Graph configuration
        node_config: Node configuration
        policy_network: Optional policy network for priors

    Returns:
        Configured MCTSGraph instance
    """
    return MCTSGraph(
        config=config,
        node_config=node_config,
        policy_network=policy_network,
    )


class MCTSGraphBuilder:
    """
    Builder pattern for constructing MCTS graphs.

    Provides fluent interface for configuring MCTS graphs.
    """

    def __init__(self):
        """Initialize builder."""
        self._config = MCTSGraphConfig()
        self._node_config = NodeConfig()
        self._policy_network: PolicyNetwork | None = None
        self._value_network: Any | None = None

    def with_iterations(self, max_iterations: int) -> MCTSGraphBuilder:
        """Set maximum iterations."""
        self._config = MCTSGraphConfig(
            max_iterations=max_iterations,
            exploration_constant=self._config.exploration_constant,
            temperature=self._config.temperature,
            parallel_simulations=self._config.parallel_simulations,
            use_policy_prior=self._config.use_policy_prior,
            default_level=self._config.default_level,
            max_retries=self._config.max_retries,
        )
        return self

    def with_exploration(self, c_puct: float) -> MCTSGraphBuilder:
        """Set exploration constant."""
        self._config = MCTSGraphConfig(
            max_iterations=self._config.max_iterations,
            exploration_constant=c_puct,
            temperature=self._config.temperature,
            parallel_simulations=self._config.parallel_simulations,
            use_policy_prior=self._config.use_policy_prior,
            default_level=self._config.default_level,
            max_retries=self._config.max_retries,
        )
        return self

    def with_temperature(self, temperature: float) -> MCTSGraphBuilder:
        """Set action selection temperature."""
        self._config = MCTSGraphConfig(
            max_iterations=self._config.max_iterations,
            exploration_constant=self._config.exploration_constant,
            temperature=temperature,
            parallel_simulations=self._config.parallel_simulations,
            use_policy_prior=self._config.use_policy_prior,
            default_level=self._config.default_level,
            max_retries=self._config.max_retries,
        )
        return self

    def with_parallel_simulations(self, num: int) -> MCTSGraphBuilder:
        """Set number of parallel simulations."""
        self._config = MCTSGraphConfig(
            max_iterations=self._config.max_iterations,
            exploration_constant=self._config.exploration_constant,
            temperature=self._config.temperature,
            parallel_simulations=num,
            use_policy_prior=self._config.use_policy_prior,
            default_level=self._config.default_level,
            max_retries=self._config.max_retries,
        )
        return self

    def with_policy_network(self, network: PolicyNetwork) -> MCTSGraphBuilder:
        """Set policy network for priors."""
        self._policy_network = network
        return self

    def with_value_network(self, network: Any) -> MCTSGraphBuilder:
        """Set value network for simulations."""
        self._value_network = network
        return self

    def build(self) -> MCTSGraph:
        """Build the configured graph."""
        graph = MCTSGraph(
            config=self._config,
            node_config=self._node_config,
            policy_network=self._policy_network,
        )

        if self._value_network is not None:
            graph.simulation_node.value_network = self._value_network

        return graph
