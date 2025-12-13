"""
Tests for MCTS implementation.
"""

from __future__ import annotations

import asyncio
from datetime import datetime

import numpy as np
import pytest

from reasoning_trading.core.actions import (
    ActionSpace,
    PositionSizeAction,
    StopLossAction,
    TimeHorizon,
    TradingAction,
    TradingDirection,
)
from reasoning_trading.core.state import TradingState
from reasoning_trading.mcts.node import Node
from reasoning_trading.mcts.rollout import (
    RewardFunction,
    RolloutResult,
    TradingRollout,
)
from reasoning_trading.mcts.tree import MCTSConfig, MCTSResult, MCTSTree
from reasoning_trading.mcts.ucb import (
    PUCTSelector,
    RiskAdjustedSelector,
    SelectionStrategy,
    UCB1Selector,
    UCBTunedSelector,
    create_selector,
)


class TestNode:
    """Tests for MCTS Node."""

    def test_node_creation(self, sample_trading_state: TradingState) -> None:
        """Test basic node creation."""
        node = Node(state=sample_trading_state)
        assert node.state == sample_trading_state
        assert node.is_root
        assert node.is_leaf
        assert node.visits == 0
        assert node.depth == 0

    def test_expand(
        self,
        sample_node: Node,
        sample_action: TradingAction,
        sample_trading_state: TradingState,
    ) -> None:
        """Test node expansion."""
        new_state = sample_trading_state.copy()
        new_state.simulation_step += 1

        child = sample_node.expand(
            action=sample_action,
            new_state=new_state,
            prior=0.5,
        )

        assert child.parent == sample_node
        assert child in sample_node.children
        assert not sample_node.is_leaf
        assert child.action == sample_action
        assert child.depth == 1
        assert child.prior == 0.5

    def test_backpropagate(self, sample_node: Node) -> None:
        """Test backpropagation."""
        # Create a child
        child_state = sample_node.state.copy()
        child = sample_node.expand(
            action=TradingAction.hold(),
            new_state=child_state,
        )

        # Backpropagate from child
        value = 0.5
        child.backpropagate(value, discount=0.99)

        assert child.visits == 1
        assert child.value_sum == value
        assert sample_node.visits == 1
        assert sample_node.value_sum == value * 0.99

    def test_best_child(self, tree_with_children: Node) -> None:
        """Test best child selection."""
        best = tree_with_children.best_child()
        assert best is not None
        assert best in tree_with_children.children

    def test_best_action_child(self, tree_with_children: Node) -> None:
        """Test best action child by visits."""
        best = tree_with_children.best_action_child()
        assert best is not None
        # Should be the most visited
        max_visits = max(c.visits for c in tree_with_children.children)
        assert best.visits == max_visits

    def test_ucb_value(self, tree_with_children: Node) -> None:
        """Test UCB value calculation."""
        for child in tree_with_children.children:
            ucb = child.ucb_value
            assert isinstance(ucb, float)
            # UCB should be mean_value + exploration bonus
            if child.visits > 0:
                assert ucb >= child.mean_value

    def test_get_path_to_root(self, tree_with_children: Node) -> None:
        """Test path to root retrieval."""
        child = tree_with_children.children[0]
        path = child.get_path_to_root()

        assert len(path) == 2
        assert path[0] == tree_with_children
        assert path[1] == child

    def test_get_action_sequence(self, tree_with_children: Node) -> None:
        """Test action sequence retrieval."""
        child = tree_with_children.children[0]
        actions = child.get_action_sequence()

        assert len(actions) == 1
        assert actions[0] == child.action


