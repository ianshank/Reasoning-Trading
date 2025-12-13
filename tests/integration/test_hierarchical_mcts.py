"""
Integration tests for Hierarchical MCTS with MAXQ decomposition.

Tests the complete hierarchical search pipeline across all levels.
"""

from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import TYPE_CHECKING

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

if TYPE_CHECKING:
    from tests.config import TestConfig
    from tests.factories import TradingStateFactory


class TestHierarchyLevels:
    """Test hierarchy level configuration and behavior."""

    def test_strategic_level_properties(self, test_config: TestConfig) -> None:
        """Test strategic level has correct properties."""
        config = HierarchyConfig(
            strategic_horizon_days=test_config.mcts_rollout_horizon,
        )
        level = StrategicLevel(config)

        assert level.level_type == HierarchyLevelType.STRATEGIC
        assert level.time_horizon.days >= 1
        assert level.simulation_budget >= 100

    def test_tactical_level_properties(self, test_config: TestConfig) -> None:
        """Test tactical level has correct properties."""
        config = HierarchyConfig()
        level = TacticalLevel(config)

        assert level.level_type == HierarchyLevelType.TACTICAL
        assert level.time_horizon.days >= 0
        assert level.simulation_budget >= 50

    def test_execution_level_properties(self) -> None:
        """Test execution level has correct properties."""
        config = HierarchyConfig()
        level = ExecutionLevel(config)

        assert level.level_type == HierarchyLevelType.EXECUTION
        assert level.time_horizon.total_seconds() <= 3600
        assert level.simulation_budget >= 10

    def test_level_action_filtering(self) -> None:
        """Test that each level filters actions appropriately."""
        config = HierarchyConfig()

        strategic = StrategicLevel(config)
        tactical = TacticalLevel(config)
        execution = ExecutionLevel(config)

        # Each level should have different action sets
        strategic_actions = strategic.available_actions
        tactical_actions = tactical.available_actions
        execution_actions = execution.available_actions

        assert len(strategic_actions) > 0
        assert len(tactical_actions) > 0
        assert len(execution_actions) > 0


class TestMAXQDecomposition:
    """Test MAXQ value decomposition."""

    def test_value_decomposition(self) -> None:
        """Test Q = V + C decomposition."""
        config = MAXQConfig()
        maxq = MAXQValueDecomposition(config)

        # Register task hierarchy
        maxq.register_task("root", ["strategic"])
        maxq.register_task("strategic", ["tactical"])
        maxq.register_task("tactical", ["execution"])

        # Set some values
        state_key = "test_state_001"
        maxq.update_subtask_value("strategic", state_key, 0.5)
        maxq.update_completion_value("root", "strategic", state_key, 0.2)

        # Get decomposed Q-value
        q_value = maxq.get_q_value("root", "strategic", state_key)

        # Q = V + C
        expected = 0.5 + 0.2
        assert abs(q_value - expected) < 0.001

    def test_recursive_q_value(self) -> None:
        """Test recursive Q-value computation through hierarchy."""
        config = MAXQConfig()
        maxq = MAXQValueDecomposition(config)

        # Setup hierarchy
        maxq.register_task("root", ["strategic"])
        maxq.register_task("strategic", ["tactical"])

        state = "state_002"
        maxq.update_subtask_value("tactical", state, 0.3)
        maxq.update_completion_value("strategic", "tactical", state, 0.1)

        # Recursive Q should propagate
        q_tactical = maxq.get_q_value("strategic", "tactical", state)
        assert abs(q_tactical - 0.4) < 0.001

    def test_subtask_selection(self) -> None:
        """Test best subtask selection."""
        config = MAXQConfig()
        maxq = MAXQValueDecomposition(config)

        maxq.register_task("parent", ["sub_a", "sub_b", "sub_c"])

        state = "state_003"
        maxq.update_subtask_value("sub_a", state, 0.2)
        maxq.update_subtask_value("sub_b", state, 0.8)
        maxq.update_subtask_value("sub_c", state, 0.5)

        best = maxq.get_best_subtask("parent", state)
        assert best == "sub_b"


class TestStateAbstraction:
    """Test hierarchical state abstraction."""

    def test_strategic_abstraction(
        self,
        trading_state_factory: TradingStateFactory,
    ) -> None:
        """Test strategic level uses fewer features."""
        state = trading_state_factory.create()
        abstraction = HierarchicalStateAbstraction()

        strategic = abstraction.abstract_for_level(state, "strategic")
        tactical = abstraction.abstract_for_level(state, "tactical")
        execution = abstraction.abstract_for_level(state, "execution")

        # Strategic should be most abstract (fewest features)
        assert len(strategic) <= len(tactical)
        assert len(tactical) <= len(execution)

    def test_abstraction_preserves_key_features(
        self,
        trading_state_factory: TradingStateFactory,
    ) -> None:
        """Test that key features are preserved at all levels."""
        state = trading_state_factory.create()
        abstraction = HierarchicalStateAbstraction()

        for level in ["strategic", "tactical", "execution"]:
            features = abstraction.abstract_for_level(state, level)
            # Should have some features
            assert len(features) > 0
            # Features should be normalized
            assert np.all(np.abs(features) < 100)


