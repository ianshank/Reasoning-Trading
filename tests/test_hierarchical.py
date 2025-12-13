"""
Unit tests for Hierarchical MCTS module.

Tests individual components of the hierarchical MCTS implementation.
"""

from __future__ import annotations

from datetime import timedelta

import numpy as np
import pytest

from reasoning_trading.hierarchical import (
    ExecutionLevel,
    HierarchicalMCTSTree,
    HierarchicalNode,
    HierarchicalStateAbstraction,
    HierarchyConfig,
    HierarchyLevelType,
    MAXQConfig,
    MAXQValueDecomposition,
    StrategicLevel,
    TacticalLevel,
    TreeConfig,
)


class TestHierarchyConfig:
    """Test HierarchyConfig configuration."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = HierarchyConfig()

        assert config.strategic_horizon_days > 0
        assert config.tactical_horizon_hours > 0
        assert config.execution_horizon_minutes > 0

    def test_env_override(self, monkeypatch) -> None:
        """Test configuration from environment."""
        monkeypatch.setenv("HIERARCHY_STRATEGIC_HORIZON_DAYS", "14")

        config = HierarchyConfig()
        assert config.strategic_horizon_days == 14


class TestHierarchyLevels:
    """Test hierarchy level implementations."""

    def test_strategic_level_type(self) -> None:
        """Test strategic level type."""
        level = StrategicLevel()
        assert level.level_type == HierarchyLevelType.STRATEGIC

    def test_tactical_level_type(self) -> None:
        """Test tactical level type."""
        level = TacticalLevel()
        assert level.level_type == HierarchyLevelType.TACTICAL

    def test_execution_level_type(self) -> None:
        """Test execution level type."""
        level = ExecutionLevel()
        assert level.level_type == HierarchyLevelType.EXECUTION

    def test_level_time_horizons_ordering(self) -> None:
        """Test that time horizons decrease with level."""
        strategic = StrategicLevel()
        tactical = TacticalLevel()
        execution = ExecutionLevel()

        assert strategic.time_horizon > tactical.time_horizon
        assert tactical.time_horizon > execution.time_horizon

    def test_level_simulation_budgets(self) -> None:
        """Test simulation budgets are positive."""
        for level_class in [StrategicLevel, TacticalLevel, ExecutionLevel]:
            level = level_class()
            assert level.simulation_budget > 0

    def test_available_actions_non_empty(self) -> None:
        """Test each level has available actions."""
        for level_class in [StrategicLevel, TacticalLevel, ExecutionLevel]:
            level = level_class()
            assert len(level.available_actions) > 0


class TestMAXQConfig:
    """Test MAXQ configuration."""

    def test_default_values(self) -> None:
        """Test default MAXQ configuration."""
        config = MAXQConfig()

        assert config.discount_factor > 0
        assert config.discount_factor <= 1
        assert config.learning_rate > 0


class TestMAXQValueDecomposition:
    """Test MAXQ value decomposition."""

    @pytest.fixture
    def maxq(self) -> MAXQValueDecomposition:
        """Create MAXQ instance."""
        return MAXQValueDecomposition()

    def test_task_registration(self, maxq: MAXQValueDecomposition) -> None:
        """Test task hierarchy registration."""
        maxq.register_task("parent", ["child_a", "child_b"])

        assert maxq.has_task("parent")
        subtasks = maxq.get_subtasks("parent")
        assert "child_a" in subtasks
        assert "child_b" in subtasks

    def test_subtask_value_update(self, maxq: MAXQValueDecomposition) -> None:
        """Test subtask value updates."""
        maxq.register_task("task", [])

        maxq.update_subtask_value("task", "state_1", 0.5)
        value = maxq.get_subtask_value("task", "state_1")

        assert abs(value - 0.5) < 0.01

    def test_completion_value_update(self, maxq: MAXQValueDecomposition) -> None:
        """Test completion value updates."""
        maxq.register_task("parent", ["child"])

        maxq.update_completion_value("parent", "child", "state_1", 0.3)
        value = maxq.get_completion_value("parent", "child", "state_1")

        assert abs(value - 0.3) < 0.01

    def test_q_value_decomposition(self, maxq: MAXQValueDecomposition) -> None:
        """Test Q = V + C decomposition."""
        maxq.register_task("parent", ["child"])

        state = "test_state"
        maxq.update_subtask_value("child", state, 0.6)
        maxq.update_completion_value("parent", "child", state, 0.2)

        q = maxq.get_q_value("parent", "child", state)
        expected = 0.6 + 0.2

        assert abs(q - expected) < 0.001

    def test_best_subtask_selection(self, maxq: MAXQValueDecomposition) -> None:
        """Test selecting best subtask."""
        maxq.register_task("parent", ["a", "b", "c"])

        state = "state_1"
        maxq.update_subtask_value("a", state, 0.3)
        maxq.update_subtask_value("b", state, 0.9)
        maxq.update_subtask_value("c", state, 0.5)

        best = maxq.get_best_subtask("parent", state)
        assert best == "b"

    def test_value_for_unknown_state(self, maxq: MAXQValueDecomposition) -> None:
        """Test getting value for unknown state returns default."""
        maxq.register_task("task", [])

        value = maxq.get_subtask_value("task", "unknown_state")
        assert value == 0.0


class TestHierarchicalStateAbstraction:
    """Test hierarchical state abstraction."""

    @pytest.fixture
    def abstraction(self) -> HierarchicalStateAbstraction:
        """Create abstraction instance."""
        return HierarchicalStateAbstraction()

    def test_strategic_abstraction_size(self, abstraction: HierarchicalStateAbstraction) -> None:
        """Test strategic level produces smaller features."""
        features = np.random.randn(500)

        strategic = abstraction.abstract_for_level_raw(features, "strategic")
        tactical = abstraction.abstract_for_level_raw(features, "tactical")
        execution = abstraction.abstract_for_level_raw(features, "execution")

        assert len(strategic) <= len(tactical)
        assert len(tactical) <= len(execution)

    def test_abstraction_deterministic(self, abstraction: HierarchicalStateAbstraction) -> None:
        """Test abstraction is deterministic."""
        features = np.random.randn(200)

        result1 = abstraction.abstract_for_level_raw(features, "tactical")
        result2 = abstraction.abstract_for_level_raw(features, "tactical")

        np.testing.assert_array_equal(result1, result2)


class TestHierarchicalNode:
    """Test hierarchical MCTS node."""

    def test_node_creation(self) -> None:
        """Test node creation with features."""
        features = np.random.randn(50)

        node = HierarchicalNode(
            state_features=features,
            level="tactical",
            action="hold",
        )

        assert node.level == "tactical"
        assert node.action == "hold"
        assert node.visits == 0
        assert len(node.children) == 0

    def test_add_child(self) -> None:
        """Test adding child nodes."""
        parent = HierarchicalNode(
            state_features=np.random.randn(50),
            level="strategic",
        )

        child = parent.add_child(
            action="buy",
            state_features=np.random.randn(50),
            prior=0.3,
            level="tactical",
        )

        assert len(parent.children) == 1
        assert child.parent == parent
        assert child.prior == 0.3

    def test_update(self) -> None:
        """Test node value update."""
        node = HierarchicalNode(
            state_features=np.random.randn(50),
            level="tactical",
        )

        node.update(0.5)
        assert node.visits == 1
        assert abs(node.value - 0.5) < 0.001

        node.update(0.7)
        assert node.visits == 2
        assert abs(node.value - 0.6) < 0.001

    def test_ucb_score(self) -> None:
        """Test UCB score calculation."""
        node = HierarchicalNode(
            state_features=np.random.randn(50),
            level="tactical",
        )
        node.visits = 5
        node.value_sum = 2.5
        node.prior = 0.4

        parent_visits = 20
        score = node.ucb_score(parent_visits, c_puct=1.41)

        assert score > 0  # Should have positive score

    def test_is_leaf(self) -> None:
        """Test leaf node detection."""
        node = HierarchicalNode(
            state_features=np.random.randn(50),
            level="tactical",
        )

        assert node.is_leaf()

        node.add_child("action", np.random.randn(50), 0.5, "execution")
        assert not node.is_leaf()


class TestTreeConfig:
    """Test tree configuration."""

    def test_default_values(self) -> None:
        """Test default tree configuration."""
        config = TreeConfig()

        assert config.strategic_simulations > 0
        assert config.tactical_simulations > 0
        assert config.execution_simulations > 0
        assert config.exploration_constant > 0


class TestHierarchicalMCTSTreeUnit:
    """Unit tests for hierarchical MCTS tree."""

    def test_tree_creation(self) -> None:
        """Test tree creation."""
        config = TreeConfig()
        tree = HierarchicalMCTSTree(config)

        assert tree is not None
        assert tree.config == config

    def test_level_budget(self) -> None:
        """Test getting simulation budget for level."""
        config = TreeConfig(
            strategic_simulations=100,
            tactical_simulations=50,
            execution_simulations=25,
        )
        tree = HierarchicalMCTSTree(config)

        assert tree._get_budget_for_level("strategic") == 100
        assert tree._get_budget_for_level("tactical") == 50
        assert tree._get_budget_for_level("execution") == 25

    def test_default_level_budget(self) -> None:
        """Test default budget for unknown level."""
        config = TreeConfig(tactical_simulations=50)
        tree = HierarchicalMCTSTree(config)

        budget = tree._get_budget_for_level("unknown")
        assert budget == 50  # Falls back to tactical
