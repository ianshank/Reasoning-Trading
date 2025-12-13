"""
MCTS rollout (simulation) engine for trading.

Implements trading-specific rollouts that simulate market scenarios
and evaluate strategy performance using risk-adjusted metrics.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import TYPE_CHECKING, Any, Protocol

import numpy as np
from numpy.typing import NDArray

if TYPE_CHECKING:
    from reasoning_trading.core.actions import TradingAction
    from reasoning_trading.core.state import TradingState
    from reasoning_trading.mcts.node import Node


class RewardFunction(str, Enum):
    """Available reward functions for rollout evaluation."""

    RAW_RETURNS = "raw_returns"
    SHARPE_RATIO = "sharpe_ratio"
    SORTINO_RATIO = "sortino_ratio"
    MAX_DRAWDOWN_PENALTY = "max_drawdown_penalty"
    RISK_ADJUSTED_RETURNS = "risk_adjusted_returns"


class MarketSimulator(Protocol):
    """Protocol for market simulation engines."""

    async def step(
        self,
        state: TradingState,
        action: TradingAction,
    ) -> tuple[TradingState, float]:
        """
        Simulate one step in the market.

        Args:
            state: Current trading state
            action: Action to execute

        Returns:
            Tuple of (new_state, immediate_reward)
        """
        ...

    def reset(self, initial_state: TradingState) -> TradingState:
        """Reset simulation to initial state."""
        ...


@dataclass
class RolloutResult:
    """Result of a rollout simulation."""

    total_return: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    max_drawdown: float = 0.0
    num_trades: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0

    # Detailed history
    returns_history: list[float] = field(default_factory=list)
    portfolio_values: list[float] = field(default_factory=list)
    actions_taken: list[TradingAction] = field(default_factory=list)

    # Metadata
    simulation_steps: int = 0
    terminal_reason: str = ""

    @property
    def annualized_sharpe(self) -> float:
        """Annualize the Sharpe ratio (assuming 252 trading days)."""
        return self.sharpe_ratio * np.sqrt(252)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "total_return": self.total_return,
            "sharpe_ratio": self.sharpe_ratio,
            "sortino_ratio": self.sortino_ratio,
            "max_drawdown": self.max_drawdown,
            "num_trades": self.num_trades,
            "win_rate": self.win_rate,
            "profit_factor": self.profit_factor,
            "annualized_sharpe": self.annualized_sharpe,
            "simulation_steps": self.simulation_steps,
            "terminal_reason": self.terminal_reason,
        }


class RolloutEngine(ABC):
    """Abstract base class for rollout engines."""

    @abstractmethod
    async def rollout(self, node: Node, depth: int) -> float:
        """
        Execute rollout from given node.

        Args:
            node: Node to start rollout from
            depth: Maximum rollout depth

        Returns:
            Rollout value (reward signal)
        """
        pass


@dataclass
class TradingRollout(RolloutEngine):
    """
    Trading-specific MCTS rollout engine.

    Simulates trading to horizon and returns risk-adjusted reward.
    Supports multiple reward functions and market simulation modes.
    """

    # Simulation parameters
    horizon_days: int = 30
    max_steps: int = 1000
    discount_factor: float = 0.99

    # Reward configuration
    reward_function: RewardFunction = RewardFunction.SHARPE_RATIO
    drawdown_lambda: float = 1.0  # Penalty weight for drawdown

    # Market simulation
    market_simulator: MarketSimulator | None = None

    # Transaction costs
    commission_rate: float = 0.001  # 0.1% per trade
    slippage_rate: float = 0.0005  # 0.05% slippage

    async def rollout(self, node: Node, depth: int | None = None) -> float:
        """
        Execute trading rollout simulation.

        Args:
            node: Starting node with trading state
            depth: Maximum rollout depth (defaults to horizon_days)

        Returns:
            Risk-adjusted reward (Sharpe ratio by default)
        """
        if node.state is None:
            return 0.0

        actual_depth = depth if depth is not None else self.horizon_days
        result = await self._simulate_trading(node.state, actual_depth)

        return self._compute_reward(result)

    async def _simulate_trading(
        self,
        initial_state: TradingState,
        horizon: int,
    ) -> RolloutResult:
        """
        Run trading simulation for given horizon.

        Args:
            initial_state: Starting state
            horizon: Number of steps to simulate

        Returns:
            RolloutResult with performance metrics
        """
        state = initial_state.copy()
        result = RolloutResult()
        result.portfolio_values.append(state.portfolio.portfolio_value)

        peak_value = state.portfolio.portfolio_value
        current_drawdown = 0.0

        for step in range(min(horizon, self.max_steps)):
            if state.is_terminal:
                result.terminal_reason = "terminal_state"
                break

            # Get action (from policy or default)
            action = await self._get_rollout_action(state)

            if action is None:
                result.terminal_reason = "no_action"
                break

            # Simulate market step
            if self.market_simulator is not None:
                state, immediate_reward = await self.market_simulator.step(state, action)
            else:
                # Use simple simulation if no simulator provided
                state, immediate_reward = self._simple_market_step(state, action)

            # Track returns
            result.returns_history.append(immediate_reward)
            result.portfolio_values.append(state.portfolio.portfolio_value)
            result.actions_taken.append(action)

            # Track drawdown
            if state.portfolio.portfolio_value > peak_value:
                peak_value = state.portfolio.portfolio_value
            current_drawdown = (
                peak_value - state.portfolio.portfolio_value
            ) / peak_value
            result.max_drawdown = max(result.max_drawdown, current_drawdown)

            # Count trades
            if action.direction.is_entry():
                result.num_trades += 1

            result.simulation_steps += 1

        # Calculate final metrics
        self._compute_metrics(result)

        return result

    async def _get_rollout_action(self, state: TradingState) -> TradingAction | None:
        """
        Get action for rollout policy.

        Default implementation uses a simple random policy.
        Override for more sophisticated policies.
        """
        from reasoning_trading.core.actions import (
            ActionSpace,
            TradingAction,
            TradingDirection,
        )

        # Simple heuristic policy based on analyst signals
        consensus = state.analyst_signals.weighted_consensus()

        if consensus > 0.3:
            direction = TradingDirection.BUY
        elif consensus < -0.3:
            direction = TradingDirection.SELL
        else:
            direction = TradingDirection.HOLD

        action_space = ActionSpace()
        return TradingAction(
            direction=direction,
            position_size=action_space.sample_position_size(),
            stop_loss=action_space.sample_stop_loss(),
            time_horizon=action_space.time_horizons[2],  # 1D default
            confidence=abs(consensus),
        )

    def _simple_market_step(
        self,
        state: TradingState,
        action: TradingAction,
    ) -> tuple[TradingState, float]:
        """
        Simple market simulation step.

        Uses geometric Brownian motion for price simulation.
        """
        from reasoning_trading.core.actions import TradingDirection

        new_state = state.copy()

        # Simulate price change (GBM-like)
        # Get volatility from state or use default
        volatility = 0.02  # 2% daily volatility default
        if state.technical_indicators.volatility_20 is not None:
            volatility = state.technical_indicators.volatility_20

        drift = 0.0001  # Small positive drift
        random_return = np.random.normal(drift, volatility)
        new_price = state.current_price * (1 + random_return)

        # Update state
        new_state.current_price = new_price
        new_state.simulation_step += 1

        # Calculate P&L based on action
        position_value = (
            state.portfolio.get_position_size(state.symbol) * state.current_price
        )

        pnl = 0.0
        if action.direction == TradingDirection.BUY and position_value > 0:
            pnl = position_value * random_return
        elif action.direction in (TradingDirection.SELL, TradingDirection.SHORT):
            pnl = -position_value * random_return

        # Apply transaction costs
        if action.direction.is_entry():
            trade_value = action.position_size.size_fraction * state.portfolio.portfolio_value
            transaction_cost = trade_value * (self.commission_rate + self.slippage_rate)
            pnl -= transaction_cost

        # Update portfolio
        new_state.portfolio.unrealized_pnl += pnl
        new_state.portfolio.portfolio_value = (
            state.portfolio.portfolio_value + pnl
        )

        # Check stop-loss
        if position_value > 0:
            loss_pct = (state.current_price - new_price) / state.current_price
            if loss_pct > action.stop_loss.stop_loss_pct:
                new_state.is_terminal = True

        # Calculate immediate reward as percentage return
        immediate_reward = pnl / max(state.portfolio.portfolio_value, 1.0)

        return new_state, immediate_reward

    def _compute_metrics(self, result: RolloutResult) -> None:
        """Compute final performance metrics."""
        if not result.returns_history:
            return

        returns = np.array(result.returns_history)

        # Total return
        result.total_return = np.sum(returns)

        # Sharpe ratio
        if len(returns) > 1:
            mean_return = np.mean(returns)
            std_return = np.std(returns)
            if std_return > 0:
                result.sharpe_ratio = mean_return / std_return
            else:
                result.sharpe_ratio = mean_return * 10 if mean_return > 0 else 0

        # Sortino ratio (downside deviation only)
        if len(returns) > 1:
            negative_returns = returns[returns < 0]
            if len(negative_returns) > 0:
                downside_std = np.std(negative_returns)
                if downside_std > 0:
                    result.sortino_ratio = np.mean(returns) / downside_std
            else:
                result.sortino_ratio = result.sharpe_ratio * 1.5  # Bonus for no downside

        # Win rate
        winning_trades = sum(1 for r in returns if r > 0)
        total_trades = sum(1 for r in returns if r != 0)
        if total_trades > 0:
            result.win_rate = winning_trades / total_trades

        # Profit factor
        gross_profit = sum(r for r in returns if r > 0)
        gross_loss = abs(sum(r for r in returns if r < 0))
        if gross_loss > 0:
            result.profit_factor = gross_profit / gross_loss
        elif gross_profit > 0:
            result.profit_factor = 10.0  # Cap at 10 if no losses

    def _compute_reward(self, result: RolloutResult) -> float:
        """
        Compute final reward based on configured reward function.

        Args:
            result: RolloutResult with computed metrics

        Returns:
            Scalar reward value
        """
        if self.reward_function == RewardFunction.RAW_RETURNS:
            return result.total_return

        elif self.reward_function == RewardFunction.SHARPE_RATIO:
            return result.annualized_sharpe

        elif self.reward_function == RewardFunction.SORTINO_RATIO:
            return result.sortino_ratio * np.sqrt(252)

        elif self.reward_function == RewardFunction.MAX_DRAWDOWN_PENALTY:
            return result.total_return - self.drawdown_lambda * result.max_drawdown

        elif self.reward_function == RewardFunction.RISK_ADJUSTED_RETURNS:
            # Combine Sharpe with drawdown penalty
            sharpe_component = result.annualized_sharpe
            drawdown_penalty = self.drawdown_lambda * result.max_drawdown
            return sharpe_component - drawdown_penalty

        else:
            return result.total_return


@dataclass
class BatchRollout:
    """
    Batch rollout engine for parallel simulation.

    Runs multiple rollouts concurrently for efficiency.
    """

    rollout_engine: TradingRollout
    num_parallel: int = 8

    async def run_batch(
        self,
        node: Node,
        num_rollouts: int,
        depth: int | None = None,
    ) -> list[float]:
        """
        Run multiple rollouts in parallel.

        Args:
            node: Starting node
            num_rollouts: Number of rollouts to run
            depth: Maximum rollout depth

        Returns:
            List of rollout values
        """
        tasks = []
        for _ in range(num_rollouts):
            tasks.append(self.rollout_engine.rollout(node, depth))

        # Run in batches to avoid overwhelming resources
        results = []
        for i in range(0, len(tasks), self.num_parallel):
            batch = tasks[i : i + self.num_parallel]
            batch_results = await asyncio.gather(*batch)
            results.extend(batch_results)

        return results

    async def mean_rollout_value(
        self,
        node: Node,
        num_rollouts: int = 10,
        depth: int | None = None,
    ) -> float:
        """
        Get mean value across multiple rollouts.

        Args:
            node: Starting node
            num_rollouts: Number of rollouts to average
            depth: Maximum rollout depth

        Returns:
            Mean rollout value
        """
        values = await self.run_batch(node, num_rollouts, depth)
        return float(np.mean(values))
