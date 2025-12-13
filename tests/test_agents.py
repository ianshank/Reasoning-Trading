"""
Tests for multi-agent coordination.
"""

from __future__ import annotations

import pytest

from reasoning_trading.agents.coordinator import (
    AgentResult,
    AgentType,
    BreakoutAgent,
    MeanReversionAgent,
    MomentumAgent,
    MultiAgentTradingMCTS,
)
from reasoning_trading.config import Settings
from reasoning_trading.core.actions import TradingAction, TradingDirection
from reasoning_trading.core.state import TradingState


class TestMomentumAgent:
    """Tests for MomentumAgent."""

    @pytest.fixture
    def agent(self, test_settings: Settings) -> MomentumAgent:
        """Create agent for testing."""
        return MomentumAgent(settings=test_settings)

    def test_agent_type(self, agent: MomentumAgent) -> None:
        """Test agent type."""
        assert agent.agent_type == AgentType.MOMENTUM

    @pytest.mark.asyncio
    async def test_analyze(
        self,
        agent: MomentumAgent,
        sample_trading_state: TradingState,
    ) -> None:
        """Test momentum analysis."""
        action = await agent.analyze(sample_trading_state)

        assert isinstance(action, TradingAction)
        assert action.direction in list(TradingDirection)

    @pytest.mark.asyncio
    async def test_analyze_strong_momentum(
        self,
        agent: MomentumAgent,
        sample_trading_state: TradingState,
    ) -> None:
        """Test with strong momentum signals."""
        # Set up strong bullish momentum
        sample_trading_state.technical_indicators.rsi_14 = 65
        sample_trading_state.technical_indicators.macd_histogram = 1.0
        sample_trading_state.technical_indicators.sma_20 = 110
        sample_trading_state.technical_indicators.sma_50 = 105

        action = await agent.analyze(sample_trading_state)

        # Should likely recommend buying
        assert action.direction in [TradingDirection.BUY, TradingDirection.HOLD]


class TestMeanReversionAgent:
    """Tests for MeanReversionAgent."""

    @pytest.fixture
    def agent(self, test_settings: Settings) -> MeanReversionAgent:
        """Create agent for testing."""
        return MeanReversionAgent(settings=test_settings)

    def test_agent_type(self, agent: MeanReversionAgent) -> None:
        """Test agent type."""
        assert agent.agent_type == AgentType.MEAN_REVERSION

    @pytest.mark.asyncio
    async def test_analyze(
        self,
        agent: MeanReversionAgent,
        sample_trading_state: TradingState,
    ) -> None:
        """Test mean reversion analysis."""
        action = await agent.analyze(sample_trading_state)

        assert isinstance(action, TradingAction)

    @pytest.mark.asyncio
    async def test_analyze_oversold(
        self,
        agent: MeanReversionAgent,
        sample_trading_state: TradingState,
    ) -> None:
        """Test with oversold conditions."""
        sample_trading_state.technical_indicators.rsi_14 = 25
        sample_trading_state.current_price = 95  # Below lower BB
        sample_trading_state.technical_indicators.bollinger_lower = 100

        action = await agent.analyze(sample_trading_state)

        # Mean reversion should consider buying oversold
        assert action.confidence > 0


class TestBreakoutAgent:
    """Tests for BreakoutAgent."""

    @pytest.fixture
    def agent(self, test_settings: Settings) -> BreakoutAgent:
        """Create agent for testing."""
        return BreakoutAgent(settings=test_settings)

    def test_agent_type(self, agent: BreakoutAgent) -> None:
        """Test agent type."""
        assert agent.agent_type == AgentType.BREAKOUT

    @pytest.mark.asyncio
    async def test_analyze(
        self,
        agent: BreakoutAgent,
        sample_trading_state: TradingState,
    ) -> None:
        """Test breakout analysis."""
        action = await agent.analyze(sample_trading_state)

        assert isinstance(action, TradingAction)

    @pytest.mark.asyncio
    async def test_analyze_upper_breakout(
        self,
        agent: BreakoutAgent,
        sample_trading_state: TradingState,
    ) -> None:
        """Test with upper breakout conditions."""
        sample_trading_state.current_price = 115  # Above upper BB
        sample_trading_state.technical_indicators.bollinger_upper = 110
        sample_trading_state.technical_indicators.adx_14 = 35

        action = await agent.analyze(sample_trading_state)

        # Breakout agent should detect the breakout
        assert action.confidence > 0


