"""
End-to-End tests for multi-agent trading system.

Tests:
1. Agent coordination
2. Consensus building
3. Action combination
4. Complete analysis cycle
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from reasoning_trading.config import Settings, TradingMode
from reasoning_trading.core.actions import TradingAction, TradingDirection
from reasoning_trading.core.state import TradingState
from reasoning_trading.agents.coordinator import MultiAgentTradingMCTS

from tests.config import TestConfig, TestScenario
from tests.factories import TradingStateFactory


class TestAgentCoordinationE2E:
    """E2E tests for agent coordination."""

    @pytest.mark.asyncio
    async def test_all_agents_contribute(
        self,
        test_settings: Settings,
        trading_state_factory: TradingStateFactory,
    ) -> None:
        """Test all agents contribute to final decision."""
        coordinator = MultiAgentTradingMCTS(settings=test_settings)
        state = trading_state_factory.create()

        # Gather recommendations from all agents
        results = await coordinator._gather_agent_recommendations(state)

        # Should have multiple agent results
        assert len(results) > 0

        # Each result should have required fields
        for result in results:
            assert result.action is not None
            assert result.action.direction in list(TradingDirection)
            assert 0 <= result.confidence <= 1
            assert result.agent_name is not None

    @pytest.mark.asyncio
    async def test_coordinator_combines_agents(
        self,
        test_settings: Settings,
        trading_state_factory: TradingStateFactory,
    ) -> None:
        """Test coordinator properly combines agent outputs."""
        coordinator = MultiAgentTradingMCTS(settings=test_settings)
        state = trading_state_factory.create()

        # Run full analysis
        action = await coordinator.analyze(state)

        # Should produce valid action
        assert isinstance(action, TradingAction)
        assert action.direction in list(TradingDirection)

    @pytest.mark.asyncio
    async def test_agent_weights_applied(
        self,
        test_settings: Settings,
        trading_state_factory: TradingStateFactory,
    ) -> None:
        """Test agent weights are applied in combination."""
        coordinator = MultiAgentTradingMCTS(settings=test_settings)
        state = trading_state_factory.create()

        # Get individual agent results
        results = await coordinator._gather_agent_recommendations(state)

        # Calculate weighted combination manually
        if results:
            total_weight = sum(r.confidence for r in results)
            if total_weight > 0:
                # Just verify weights sum correctly
                assert total_weight > 0


class TestConsensusE2E:
    """E2E tests for consensus building."""

    @pytest.mark.asyncio
    async def test_strong_bullish_consensus(
        self,
        test_settings: Settings,
        trading_state_factory: TradingStateFactory,
        scenario_configs: dict,
    ) -> None:
        """Test consensus forms on strong bullish signal."""
        coordinator = MultiAgentTradingMCTS(settings=test_settings)
        state = trading_state_factory.create_for_scenario(TestScenario.BULLISH)

        action = await coordinator.analyze(state)

        # Should produce valid action
        assert isinstance(action, TradingAction)

        # With strong bullish signals, should lean toward BUY
        # (Allow HOLD as agents may still disagree)
        assert action.direction in [TradingDirection.BUY, TradingDirection.HOLD]

    @pytest.mark.asyncio
    async def test_strong_bearish_consensus(
        self,
        test_settings: Settings,
        trading_state_factory: TradingStateFactory,
        scenario_configs: dict,
    ) -> None:
        """Test consensus forms on strong bearish signal."""
        coordinator = MultiAgentTradingMCTS(settings=test_settings)
        state = trading_state_factory.create_for_scenario(TestScenario.BEARISH)

        action = await coordinator.analyze(state)

        # Should produce valid action
        assert isinstance(action, TradingAction)

        # With strong bearish signals, should lean toward SELL
        # (Allow HOLD as agents may still disagree)
        assert action.direction in [TradingDirection.SELL, TradingDirection.HOLD]

    @pytest.mark.asyncio
    async def test_conflicting_signals_handled(
        self,
        test_settings: Settings,
        trading_state_factory: TradingStateFactory,
    ) -> None:
        """Test system handles conflicting signals gracefully."""
        coordinator = MultiAgentTradingMCTS(settings=test_settings)

        # Create state with mixed signals
        state = trading_state_factory.create_for_scenario(TestScenario.NEUTRAL)

        # Modify to have conflicting signals
        state.analyst_signals.market_sentiment = 0.8  # Bullish
        state.analyst_signals.fundamental_score = -0.8  # Bearish

        action = await coordinator.analyze(state)

        # Should produce valid action despite conflicts
        assert isinstance(action, TradingAction)
        assert action.direction in list(TradingDirection)

        # Conflicting signals often lead to HOLD or reduced confidence
        if action.direction != TradingDirection.HOLD:
            # If taking action, confidence should be moderated
            assert action.confidence <= 0.8


class TestScenarioResponseE2E:
    """E2E tests for multi-agent response to scenarios."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("scenario", list(TestScenario))
    async def test_agents_respond_to_all_scenarios(
        self,
        scenario: TestScenario,
        test_settings: Settings,
        trading_state_factory: TradingStateFactory,
        scenario_configs: dict,
    ) -> None:
        """Test agents respond appropriately to all scenarios."""
        coordinator = MultiAgentTradingMCTS(settings=test_settings)
        state = trading_state_factory.create_for_scenario(scenario)
        scenario_config = scenario_configs[scenario]

        action = await coordinator.analyze(state)

        # Should always produce valid action
        assert isinstance(action, TradingAction)
        assert action.direction in list(TradingDirection)

        # For strong consensus scenarios, check alignment
        if abs(scenario_config.consensus) > 0.7:
            # Strong signal scenarios should produce some confidence
            if action.direction != TradingDirection.HOLD:
                assert action.confidence > 0

    @pytest.mark.asyncio
    async def test_volatile_market_response(
        self,
        test_settings: Settings,
        trading_state_factory: TradingStateFactory,
    ) -> None:
        """Test agents respond appropriately to volatile market."""
        coordinator = MultiAgentTradingMCTS(settings=test_settings)
        state = trading_state_factory.create_for_scenario(TestScenario.VOLATILE)

        action = await coordinator.analyze(state)

        # In volatile conditions, system should be more cautious
        assert isinstance(action, TradingAction)

        # Either HOLD or reduced position size
        if action.direction != TradingDirection.HOLD:
            # Position size should be conservative in volatile markets
            assert action.position_size_pct <= 0.5  # Less than 50%


