"""
User journey tests for trading sessions.

Simulates complete user trading sessions:
1. Morning analysis routine
2. Trade execution and management
3. End of day review
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
from reasoning_trading.services.market_data import MarketDataService
from reasoning_trading.services.portfolio import PortfolioService
from reasoning_trading.workflow.hybrid import HybridTradingArchitecture
from reasoning_trading.agents.coordinator import MultiAgentTradingMCTS

from tests.config import TestConfig, TestScenario
from tests.factories import (
    MarketDataFactory,
    PortfolioFactory,
    TradingStateFactory,
)


class TestMorningAnalysisJourney:
    """User journey: Morning market analysis."""

    @pytest.mark.asyncio
    async def test_morning_analysis_routine(
        self,
        test_settings: Settings,
        market_data_factory: MarketDataFactory,
        portfolio_factory: PortfolioFactory,
        test_config: TestConfig,
        action_space: ActionSpace,
    ) -> None:
        """
        Simulate a complete morning analysis routine.

        User story:
        As a trader, I want to analyze the market each morning
        to determine what trades to make today.

        Steps:
        1. Fetch latest market data
        2. Calculate indicators
        3. Check existing positions
        4. Run MCTS analysis
        5. Get trading recommendations
        """
        # Step 1: Fetch market data
        bars = market_data_factory.generate_bars(n_bars=test_config.ohlcv_bars)
        market_service = MarketDataService()

        # Step 2: Calculate indicators
        indicators = market_service.calculate_indicators(bars)
        assert indicators.sma_20 is not None
        assert indicators.rsi_14 is not None

        ohlcv = market_service.bars_to_ohlcv(bars)
        regime = market_service.detect_market_regime(bars)

        # Step 3: Check portfolio
        portfolio = portfolio_factory.create_with_position()
        portfolio_state = portfolio

        # Step 4: Build trading state
        state = TradingState(
            symbol=test_config.primary_symbol,
            timestamp=datetime.now(),
            current_price=bars[-1].close,
            ohlcv_history=ohlcv,
            technical_indicators=indicators,
            portfolio=portfolio_state,
            market_regime=regime,
        )

        # Step 5: Run MCTS analysis
        mcts_config = MCTSConfig(
            max_simulations=test_config.mcts_simulations,
            rollout_horizon=test_config.mcts_rollout_horizon,
        )

        tree = MCTSTree(config=mcts_config)
        result = await tree.search(state, action_space)

        # Verify we got actionable results
        assert result.total_simulations > 0
        assert result.best_action is not None
        assert result.best_action.direction in list(TradingDirection)

        # User can now make informed decision
        recommendation = result.best_action
        assert recommendation.confidence >= 0

    @pytest.mark.asyncio
    async def test_multi_symbol_morning_analysis(
        self,
        test_settings: Settings,
        trading_state_factory: TradingStateFactory,
        test_config: TestConfig,
        action_space: ActionSpace,
    ) -> None:
        """
        Simulate morning analysis for multiple symbols.

        User story:
        As a portfolio manager, I want to analyze multiple stocks
        each morning to identify the best opportunities.
        """
        symbols = [test_config.primary_symbol, test_config.secondary_symbol]
        recommendations: dict[str, TradingAction] = {}

        for symbol in symbols:
            state = trading_state_factory.create()
            state.symbol = symbol

            mcts_config = MCTSConfig(
                max_simulations=test_config.mcts_simulations,
                rollout_horizon=test_config.mcts_rollout_horizon,
            )

            tree = MCTSTree(config=mcts_config)
            result = await tree.search(state, action_space)

            if result.best_action:
                recommendations[symbol] = result.best_action

        # Should have analysis for all symbols
        assert len(recommendations) == len(symbols)

        # User can compare recommendations
        for symbol, action in recommendations.items():
            assert action.direction in list(TradingDirection)


class TestTradeExecutionJourney:
    """User journey: Trade execution and management."""

    @pytest.mark.asyncio
    async def test_full_trade_execution_journey(
        self,
        test_config: TestConfig,
    ) -> None:
        """
        Simulate complete trade execution journey.

        User story:
        As a trader, I want to execute a trade and manage it
        through its complete lifecycle.

        Steps:
        1. Check if trade is viable
        2. Execute entry
        3. Monitor position
        4. Execute exit (profit or loss)
        """
        portfolio = PortfolioService(initial_cash=test_config.initial_cash)

        # Step 1: Check trade viability
        trade_value = test_config.initial_cash * test_config.default_position_size
        can_trade, reason = portfolio.can_open_position(
            symbol=test_config.primary_symbol,
            direction=TradingDirection.BUY,
            value=trade_value,
        )
        assert can_trade, f"Cannot trade: {reason}"

        # Step 2: Execute entry
        entry_trade = portfolio.execute_trade(
            symbol=test_config.primary_symbol,
            direction=TradingDirection.BUY,
            quantity=100,
            price=test_config.base_price,
            stop_loss_pct=test_config.default_stop_loss,
        )

        assert entry_trade.symbol == test_config.primary_symbol
        position = portfolio.get_position(test_config.primary_symbol)
        assert position is not None

        # Step 3: Monitor position (simulate price movements)
        monitoring_prices = [
            test_config.base_price * 1.02,  # Up 2%
            test_config.base_price * 1.01,  # Back to 1%
            test_config.base_price * 1.05,  # Up 5%
        ]

        for price in monitoring_prices:
            portfolio.update_prices({test_config.primary_symbol: price})
            position = portfolio.get_position(test_config.primary_symbol)

            # User checks position status
            assert position.current_price == price
            pnl_status = "profit" if position.unrealized_pnl > 0 else "loss"
            assert pnl_status  # User sees status

        # Step 4: Execute exit
        exit_price = monitoring_prices[-1]
        exit_trade = portfolio.execute_trade(
            symbol=test_config.primary_symbol,
            direction=TradingDirection.SELL,
            quantity=100,
            price=exit_price,
        )

        # Verify trade completed
        assert portfolio.get_position(test_config.primary_symbol) is None
        assert exit_trade.pnl > 0  # Made profit

    @pytest.mark.asyncio
    async def test_stop_loss_triggered_journey(
        self,
        test_config: TestConfig,
    ) -> None:
        """
        Simulate stop-loss triggered journey.

        User story:
        As a trader, I want my stop-loss to protect me
        from excessive losses.
        """
        portfolio = PortfolioService(initial_cash=test_config.initial_cash)

        # Enter position with stop-loss
        portfolio.execute_trade(
            symbol=test_config.primary_symbol,
            direction=TradingDirection.BUY,
            quantity=100,
            price=test_config.base_price,
            stop_loss_pct=test_config.default_stop_loss,
        )

        # Price drops significantly
        drop_prices = [
            test_config.base_price * 0.98,  # -2%
            test_config.base_price * 0.95,  # -5%
            test_config.base_price * 0.90,  # -10%
        ]

        stop_triggered = False
        for price in drop_prices:
            portfolio.update_prices({test_config.primary_symbol: price})

            # Check stop-loss
            triggered = portfolio.check_stop_losses()
            if test_config.primary_symbol in triggered:
                stop_triggered = True

                # Execute stop-loss
                position = portfolio.get_position(test_config.primary_symbol)
                if position:
                    portfolio.execute_trade(
                        symbol=test_config.primary_symbol,
                        direction=TradingDirection.SELL,
                        quantity=position.quantity,
                        price=price,
                    )
                break

        # Stop should have triggered
        assert stop_triggered
        assert portfolio.get_position(test_config.primary_symbol) is None


class TestEndOfDayJourney:
    """User journey: End of day review."""

    @pytest.mark.asyncio
    async def test_end_of_day_review(
        self,
        test_config: TestConfig,
    ) -> None:
        """
        Simulate end of day portfolio review.

        User story:
        As a trader, I want to review my portfolio performance
        at the end of each trading day.
        """
        portfolio = PortfolioService(initial_cash=test_config.initial_cash)

        # Simulate day's trading
        trades_today = [
            (TradingDirection.BUY, 100, test_config.base_price),
            (TradingDirection.SELL, 50, test_config.base_price * 1.02),
            (TradingDirection.SELL, 50, test_config.base_price * 1.03),
        ]

        for direction, qty, price in trades_today:
            portfolio.execute_trade(
                symbol=test_config.primary_symbol,
                direction=direction,
                quantity=qty,
                price=price,
            )

        # End of day review
        state = portfolio.get_state()

        # User checks key metrics
        assert state.cash_balance is not None
        assert state.portfolio_value is not None
        assert state.realized_pnl_total is not None

        # Calculate Sharpe ratio
        sharpe = portfolio.calculate_sharpe_ratio()
        assert isinstance(sharpe, float)

        # Review shows profit from trades
        assert state.realized_pnl_total > 0


class TestMultiDayJourney:
    """User journey: Multi-day trading session."""

    @pytest.mark.asyncio
    async def test_multi_day_trading_session(
        self,
        test_settings: Settings,
        trading_state_factory: TradingStateFactory,
        test_config: TestConfig,
        action_space: ActionSpace,
    ) -> None:
        """
        Simulate multi-day trading session.

        User story:
        As a swing trader, I want to manage positions
        over multiple days.
        """
        portfolio = PortfolioService(initial_cash=test_config.initial_cash)

        # Simulate 5 trading days
        daily_prices = [
            test_config.base_price,
            test_config.base_price * 1.01,
            test_config.base_price * 0.99,
            test_config.base_price * 1.03,
            test_config.base_price * 1.05,
        ]

        position_opened = False

        for day, price in enumerate(daily_prices, 1):
            # Create state for the day
            state = trading_state_factory.create()
            state.current_price = price

            # Run analysis
            mcts_config = MCTSConfig(
                max_simulations=test_config.mcts_simulations // 2,
                rollout_horizon=test_config.mcts_rollout_horizon,
            )

            tree = MCTSTree(config=mcts_config)
            result = await tree.search(state, action_space)

            # Update prices
            portfolio.update_prices({test_config.primary_symbol: price})

            # Day 1: Open position based on recommendation
            if day == 1 and result.best_action:
                if result.best_action.direction == TradingDirection.BUY:
                    portfolio.execute_trade(
                        symbol=test_config.primary_symbol,
                        direction=TradingDirection.BUY,
                        quantity=100,
                        price=price,
                        stop_loss_pct=test_config.default_stop_loss,
                    )
                    position_opened = True

            # Day 5: Close position if open
            if day == 5 and position_opened:
                position = portfolio.get_position(test_config.primary_symbol)
                if position:
                    portfolio.execute_trade(
                        symbol=test_config.primary_symbol,
                        direction=TradingDirection.SELL,
                        quantity=position.quantity,
                        price=price,
                    )

        # Final review
        final_state = portfolio.get_state()
        assert final_state.portfolio_value >= 0

        # If position was opened and closed, should have some P&L
        if position_opened:
            assert final_state.realized_pnl_total != 0


class TestHybridArchitectureJourney:
    """User journey: Using hybrid architecture."""

    @pytest.mark.asyncio
    async def test_batch_then_realtime_journey(
        self,
        test_settings: Settings,
        trading_state_factory: TradingStateFactory,
        test_config: TestConfig,
    ) -> None:
        """
        Simulate using hybrid batch/realtime architecture.

        User story:
        As a systematic trader, I want to use pre-computed
        policies during the day for fast decisions.
        """
        hybrid = HybridTradingArchitecture(
            settings=test_settings,
            batch_simulations=test_config.mcts_simulations,
            realtime_simulations=test_config.mcts_simulations // 10,
        )

        # Morning: Batch compute policies for likely states
        morning_states = [
            trading_state_factory.create_for_scenario(scenario)
            for scenario in [TestScenario.BULLISH, TestScenario.BEARISH, TestScenario.NEUTRAL]
        ]

        # Pre-compute policies
        from reasoning_trading.workflow.hybrid import PolicyEntry
        from tests.factories import ActionFactory

        action_factory = ActionFactory(config=test_config)

        for state in morning_states:
            state_hash = hybrid._compute_state_hash(state)
            action = hybrid._heuristic_action(state)

            entry = PolicyEntry(
                action=action,
                value=0.5,
                confidence=action.confidence,
                computed_at=datetime.now(),
                expires_at=datetime.now() + timedelta(hours=8),
                state_hash=state_hash,
            )

            cache_key = f"policy:{test_config.primary_symbol}:{state_hash}"
            hybrid._local_cache[cache_key] = entry

        # During the day: Fast realtime lookups
        for _ in range(10):  # Simulate 10 decision points
            # Pick random state
            state = morning_states[np.random.randint(0, len(morning_states))]
            state_hash = hybrid._compute_state_hash(state)

            # Fast lookup
            cached = await hybrid._get_cached_policy(
                test_config.primary_symbol, state_hash
            )

            if cached:
                # Use cached policy
                action = cached.action
            else:
                # Fallback to heuristic
                action = hybrid._heuristic_action(state)

            assert action.direction in list(TradingDirection)


class TestMultiAgentJourney:
    """User journey: Using multi-agent system."""

    @pytest.mark.asyncio
    async def test_agent_consensus_journey(
        self,
        test_settings: Settings,
        trading_state_factory: TradingStateFactory,
    ) -> None:
        """
        Simulate getting consensus from multiple agents.

        User story:
        As a trader, I want multiple analysts to provide
        opinions before I make a decision.
        """
        coordinator = MultiAgentTradingMCTS(settings=test_settings)

        # Create market state
        state = trading_state_factory.create()

        # Get individual agent opinions
        results = await coordinator._gather_agent_recommendations(state)

        # User reviews each agent's recommendation
        agent_opinions: dict[str, TradingDirection] = {}
        for result in results:
            agent_opinions[result.agent_name] = result.action.direction

        # Get combined recommendation
        final_action = await coordinator.analyze(state)

        # User makes informed decision based on consensus
        assert final_action.direction in list(TradingDirection)
        assert final_action.confidence >= 0

        # User can see how agents voted
        assert len(agent_opinions) > 0
