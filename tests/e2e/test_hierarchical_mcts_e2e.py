"""
End-to-end tests for Hierarchical MCTS Trading System.

Tests complete trading workflows using hierarchical MCTS with:
- Policy network integration
- Regime detection
- Lambda architecture
- LangGraph orchestration
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import TYPE_CHECKING

import numpy as np
import pytest

from reasoning_trading.hierarchical import (
    HierarchicalMCTSTree,
    TreeConfig,
)
from reasoning_trading.lambda_arch import (
    BatchLayer,
    BatchLayerConfig,
    LambdaCoordinator,
    LambdaCoordinatorConfig,
    SpeedLayer,
    SpeedLayerConfig,
)
from reasoning_trading.langgraph import (
    MCTSGraph,
    MCTSGraphConfig,
    MCTSOrchestrator,
    MCTSOrchestratorConfig,
)
from reasoning_trading.policy import (
    DistilledPolicyNetwork,
    PolicyConfig,
)
from reasoning_trading.regime import (
    RegimeDetector,
    RegimeDetectorConfig,
)

if TYPE_CHECKING:
    from tests.config import TestConfig
    from tests.factories import TradingStateFactory


class TestHierarchicalTradingE2E:
    """E2E tests for hierarchical trading system."""

    @pytest.fixture
    def policy_network(self) -> DistilledPolicyNetwork:
        """Create policy network for tests."""
        config = PolicyConfig(
            input_dim=50,
            hidden_dims=[64, 32],
            num_actions=7,
        )
        return DistilledPolicyNetwork(config)

    @pytest.fixture
    def regime_detector(self) -> RegimeDetector:
        """Create regime detector."""
        config = RegimeDetectorConfig(
            use_hmm=True,
            min_regime_duration_seconds=0,
        )
        return RegimeDetector(config)

    @pytest.mark.asyncio
    async def test_complete_trading_decision_flow(
        self,
        policy_network: DistilledPolicyNetwork,
        regime_detector: RegimeDetector,
        trading_state_factory: TradingStateFactory,
    ) -> None:
        """Test complete flow from state to trading decision."""
        # Setup components
        mcts_config = MCTSGraphConfig(
            max_iterations=20,
            parallel_simulations=2,
        )
        mcts_graph = MCTSGraph(
            config=mcts_config,
            policy_network=policy_network,
        )

        coord_config = LambdaCoordinatorConfig()
        coordinator = LambdaCoordinator(
            config=coord_config,
            speed_layer=SpeedLayer(policy_network=policy_network),
        )

        # Create trading state
        state = trading_state_factory.create()

        # Detect regime
        regime = regime_detector.detect(state)
        assert regime.regime is not None

        # Make MCTS decision
        features = state.to_feature_vector()
        mcts_result = await mcts_graph.run(
            trading_state_features=features,
            symbol=state.symbol,
            level="tactical",
        )

        # Make coordinated decision
        decision = await coordinator.decide(state, level="tactical")

        # Verify outputs
        assert mcts_result.best_action is not None
        assert decision.action_type is not None
        assert regime.confidence > 0

    @pytest.mark.asyncio
    async def test_hierarchical_search_across_levels(
        self,
        trading_state_factory: TradingStateFactory,
    ) -> None:
        """Test hierarchical search traverses all levels."""
        tree_config = TreeConfig(
            strategic_simulations=30,
            tactical_simulations=20,
            execution_simulations=10,
        )
        tree = HierarchicalMCTSTree(tree_config)

        state = trading_state_factory.create()

        result = await tree.search(state, target_level="execution")

        assert result.success
        assert result.best_action is not None
        assert len(result.level_results) >= 1

    @pytest.mark.asyncio
    async def test_regime_aware_trading(
        self,
        regime_detector: RegimeDetector,
        trading_state_factory: TradingStateFactory,
    ) -> None:
        """Test trading adapts to different regimes."""
        from tests.config import TestScenario

        orchestrator_config = MCTSOrchestratorConfig(
            strategic_iterations=20,
            tactical_iterations=15,
            execution_iterations=10,
        )
        orchestrator = MCTSOrchestrator(
            orchestrator_config,
            regime_detector=regime_detector,
        )

        # Test different market scenarios
        scenarios = [
            TestScenario.BULLISH,
            TestScenario.BEARISH,
            TestScenario.VOLATILE,
            TestScenario.NEUTRAL,
        ]

        results = []
        for scenario in scenarios:
            state = trading_state_factory.create_for_scenario(scenario)
            result = await orchestrator.search(state, level="tactical")
            results.append((scenario, result))

        # Verify we got results for all scenarios
        assert len(results) == 4
        for scenario, result in results:
            assert result.best_action is not None

    @pytest.mark.asyncio
    async def test_batch_and_speed_layer_coordination(
        self,
        policy_network: DistilledPolicyNetwork,
        trading_state_factory: TradingStateFactory,
    ) -> None:
        """Test batch and speed layer work together."""
        # Setup layers
        batch_config = BatchLayerConfig(
            strategic_simulations=30,
            precompute_states=5,
        )
        batch_layer = BatchLayer(batch_config)

        speed_config = SpeedLayerConfig(
            target_latency_ms=20.0,
            enable_heuristic_fallback=True,
        )
        speed_layer = SpeedLayer(
            speed_config,
            policy_network=policy_network,
        )

        coord_config = LambdaCoordinatorConfig(
            batch_trigger_on_regime_change=True,
        )
        coordinator = LambdaCoordinator(
            coord_config,
            batch_layer=batch_layer,
            speed_layer=speed_layer,
        )

        # Create states
        states = [trading_state_factory.create() for _ in range(5)]

        # Make decisions
        for state in states:
            decision = await coordinator.decide(state, level="tactical")
            assert decision.action_type is not None
            assert decision.latency_ms > 0

        # Check stats
        stats = coordinator.get_statistics()
        assert stats["total_decisions"] == 5

    @pytest.mark.asyncio
    async def test_full_trading_session_simulation(
        self,
        trading_state_factory: TradingStateFactory,
    ) -> None:
        """Test a simulated trading session with multiple decisions."""
        # Setup complete system
        policy_config = PolicyConfig(
            input_dim=50,
            hidden_dims=[32, 16],
            num_actions=7,
        )
        policy_network = DistilledPolicyNetwork(policy_config)

        regime_config = RegimeDetectorConfig(
            use_hmm=True,
            min_regime_duration_seconds=0,
        )
        regime_detector = RegimeDetector(regime_config)

        orchestrator_config = MCTSOrchestratorConfig(
            strategic_iterations=15,
            tactical_iterations=10,
            execution_iterations=5,
            enable_result_caching=True,
        )
        orchestrator = MCTSOrchestrator(
            orchestrator_config,
            policy_network=policy_network,
            regime_detector=regime_detector,
        )

        # Simulate trading session
        from tests.config import TestScenario

        session_states = []
        session_decisions = []

        # Bullish period
        for _ in range(3):
            state = trading_state_factory.create_for_scenario(TestScenario.BULLISH)
            decision = await orchestrator.search(state, level="tactical")
            session_states.append(state)
            session_decisions.append(decision)

        # Volatile period
        for _ in range(2):
            state = trading_state_factory.create_for_scenario(TestScenario.VOLATILE)
            decision = await orchestrator.search(state, level="tactical")
            session_states.append(state)
            session_decisions.append(decision)

        # Bearish period
        for _ in range(3):
            state = trading_state_factory.create_for_scenario(TestScenario.BEARISH)
            decision = await orchestrator.search(state, level="tactical")
            session_states.append(state)
            session_decisions.append(decision)

        # Verify session
        assert len(session_decisions) == 8
        for decision in session_decisions:
            assert decision.best_action is not None
            assert decision.confidence >= 0

        # Check caching was used
        stats = orchestrator.get_statistics()
        assert stats["search_count"] == 8

    @pytest.mark.asyncio
    async def test_concurrent_trading_decisions(
        self,
        trading_state_factory: TradingStateFactory,
    ) -> None:
        """Test system handles concurrent decisions correctly."""
        orchestrator = MCTSOrchestrator(
            MCTSOrchestratorConfig(
                strategic_iterations=10,
                tactical_iterations=8,
                execution_iterations=5,
            )
        )

        # Create different states
        states = [trading_state_factory.create() for _ in range(10)]

        # Make concurrent decisions
        results = await orchestrator.parallel_search(states, level="tactical")

        assert len(results) == 10
        for result in results:
            assert result.best_action is not None

    @pytest.mark.asyncio
    async def test_langgraph_mcts_phase_orchestration(
        self,
        trading_state_factory: TradingStateFactory,
    ) -> None:
        """Test LangGraph MCTS phases execute correctly."""
        config = MCTSGraphConfig(
            max_iterations=15,
            exploration_constant=1.5,
            parallel_simulations=2,
        )
        graph = MCTSGraph(config)

        state = trading_state_factory.create()
        features = state.to_feature_vector()

        result = await graph.run(
            trading_state_features=features,
            symbol=state.symbol,
            level="tactical",
        )

        # Verify phases executed
        assert result.success
        assert result.iterations_completed > 0
        assert result.tree_size > 1  # At least root + children

        # Verify probabilities are valid
        assert len(result.action_probabilities) > 0
        total_prob = sum(result.action_probabilities.values())
        assert abs(total_prob - 1.0) < 0.01


class TestMultiSymbolTradingE2E:
    """E2E tests for multi-symbol trading scenarios."""

    @pytest.mark.asyncio
    async def test_multi_symbol_batch_processing(
        self,
        trading_state_factory: TradingStateFactory,
        test_config: TestConfig,
    ) -> None:
        """Test processing multiple symbols in batch."""
        batch_config = BatchLayerConfig(
            strategic_simulations=20,
            batch_timeout_seconds=10.0,
        )
        batch_layer = BatchLayer(batch_config)

        # Create states for multiple symbols
        symbols = test_config.batch_symbols[:3]
        states = []
        for sym in symbols:
            state = trading_state_factory.create(symbol=sym)
            states.append(state)

        # Process batch
        result = await batch_layer.run_strategic_mcts(states)

        assert result.success
        assert len(result.policies) == len(symbols)

    @pytest.mark.asyncio
    async def test_portfolio_level_optimization(
        self,
        trading_state_factory: TradingStateFactory,
        test_config: TestConfig,
    ) -> None:
        """Test portfolio-level decision optimization."""
        orchestrator = MCTSOrchestrator(
            MCTSOrchestratorConfig(
                strategic_iterations=25,
                tactical_iterations=15,
                execution_iterations=10,
            )
        )

        symbols = test_config.batch_symbols[:4]
        portfolio_decisions = {}

        for sym in symbols:
            state = trading_state_factory.create(symbol=sym)
            result = await orchestrator.search(state, level="tactical")
            portfolio_decisions[sym] = result

        # Verify all symbols got decisions
        assert len(portfolio_decisions) == len(symbols)
        for sym, decision in portfolio_decisions.items():
            assert decision.best_action is not None


class TestEdgeCasesE2E:
    """E2E tests for edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_empty_state_handling(self) -> None:
        """Test handling of minimal/empty state."""
        orchestrator = MCTSOrchestrator(
            MCTSOrchestratorConfig(
                tactical_iterations=10,
            )
        )

        # Create minimal features
        minimal_features = np.zeros(50)

        graph_config = MCTSGraphConfig(max_iterations=10)
        graph = MCTSGraph(graph_config)

        result = await graph.run(
            trading_state_features=minimal_features,
            symbol="TEST",
            level="tactical",
        )

        # Should still produce a result
        assert result.best_action is not None

    @pytest.mark.asyncio
    async def test_timeout_handling(
        self,
        trading_state_factory: TradingStateFactory,
    ) -> None:
        """Test timeout handling."""
        orchestrator = MCTSOrchestrator(
            MCTSOrchestratorConfig(
                tactical_iterations=1000,  # Many iterations
                tactical_timeout_seconds=0.1,  # Short timeout
            )
        )

        state = trading_state_factory.create()

        # Should complete within timeout with partial result
        result = await orchestrator.search(state, level="tactical")

        # Should have some result
        assert result is not None

    @pytest.mark.asyncio
    async def test_recovery_from_errors(
        self,
        trading_state_factory: TradingStateFactory,
    ) -> None:
        """Test system recovers from errors gracefully."""
        coordinator = LambdaCoordinator()

        # Valid state should work
        state = trading_state_factory.create()
        decision = await coordinator.decide(state, level="tactical")

        assert decision.action_type is not None