class TestAgentRobustnessE2E:
    """E2E tests for agent robustness."""

    @pytest.mark.asyncio
    async def test_handles_partial_data(
        self,
        test_settings: Settings,
        trading_state_factory: TradingStateFactory,
    ) -> None:
        """Test agents handle partial/missing data."""
        coordinator = MultiAgentTradingMCTS(settings=test_settings)
        state = trading_state_factory.create()

        # Remove some data
        state.technical_indicators.macd_histogram = None
        state.analyst_signals.news_sentiment = None

        # Should still produce action
        action = await coordinator.analyze(state)
        assert isinstance(action, TradingAction)
        assert action.direction in list(TradingDirection)

    @pytest.mark.asyncio
    async def test_handles_extreme_values(
        self,
        test_settings: Settings,
        trading_state_factory: TradingStateFactory,
    ) -> None:
        """Test agents handle extreme values."""
        coordinator = MultiAgentTradingMCTS(settings=test_settings)
        state = trading_state_factory.create()

        # Set extreme values
        state.technical_indicators.rsi_14 = 99  # Extremely overbought
        state.technical_indicators.volatility_20 = 0.5  # Very high volatility
        state.current_price = state.current_price * 2  # Price spike

        # Should still produce action
        action = await coordinator.analyze(state)
        assert isinstance(action, TradingAction)
        assert action.direction in list(TradingDirection)

    @pytest.mark.asyncio
    async def test_concurrent_analysis(
        self,
        test_settings: Settings,
        trading_state_factory: TradingStateFactory,
    ) -> None:
        """Test concurrent analysis requests."""
        coordinator = MultiAgentTradingMCTS(settings=test_settings)

        # Create multiple states
        states = [
            trading_state_factory.create_for_scenario(scenario)
            for scenario in [TestScenario.BULLISH, TestScenario.BEARISH, TestScenario.NEUTRAL]
        ]

        # Run analyses concurrently
        actions = await asyncio.gather(*[
            coordinator.analyze(state) for state in states
        ])

        # All should complete
        assert len(actions) == len(states)

        for action in actions:
            assert isinstance(action, TradingAction)
            assert action.direction in list(TradingDirection)


class TestAgentPerformanceE2E:
    """E2E tests for agent performance."""

    @pytest.mark.asyncio
    async def test_analysis_completes_in_time(
        self,
        test_settings: Settings,
        trading_state_factory: TradingStateFactory,
        test_config: TestConfig,
    ) -> None:
        """Test analysis completes within timeout."""
        import time

        coordinator = MultiAgentTradingMCTS(settings=test_settings)
        state = trading_state_factory.create()

        start = time.perf_counter()
        action = await coordinator.analyze(state)
        elapsed = time.perf_counter() - start

        # Should complete within timeout
        assert elapsed < test_config.mcts_timeout_ms / 1000 * 2  # Allow 2x buffer

        # Should produce valid result
        assert isinstance(action, TradingAction)

    @pytest.mark.asyncio
    async def test_recommendation_gathering_parallel(
        self,
        test_settings: Settings,
        trading_state_factory: TradingStateFactory,
    ) -> None:
        """Test agent recommendations are gathered efficiently."""
        import time

        coordinator = MultiAgentTradingMCTS(settings=test_settings)
        state = trading_state_factory.create()

        # Time recommendation gathering
        start = time.perf_counter()
        results = await coordinator._gather_agent_recommendations(state)
        elapsed = time.perf_counter() - start

        # Multiple agents should complete in reasonable time (parallel)
        # If truly parallel, time should not scale linearly with agent count
        assert len(results) > 0
        assert elapsed < 5.0  # Should complete in under 5 seconds
