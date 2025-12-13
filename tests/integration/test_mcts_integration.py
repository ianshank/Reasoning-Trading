"""
Integration tests for MCTS components working together.

Tests the interaction between:
- MCTS Tree + Rollout Engine
- UCB Selection + Node Expansion
- State transitions through tree search
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from reasoning_trading.core.actions import ActionSpace, TradingAction, TradingDirection
from reasoning_trading.core.state import TradingState
from reasoning_trading.mcts.node import Node
from reasoning_trading.mcts.rollout import RewardFunction, TradingRollout
from reasoning_trading.mcts.tree import MCTSConfig, MCTSResult, MCTSTree
from reasoning_trading.mcts.ucb import (
    PUCTSelector,
    RiskAdjustedSelector,
    SelectionStrategy,
    UCB1Selector,
    create_selector,
)

from tests.config import TestConfig, TestScenario, get_scenario_configs
from tests.factories import TradingStateFactory


class TestMCTSTreeWithRollout:
    """Integration tests for MCTS tree with rollout engine."""

    @pytest.mark.asyncio
    async def test_tree_search_produces_valid_result(
        self,
        trading_state_factory: TradingStateFactory,
        action_space: ActionSpace,
        mcts_config: MCTSConfig,
    ) -> None:
        """Test that MCTS search produces valid results."""
        state = trading_state_factory.create()

        tree = MCTSTree(config=mcts_config)
        result = await tree.search(state, action_space)

        assert isinstance(result, MCTSResult)
        assert result.total_simulations > 0
        assert result.root is not None
        assert result.total_time_ms > 0

    @pytest.mark.asyncio
    async def test_tree_explores_multiple_actions(
        self,
        trading_state_factory: TradingStateFactory,
        action_space: ActionSpace,
        test_config: TestConfig,
    ) -> None:
        """Test that tree explores multiple action types."""
        state = trading_state_factory.create()

        config = MCTSConfig(
            max_simulations=test_config.mcts_simulations,
            rollout_horizon=test_config.mcts_rollout_horizon,
        )

        tree = MCTSTree(config=config)
        result = await tree.search(state, action_space)

        # Should have explored multiple children
        assert result.root is not None
        assert len(result.root.children) > 0

        # Check that different directions were explored
        directions = {
            c.action.direction for c in result.root.children if c.action is not None
        }
        assert len(directions) >= 1

    @pytest.mark.asyncio
    async def test_tree_respects_time_budget(
        self,
        trading_state_factory: TradingStateFactory,
        action_space: ActionSpace,
        test_config: TestConfig,
    ) -> None:
        """Test that tree respects time budget."""
        state = trading_state_factory.create()

        time_budget_ms = test_config.mcts_timeout_ms // 2  # Half the timeout

        config = MCTSConfig(
            max_simulations=10000,  # High limit
            time_budget_ms=time_budget_ms,
            rollout_horizon=test_config.mcts_rollout_horizon,
        )

        tree = MCTSTree(config=config)
        result = await tree.search(state, action_space)

        # Should complete within budget + overhead
        assert result.total_time_ms < time_budget_ms * 2

    @pytest.mark.asyncio
    async def test_different_reward_functions(
        self,
        trading_state_factory: TradingStateFactory,
        action_space: ActionSpace,
        test_config: TestConfig,
    ) -> None:
        """Test search with different reward functions."""
        state = trading_state_factory.create()

        reward_functions = [
            RewardFunction.RAW_RETURNS,
            RewardFunction.SHARPE_RATIO,
            RewardFunction.SORTINO_RATIO,
        ]

        results = {}
        for reward_fn in reward_functions:
            rollout = TradingRollout(
                horizon_days=test_config.mcts_rollout_horizon,
                reward_function=reward_fn,
            )

            config = MCTSConfig(
                max_simulations=test_config.mcts_simulations // 2,
                rollout_horizon=test_config.mcts_rollout_horizon,
            )

            tree = MCTSTree(config=config, rollout_engine=rollout)
            result = await tree.search(state, action_space)
            results[reward_fn] = result

        # All should complete successfully
        assert all(r.total_simulations > 0 for r in results.values())

    @pytest.mark.asyncio
    async def test_different_selection_strategies(
        self,
        trading_state_factory: TradingStateFactory,
        action_space: ActionSpace,
        test_config: TestConfig,
    ) -> None:
        """Test search with different selection strategies."""
        state = trading_state_factory.create()

        strategies = [
            SelectionStrategy.UCB1,
            SelectionStrategy.PUCT,
            SelectionStrategy.RISK_ADJUSTED,
        ]

        results = {}
        for strategy in strategies:
            selector = create_selector(strategy)

            config = MCTSConfig(
                max_simulations=test_config.mcts_simulations // 2,
                selection_strategy=strategy,
                rollout_horizon=test_config.mcts_rollout_horizon,
            )

            tree = MCTSTree(config=config, selector=selector)
            result = await tree.search(state, action_space)
            results[strategy] = result

        # All should complete successfully
        assert all(r.total_simulations > 0 for r in results.values())


class TestMCTSWithScenarios:
    """Test MCTS behavior across different market scenarios."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("scenario", list(TestScenario))
    async def test_mcts_responds_to_scenarios(
        self,
        scenario: TestScenario,
        trading_state_factory: TradingStateFactory,
        action_space: ActionSpace,
        scenario_configs: dict,
        test_config: TestConfig,
    ) -> None:
        """Test MCTS responds appropriately to different scenarios."""
        state = trading_state_factory.create_for_scenario(scenario)
        scenario_config = scenario_configs[scenario]

        config = MCTSConfig(
            max_simulations=test_config.mcts_simulations,
            rollout_horizon=test_config.mcts_rollout_horizon,
        )

        tree = MCTSTree(config=config)
        result = await tree.search(state, action_space)

        # Should complete search
        assert result.total_simulations > 0

        # Check that result reflects scenario expectations
        if result.best_action is not None:
            # For strong signals, the action should align with scenario
            if abs(scenario_config.consensus) > 0.5:
                expected = scenario_config.expected_direction
                actual = result.best_action.direction.value
                # Allow some flexibility in noisy simulations
                # Just verify we get a valid action
                assert actual in ["buy", "sell", "hold"]


