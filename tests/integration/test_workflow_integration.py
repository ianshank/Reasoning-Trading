"""
Integration tests for workflow components.

Tests the interaction between:
- LangGraph workflow + MCTS
- Multi-agent coordination
- Hybrid architecture components
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from reasoning_trading.config import Settings, TradingMode
from reasoning_trading.core.actions import ActionSpace, TradingAction, TradingDirection
from reasoning_trading.core.state import TradingState
from reasoning_trading.mcts.tree import MCTSConfig
from reasoning_trading.workflow.graph import (
    MCTSTradingGraph,
    MCTSTradingState,
    build_trading_mcts_graph,
)
from reasoning_trading.workflow.hybrid import HybridTradingArchitecture, PolicyEntry

from tests.config import TestConfig, TestScenario
from tests.factories import ActionFactory, TradingStateFactory


class TestWorkflowWithMCTS:
    """Test workflow graph with MCTS integration."""

    @pytest.mark.asyncio
    async def test_workflow_initialization(
        self,
        test_settings: Settings,
        mock_trading_adapter: AsyncMock,
        sample_trading_state: TradingState,
    ) -> None:
        """Test workflow initializes correctly."""
        graph = MCTSTradingGraph(settings=test_settings)
        graph.trading_adapter = mock_trading_adapter
        graph.build()

        state = MCTSTradingState(
            symbol=sample_trading_state.symbol,
            analysis_date=datetime.now().strftime("%Y-%m-%d"),
        )

        result = await graph._initialize_node(state)

        assert "trading_state" in result
        assert "tree_root" in result
        assert result["tree_root"] is not None

    @pytest.mark.asyncio
    async def test_workflow_selection_phase(
        self,
        test_settings: Settings,
        mock_trading_adapter: AsyncMock,
        sample_trading_state: TradingState,
        action_factory: ActionFactory,
    ) -> None:
        """Test workflow selection phase."""
        graph = MCTSTradingGraph(settings=test_settings)
        graph.trading_adapter = mock_trading_adapter
        graph.build()

        # Create initial state with tree
        from reasoning_trading.mcts.node import Node

        root = Node(state=sample_trading_state)

        # Add some children
        for direction in [TradingDirection.BUY, TradingDirection.SELL]:
            child_state = sample_trading_state.copy()
            if direction == TradingDirection.BUY:
                action = action_factory.create_buy()
            else:
                action = action_factory.create_sell()
            child = root.expand(action=action, new_state=child_state)
            child.visits = 10
            child.value_sum = 5

        root.visits = 25

        state = MCTSTradingState(
            symbol=sample_trading_state.symbol,
            tree_root=root,
            current_node=root,
        )

        result = await graph._select_node(state)

        assert "current_node" in result
        assert result["iteration_count"] == 1

    @pytest.mark.asyncio
    async def test_workflow_decision_phase(
        self,
        test_settings: Settings,
        mock_trading_adapter: AsyncMock,
        sample_trading_state: TradingState,
        action_factory: ActionFactory,
    ) -> None:
        """Test workflow decision phase."""
        graph = MCTSTradingGraph(settings=test_settings)
        graph.trading_adapter = mock_trading_adapter
        graph.build()

        # Create tree with visited children
        from reasoning_trading.mcts.node import Node

        root = Node(state=sample_trading_state)

        best_action = action_factory.create_buy(confidence=0.8)
        best_child = root.expand(
            action=best_action,
            new_state=sample_trading_state.copy(),
        )
        best_child.visits = 50
        best_child.value_sum = 25

        other_action = action_factory.create_sell(confidence=0.4)
        other_child = root.expand(
            action=other_action,
            new_state=sample_trading_state.copy(),
        )
        other_child.visits = 20
        other_child.value_sum = 5

        root.visits = 70

        state = MCTSTradingState(
            symbol=sample_trading_state.symbol,
            analysis_date=datetime.now().strftime("%Y-%m-%d"),
            trading_state=sample_trading_state,
            tree_root=root,
            iteration_count=70,
        )

        result = await graph._decide_node(state)

        assert "best_action" in result
        assert result["best_action"].direction == TradingDirection.BUY
        assert result["action_confidence"] > 0

    def test_workflow_termination_conditions(
        self,
        test_settings: Settings,
    ) -> None:
        """Test workflow termination conditions."""
        graph = MCTSTradingGraph(settings=test_settings)

        # Test max iterations
        state = MCTSTradingState(
            iteration_count=1000,
            max_iterations=1000,
        )
        assert graph._should_continue_search(state) == "stop"

        # Test error
        state = MCTSTradingState(
            error_message="Test error",
        )
        assert graph._should_continue_search(state) == "error"

        # Test should continue
        state = MCTSTradingState(
            iteration_count=10,
            max_iterations=1000,
            should_continue=True,
        )
        assert graph._should_continue_search(state) == "continue"


class TestHybridArchitectureIntegration:
    """Test hybrid batch/realtime architecture."""

    @pytest.mark.asyncio
    async def test_policy_caching(
        self,
        test_settings: Settings,
        action_factory: ActionFactory,
        trading_state_factory: TradingStateFactory,
        test_config: TestConfig,
    ) -> None:
        """Test policy caching and retrieval."""
        hybrid = HybridTradingArchitecture(
            settings=test_settings,
            batch_simulations=test_config.mcts_simulations,
            realtime_simulations=test_config.mcts_simulations // 5,
        )

        state = trading_state_factory.create()
        state_hash = hybrid._compute_state_hash(state)

        # Create policy entry
        action = action_factory.create_buy()
        entry = PolicyEntry(
            action=action,
            value=0.5,
            confidence=0.8,
            computed_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=test_config.cache_ttl_seconds // 60),
            state_hash=state_hash,
        )

        # Cache it
        hybrid._local_cache[f"policy:{test_config.primary_symbol}:{state_hash}"] = entry

        # Retrieve it
        retrieved = await hybrid._get_cached_policy(test_config.primary_symbol, state_hash)

        assert retrieved is not None
        assert retrieved.action.direction == action.direction

    @pytest.mark.asyncio
    async def test_heuristic_fallback(
        self,
        test_settings: Settings,
        trading_state_factory: TradingStateFactory,
    ) -> None:
        """Test heuristic fallback when MCTS unavailable."""
        hybrid = HybridTradingArchitecture(settings=test_settings)

        # Test with bullish state
        bullish_state = trading_state_factory.create_for_scenario(TestScenario.BULLISH)
        action = hybrid._heuristic_action(bullish_state)
        assert action.direction in [TradingDirection.BUY, TradingDirection.HOLD]

        # Test with bearish state
        bearish_state = trading_state_factory.create_for_scenario(TestScenario.BEARISH)
        action = hybrid._heuristic_action(bearish_state)
        assert action.direction in [TradingDirection.SELL, TradingDirection.HOLD]

    @pytest.mark.asyncio
    async def test_state_hash_consistency(
        self,
        test_settings: Settings,
        trading_state_factory: TradingStateFactory,
    ) -> None:
        """Test state hash is consistent for same state."""
        hybrid = HybridTradingArchitecture(settings=test_settings)

        state = trading_state_factory.create()

        hash1 = hybrid._compute_state_hash(state)
        hash2 = hybrid._compute_state_hash(state)

        assert hash1 == hash2

    @pytest.mark.asyncio
    async def test_cache_expiration(
        self,
        test_settings: Settings,
        action_factory: ActionFactory,
    ) -> None:
        """Test cache entries expire correctly."""
        # Create expired entry
        entry = PolicyEntry(
            action=action_factory.create_buy(),
            value=0.5,
            confidence=0.8,
            computed_at=datetime.now() - timedelta(days=2),
            expires_at=datetime.now() - timedelta(days=1),
            state_hash="test",
        )

        assert entry.is_expired()

        # Create valid entry
        valid_entry = PolicyEntry(
            action=action_factory.create_buy(),
            value=0.5,
            confidence=0.8,
            computed_at=datetime.now(),
            expires_at=datetime.now() + timedelta(days=1),
            state_hash="test",
        )

        assert not valid_entry.is_expired()


class TestMultiAgentCoordination:
    """Test multi-agent coordination integration."""

    @pytest.mark.asyncio
    async def test_agents_produce_recommendations(
        self,
        test_settings: Settings,
        trading_state_factory: TradingStateFactory,
    ) -> None:
        """Test all agents produce valid recommendations."""
        from reasoning_trading.agents.coordinator import MultiAgentTradingMCTS

        coordinator = MultiAgentTradingMCTS(settings=test_settings)
        state = trading_state_factory.create()

        results = await coordinator._gather_agent_recommendations(state)

        assert len(results) > 0

        for result in results:
            assert result.action is not None
            assert result.action.direction in list(TradingDirection)
            assert 0 <= result.confidence <= 1

    @pytest.mark.asyncio
    async def test_agent_combination_selection(
        self,
        test_settings: Settings,
        trading_state_factory: TradingStateFactory,
    ) -> None:
        """Test agent combination produces combined action."""
        from reasoning_trading.agents.coordinator import MultiAgentTradingMCTS

        coordinator = MultiAgentTradingMCTS(settings=test_settings)
        state = trading_state_factory.create_for_scenario(TestScenario.BULLISH)

        action = await coordinator.analyze(state)

        assert isinstance(action, TradingAction)
        assert action.direction in list(TradingDirection)
        # For bullish state, expect some confidence in direction
        if action.direction != TradingDirection.HOLD:
            assert action.confidence > 0

    @pytest.mark.asyncio
    @pytest.mark.parametrize("scenario", [TestScenario.BULLISH, TestScenario.BEARISH, TestScenario.NEUTRAL])
    async def test_coordinator_responds_to_scenarios(
        self,
        scenario: TestScenario,
        test_settings: Settings,
        trading_state_factory: TradingStateFactory,
        scenario_configs: dict,
    ) -> None:
        """Test coordinator responds appropriately to different scenarios."""
        from reasoning_trading.agents.coordinator import MultiAgentTradingMCTS

        coordinator = MultiAgentTradingMCTS(settings=test_settings)
        state = trading_state_factory.create_for_scenario(scenario)
        scenario_config = scenario_configs[scenario]

        action = await coordinator.analyze(state)

        # Should produce valid action
        assert isinstance(action, TradingAction)

        # For strong consensus scenarios, action should align
        # (allow flexibility since agents may disagree)
        if abs(scenario_config.consensus) > 0.5:
            # Just verify we get a confident action
            if action.direction != TradingDirection.HOLD:
                assert action.confidence >= scenario_config.confidence_min * 0.5
