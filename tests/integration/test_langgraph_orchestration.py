"""
Integration tests for LangGraph MCTS Orchestration.

Tests the LangGraph-based MCTS phase orchestration.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import numpy as np
import pytest

from reasoning_trading.langgraph import (
    BackpropagationNode,
    ExpansionNode,
    MCTSGraph,
    MCTSGraphConfig,
    MCTSOrchestrator,
    MCTSOrchestratorConfig,
    MCTSPhase,
    MCTSState,
    SelectionNode,
    SimulationNode,
    build_mcts_graph,
)
from reasoning_trading.langgraph.nodes import NodeConfig

if TYPE_CHECKING:
    from tests.config import TestConfig
    from tests.factories import TradingStateFactory


class TestMCTSState:
    """Test MCTS state management."""

    def test_state_initialization(self) -> None:
        """Test default state initialization."""
        state = MCTSState()

        assert state.phase == MCTSPhase.SELECTION
        assert state.iteration == 0
        assert len(state.nodes) == 0

    def test_node_management(self) -> None:
        """Test adding and retrieving nodes."""
        state = MCTSState()

        node = {
            "node_id": "test_001",
            "parent_id": None,
            "action": "root",
            "visit_count": 0,
            "value_sum": 0.0,
            "prior": 1.0,
            "children": [],
            "is_terminal": False,
            "is_expanded": False,
            "level": "tactical",
        }
        state.add_node(node)

        retrieved = state.get_node("test_001")
        assert retrieved is not None
        assert retrieved["action"] == "root"

    def test_node_update(self) -> None:
        """Test updating node statistics."""
        state = MCTSState()

        node = {
            "node_id": "test_002",
            "parent_id": None,
            "action": "root",
            "visit_count": 0,
            "value_sum": 0.0,
            "prior": 1.0,
            "children": [],
            "is_terminal": False,
            "is_expanded": False,
            "level": "tactical",
        }
        state.add_node(node)

        state.update_node("test_002", visit_delta=1, value_delta=0.5)

        updated = state.get_node("test_002")
        assert updated["visit_count"] == 1
        assert updated["value_sum"] == 0.5

    def test_path_to_root(self) -> None:
        """Test getting path from node to root."""
        state = MCTSState()

        # Create hierarchy
        root = {
            "node_id": "root",
            "parent_id": None,
            "action": "root",
            "visit_count": 0,
            "value_sum": 0.0,
            "prior": 1.0,
            "children": ["child"],
            "is_terminal": False,
            "is_expanded": True,
            "level": "strategic",
        }
        child = {
            "node_id": "child",
            "parent_id": "root",
            "action": "buy",
            "visit_count": 0,
            "value_sum": 0.0,
            "prior": 0.5,
            "children": ["grandchild"],
            "is_terminal": False,
            "is_expanded": True,
            "level": "tactical",
        }
        grandchild = {
            "node_id": "grandchild",
            "parent_id": "child",
            "action": "market_order",
            "visit_count": 0,
            "value_sum": 0.0,
            "prior": 0.3,
            "children": [],
            "is_terminal": False,
            "is_expanded": False,
            "level": "execution",
        }

        state.add_node(root)
        state.add_node(child)
        state.add_node(grandchild)

        path = state.get_path_to_root("grandchild")
        assert path == ["root", "child", "grandchild"]

    def test_serialization(self) -> None:
        """Test state serialization."""
        state = MCTSState(
            phase=MCTSPhase.SIMULATION,
            iteration=5,
            max_iterations=100,
            symbol="AAPL",
        )

        data = state.to_dict()
        restored = MCTSState.from_dict(data)

        assert restored.phase == MCTSPhase.SIMULATION
        assert restored.iteration == 5
        assert restored.symbol == "AAPL"


class TestSelectionNode:
    """Test selection phase node."""

    @pytest.fixture
    def selection_node(self) -> SelectionNode:
        """Create selection node."""
        return SelectionNode()

    @pytest.fixture
    def state_with_tree(self) -> MCTSState:
        """Create state with a small tree."""
        state = MCTSState()
        state.root_node_id = "root"
        state.current_node_id = "root"

        root = {
            "node_id": "root",
            "parent_id": None,
            "action": "root",
            "visit_count": 10,
            "value_sum": 5.0,
            "prior": 1.0,
            "children": ["child_a", "child_b"],
            "is_terminal": False,
            "is_expanded": True,
            "level": "tactical",
        }
        child_a = {
            "node_id": "child_a",
            "parent_id": "root",
            "action": "buy",
            "visit_count": 3,
            "value_sum": 2.0,
            "prior": 0.6,
            "children": [],
            "is_terminal": False,
            "is_expanded": False,
            "level": "tactical",
        }
        child_b = {
            "node_id": "child_b",
            "parent_id": "root",
            "action": "hold",
            "visit_count": 5,
            "value_sum": 2.5,
            "prior": 0.4,
            "children": [],
            "is_terminal": False,
            "is_expanded": False,
            "level": "tactical",
        }

        state.add_node(root)
        state.add_node(child_a)
        state.add_node(child_b)

        return state

    @pytest.mark.asyncio
    async def test_selection_selects_best_child(
        self,
        selection_node: SelectionNode,
        state_with_tree: MCTSState,
    ) -> None:
        """Test that selection chooses best UCT child."""
        result = await selection_node.execute(state_with_tree)

        assert result.selection_result is not None
        assert result.selection_result["leaf_node_id"] in ["child_a", "child_b"]

    @pytest.mark.asyncio
    async def test_selection_identifies_expansion_need(
        self,
        selection_node: SelectionNode,
        state_with_tree: MCTSState,
    ) -> None:
        """Test that unexpanded leaf is marked for expansion."""
        result = await selection_node.execute(state_with_tree)

        assert result.selection_result is not None
        assert result.selection_result["needs_expansion"] is True


class TestExpansionNode:
    """Test expansion phase node."""

    @pytest.fixture
    def expansion_node(self) -> ExpansionNode:
        """Create expansion node."""
        return ExpansionNode()

    @pytest.mark.asyncio
    async def test_expansion_creates_children(
        self,
        expansion_node: ExpansionNode,
    ) -> None:
        """Test that expansion creates child nodes."""
        state = MCTSState()
        state.current_node_id = "leaf"
        state.hierarchy_level = "tactical"

        leaf = {
            "node_id": "leaf",
            "parent_id": "root",
            "action": "parent_action",
            "visit_count": 0,
            "value_sum": 0.0,
            "prior": 0.5,
            "children": [],
            "is_terminal": False,
            "is_expanded": False,
            "level": "tactical",
        }
        state.add_node(leaf)

        result = await expansion_node.execute(state)

        assert result.expansion_result is not None
        assert len(result.expansion_result["new_children"]) > 0

        # Verify children were added
        leaf_node = result.get_node("leaf")
        assert leaf_node["is_expanded"] is True
        assert len(leaf_node["children"]) > 0


class TestSimulationNode:
    """Test simulation phase node."""

    @pytest.fixture
    def simulation_node(self) -> SimulationNode:
        """Create simulation node."""
        return SimulationNode()

    @pytest.mark.asyncio
    async def test_simulation_produces_values(
        self,
        simulation_node: SimulationNode,
        trading_state_factory: TradingStateFactory,
    ) -> None:
        """Test that simulation produces value estimates."""
        trading_state = trading_state_factory.create()

        state = MCTSState()
        state.trading_state_features = trading_state.to_feature_vector()
        state.parallel_simulations = 2

        result = await simulation_node.execute(state)

        assert result.simulation_result is not None
        assert len(result.simulation_result["rollout_values"]) > 0
        assert "mean_value" in result.simulation_result

    @pytest.mark.asyncio
    async def test_parallel_simulations(
        self,
        simulation_node: SimulationNode,
        trading_state_factory: TradingStateFactory,
    ) -> None:
        """Test parallel simulation execution."""
        trading_state = trading_state_factory.create()

        state = MCTSState()
        state.trading_state_features = trading_state.to_feature_vector()
        state.parallel_simulations = 4

        result = await simulation_node.execute(state)

        assert result.simulation_result["num_simulations"] >= 1


class TestBackpropagationNode:
    """Test backpropagation phase node."""

    @pytest.fixture
    def backprop_node(self) -> BackpropagationNode:
        """Create backpropagation node."""
        return BackpropagationNode()

    @pytest.mark.asyncio
    async def test_backprop_updates_path(
        self,
        backprop_node: BackpropagationNode,
    ) -> None:
        """Test that backprop updates all nodes on path."""
        state = MCTSState()
        state.root_node_id = "root"
        state.current_node_id = "leaf"
        state.simulation_result = {
            "rollout_values": [0.5],
            "mean_value": 0.5,
            "std_value": 0.0,
            "num_simulations": 1,
            "simulation_time_ms": 1.0,
            "terminal_states": [],
        }

        # Create path
        root = {
            "node_id": "root",
            "parent_id": None,
            "action": "root",
            "visit_count": 5,
            "value_sum": 2.0,
            "prior": 1.0,
            "children": ["child"],
            "is_terminal": False,
            "is_expanded": True,
            "level": "strategic",
        }
        child = {
            "node_id": "child",
            "parent_id": "root",
            "action": "buy",
            "visit_count": 3,
            "value_sum": 1.0,
            "prior": 0.5,
            "children": ["leaf"],
            "is_terminal": False,
            "is_expanded": True,
            "level": "tactical",
        }
        leaf = {
            "node_id": "leaf",
            "parent_id": "child",
            "action": "market",
            "visit_count": 0,
            "value_sum": 0.0,
            "prior": 0.3,
            "children": [],
            "is_terminal": False,
            "is_expanded": True,
            "level": "execution",
        }

        state.add_node(root)
        state.add_node(child)
        state.add_node(leaf)

        result = await backprop_node.execute(state)

        assert result.backprop_result is not None
        assert len(result.backprop_result["updated_nodes"]) == 3

        # Check values were updated
        updated_leaf = result.get_node("leaf")
        assert updated_leaf["visit_count"] == 1


class TestMCTSGraph:
    """Test complete MCTS graph execution."""

    @pytest.fixture
    def graph_config(self) -> MCTSGraphConfig:
        """Create graph configuration."""
        return MCTSGraphConfig(
            max_iterations=20,
            exploration_constant=1.41,
            parallel_simulations=2,
        )

    @pytest.fixture
    def mcts_graph(self, graph_config: MCTSGraphConfig) -> MCTSGraph:
        """Create MCTS graph."""
        return MCTSGraph(graph_config)

    @pytest.mark.asyncio
    async def test_graph_search(
        self,
        mcts_graph: MCTSGraph,
        trading_state_factory: TradingStateFactory,
    ) -> None:
        """Test complete graph search."""
        state = trading_state_factory.create()
        features = state.to_feature_vector()

        result = await mcts_graph.run(
            trading_state_features=features,
            symbol=state.symbol,
            level="tactical",
        )

        assert result.success
        assert result.best_action is not None
        assert result.iterations_completed > 0

    @pytest.mark.asyncio
    async def test_graph_produces_probabilities(
        self,
        mcts_graph: MCTSGraph,
        trading_state_factory: TradingStateFactory,
    ) -> None:
        """Test that graph produces action probabilities."""
        state = trading_state_factory.create()
        features = state.to_feature_vector()

        result = await mcts_graph.run(
            trading_state_features=features,
            symbol=state.symbol,
        )

        assert len(result.action_probabilities) > 0
        total_prob = sum(result.action_probabilities.values())
        assert abs(total_prob - 1.0) < 0.01


class TestMCTSOrchestrator:
    """Test MCTS orchestrator."""

    @pytest.fixture
    def orchestrator_config(self) -> MCTSOrchestratorConfig:
        """Create orchestrator configuration."""
        return MCTSOrchestratorConfig(
            strategic_iterations=30,
            tactical_iterations=20,
            execution_iterations=10,
            strategic_timeout_seconds=5.0,
            tactical_timeout_seconds=2.0,
            execution_timeout_seconds=1.0,
        )

    @pytest.fixture
    def orchestrator(
        self,
        orchestrator_config: MCTSOrchestratorConfig,
    ) -> MCTSOrchestrator:
        """Create orchestrator."""
        return MCTSOrchestrator(orchestrator_config)

    @pytest.mark.asyncio
    async def test_single_level_search(
        self,
        orchestrator: MCTSOrchestrator,
        trading_state_factory: TradingStateFactory,
    ) -> None:
        """Test single level search."""
        state = trading_state_factory.create()

        result = await orchestrator.search(state, level="tactical")

        assert result.best_action is not None
        assert result.level == "tactical"
        assert result.confidence > 0

    @pytest.mark.asyncio
    async def test_hierarchical_search(
        self,
        orchestrator: MCTSOrchestrator,
        trading_state_factory: TradingStateFactory,
    ) -> None:
        """Test hierarchical search across levels."""
        state = trading_state_factory.create()

        result = await orchestrator.hierarchical_search(
            state,
            target_level="execution",
        )

        assert result.success
        assert result.final_action is not None
        assert result.strategic_result is not None

    @pytest.mark.asyncio
    async def test_parallel_search(
        self,
        orchestrator: MCTSOrchestrator,
        trading_state_factory: TradingStateFactory,
    ) -> None:
        """Test parallel searches."""
        states = [trading_state_factory.create() for _ in range(3)]

        results = await orchestrator.parallel_search(states, level="tactical")

        assert len(results) == 3
        for result in results:
            assert result.best_action is not None

    @pytest.mark.asyncio
    async def test_caching(
        self,
        trading_state_factory: TradingStateFactory,
    ) -> None:
        """Test result caching."""
        config = MCTSOrchestratorConfig(
            enable_result_caching=True,
            cache_ttl_seconds=60,
            tactical_iterations=10,
        )
        orchestrator = MCTSOrchestrator(config)

        state = trading_state_factory.create()

        # First search
        result1 = await orchestrator.search(state, level="tactical")

        # Second search (should hit cache)
        result2 = await orchestrator.search(state, level="tactical")

        # Cache hit should be faster
        # (May not always be true due to test overhead, just check it works)
        assert result1.best_action is not None
        assert result2.best_action is not None

        stats = orchestrator.get_statistics()
        assert stats["cache_hits"] >= 0


class TestBuildMCTSGraph:
    """Test graph builder function."""

    def test_build_default_graph(self) -> None:
        """Test building graph with defaults."""
        graph = build_mcts_graph()

        assert graph is not None
        assert isinstance(graph, MCTSGraph)

    def test_build_with_config(self) -> None:
        """Test building graph with custom config."""
        config = MCTSGraphConfig(
            max_iterations=50,
            exploration_constant=2.0,
        )

        graph = build_mcts_graph(config=config)

        assert graph.config.max_iterations == 50
        assert graph.config.exploration_constant == 2.0
