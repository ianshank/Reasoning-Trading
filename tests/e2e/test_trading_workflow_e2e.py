"""
End-to-End tests for complete trading workflows.

Tests the full cycle:
1. Market data ingestion
2. State construction
3. MCTS search
4. Decision making
5. Action execution
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
from reasoning_trading.mcts.tree import MCTSConfig, MCTSTree
from reasoning_trading.services.adapter import TradingServiceAdapter
from reasoning_trading.services.market_data import MarketDataService
from reasoning_trading.services.portfolio import PortfolioService
from reasoning_trading.workflow.graph import MCTSTradingGraph, MCTSTradingState

from tests.config import TestConfig, TestScenario
from tests.factories import (
    MarketDataFactory,
    PortfolioFactory,
    TradingStateFactory,
)


class TestCompleteTradeE2E:
    """E2E tests for complete trade execution flow."""

    @pytest.mark.asyncio
    async def test_market_data_to_decision(
        self,
        test_settings: Settings,
        market_data_factory: MarketDataFactory,
        portfolio_factory: PortfolioFactory,
        test_config: TestConfig,
        action_space: ActionSpace,
    ) -> None:
        """Test complete flow: market data -> indicators -> MCTS -> decision."""
        # Step 1: Generate market data
        bars = market_data_factory.generate_bars(n_bars=test_config.ohlcv_bars)

        # Step 2: Calculate indicators
        market_service = MarketDataService()
        indicators = market_service.calculate_indicators(bars)
        ohlcv = market_service.bars_to_ohlcv(bars)
        regime = market_service.detect_market_regime(bars)

        # Step 3: Construct trading state
        portfolio = portfolio_factory.create_with_position()

        state = TradingState(
            symbol=test_config.primary_symbol,
            timestamp=datetime.now(),
            current_price=bars[-1].close,
            ohlcv_history=ohlcv,
            technical_indicators=indicators,
            portfolio=portfolio,
            market_regime=regime,
        )

        # Step 4: Run MCTS search
        mcts_config = MCTSConfig(
            max_simulations=test_config.mcts_simulations,
            rollout_horizon=test_config.mcts_rollout_horizon,
            time_budget_ms=test_config.mcts_timeout_ms,
        )

        tree = MCTSTree(config=mcts_config)
        result = await tree.search(state, action_space)

        # Step 5: Verify decision
        assert result.total_simulations > 0
        assert result.best_action is not None
        assert result.best_action.direction in list(TradingDirection)
        assert result.best_action.confidence >= 0

    @pytest.mark.asyncio
    async def test_full_workflow_graph_execution(
        self,
        test_settings: Settings,
        mock_trading_adapter: AsyncMock,
        test_config: TestConfig,
    ) -> None:
        """Test complete workflow graph execution."""
        # Create and build graph
        graph = MCTSTradingGraph(settings=test_settings)
        graph.trading_adapter = mock_trading_adapter
        graph.build()

        # Create initial state
        initial_state = MCTSTradingState(
            symbol=test_config.primary_symbol,
            analysis_date=datetime.now().strftime("%Y-%m-%d"),
            max_iterations=test_config.mcts_simulations,
        )

        # Execute workflow - initialize phase
        initialized = await graph._initialize_node(initial_state)

        assert initialized["trading_state"] is not None
        assert initialized["tree_root"] is not None

        # Continue with selection and expansion phases
        state_with_tree = MCTSTradingState(
            **{**initial_state.__dict__, **initialized}
        )
        state_with_tree.current_node = state_with_tree.tree_root

        selected = await graph._select_node(state_with_tree)
        assert selected["current_node"] is not None
        assert selected["iteration_count"] >= 1

    @pytest.mark.asyncio
    async def test_decision_to_order_execution(
        self,
        test_settings: Settings,
        mock_trading_adapter: AsyncMock,
        trading_state_factory: TradingStateFactory,
        test_config: TestConfig,
        action_space: ActionSpace,
    ) -> None:
        """Test flow from MCTS decision to order execution."""
        # Get trading state
        state = trading_state_factory.create()

        # Run MCTS
        mcts_config = MCTSConfig(
            max_simulations=test_config.mcts_simulations,
            rollout_horizon=test_config.mcts_rollout_horizon,
        )

        tree = MCTSTree(config=mcts_config)
        result = await tree.search(state, action_space)

        # Extract decision
        best_action = result.best_action
        assert best_action is not None

        # Execute order via adapter
        if best_action.direction != TradingDirection.HOLD:
            order_result = await mock_trading_adapter.execute_trade(
                symbol=state.symbol,
                direction=best_action.direction.value,
                quantity=int(best_action.position_size_pct * 1000),  # Example qty
                price=state.current_price,
            )

            assert order_result.status == "filled"
            assert order_result.symbol == state.symbol


class TestMultiSymbolE2E:
    """E2E tests for multi-symbol trading scenarios."""

    @pytest.mark.asyncio
    async def test_parallel_symbol_analysis(
        self,
        test_settings: Settings,
        trading_state_factory: TradingStateFactory,
        test_config: TestConfig,
        action_space: ActionSpace,
    ) -> None:
        """Test parallel analysis of multiple symbols."""
        symbols = [test_config.primary_symbol, test_config.secondary_symbol]

        async def analyze_symbol(symbol: str) -> tuple[str, TradingAction | None]:
            state = trading_state_factory.create()
            state.symbol = symbol

            mcts_config = MCTSConfig(
                max_simulations=test_config.mcts_simulations // 2,
                rollout_horizon=test_config.mcts_rollout_horizon,
            )

            tree = MCTSTree(config=mcts_config)
            result = await tree.search(state, action_space)
            return symbol, result.best_action

        # Run analyses in parallel
        results = await asyncio.gather(*[analyze_symbol(s) for s in symbols])

        # Verify all completed
        assert len(results) == len(symbols)
        for symbol, action in results:
            assert symbol in symbols
            # Action may be None if search failed, but should typically exist
            if action is not None:
                assert action.direction in list(TradingDirection)


class TestPortfolioE2E:
    """E2E tests for portfolio management."""

    @pytest.mark.asyncio
    async def test_complete_trade_lifecycle(
        self,
        test_config: TestConfig,
    ) -> None:
        """Test complete trade lifecycle: open -> manage -> close."""
        portfolio = PortfolioService(initial_cash=test_config.initial_cash)

        # Phase 1: Open position
        can_open, _ = portfolio.can_open_position(
            symbol=test_config.primary_symbol,
            direction=TradingDirection.BUY,
            value=test_config.initial_cash * test_config.default_position_size,
        )
        assert can_open

        trade1 = portfolio.execute_trade(
            symbol=test_config.primary_symbol,
            direction=TradingDirection.BUY,
            quantity=100,
            price=test_config.base_price,
            stop_loss_pct=test_config.default_stop_loss,
        )

        initial_state = portfolio.get_state()
        assert initial_state.position_count == 1

        # Phase 2: Price movements
        prices_up = [
            test_config.base_price * (1 + 0.01 * i)
            for i in range(1, 6)
        ]

        for price in prices_up:
            portfolio.update_prices({test_config.primary_symbol: price})
            state = portfolio.get_state()
            # Unrealized P&L should be positive for price increases
            assert state.unrealized_pnl >= 0

        # Phase 3: Close position
        final_price = prices_up[-1]
        trade2 = portfolio.execute_trade(
            symbol=test_config.primary_symbol,
            direction=TradingDirection.SELL,
            quantity=100,
            price=final_price,
        )

        final_state = portfolio.get_state()
        assert final_state.position_count == 0
        assert trade2.pnl > 0  # Should have profit

    @pytest.mark.asyncio
    async def test_stop_loss_execution_e2e(
        self,
        test_config: TestConfig,
    ) -> None:
        """Test stop-loss triggered and executed."""
        portfolio = PortfolioService(initial_cash=test_config.initial_cash)

        # Open position with stop-loss
        portfolio.execute_trade(
            symbol=test_config.primary_symbol,
            direction=TradingDirection.BUY,
            quantity=100,
            price=test_config.base_price,
            stop_loss_pct=test_config.default_stop_loss,
        )

        # Price drops below stop-loss
        stop_price = test_config.base_price * (1 - test_config.default_stop_loss)
        trigger_price = stop_price * 0.99  # Below stop

        portfolio.update_prices({test_config.primary_symbol: trigger_price})

        # Check stop-loss triggered
        triggered = portfolio.check_stop_losses()
        assert test_config.primary_symbol in triggered

        # Execute stop-loss
        if triggered:
            position = portfolio.get_position(test_config.primary_symbol)
            if position:
                portfolio.execute_trade(
                    symbol=test_config.primary_symbol,
                    direction=TradingDirection.SELL,
                    quantity=position.quantity,
                    price=trigger_price,
                )

        # Position should be closed
        assert portfolio.get_position(test_config.primary_symbol) is None


class TestRiskManagementE2E:
    """E2E tests for risk management."""

    @pytest.mark.asyncio
    async def test_position_sizing_respects_limits(
        self,
        test_config: TestConfig,
        trading_state_factory: TradingStateFactory,
        action_space: ActionSpace,
    ) -> None:
        """Test that position sizing respects risk limits."""
        state = trading_state_factory.create()

        # Run MCTS to get action
        mcts_config = MCTSConfig(
            max_simulations=test_config.mcts_simulations,
            rollout_horizon=test_config.mcts_rollout_horizon,
        )

        tree = MCTSTree(config=mcts_config)
        result = await tree.search(state, action_space)

        if result.best_action is not None:
            action = result.best_action

            # Verify position size is within limits
            assert action.position_size_pct <= test_config.max_position_size
            assert action.position_size_pct >= 0

            # Verify stop-loss is set
            if action.direction != TradingDirection.HOLD:
                assert action.stop_loss_pct > 0
                assert action.stop_loss_pct <= test_config.default_stop_loss * 2

    @pytest.mark.asyncio
    async def test_portfolio_concentration_limits(
        self,
        test_config: TestConfig,
    ) -> None:
        """Test portfolio doesn't exceed concentration limits."""
        portfolio = PortfolioService(initial_cash=test_config.initial_cash)

        # Try to open position larger than max allowed
        max_value = test_config.initial_cash * test_config.max_position_size
        oversized_value = max_value * 2

        can_open, reason = portfolio.can_open_position(
            symbol=test_config.primary_symbol,
            direction=TradingDirection.BUY,
            value=oversized_value,
        )

        assert not can_open
        assert reason  # Should have reason for rejection