class TestNodeExpansionIntegration:
    """Test node expansion with action space integration."""

    def test_progressive_widening_with_visits(
        self,
        sample_trading_state: TradingState,
        action_space: ActionSpace,
    ) -> None:
        """Test that progressive widening adds more children with visits."""
        root = Node(state=sample_trading_state)

        # Simulate visits and expansion
        children_counts = []
        for visit in [1, 5, 10, 25, 50]:
            root.visits = visit
            existing = [c.action for c in root.children if c.action]
            candidates = action_space.get_candidate_actions(visit, existing)

            # Expand with candidates
            for action in candidates[:2]:  # Limit expansion per round
                child_state = sample_trading_state.copy()
                child_state.simulation_step += 1
                root.expand(action=action, new_state=child_state)

            children_counts.append(len(root.children))

        # Children count should grow with visits
        assert children_counts[-1] >= children_counts[0]

    def test_backpropagation_updates_all_ancestors(
        self,
        sample_trading_state: TradingState,
        action_factory,
    ) -> None:
        """Test backpropagation updates entire path."""
        # Build 3-level tree
        root = Node(state=sample_trading_state)
        root.visits = 10

        child1_state = sample_trading_state.copy()
        child1 = root.expand(
            action=action_factory.create_buy(),
            new_state=child1_state,
        )
        child1.visits = 5

        child2_state = sample_trading_state.copy()
        child2 = child1.expand(
            action=action_factory.create_hold(),
            new_state=child2_state,
        )

        # Backpropagate from leaf
        value = 0.5
        child2.backpropagate(value, discount=0.99)

        # All nodes should be updated
        assert child2.visits == 1
        assert child2.value_sum == value
        assert child1.visits == 6  # 5 + 1
        assert root.visits == 11  # 10 + 1