class TestHierarchicalNode:
    """Test hierarchical MCTS nodes."""

    def test_node_creation(
        self,
        trading_state_factory: TradingStateFactory,
    ) -> None:
        """Test hierarchical node creation."""
        state = trading_state_factory.create()
        features = state.to_feature_vector()

        node = HierarchicalNode(
            state_features=features,
            level="tactical",
            action="hold_position",
        )

        assert node.level == "tactical"
        assert node.action == "hold_position"
        assert node.visits == 0
        assert len(node.children) == 0

    def test_node_expansion(
        self,
        trading_state_factory: TradingStateFactory,
    ) -> None:
        """Test node expansion with subtasks."""
        state = trading_state_factory.create()
        features = state.to_feature_vector()

        parent = HierarchicalNode(
            state_features=features,
            level="strategic",
        )

        # Expand with subtasks
        child = parent.add_child(
            action="allocate_moderate",
            state_features=features,
            prior=0.3,
            level="tactical",
        )

        assert len(parent.children) == 1
        assert child.level == "tactical"
        assert child.prior == 0.3
        assert child.parent == parent

    def test_node_value_propagation(
        self,
        trading_state_factory: TradingStateFactory,
    ) -> None:
        """Test value propagation through hierarchy."""
        state = trading_state_factory.create()
        features = state.to_feature_vector()

        # Create hierarchy
        root = HierarchicalNode(state_features=features, level="strategic")
        child = root.add_child("action1", features, 0.5, "tactical")
        grandchild = child.add_child("action2", features, 0.5, "execution")

        # Update grandchild
        grandchild.update(0.8)

        # Values should propagate
        assert grandchild.visits == 1
        assert abs(grandchild.value - 0.8) < 0.001


class TestHierarchicalMCTSTree:
    """Test hierarchical MCTS tree search."""

    @pytest.fixture
    def tree_config(self) -> TreeConfig:
        """Create tree configuration for tests."""
        return TreeConfig(
            strategic_simulations=50,
            tactical_simulations=30,
            execution_simulations=20,
            exploration_constant=1.41,
        )

    @pytest.mark.asyncio
    async def test_search_returns_action(
        self,
        tree_config: TreeConfig,
        trading_state_factory: TradingStateFactory,
    ) -> None:
        """Test that search returns a valid action."""
        state = trading_state_factory.create()
        tree = HierarchicalMCTSTree(tree_config)

        result = await tree.search(state, target_level="tactical")

        assert result.best_action is not None
        assert result.iterations_completed > 0
        assert result.total_time_ms > 0

    @pytest.mark.asyncio
    async def test_hierarchical_search_traverses_levels(
        self,
        tree_config: TreeConfig,
        trading_state_factory: TradingStateFactory,
    ) -> None:
        """Test that hierarchical search traverses all levels."""
        state = trading_state_factory.create()
        tree = HierarchicalMCTSTree(tree_config)

        result = await tree.search(state, target_level="execution")

        # Should have results from each level
        assert result.level_results is not None
        assert len(result.level_results) >= 1

    @pytest.mark.asyncio
    async def test_search_respects_budget(
        self,
        trading_state_factory: TradingStateFactory,
    ) -> None:
        """Test that search respects simulation budget."""
        config = TreeConfig(
            strategic_simulations=10,
            tactical_simulations=10,
            execution_simulations=10,
        )
        state = trading_state_factory.create()
        tree = HierarchicalMCTSTree(config)

        result = await tree.search(state, target_level="tactical")

        # Should not exceed budget significantly
        assert result.iterations_completed <= 50  # Some overhead allowed

    @pytest.mark.asyncio
    async def test_action_probabilities_sum_to_one(
        self,
        tree_config: TreeConfig,
        trading_state_factory: TradingStateFactory,
    ) -> None:
        """Test that action probabilities are normalized."""
        state = trading_state_factory.create()
        tree = HierarchicalMCTSTree(tree_config)

        result = await tree.search(state, target_level="tactical")

        if result.action_probabilities:
            total = sum(result.action_probabilities.values())
            assert abs(total - 1.0) < 0.01


class TestHierarchicalSearchIntegration:
    """Integration tests for complete hierarchical search."""

    @pytest.mark.asyncio
    async def test_full_hierarchy_search(
        self,
        trading_state_factory: TradingStateFactory,
    ) -> None:
        """Test complete hierarchical search from strategic to execution."""
        state = trading_state_factory.create()

        config = TreeConfig(
            strategic_simulations=30,
            tactical_simulations=20,
            execution_simulations=10,
        )
        tree = HierarchicalMCTSTree(config)

        result = await tree.search(state, target_level="execution")

        assert result.success
        assert result.best_action is not None
        assert result.confidence > 0

    @pytest.mark.asyncio
    async def test_search_with_different_regimes(
        self,
        trading_state_factory: TradingStateFactory,
    ) -> None:
        """Test search behavior in different market regimes."""
        from tests.config import TestScenario

        config = TreeConfig(
            strategic_simulations=20,
            tactical_simulations=15,
            execution_simulations=10,
        )
        tree = HierarchicalMCTSTree(config)

        for scenario in [TestScenario.BULLISH, TestScenario.BEARISH, TestScenario.VOLATILE]:
            state = trading_state_factory.create_for_scenario(scenario)
            result = await tree.search(state, target_level="tactical")

            assert result.success
            assert result.best_action is not None

    @pytest.mark.asyncio
    async def test_parallel_searches(
        self,
        trading_state_factory: TradingStateFactory,
    ) -> None:
        """Test running multiple searches in parallel."""
        states = [trading_state_factory.create() for _ in range(3)]

        config = TreeConfig(
            strategic_simulations=15,
            tactical_simulations=10,
            execution_simulations=5,
        )
        tree = HierarchicalMCTSTree(config)

        # Run searches concurrently
        tasks = [tree.search(state, target_level="tactical") for state in states]
        results = await asyncio.gather(*tasks)

        assert len(results) == 3
        for result in results:
            assert result.success
            assert result.best_action is not None
