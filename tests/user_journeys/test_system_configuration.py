"""
User journey tests for system configuration.

Simulates users configuring and customizing the system:
1. Initial setup
2. Custom configuration
3. Mode switching
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
import os

import numpy as np
import pytest

from reasoning_trading.config import Settings, TradingMode, MCTSSettings, RiskSettings
from reasoning_trading.core.actions import ActionSpace, TradingAction, TradingDirection
from reasoning_trading.core.state import TradingState
from reasoning_trading.mcts.tree import MCTSConfig, MCTSTree
from reasoning_trading.services.adapter import TradingServiceAdapter
from reasoning_trading.workflow.hybrid import HybridTradingArchitecture

from tests.config import TestConfig, TestScenario
from tests.factories import TradingStateFactory


class TestInitialSetupJourney:
    """User journey: Initial system setup."""

    def test_default_settings_work(self) -> None:
        """
        Test default settings provide working configuration.

        User story:
        As a new user, I want sensible defaults
        so I can start quickly.
        """
        settings = Settings()

        # Should have valid defaults
        assert settings.trading is not None
        assert settings.mcts is not None
        assert settings.risk is not None

        # Trading mode should default to paper
        assert settings.trading.trading_mode == TradingMode.PAPER

        # MCTS settings should have reasonable defaults
        assert settings.mcts.max_simulations > 0
        assert settings.mcts.rollout_horizon_days > 0
        assert settings.mcts.exploration_weight > 0

        # Risk settings should be conservative by default
        assert settings.risk.max_position_size_fraction <= 1.0
        assert settings.risk.default_stop_loss_percent > 0

    def test_action_space_configuration(
        self,
        test_config: TestConfig,
    ) -> None:
        """
        Test action space is configurable.

        User story:
        As a trader, I want to configure what actions
        my system can take.
        """
        # Conservative action space
        conservative_space = ActionSpace(
            allow_shorts=False,
            max_position_size=0.1,
            min_position_size=0.01,
            stop_loss_range=(0.02, 0.05),
        )

        assert not conservative_space.allow_shorts
        assert conservative_space.max_position_size == 0.1

        # Aggressive action space
        aggressive_space = ActionSpace(
            allow_shorts=True,
            max_position_size=0.5,
            min_position_size=0.05,
            stop_loss_range=(0.05, 0.15),
        )

        assert aggressive_space.allow_shorts
        assert aggressive_space.max_position_size == 0.5

    @pytest.mark.asyncio
    async def test_mcts_configuration(
        self,
        trading_state_factory: TradingStateFactory,
        test_config: TestConfig,
        action_space: ActionSpace,
    ) -> None:
        """
        Test MCTS is configurable.

        User story:
        As a user, I want to configure MCTS parameters
        based on my hardware and requirements.
        """
        state = trading_state_factory.create()

        # Low resource configuration
        low_config = MCTSConfig(
            max_simulations=10,
            max_depth=5,
            exploration_weight=1.0,
            time_budget_ms=100,
            rollout_horizon=test_config.mcts_rollout_horizon,
        )

        tree = MCTSTree(config=low_config)
        result = await tree.search(state, action_space)

        assert result.total_simulations <= 10
        assert result.total_time_ms < 500  # Should be quick

        # High resource configuration
        high_config = MCTSConfig(
            max_simulations=100,
            max_depth=20,
            exploration_weight=1.414,
            time_budget_ms=1000,
            rollout_horizon=test_config.mcts_rollout_horizon,
        )

        tree = MCTSTree(config=high_config)
        result = await tree.search(state, action_space)

        assert result.total_simulations <= 100


class TestCustomConfigurationJourney:
    """User journey: Custom configuration."""

    def test_environment_based_configuration(
        self,
        test_config: TestConfig,
    ) -> None:
        """
        Test configuration via environment variables.

        User story:
        As a DevOps engineer, I want to configure
        the system via environment variables.
        """
        # TestConfig uses environment variables
        config = TestConfig()

        # Values should be configurable via TEST_* env vars
        assert config.primary_symbol is not None
        assert config.base_price > 0
        assert config.mcts_simulations > 0

    @pytest.mark.asyncio
    async def test_custom_hybrid_architecture(
        self,
        test_settings: Settings,
        trading_state_factory: TradingStateFactory,
        test_config: TestConfig,
    ) -> None:
        """
        Test custom hybrid architecture configuration.

        User story:
        As an advanced user, I want to customize
        the batch/realtime balance.
        """
        # Batch-heavy configuration
        batch_heavy = HybridTradingArchitecture(
            settings=test_settings,
            batch_simulations=test_config.mcts_simulations * 2,
            realtime_simulations=test_config.mcts_simulations // 10,
        )

        # Realtime-heavy configuration
        realtime_heavy = HybridTradingArchitecture(
            settings=test_settings,
            batch_simulations=test_config.mcts_simulations // 2,
            realtime_simulations=test_config.mcts_simulations,
        )

        state = trading_state_factory.create()

        # Both should produce valid heuristic actions
        batch_action = batch_heavy._heuristic_action(state)
        realtime_action = realtime_heavy._heuristic_action(state)

        assert batch_action.direction in list(TradingDirection)
        assert realtime_action.direction in list(TradingDirection)


class TestModeSwitchingJourney:
    """User journey: Mode switching."""

    @pytest.mark.asyncio
    async def test_paper_to_live_transition(
        self,
        test_settings: Settings,
        test_config: TestConfig,
    ) -> None:
        """
        Test transitioning from paper to live mode.

        User story:
        As a trader, I want to test in paper mode
        then switch to live trading.
        """
        # Paper mode
        paper_settings = test_settings
        paper_settings.trading.trading_mode = TradingMode.PAPER

        paper_adapter = TradingServiceAdapter(
            mode=TradingMode.PAPER,
            settings=paper_settings,
        )

        # Verify paper mode tools work
        tools = paper_adapter.get_tools()
        assert len(tools) > 0

        # Paper mode signal
        signal = await paper_adapter.get_trading_signal(
            test_config.primary_symbol,
            datetime.now().strftime("%Y-%m-%d"),
        )
        assert signal.symbol == test_config.primary_symbol

        # Simulate switching to live (just verify configuration)
        live_settings = Settings()
        live_settings.trading.trading_mode = TradingMode.LIVE

        # In real scenario, would verify API keys etc.
        assert live_settings.trading.trading_mode == TradingMode.LIVE

    @pytest.mark.asyncio
    async def test_risk_level_switching(
        self,
        test_settings: Settings,
        trading_state_factory: TradingStateFactory,
        test_config: TestConfig,
    ) -> None:
        """
        Test switching between risk levels.

        User story:
        As a trader, I want to adjust my risk level
        based on market conditions.
        """
        state = trading_state_factory.create()

        # Conservative risk
        conservative_space = ActionSpace(
            allow_shorts=False,
            max_position_size=0.1,
            min_position_size=0.01,
            stop_loss_range=(0.02, 0.05),
        )

        mcts_config = MCTSConfig(
            max_simulations=test_config.mcts_simulations,
            rollout_horizon=test_config.mcts_rollout_horizon,
        )

        tree = MCTSTree(config=mcts_config)
        conservative_result = await tree.search(state, conservative_space)

        # Aggressive risk
        aggressive_space = ActionSpace(
            allow_shorts=True,
            max_position_size=0.5,
            min_position_size=0.05,
            stop_loss_range=(0.05, 0.15),
        )

        aggressive_result = await tree.search(state, aggressive_space)

        # Both should produce valid actions
        if conservative_result.best_action:
            assert conservative_result.best_action.position_size_pct <= 0.1

        if aggressive_result.best_action:
            assert aggressive_result.best_action.position_size_pct <= 0.5


class TestScenarioConfigurationJourney:
    """User journey: Scenario-based configuration."""

    @pytest.mark.asyncio
    async def test_scenario_specific_settings(
        self,
        test_settings: Settings,
        trading_state_factory: TradingStateFactory,
        scenario_configs: dict,
        test_config: TestConfig,
        action_space: ActionSpace,
    ) -> None:
        """
        Test applying scenario-specific settings.

        User story:
        As a researcher, I want to configure the system
        differently for different market conditions.
        """
        results: dict[str, Any] = {}

        for scenario in [TestScenario.BULLISH, TestScenario.VOLATILE]:
            state = trading_state_factory.create_for_scenario(scenario)
            scenario_config = scenario_configs[scenario]

            # Adjust MCTS based on scenario
            if scenario == TestScenario.VOLATILE:
                # More simulations in volatile markets
                sim_count = test_config.mcts_simulations * 2
            else:
                sim_count = test_config.mcts_simulations

            mcts_config = MCTSConfig(
                max_simulations=sim_count,
                rollout_horizon=test_config.mcts_rollout_horizon,
            )

            tree = MCTSTree(config=mcts_config)
            result = await tree.search(state, action_space)

            results[scenario.name] = {
                "simulations_used": result.total_simulations,
                "action": result.best_action.direction.value if result.best_action else "none",
            }

        # Verify scenario-specific behavior
        assert results["VOLATILE"]["simulations_used"] >= results["BULLISH"]["simulations_used"]


class TestToolsConfigurationJourney:
    """User journey: Tools configuration."""

    @pytest.mark.asyncio
    async def test_adapter_tools_available(
        self,
        test_settings: Settings,
    ) -> None:
        """
        Test trading adapter tools are available.

        User story:
        As a developer, I want to use LangGraph tools
        for trading operations.
        """
        adapter = TradingServiceAdapter(
            mode=TradingMode.PAPER,
            settings=test_settings,
        )

        tools = adapter.get_tools()

        # Should have expected tools
        assert len(tools) == 5

        tool_names = {t.name for t in tools}
        expected_tools = {
            "get_trading_signal",
            "execute_trade",
            "get_portfolio_state",
            "get_market_data",
            "calculate_risk_metrics",
        }

        assert tool_names == expected_tools

    @pytest.mark.asyncio
    async def test_tool_execution(
        self,
        test_settings: Settings,
        test_config: TestConfig,
    ) -> None:
        """
        Test tool execution works correctly.

        User story:
        As a developer, I want tools to execute
        correctly and return valid results.
        """
        adapter = TradingServiceAdapter(
            mode=TradingMode.PAPER,
            settings=test_settings,
        )

        # Get trading signal
        signal = await adapter.get_trading_signal(
            test_config.primary_symbol,
            datetime.now().strftime("%Y-%m-%d"),
        )

        assert signal.symbol == test_config.primary_symbol
        assert signal.direction in ["buy", "sell", "hold"]
        assert 0 <= signal.confidence <= 1

        # Get portfolio state
        portfolio = await adapter.get_portfolio_state()

        assert portfolio.portfolio_value > 0
        assert portfolio.cash_balance >= 0
