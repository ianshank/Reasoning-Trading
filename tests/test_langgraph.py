"""
Unit tests for LangGraph MCTS Orchestration module.

Tests state management, phase nodes, and graph execution.
"""

from __future__ import annotations

from datetime import datetime

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
from reasoning_trading.langgraph.state import (
    BackpropResult,
    ExpansionResult,
    NodeInfo,
    SelectionResult,
    SimulationResult,
)


class TestMCTSPhase:
    """Test MCTSPhase enum."""

    def test_all_phases(self) -> None:
        """Test all phases exist."""
        phases = [p.value for p in MCTSPhase]

        assert "selection" in phases
        assert "expansion" in phases
        assert "simulation" in phases
        assert "backpropagation" in phases
        assert "complete" in phases
        assert "error" in phases


class TestNodeInfo:
    """Test NodeInfo TypedDict."""

    def test_node_creation(self) -> None:
        """Test creating node info."""
        node: NodeInfo = {
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

        assert node["node_id"] == "test_001"
        assert node["action"] == "root"


class TestMCTSState:
    """Test MCTSState dataclass."""

    def test_default_initialization(self) -> None:
        """Test default state initialization."""
        state = MCTSState()

        assert state.phase == MCTSPhase.SELECTION
        assert state.iteration == 0
        assert len(state.nodes) == 0

    def test_add_node(self) -> None:
        """Test adding node to state."""
        state = MCTSState()

        node: NodeInfo = {
            "node_id": "node_001",
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

        assert len(state.nodes) == 1
        assert "node_001" in state.nodes

    def test_get_node(self) -> None:
        """Test retrieving node."""
        state = MCTSState()

        node: NodeInfo = {
            "node_id": "node_002",
            "parent_id": None,
            "action": "test",
            "visit_count": 5,
            "value_sum": 2.5,
            "prior": 0.5,
            "children": [],
            "is_terminal": False,
            "is_expanded": False,
            "level": "tactical",
        }

        state.add_node(node)
        retrieved = state.get_node("node_002")

        assert retrieved is not None
        assert retrieved["visit_count"] == 5

    def test_update_node(self) -> None:
        """Test updating node statistics."""
        state = MCTSState()

        node: NodeInfo = {
            "node_id": "node_003",
            "parent_id": None,
            "action": "test",
            "visit_count": 0,
            "value_sum": 0.0,
            "prior": 1.0,
            "children": [],
            "is_terminal": False,
            "is_expanded": False,
            "level": "tactical",
        }

        state.add_node(node)
        state.update_node("node_003", visit_delta=2, value_delta=1.5)

        updated = state.get_node("node_003")
        assert updated["visit_count"] == 2
        assert updated["value_sum"] == 1.5

    def test_get_children(self) -> None:
        """Test getting child nodes."""
        state = MCTSState()

        parent: NodeInfo = {
            "node_id": "parent",
            "parent_id": None,
            "action": "root",
            "visit_count": 0,
            "value_sum": 0.0,
            "prior": 1.0,
            "children": ["child_a", "child_b"],
            "is_terminal": False,
            "is_expanded": True,
            "level": "strategic",
        }
        child_a: NodeInfo = {
            "node_id": "child_a",
            "parent_id": "parent",
            "action": "buy",
            "visit_count": 0,
            "value_sum": 0.0,
            "prior": 0.5,
            "children": [],
            "is_terminal": False,
            "is_expanded": False,
            "level": "tactical",
        }
        child_b: NodeInfo = {
            "node_id": "child_b",
            "parent_id": "parent",
            "action": "sell",
            "visit_count": 0,
            "value_sum": 0.0,
            "prior": 0.5,
            "children": [],
            "is_terminal": False,
            "is_expanded": False,
            "level": "tactical",
        }

        state.add_node(parent)
        state.add_node(child_a)
        state.add_node(child_b)

        children = state.get_children("parent")
        assert len(children) == 2

    def test_path_to_root(self) -> None:
        """Test getting path from node to root."""
        state = MCTSState()

        state.add_node({
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
        })
        state.add_node({
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
        })
        state.add_node({
            "node_id": "grandchild",
            "parent_id": "child",
            "action": "market",
            "visit_count": 0,
            "value_sum": 0.0,
            "prior": 0.3,
            "children": [],
            "is_terminal": False,
            "is_expanded": False,
            "level": "execution",
        })

        path = state.get_path_to_root("grandchild")
        assert path == ["root", "child", "grandchild"]

    def test_is_search_complete(self) -> None:
        """Test search completion check."""
        state = MCTSState(max_iterations=10)

        assert not state.is_search_complete()

        state.iteration = 10
        assert state.is_search_complete()

        state.iteration = 5
        state.phase = MCTSPhase.COMPLETE
        assert state.is_search_complete()

    def test_record_phase_time(self) -> None:
        """Test phase time recording."""
        state = MCTSState()

        state.record_phase_time("selection", 5.0)
        state.record_phase_time("selection", 3.0)

        assert state.phase_times["selection"] == 8.0

    def test_total_time(self) -> None:
        """Test total time calculation."""
        state = MCTSState()

        state.record_phase_time("selection", 5.0)
        state.record_phase_time("expansion", 3.0)
        state.record_phase_time("simulation", 10.0)

        assert state.get_total_time_ms() == 18.0

    def test_serialization(self) -> None:
        """Test state serialization."""
        state = MCTSState(
            phase=MCTSPhase.EXPANSION,
            iteration=5,
            symbol="AAPL",
        )

        data = state.to_dict()
        restored = MCTSState.from_dict(data)

        assert restored.phase == MCTSPhase.EXPANSION
        assert restored.iteration == 5
        assert restored.symbol == "AAPL"


class TestNodeConfig:
    """Test NodeConfig configuration."""

    def test_default_values(self) -> None:
        """Test default configuration."""
        config = NodeConfig()

        assert config.exploration_constant > 0
        assert config.prior_weight > 0
        assert config.max_rollout_depth > 0
        assert 0 < config.discount_factor <= 1


class TestSelectionNode:
    """Test SelectionNode."""

    @pytest.fixture
    def node(self) -> SelectionNode:
        """Create selection node."""
        return SelectionNode()

    def test_creation(self, node: SelectionNode) -> None:
        """Test node creation."""
        assert node is not None


class TestExpansionNode:
    """Test ExpansionNode."""

    @pytest.fixture
    def node(self) -> ExpansionNode:
        """Create expansion node."""
        return ExpansionNode()

    def test_creation(self, node: ExpansionNode) -> None:
        """Test node creation."""
        assert node is not None

    def test_level_actions(self, node: ExpansionNode) -> None:
        """Test getting level-specific actions."""
        strategic = node._get_level_actions("strategic")
        tactical = node._get_level_actions("tactical")
        execution = node._get_level_actions("execution")

        assert len(strategic) > 0
        assert len(tactical) > 0
        assert len(execution) > 0


class TestSimulationNode:
    """Test SimulationNode."""

    @pytest.fixture
    def node(self) -> SimulationNode:
        """Create simulation node."""
        return SimulationNode()

    def test_creation(self, node: SimulationNode) -> None:
        """Test node creation."""
        assert node is not None


class TestBackpropagationNode:
    """Test BackpropagationNode."""

    @pytest.fixture
    def node(self) -> BackpropagationNode:
        """Create backpropagation node."""
        return BackpropagationNode()

    def test_creation(self, node: BackpropagationNode) -> None:
        """Test node creation."""
        assert node is not None


class TestMCTSGraphConfig:
    """Test MCTSGraphConfig configuration."""

    def test_default_values(self) -> None:
        """Test default configuration."""
        config = MCTSGraphConfig()

        assert config.max_iterations > 0
        assert config.exploration_constant > 0
        assert config.parallel_simulations >= 1

    def test_env_override(self, monkeypatch) -> None:
        """Test environment override."""
        monkeypatch.setenv("MCTS_GRAPH_MAX_ITERATIONS", "500")

        config = MCTSGraphConfig()
        assert config.max_iterations == 500


class TestMCTSGraph:
    """Test MCTSGraph."""

    @pytest.fixture
    def graph(self) -> MCTSGraph:
        """Create MCTS graph."""
        config = MCTSGraphConfig(max_iterations=10)
        return MCTSGraph(config)

    def test_creation(self, graph: MCTSGraph) -> None:
        """Test graph creation."""
        assert graph is not None
        assert graph.selection_node is not None
        assert graph.expansion_node is not None
        assert graph.simulation_node is not None
        assert graph.backprop_node is not None

    def test_get_phase_stats(self, graph: MCTSGraph) -> None:
        """Test getting phase statistics."""
        stats = graph.get_phase_stats()

        assert "selection_config" in stats
        assert "simulation_config" in stats


class TestBuildMCTSGraph:
    """Test build_mcts_graph function."""

    def test_build_default(self) -> None:
        """Test building with defaults."""
        graph = build_mcts_graph()

        assert graph is not None
        assert isinstance(graph, MCTSGraph)

    def test_build_with_config(self) -> None:
        """Test building with custom config."""
        config = MCTSGraphConfig(
            max_iterations=200,
            exploration_constant=2.5,
        )

        graph = build_mcts_graph(config=config)

        assert graph.config.max_iterations == 200
        assert graph.config.exploration_constant == 2.5


class TestMCTSOrchestratorConfig:
    """Test MCTSOrchestratorConfig configuration."""

    def test_default_values(self) -> None:
        """Test default configuration."""
        config = MCTSOrchestratorConfig()

        assert config.strategic_iterations > 0
        assert config.tactical_iterations > 0
        assert config.execution_iterations > 0
        assert config.strategic_iterations > config.tactical_iterations
        assert config.tactical_iterations > config.execution_iterations

    def test_timeout_ordering(self) -> None:
        """Test timeout values are properly ordered."""
        config = MCTSOrchestratorConfig()

        assert config.strategic_timeout_seconds > config.tactical_timeout_seconds
        assert config.tactical_timeout_seconds > config.execution_timeout_seconds


class TestMCTSOrchestrator:
    """Test MCTSOrchestrator."""

    @pytest.fixture
    def orchestrator(self) -> MCTSOrchestrator:
        """Create orchestrator instance."""
        config = MCTSOrchestratorConfig(
            strategic_iterations=20,
            tactical_iterations=10,
            execution_iterations=5,
        )
        return MCTSOrchestrator(config)

    def test_creation(self, orchestrator: MCTSOrchestrator) -> None:
        """Test orchestrator creation."""
        assert orchestrator is not None

    def test_get_statistics(self, orchestrator: MCTSOrchestrator) -> None:
        """Test getting statistics."""
        stats = orchestrator.get_statistics()

        assert "search_count" in stats
        assert "cache_hits" in stats
        assert "cache_size" in stats

    def test_clear_cache(self, orchestrator: MCTSOrchestrator) -> None:
        """Test clearing cache."""
        orchestrator.clear_cache()

        stats = orchestrator.get_statistics()
        assert stats["cache_size"] == 0

    def test_reset_metrics(self, orchestrator: MCTSOrchestrator) -> None:
        """Test resetting metrics."""
        orchestrator.reset_metrics()

        stats = orchestrator.get_statistics()
        assert stats["search_count"] == 0