class TestUCBSelectors:
    """Tests for UCB selection strategies."""

    def test_ucb1_selector(self, tree_with_children: Node) -> None:
        """Test UCB1 selection."""
        selector = UCB1Selector(exploration_constant=1.414)
        selected = selector.select(tree_with_children)

        assert selected is not None
        assert selected in tree_with_children.children

    def test_ucb1_score(self, tree_with_children: Node) -> None:
        """Test UCB1 score calculation."""
        selector = UCB1Selector()

        for child in tree_with_children.children:
            score = selector.score(child)
            assert isinstance(score, float)

    def test_puct_selector(self, tree_with_children: Node) -> None:
        """Test PUCT selection."""
        selector = PUCTSelector(c_puct=1.0)
        selected = selector.select(tree_with_children)

        assert selected is not None
        assert selected in tree_with_children.children

    def test_ucb_tuned_selector(self, tree_with_children: Node) -> None:
        """Test UCB-Tuned selection."""
        selector = UCBTunedSelector()
        selected = selector.select(tree_with_children)

        assert selected is not None

    def test_risk_adjusted_selector(self, tree_with_children: Node) -> None:
        """Test risk-adjusted selection."""
        selector = RiskAdjustedSelector(
            base_exploration=1.414,
            risk_aversion=0.5,
        )
        selected = selector.select(tree_with_children)

        assert selected is not None

    def test_create_selector(self) -> None:
        """Test selector factory."""
        for strategy in SelectionStrategy:
            selector = create_selector(strategy)
            assert selector is not None

    def test_unvisited_node_score(self, sample_node: Node) -> None:
        """Test score for unvisited nodes."""
        # Create child with zero visits
        child_state = sample_node.state.copy()
        child = sample_node.expand(
            action=TradingAction.hold(),
            new_state=child_state,
        )

        selector = UCB1Selector()
        score = selector.score(child)

        # Unvisited nodes should have infinite score
        assert score == float("inf")


class TestTradingRollout:
    """Tests for trading rollout engine."""

    @pytest.mark.asyncio
    async def test_rollout(self, sample_node: Node) -> None:
        """Test basic rollout execution."""
        rollout = TradingRollout(
            horizon_days=5,
            discount_factor=0.99,
        )

        value = await rollout.rollout(sample_node, depth=5)
        assert isinstance(value, float)

    @pytest.mark.asyncio
    async def test_rollout_sharpe_reward(self, sample_node: Node) -> None:
        """Test rollout with Sharpe ratio reward."""
        rollout = TradingRollout(
            horizon_days=10,
            reward_function=RewardFunction.SHARPE_RATIO,
        )

        value = await rollout.rollout(sample_node)
        assert isinstance(value, float)

    @pytest.mark.asyncio
    async def test_rollout_raw_returns(self, sample_node: Node) -> None:
        """Test rollout with raw returns reward."""
        rollout = TradingRollout(
            horizon_days=10,
            reward_function=RewardFunction.RAW_RETURNS,
        )

        value = await rollout.rollout(sample_node)
        assert isinstance(value, float)

    @pytest.mark.asyncio
    async def test_rollout_drawdown_penalty(self, sample_node: Node) -> None:
        """Test rollout with drawdown penalty."""
        rollout = TradingRollout(
            horizon_days=10,
            reward_function=RewardFunction.MAX_DRAWDOWN_PENALTY,
            drawdown_lambda=1.0,
        )

        value = await rollout.rollout(sample_node)
        assert isinstance(value, float)


class TestRolloutResult:
    """Tests for RolloutResult."""

    def test_annualized_sharpe(self) -> None:
        """Test annualized Sharpe calculation."""
        result = RolloutResult(sharpe_ratio=0.1)
        annual = result.annualized_sharpe

        # Should be roughly 0.1 * sqrt(252)
        assert abs(annual - 0.1 * np.sqrt(252)) < 0.01

    def test_to_dict(self) -> None:
        """Test result serialization."""
        result = RolloutResult(
            total_return=0.05,
            sharpe_ratio=1.5,
            max_drawdown=0.1,
            num_trades=10,
        )

        data = result.to_dict()
        assert data["total_return"] == 0.05
        assert data["sharpe_ratio"] == 1.5


