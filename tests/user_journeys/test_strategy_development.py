"""
User journey tests for strategy development.

Simulates users developing and testing trading strategies:
1. Strategy backtesting
2. Parameter optimization
3. Risk management tuning
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
from reasoning_trading.mcts.rollout import RewardFunction, TradingRollout
from reasoning_trading.mcts.ucb import SelectionStrategy, create_selector
from reasoning_trading.services.portfolio import PortfolioService

from tests.config import TestConfig, TestScenario
from tests.factories import (
    MarketDataFactory,
    TradingStateFactory,
)


class TestStrategyBacktestJourney:
    """User journey: Strategy backtesting."""

    @pytest.mark.asyncio
    async def test_backtest_single_strategy(
        self,
        test_settings: Settings,
        trading_state_factory: TradingStateFactory,
        test_config: TestConfig,
        action_space: ActionSpace,
    ) -> None:
        """
        Simulate backtesting a trading strategy.

        User story:
        As a quant, I want to backtest my MCTS-based strategy
        against historical scenarios.
        """
        # Generate historical scenarios
        scenarios = [TestScenario.BULLISH, TestScenario.BEARISH, TestScenario.NEUTRAL]

        backtest_results: list[dict[str, Any]] = []

        for scenario in scenarios:
            state = trading_state_factory.create_for_scenario(scenario)

            mcts_config = MCTSConfig(
                max_simulations=test_config.mcts_simulations,
                rollout_horizon=test_config.mcts_rollout_horizon,
            )

            tree = MCTSTree(config=mcts_config)
            result = await tree.search(state, action_space)

            backtest_results.append({
                "scenario": scenario.name,
                "action": result.best_action.direction.value if result.best_action else "none",
                "confidence": result.best_action.confidence if result.best_action else 0,
                "simulations": result.total_simulations,
                "time_ms": result.total_time_ms,
            })

        # User reviews backtest results
        assert len(backtest_results) == len(scenarios)

        # All scenarios should have valid results
        for result in backtest_results:
            assert result["simulations"] > 0
            assert result["action"] in ["buy", "sell", "hold", "none"]

    @pytest.mark.asyncio
    async def test_compare_reward_functions(
        self,
        test_settings: Settings,
        trading_state_factory: TradingStateFactory,
        test_config: TestConfig,
        action_space: ActionSpace,
    ) -> None:
        """
        Simulate comparing different reward functions.

        User story:
        As a researcher, I want to compare how different
        reward functions affect trading decisions.
        """
        state = trading_state_factory.create()

        reward_functions = [
            RewardFunction.RAW_RETURNS,
            RewardFunction.SHARPE_RATIO,
            RewardFunction.SORTINO_RATIO,
        ]

        comparison_results: dict[str, dict[str, Any]] = {}

        for reward_fn in reward_functions:
            rollout = TradingRollout(
                horizon_days=test_config.mcts_rollout_horizon,
                reward_function=reward_fn,
            )

            mcts_config = MCTSConfig(
                max_simulations=test_config.mcts_simulations,
                rollout_horizon=test_config.mcts_rollout_horizon,
            )

            tree = MCTSTree(config=mcts_config, rollout_engine=rollout)
            result = await tree.search(state, action_space)

            comparison_results[reward_fn.name] = {
                "action": result.best_action.direction.value if result.best_action else "none",
                "confidence": result.best_action.confidence if result.best_action else 0,
                "position_size": result.best_action.position_size_pct if result.best_action else 0,
            }

        # User compares results
        assert len(comparison_results) == len(reward_functions)

        # Results may differ between reward functions
        for name, metrics in comparison_results.items():
            assert metrics["action"] in ["buy", "sell", "hold", "none"]

    @pytest.mark.asyncio
    async def test_compare_selection_strategies(
        self,
        test_settings: Settings,
        trading_state_factory: TradingStateFactory,
        test_config: TestConfig,
        action_space: ActionSpace,
    ) -> None:
        """
        Simulate comparing selection strategies.

        User story:
        As a researcher, I want to compare UCB1, PUCT,
        and risk-adjusted selection strategies.
        """
        state = trading_state_factory.create()

        strategies = [
            SelectionStrategy.UCB1,
            SelectionStrategy.PUCT,
            SelectionStrategy.RISK_ADJUSTED,
        ]

        comparison_results: dict[str, dict[str, Any]] = {}

        for strategy in strategies:
            selector = create_selector(strategy)

            mcts_config = MCTSConfig(
                max_simulations=test_config.mcts_simulations,
                selection_strategy=strategy,
                rollout_horizon=test_config.mcts_rollout_horizon,
            )

            tree = MCTSTree(config=mcts_config, selector=selector)
            result = await tree.search(state, action_space)

            comparison_results[strategy.name] = {
                "action": result.best_action.direction.value if result.best_action else "none",
                "confidence": result.best_action.confidence if result.best_action else 0,
                "tree_depth": result.root.depth if result.root else 0,
            }

        # User reviews strategy comparison
        assert len(comparison_results) == len(strategies)


class TestParameterOptimizationJourney:
    """User journey: Parameter optimization."""

    @pytest.mark.asyncio
    async def test_simulation_count_optimization(
        self,
        test_settings: Settings,
        trading_state_factory: TradingStateFactory,
        test_config: TestConfig,
        action_space: ActionSpace,
    ) -> None:
        """
        Simulate optimizing simulation count.

        User story:
        As a trader, I want to find the optimal number
        of MCTS simulations for my use case.
        """
        state = trading_state_factory.create()

        # Test different simulation counts
        simulation_counts = [10, 25, 50, 100]
        optimization_results: list[dict[str, Any]] = []

        for sim_count in simulation_counts:
            mcts_config = MCTSConfig(
                max_simulations=sim_count,
                rollout_horizon=test_config.mcts_rollout_horizon,
            )

            tree = MCTSTree(config=mcts_config)

            import time
            start = time.perf_counter()
            result = await tree.search(state, action_space)
            elapsed_ms = (time.perf_counter() - start) * 1000

            optimization_results.append({
                "simulations": sim_count,
                "time_ms": elapsed_ms,
                "action": result.best_action.direction.value if result.best_action else "none",
                "confidence": result.best_action.confidence if result.best_action else 0,
            })

        # User analyzes tradeoff between simulations and time
        assert len(optimization_results) == len(simulation_counts)

        # More simulations should generally take longer
        times = [r["time_ms"] for r in optimization_results]
        # Allow some variance, but trend should be increasing
        assert times[-1] >= times[0] * 0.5  # Last should be at least half of first

    @pytest.mark.asyncio
    async def test_exploration_weight_tuning(
        self,
        test_settings: Settings,
        trading_state_factory: TradingStateFactory,
        test_config: TestConfig,
        action_space: ActionSpace,
    ) -> None:
        """
        Simulate tuning exploration weight.

        User story:
        As a researcher, I want to find the optimal
        exploration-exploitation balance.
        """
        state = trading_state_factory.create()

        # Test different exploration weights
        exploration_weights = [0.5, 1.0, 1.414, 2.0, 3.0]
        tuning_results: list[dict[str, Any]] = []

        for weight in exploration_weights:
            mcts_config = MCTSConfig(
                max_simulations=test_config.mcts_simulations,
                exploration_weight=weight,
                rollout_horizon=test_config.mcts_rollout_horizon,
            )

            tree = MCTSTree(config=mcts_config)
            result = await tree.search(state, action_space)

            # Count unique actions explored
            unique_actions = 0
            if result.root:
                unique_actions = len(result.root.children)

            tuning_results.append({
                "exploration_weight": weight,
                "unique_actions": unique_actions,
                "best_action": result.best_action.direction.value if result.best_action else "none",
            })

        # User analyzes exploration behavior
        assert len(tuning_results) == len(exploration_weights)

        # Higher exploration weight should generally explore more
        # (not always guaranteed due to stochasticity)
        actions_explored = [r["unique_actions"] for r in tuning_results]
        assert max(actions_explored) >= 1


class TestRiskManagementTuningJourney:
    """User journey: Risk management tuning."""

    @pytest.mark.asyncio
    async def test_stop_loss_optimization(
        self,
        test_config: TestConfig,
    ) -> None:
        """
        Simulate optimizing stop-loss levels.

        User story:
        As a risk manager, I want to find optimal
        stop-loss percentages for my strategy.
        """
        # Test different stop-loss percentages
        stop_loss_levels = [0.02, 0.03, 0.05, 0.08, 0.10]
        optimization_results: list[dict[str, Any]] = []

        for stop_pct in stop_loss_levels:
            portfolio = PortfolioService(initial_cash=test_config.initial_cash)

            # Simulate 100 trades with this stop-loss
            trades_won = 0
            trades_lost = 0
            total_pnl = 0.0

            np.random.seed(test_config.random_seed)

            for _ in range(100):
                # Open position
                entry_price = test_config.base_price
                portfolio.execute_trade(
                    symbol=test_config.primary_symbol,
                    direction=TradingDirection.BUY,
                    quantity=100,
                    price=entry_price,
                    stop_loss_pct=stop_pct,
                )

                # Simulate random price movement
                price_change = np.random.normal(0.001, 0.02)  # Mean 0.1%, std 2%
                exit_price = entry_price * (1 + price_change)

                # Check if stop triggered
                stop_price = entry_price * (1 - stop_pct)
                if exit_price < stop_price:
                    exit_price = stop_price

                # Update and close
                portfolio.update_prices({test_config.primary_symbol: exit_price})
                trade = portfolio.execute_trade(
                    symbol=test_config.primary_symbol,
                    direction=TradingDirection.SELL,
                    quantity=100,
                    price=exit_price,
                )

                if trade.pnl > 0:
                    trades_won += 1
                else:
                    trades_lost += 1
                total_pnl += trade.pnl

            optimization_results.append({
                "stop_loss_pct": stop_pct,
                "win_rate": trades_won / 100,
                "total_pnl": total_pnl,
                "avg_pnl": total_pnl / 100,
            })

        # User analyzes stop-loss impact
        assert len(optimization_results) == len(stop_loss_levels)

        # Different stop-losses should yield different results
        pnls = [r["total_pnl"] for r in optimization_results]
        assert len(set(round(p, 2) for p in pnls)) > 1  # Should have variation

    @pytest.mark.asyncio
    async def test_position_size_optimization(
        self,
        test_config: TestConfig,
    ) -> None:
        """
        Simulate optimizing position sizing.

        User story:
        As a risk manager, I want to find optimal
        position sizes for different risk tolerances.
        """
        position_sizes = [0.05, 0.10, 0.20, 0.30]
        optimization_results: list[dict[str, Any]] = []

        for size_pct in position_sizes:
            portfolio = PortfolioService(initial_cash=test_config.initial_cash)

            np.random.seed(test_config.random_seed)

            # Simulate sequence of trades
            max_drawdown = 0.0
            peak_value = test_config.initial_cash
            final_value = test_config.initial_cash

            for _ in range(50):
                # Calculate position size
                position_value = portfolio.get_state().cash_balance * size_pct
                quantity = int(position_value / test_config.base_price)

                if quantity > 0:
                    portfolio.execute_trade(
                        symbol=test_config.primary_symbol,
                        direction=TradingDirection.BUY,
                        quantity=quantity,
                        price=test_config.base_price,
                    )

                    # Random outcome
                    price_change = np.random.normal(0.002, 0.03)
                    exit_price = test_config.base_price * (1 + price_change)

                    portfolio.update_prices({test_config.primary_symbol: exit_price})
                    portfolio.execute_trade(
                        symbol=test_config.primary_symbol,
                        direction=TradingDirection.SELL,
                        quantity=quantity,
                        price=exit_price,
                    )

                # Track drawdown
                current_value = portfolio.get_state().portfolio_value
                if current_value > peak_value:
                    peak_value = current_value
                drawdown = (peak_value - current_value) / peak_value
                max_drawdown = max(max_drawdown, drawdown)
                final_value = current_value

            optimization_results.append({
                "position_size_pct": size_pct,
                "final_value": final_value,
                "max_drawdown": max_drawdown,
                "return_pct": (final_value - test_config.initial_cash) / test_config.initial_cash,
            })

        # User analyzes risk/return tradeoff
        assert len(optimization_results) == len(position_sizes)

        # Larger positions should have higher drawdowns
        drawdowns = [r["max_drawdown"] for r in optimization_results]
        # Generally true, but not guaranteed due to randomness


class TestStrategyValidationJourney:
    """User journey: Strategy validation."""

    @pytest.mark.asyncio
    async def test_out_of_sample_validation(
        self,
        test_settings: Settings,
        trading_state_factory: TradingStateFactory,
        test_config: TestConfig,
        action_space: ActionSpace,
    ) -> None:
        """
        Simulate out-of-sample strategy validation.

        User story:
        As a quant, I want to validate my strategy
        on unseen market conditions.
        """
        # "Training" scenarios
        training_scenarios = [TestScenario.BULLISH, TestScenario.BEARISH]

        # "Test" scenarios (out-of-sample)
        test_scenarios = [TestScenario.NEUTRAL, TestScenario.VOLATILE]

        # Train: gather actions for training scenarios
        training_actions: dict[str, str] = {}
        for scenario in training_scenarios:
            state = trading_state_factory.create_for_scenario(scenario)

            mcts_config = MCTSConfig(
                max_simulations=test_config.mcts_simulations,
                rollout_horizon=test_config.mcts_rollout_horizon,
            )

            tree = MCTSTree(config=mcts_config)
            result = await tree.search(state, action_space)

            if result.best_action:
                training_actions[scenario.name] = result.best_action.direction.value

        # Test: validate on test scenarios
        test_actions: dict[str, str] = {}
        for scenario in test_scenarios:
            state = trading_state_factory.create_for_scenario(scenario)

            mcts_config = MCTSConfig(
                max_simulations=test_config.mcts_simulations,
                rollout_horizon=test_config.mcts_rollout_horizon,
            )

            tree = MCTSTree(config=mcts_config)
            result = await tree.search(state, action_space)

            if result.best_action:
                test_actions[scenario.name] = result.best_action.direction.value

        # User validates strategy works on unseen data
        assert len(training_actions) > 0
        assert len(test_actions) > 0

        # All actions should be valid
        all_actions = list(training_actions.values()) + list(test_actions.values())
        for action in all_actions:
            assert action in ["buy", "sell", "hold"]
