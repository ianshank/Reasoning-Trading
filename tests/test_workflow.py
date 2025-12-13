"""
Tests for LangGraph workflow and hybrid architecture.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from reasoning_trading.config import Settings
from reasoning_trading.core.actions import TradingAction, TradingDirection
from reasoning_trading.core.state import TradingState
from reasoning_trading.workflow.graph import (
    MCTSTradingGraph,
    MCTSTradingState,
    build_trading_mcts_graph,
)
from reasoning_trading.workflow.hybrid import (
    HybridTradingArchitecture,
    PolicyEntry,
)


class TestMCTSTradingState:
    """Tests for MCTSTradingState."""

    def test_creation(self) -> None:
        """Test state creation."""
        state = MCTSTradingState(
            symbol="AAPL",
            analysis_date="2024-01-15",
        )

        assert state.symbol == "AAPL"
        assert state.analysis_date == "2024-01-15"
        assert state.iteration_count == 0
        assert state.should_continue is True

    def test_with_defaults(self) -> None:
        """Test default values."""
        state = MCTSTradingState()

        assert state.symbol == ""
        assert len(state.messages) == 0
        assert state.tree_root is None


class TestMCTSTradingGraph:
    """Tests for MCTSTradingGraph."""

    @pytest.fixture
    def graph(self, test_settings: Settings) -> MCTSTradingGraph:
        """Create graph for testing."""
        return MCTSTradingGraph(settings=test_settings)

    def test_build(self, graph: MCTSTradingGraph) -> None:
        """Test graph building."""
        workflow = graph.build()
        assert workflow is not None

    def test_compile(self, graph: MCTSTradingGraph) -> None:
        """Test graph compilation."""
        compiled = graph.compile()
        assert compiled is not None

    @pytest.mark.asyncio
    async def test_initialize_node(
        self,
        graph: MCTSTradingGraph,
        sample_trading_state: TradingState,
    ) -> None:
        """Test initialization node."""
        # Build the graph
        graph.build()

        # Mock the adapter
        from unittest.mock import AsyncMock

        graph.trading_adapter = AsyncMock()
        graph.trading_adapter.build_trading_state = AsyncMock(return_value=sample_trading_state)
        graph.trading_adapter.get_portfolio_state = AsyncMock(
            return_value=sample_trading_state.portfolio
        )

        state = MCTSTradingState(symbol="AAPL", analysis_date="2024-01-15")
        result = await graph._initialize_node(state)

        assert "trading_state" in result
        assert "tree_root" in result
        assert result["tree_root"] is not None

    def test_should_continue_search_max_iterations(
        self, graph: MCTSTradingGraph
    ) -> None:
        """Test termination at max iterations."""
        state = MCTSTradingState(
            iteration_count=1000,
            max_iterations=1000,
        )

        result = graph._should_continue_search(state)
        assert result == "stop"

    def test_should_continue_search_with_error(
        self, graph: MCTSTradingGraph
    ) -> None:
        """Test termination on error."""
        state = MCTSTradingState(
            error_message="Test error",
        )

        result = graph._should_continue_search(state)
        assert result == "error"

    def test_build_decision_reasoning(
        self,
        graph: MCTSTradingGraph,
        sample_trading_state: TradingState,
        sample_action: TradingAction,
    ) -> None:
        """Test reasoning generation."""
        from reasoning_trading.mcts.node import Node

        state = MCTSTradingState(
            symbol="AAPL",
            analysis_date="2024-01-15",
            trading_state=sample_trading_state,
            iteration_count=50,
        )

        best_child = Node(
            state=sample_trading_state,
            action=sample_action,
        )
        best_child.visits = 30
        best_child.value_sum = 15.0

        reasoning = graph._build_decision_reasoning(state, best_child)

        assert "AAPL" in reasoning
        assert "MCTS" in reasoning
        assert str(best_child.visits) in reasoning


class TestBuildTradingMCTSGraph:
    """Tests for graph factory function."""

    def test_factory(self, test_settings: Settings) -> None:
        """Test factory function."""
        graph = build_trading_mcts_graph(test_settings)

        assert isinstance(graph, MCTSTradingGraph)
        assert graph._compiled_graph is not None


class TestPolicyEntry:
    """Tests for PolicyEntry."""

    @pytest.fixture
    def sample_entry(self, sample_action: TradingAction) -> PolicyEntry:
        """Create sample policy entry."""
        return PolicyEntry(
            action=sample_action,
            value=0.5,
            confidence=0.8,
            computed_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=24),
            state_hash="abc123",
        )

    def test_is_expired(self, sample_entry: PolicyEntry) -> None:
        """Test expiration check."""
        assert not sample_entry.is_expired()

        # Create expired entry
        expired = PolicyEntry(
            action=sample_entry.action,
            value=0.5,
            confidence=0.8,
            computed_at=datetime.now() - timedelta(hours=48),
            expires_at=datetime.now() - timedelta(hours=24),
            state_hash="abc123",
        )
        assert expired.is_expired()

    def test_to_dict_from_dict(self, sample_entry: PolicyEntry) -> None:
        """Test serialization roundtrip."""
        data = sample_entry.to_dict()
        restored = PolicyEntry.from_dict(data)

        assert restored.value == sample_entry.value
        assert restored.confidence == sample_entry.confidence
        assert restored.state_hash == sample_entry.state_hash


class TestHybridTradingArchitecture:
    """Tests for HybridTradingArchitecture."""

    @pytest.fixture
    def hybrid(self, test_settings: Settings) -> HybridTradingArchitecture:
        """Create hybrid architecture for testing."""
        return HybridTradingArchitecture(
            settings=test_settings,
            batch_simulations=50,
            realtime_simulations=10,
        )

    def test_compute_state_hash(
        self,
        hybrid: HybridTradingArchitecture,
        sample_trading_state: TradingState,
    ) -> None:
        """Test state hashing."""
        hash1 = hybrid._compute_state_hash(sample_trading_state)
        hash2 = hybrid._compute_state_hash(sample_trading_state)

        assert hash1 == hash2
        assert len(hash1) == 16  # MD5 truncated

    def test_heuristic_action(
        self,
        hybrid: HybridTradingArchitecture,
        sample_trading_state: TradingState,
    ) -> None:
        """Test heuristic fallback."""
        action = hybrid._heuristic_action(sample_trading_state)

        assert isinstance(action, TradingAction)
        assert action.direction in list(TradingDirection)

    @pytest.mark.asyncio
    async def test_get_cache_stats(
        self, hybrid: HybridTradingArchitecture
    ) -> None:
        """Test cache statistics."""
        stats = await hybrid.get_cache_stats()

        assert "local_cache_size" in stats
        assert "redis_connected" in stats

    @pytest.mark.asyncio
    async def test_clear_cache(
        self, hybrid: HybridTradingArchitecture
    ) -> None:
        """Test cache clearing."""
        # Add something to local cache
        hybrid._local_cache["policy:AAPL:test"] = None

        cleared = await hybrid.clear_cache("AAPL")

        assert cleared > 0
        assert "policy:AAPL:test" not in hybrid._local_cache