class TestMCTSTree:
    """Tests for MCTS tree search."""

    @pytest.mark.asyncio
    async def test_search(
        self,
        sample_trading_state: TradingState,
        action_space: ActionSpace,
        mcts_config: MCTSConfig,
    ) -> None:
        """Test MCTS search."""
        tree = MCTSTree(config=mcts_config)

        result = await tree.search(sample_trading_state, action_space)

        assert isinstance(result, MCTSResult)
        assert result.total_simulations > 0
        assert result.root is not None

    @pytest.mark.asyncio
    async def test_search_finds_action(
        self,
        sample_trading_state: TradingState,
        action_space: ActionSpace,
    ) -> None:
        """Test that search finds a valid action."""
        config = MCTSConfig(
            max_simulations=20,
            rollout_horizon=3,
        )
        tree = MCTSTree(config=config)

        result = await tree.search(sample_trading_state, action_space)

        # Should find some action
        assert result.best_action is not None or result.total_simulations < config.max_simulations

    @pytest.mark.asyncio
    async def test_search_with_time_budget(
        self,
        sample_trading_state: TradingState,
        action_space: ActionSpace,
    ) -> None:
        """Test search with time budget."""
        config = MCTSConfig(
            max_simulations=1000,
            time_budget_ms=500,  # 500ms budget
            rollout_horizon=3,
        )
        tree = MCTSTree(config=config)

        result = await tree.search(sample_trading_state, action_space)

        # Should complete within time budget
        assert result.total_time_ms < 1000  # Allow some overhead

    def test_get_action_distribution(
        self,
        sample_trading_state: TradingState,
        action_space: ActionSpace,
    ) -> None:
        """Test action distribution extraction."""
        tree = MCTSTree()
        tree._action_space = action_space
        tree.root = Node(state=sample_trading_state)

        # Add some children with visits
        for direction in [TradingDirection.BUY, TradingDirection.SELL]:
            child_state = sample_trading_state.copy()
            action = TradingAction(
                direction=direction,
                position_size=PositionSizeAction(size_fraction=0.1),
                stop_loss=StopLossAction(stop_loss_pct=0.05),
                time_horizon=TimeHorizon.INTRADAY,
            )
            child = tree.root.expand(action=action, new_state=child_state)
            child.visits = 10

        dist = tree.get_action_distribution()
        assert len(dist) == 2
        assert sum(dist.values()) == pytest.approx(1.0)

    def test_get_top_actions(
        self,
        sample_trading_state: TradingState,
    ) -> None:
        """Test top actions extraction."""
        tree = MCTSTree()
        tree.root = Node(state=sample_trading_state)

        # Add children
        for i, direction in enumerate([TradingDirection.BUY, TradingDirection.SELL, TradingDirection.HOLD]):
            child_state = sample_trading_state.copy()
            action = TradingAction(
                direction=direction,
                position_size=PositionSizeAction(size_fraction=0.1),
                stop_loss=StopLossAction(stop_loss_pct=0.05),
                time_horizon=TimeHorizon.INTRADAY,
            )
            child = tree.root.expand(action=action, new_state=child_state)
            child.visits = (i + 1) * 10
            child.value_sum = child.visits * 0.5

        top = tree.get_top_actions(n=2)
        assert len(top) == 2
        # Should be sorted by visits (descending)
        assert top[0][2] >= top[1][2]


class TestMCTSConfig:
    """Tests for MCTS configuration."""

    def test_from_settings(self, test_settings) -> None:
        """Test config creation from settings."""
        config = MCTSConfig.from_settings(test_settings.mcts)

        assert config.max_simulations == test_settings.mcts.max_simulations
        assert config.exploration_weight == test_settings.mcts.exploration_weight


class TestMCTSResult:
    """Tests for MCTS result."""

    def test_to_dict(self, sample_action: TradingAction) -> None:
        """Test result serialization."""
        result = MCTSResult(
            best_action=sample_action,
            total_simulations=100,
            best_value=0.5,
            best_visits=50,
        )

        data = result.to_dict()
        assert data["total_simulations"] == 100
        assert data["best_value"] == 0.5
        assert data["best_action"] is not None
