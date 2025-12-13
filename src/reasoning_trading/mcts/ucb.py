"""
UCB (Upper Confidence Bound) selection strategies for MCTS.

Implements various selection strategies including UCB1, PUCT, and
trading-specific adaptations that account for risk-adjusted returns.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from reasoning_trading.mcts.node import Node


class SelectionStrategy(str, Enum):
    """Available UCB selection strategies."""

    UCB1 = "ucb1"  # Classic UCB1
    PUCT = "puct"  # AlphaGo-style with prior
    UCB_TUNED = "ucb_tuned"  # Variance-aware UCB
    RISK_ADJUSTED = "risk_adjusted"  # Trading-specific


class UCBSelector(ABC):
    """Abstract base class for UCB selection strategies."""

    @abstractmethod
    def select(self, node: Node) -> Node | None:
        """
        Select best child of the given node.

        Args:
            node: Parent node to select from

        Returns:
            Selected child node or None if no children
        """
        pass

    @abstractmethod
    def score(self, node: Node) -> float:
        """
        Calculate selection score for a node.

        Args:
            node: Node to score

        Returns:
            UCB score (higher is better)
        """
        pass


@dataclass
class UCB1Selector(UCBSelector):
    """
    Classic UCB1 selection strategy.

    Uses the formula: Q(s,a) + c * sqrt(ln(N(s)) / N(s,a))
    """

    exploration_constant: float = 1.414  # sqrt(2)

    def score(self, node: Node) -> float:
        """Calculate UCB1 score."""
        if node.visits == 0:
            return float("inf")

        if node.parent is None or node.parent.visits == 0:
            return node.mean_value

        exploitation = node.mean_value
        exploration = self.exploration_constant * math.sqrt(
            math.log(node.parent.visits) / node.visits
        )

        return exploitation + exploration

    def select(self, node: Node) -> Node | None:
        """Select child with highest UCB1 score."""
        if not node.children:
            return None
        return max(node.children, key=self.score)


@dataclass
class PUCTSelector(UCBSelector):
    """
    PUCT (Predictor Upper Confidence Tree) selection.

    Used in AlphaGo/AlphaZero with neural network priors:
    Q(s,a) + c_puct * P(s,a) * sqrt(N(s)) / (1 + N(s,a))
    """

    c_puct: float = 1.0
    fpu_reduction: float = 0.0  # First Play Urgency reduction

    def score(self, node: Node) -> float:
        """Calculate PUCT score."""
        if node.parent is None:
            return node.mean_value

        # First Play Urgency: unvisited nodes get reduced parent value
        if node.visits == 0:
            parent_q = node.parent.mean_value if node.parent.visits > 0 else 0.0
            q_value = parent_q - self.fpu_reduction
        else:
            q_value = node.mean_value

        # Prior bonus
        u_value = (
            self.c_puct * node.prior * math.sqrt(node.parent.visits) / (1 + node.visits)
        )

        return q_value + u_value

    def select(self, node: Node) -> Node | None:
        """Select child with highest PUCT score."""
        if not node.children:
            return None
        return max(node.children, key=self.score)


@dataclass
class UCBTunedSelector(UCBSelector):
    """
    UCB-Tuned selection with variance estimation.

    More sophisticated exploration that considers reward variance:
    Q(s,a) + sqrt(ln(N(s)) / N(s,a) * min(1/4, V(s,a)))

    where V(s,a) is the variance of rewards plus exploration bonus.
    """

    def score(self, node: Node) -> float:
        """Calculate UCB-Tuned score."""
        if node.visits == 0:
            return float("inf")

        if node.parent is None or node.parent.visits == 0:
            return node.mean_value

        n = node.visits
        n_parent = node.parent.visits
        mean = node.mean_value

        # Estimate variance (using upper bound for variance)
        # V = sigma^2 + sqrt(2 * ln(n_parent) / n)
        # We approximate sigma^2 as mean * (1 - mean) for bounded rewards
        variance_estimate = mean * (1 - mean) if 0 <= mean <= 1 else 0.25
        variance_bonus = math.sqrt(2 * math.log(n_parent) / n)
        v_bound = min(0.25, variance_estimate + variance_bonus)

        exploration = math.sqrt(math.log(n_parent) / n * v_bound)

        return mean + exploration

    def select(self, node: Node) -> Node | None:
        """Select child with highest UCB-Tuned score."""
        if not node.children:
            return None
        return max(node.children, key=self.score)


@dataclass
class RiskAdjustedSelector(UCBSelector):
    """
    Risk-adjusted selection strategy for trading.

    Incorporates Sharpe ratio optimization into selection:
    - Penalizes high variance actions
    - Accounts for drawdown risk
    - Uses risk profile to adjust exploration/exploitation
    """

    base_exploration: float = 1.414
    risk_aversion: float = 0.5  # Higher = more risk-averse
    drawdown_penalty: float = 2.0  # Penalty multiplier for drawdown

    def score(self, node: Node) -> float:
        """
        Calculate risk-adjusted UCB score.

        The score balances expected return with risk considerations:
        score = Q - risk_aversion * variance + exploration_bonus - drawdown_penalty
        """
        if node.visits == 0:
            return float("inf")

        if node.parent is None or node.parent.visits == 0:
            return node.mean_value

        # Base exploitation term
        exploitation = node.mean_value

        # Variance penalty (estimate from visit count)
        # More visits = lower uncertainty about value
        variance_penalty = self.risk_aversion / math.sqrt(node.visits)

        # Exploration bonus
        exploration = self.base_exploration * math.sqrt(
            math.log(node.parent.visits) / node.visits
        )

        # Drawdown penalty based on action (if available)
        drawdown_penalty = 0.0
        if node.action is not None and node.state is not None:
            # Penalize actions that could lead to large drawdowns
            position_risk = node.action.position_size.size_fraction
            stop_loss = node.action.stop_loss.stop_loss_pct
            potential_loss = position_risk * stop_loss
            drawdown_penalty = self.drawdown_penalty * potential_loss

        return exploitation - variance_penalty + exploration - drawdown_penalty

    def select(self, node: Node) -> Node | None:
        """Select child with highest risk-adjusted score."""
        if not node.children:
            return None
        return max(node.children, key=self.score)


def create_selector(
    strategy: SelectionStrategy = SelectionStrategy.UCB1,
    **kwargs: float,
) -> UCBSelector:
    """
    Factory function to create UCB selector.

    Args:
        strategy: Selection strategy to use
        **kwargs: Strategy-specific parameters

    Returns:
        Configured UCB selector
    """
    selectors = {
        SelectionStrategy.UCB1: UCB1Selector,
        SelectionStrategy.PUCT: PUCTSelector,
        SelectionStrategy.UCB_TUNED: UCBTunedSelector,
        SelectionStrategy.RISK_ADJUSTED: RiskAdjustedSelector,
    }

    selector_class = selectors.get(strategy)
    if selector_class is None:
        raise ValueError(f"Unknown selection strategy: {strategy}")

    return selector_class(**kwargs)