class TestMarketConditionsE2E:
    """E2E tests for different market conditions."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("scenario", list(TestScenario))
    async def test_system_handles_all_scenarios(
        self,
        scenario: TestScenario,
        test_settings: Settings,
        trading_state_factory: TradingStateFactory,
        scenario_configs: dict,
        test_config: TestConfig,
        action_space: ActionSpace,
    ) -> None:
        """Test system handles all market scenarios end-to-end."""
        state = trading_state_factory.create_for_scenario(scenario)
        scenario_config = scenario_configs[scenario]

        # Run MCTS
        mcts_config = MCTSConfig(
            max_simulations=test_config.mcts_simulations,
            rollout_horizon=test_config.mcts_rollout_horizon,
        )

        tree = MCTSTree(config=mcts_config)
        result = await tree.search(state, action_space)

        # System should produce valid result
        assert result.total_simulations > 0

        # Should have explored the tree
        assert result.root is not None
        assert result.root.visits > 0

        # Best action should be valid
        if result.best_action is not None:
            assert result.best_action.direction in list(TradingDirection)


class TestSystemRecoveryE2E:
    """E2E tests for system recovery scenarios."""

    @pytest.mark.asyncio
    async def test_handles_missing_data_gracefully(
        self,
        test_settings: Settings,
        trading_state_factory: TradingStateFactory,
        test_config: TestConfig,
        action_space: ActionSpace,
    ) -> None:
        """Test system handles missing data gracefully."""
        state = trading_state_factory.create()

        # Simulate missing some indicators
        state.technical_indicators.macd_histogram = None
        state.technical_indicators.bollinger_upper = None

        # Should still complete search
        mcts_config = MCTSConfig(
            max_simulations=test_config.mcts_simulations,
            rollout_horizon=test_config.mcts_rollout_horizon,
        )

        tree = MCTSTree(config=mcts_config)
        result = await tree.search(state, action_space)

        # Should complete without error
        assert result.total_simulations > 0

    @pytest.mark.asyncio
    async def test_timeout_handling(
        self,
        test_settings: Settings,
        trading_state_factory: TradingStateFactory,
        test_config: TestConfig,
        action_space: ActionSpace,
    ) -> None:
        """Test system handles timeout correctly."""
        state = trading_state_factory.create()

        # Very short timeout
        short_timeout_ms = 100

        mcts_config = MCTSConfig(
            max_simulations=10000,  # High simulation count
            time_budget_ms=short_timeout_ms,
            rollout_horizon=test_config.mcts_rollout_horizon,
        )

        tree = MCTSTree(config=mcts_config)
        result = await tree.search(state, action_space)

        # Should complete within reasonable time
        assert result.total_time_ms < short_timeout_ms * 3  # Allow some overhead

        # Should still produce valid result
        assert result.root is not None