class TestAgentResult:
    """Tests for AgentResult."""

    def test_creation(self, sample_action: TradingAction) -> None:
        """Test result creation."""
        result = AgentResult(
            agent_type=AgentType.MOMENTUM,
            action=sample_action,
            confidence=0.8,
            reasoning="Test reasoning",
            analysis_time_ms=50.0,
        )

        assert result.agent_type == AgentType.MOMENTUM
        assert result.confidence == 0.8


class TestMultiAgentTradingMCTS:
    """Tests for MultiAgentTradingMCTS."""

    @pytest.fixture
    def coordinator(self, test_settings: Settings) -> MultiAgentTradingMCTS:
        """Create coordinator for testing."""
        return MultiAgentTradingMCTS(settings=test_settings)

    def test_default_agents(self, coordinator: MultiAgentTradingMCTS) -> None:
        """Test default agent registration."""
        assert len(coordinator.agents) == 3
        assert AgentType.MOMENTUM in coordinator.agents
        assert AgentType.MEAN_REVERSION in coordinator.agents
        assert AgentType.BREAKOUT in coordinator.agents

    @pytest.mark.asyncio
    async def test_analyze(
        self,
        coordinator: MultiAgentTradingMCTS,
        sample_trading_state: TradingState,
    ) -> None:
        """Test multi-agent analysis."""
        action = await coordinator.analyze(sample_trading_state)

        assert isinstance(action, TradingAction)
        assert action.direction in list(TradingDirection)

    @pytest.mark.asyncio
    async def test_gather_agent_recommendations(
        self,
        coordinator: MultiAgentTradingMCTS,
        sample_trading_state: TradingState,
    ) -> None:
        """Test gathering recommendations from all agents."""
        results = await coordinator._gather_agent_recommendations(sample_trading_state)

        assert len(results) == 3  # 3 default agents
        assert all(isinstance(r, AgentResult) for r in results)

    @pytest.mark.asyncio
    async def test_select_best_combination(
        self,
        coordinator: MultiAgentTradingMCTS,
        sample_trading_state: TradingState,
        sample_action: TradingAction,
    ) -> None:
        """Test agent combination selection."""
        # Create mock results
        results = [
            AgentResult(
                agent_type=AgentType.MOMENTUM,
                action=sample_action,
                confidence=0.7,
            ),
            AgentResult(
                agent_type=AgentType.MEAN_REVERSION,
                action=TradingAction.hold(),
                confidence=0.3,
            ),
        ]

        action = await coordinator._select_best_combination(
            sample_trading_state, results
        )

        assert isinstance(action, TradingAction)

    def test_register_agent(self, coordinator: MultiAgentTradingMCTS) -> None:
        """Test agent registration."""
        # Create custom agent
        custom_agent = MomentumAgent(settings=coordinator.settings)

        initial_count = len(coordinator.agents)
        coordinator.register_agent(custom_agent)

        assert len(coordinator.agents) == initial_count  # Already registered

    def test_remove_agent(self, coordinator: MultiAgentTradingMCTS) -> None:
        """Test agent removal."""
        coordinator.remove_agent(AgentType.MOMENTUM)

        assert AgentType.MOMENTUM not in coordinator.agents

    def test_get_agent_stats(self, coordinator: MultiAgentTradingMCTS) -> None:
        """Test statistics retrieval."""
        stats = coordinator.get_agent_stats()

        assert stats["total_agents"] == 3
        assert len(stats["agent_types"]) == 3