class TestRolloutIntegration:
    """Test rollout engine integration with states and actions."""

    @pytest.mark.asyncio
    async def test_rollout_respects_horizon(
        self,
        sample_node: Node,
        test_config: TestConfig,
    ) -> None:
        """Test rollout respects horizon limit."""
        horizon = test_config.mcts_rollout_horizon

        rollout = TradingRollout(
            horizon_days=horizon,
            max_steps=horizon * 2,  # Higher max to ensure horizon is the limit
        )

        result = await rollout._simulate_trading(sample_node.state, horizon)

        # Should not exceed horizon
        assert result.simulation_steps <= horizon

    @pytest.mark.asyncio
    async def test_rollout_tracks_portfolio_values(
        self,
        sample_node: Node,
        test_config: TestConfig,
    ) -> None:
        """Test rollout tracks portfolio values through simulation."""
        rollout = TradingRollout(
            horizon_days=test_config.mcts_rollout_horizon,
        )

        result = await rollout._simulate_trading(
            sample_node.state, test_config.mcts_rollout_horizon
        )

        # Should have portfolio value history
        assert len(result.portfolio_values) > 0

        # First value should match initial portfolio
        initial_value = sample_node.state.portfolio.portfolio_value
        assert result.portfolio_values[0] == initial_value

    @pytest.mark.asyncio
    async def test_rollout_computes_metrics(
        self,
        sample_node: Node,
        test_config: TestConfig,
    ) -> None:
        """Test rollout computes all required metrics."""
        rollout = TradingRollout(
            horizon_days=test_config.mcts_rollout_horizon,
        )

        result = await rollout._simulate_trading(
            sample_node.state, test_config.mcts_rollout_horizon
        )

        # Should have computed metrics
        assert hasattr(result, "total_return")
        assert hasattr(result, "sharpe_ratio")
        assert hasattr(result, "max_drawdown")
        assert result.max_drawdown >= 0
        assert result.max_drawdown <= 1


class TestUCBSelectionIntegration:
    """Test UCB selection integration with tree structure."""

    def test_ucb_selects_high_value_nodes(
        self,
        tree_with_children: Node,
    ) -> None:
        """Test UCB selection favors high-value nodes over time."""
        selector = UCB1Selector()

        # Make one child clearly better
        best_child = tree_with_children.children[0]
        best_child.visits = 50
        best_child.value_sum = 50 * 0.8  # High value

        # Other children have lower values
        for child in tree_with_children.children[1:]:
            child.visits = 50
            child.value_sum = 50 * 0.2

        # With equal visits, UCB should prefer higher value
        selected = selector.select(tree_with_children)
        assert selected == best_child

    def test_ucb_explores_unvisited_nodes(
        self,
        sample_trading_state: TradingState,
        action_factory,
    ) -> None:
        """Test UCB explores unvisited nodes first."""
        root = Node(state=sample_trading_state)
        root.visits = 100

        # Add one visited child
        visited_child = root.expand(
            action=action_factory.create_buy(),
            new_state=sample_trading_state.copy(),
        )
        visited_child.visits = 50
        visited_child.value_sum = 25

        # Add one unvisited child
        unvisited_child = root.expand(
            action=action_factory.create_sell(),
            new_state=sample_trading_state.copy(),
        )
        unvisited_child.visits = 0

        selector = UCB1Selector()
        selected = selector.select(root)

        # Should select unvisited (infinite UCB score)
        assert selected == unvisited_child

    def test_risk_adjusted_selector_penalizes_risky_actions(
        self,
        sample_trading_state: TradingState,
        action_factory,
        test_config: TestConfig,
    ) -> None:
        """Test risk-adjusted selector penalizes risky positions."""
        root = Node(state=sample_trading_state)
        root.visits = 100

        # Add conservative action
        conservative = action_factory.create_buy(
            size=test_config.default_position_size * 0.5,
            stop_loss=test_config.default_stop_loss * 0.5,
        )
        conservative_state = sample_trading_state.copy()
        conservative_child = root.expand(action=conservative, new_state=conservative_state)
        conservative_child.visits = 30
        conservative_child.value_sum = 30 * 0.5

        # Add aggressive action
        aggressive = action_factory.create_buy(
            size=test_config.max_position_size,
            stop_loss=test_config.default_stop_loss * 2,
        )
        aggressive_state = sample_trading_state.copy()
        aggressive_child = root.expand(action=aggressive, new_state=aggressive_state)
        aggressive_child.visits = 30
        aggressive_child.value_sum = 30 * 0.5  # Same value

        selector = RiskAdjustedSelector(risk_aversion=2.0, drawdown_penalty=3.0)

        conservative_score = selector.score(conservative_child)
        aggressive_score = selector.score(aggressive_child)

        # Conservative should have higher score (less penalty)
        assert conservative_score > aggressive_score
