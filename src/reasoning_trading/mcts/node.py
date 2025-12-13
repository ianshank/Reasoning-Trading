"""
MCTS Node implementation for trading decisions.

Each node represents a trading state with associated statistics for
guiding tree search, following the LATS (Language Agent Tree Search)
architecture from LangChain.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from langchain_core.messages import BaseMessage

if TYPE_CHECKING:
    from reasoning_trading.core.actions import TradingAction
    from reasoning_trading.core.state import TradingState


@dataclass
class Node:
    """
    MCTS tree node for trading decisions.

    Stores the state, action that led to this state, and statistics
    needed for UCB selection and value backpropagation.
    """

    # Unique identifier
    id: str = field(default_factory=lambda: str(uuid4()))

    # State representation
    state: TradingState | None = None

    # Action that led to this state (None for root)
    action: TradingAction | None = None

    # Tree structure
    parent: Node | None = None
    children: list[Node] = field(default_factory=list)

    # Conversation history (for LLM context)
    messages: list[BaseMessage] = field(default_factory=list)

    # Self-evaluation from LLM
    reflection: str = ""

    # Value estimation (Sharpe ratio scale, typically -3 to 3)
    value: float = 0.0

    # Visit statistics
    visits: int = 0
    value_sum: float = 0.0

    # Q-value for action selection (cumulative discounted reward)
    q_value: float = 0.0

    # Prior probability from policy network (0-1)
    prior: float = 0.0

    # Terminal state flag
    is_solved: bool = False
    is_terminal: bool = False

    # Metadata
    depth: int = 0
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        """Initialize depth based on parent."""
        if self.parent is not None:
            self.depth = self.parent.depth + 1

    @property
    def is_leaf(self) -> bool:
        """Check if this is a leaf node (no children)."""
        return len(self.children) == 0

    @property
    def is_root(self) -> bool:
        """Check if this is the root node."""
        return self.parent is None

    @property
    def mean_value(self) -> float:
        """Calculate mean value across visits."""
        if self.visits == 0:
            return 0.0
        return self.value_sum / self.visits

    @property
    def ucb_value(self) -> float:
        """
        Calculate UCB1 value for node selection.

        Uses the formula: Q(s,a) + c * sqrt(ln(N(s)) / N(s,a))
        where c is the exploration constant (typically sqrt(2)).
        """
        if self.visits == 0:
            return float("inf")

        if self.parent is None or self.parent.visits == 0:
            return self.mean_value

        exploration_constant = math.sqrt(2)
        exploitation = self.mean_value
        exploration = exploration_constant * math.sqrt(
            math.log(self.parent.visits) / self.visits
        )

        return exploitation + exploration

    def ucb_with_prior(self, c_puct: float = 1.0) -> float:
        """
        Calculate PUCT (Predictor + UCB) value with prior probability.

        Used when a policy network provides action priors:
        Q(s,a) + c_puct * P(s,a) * sqrt(N(s)) / (1 + N(s,a))

        Args:
            c_puct: Exploration constant for PUCT

        Returns:
            PUCT value for this node
        """
        if self.parent is None:
            return self.mean_value

        u_value = (
            c_puct * self.prior * math.sqrt(self.parent.visits) / (1 + self.visits)
        )

        return self.mean_value + u_value

    def expand(
        self,
        action: TradingAction,
        new_state: TradingState,
        prior: float = 0.0,
        messages: list[BaseMessage] | None = None,
    ) -> Node:
        """
        Expand this node with a new child.

        Args:
            action: Action taken to reach new state
            new_state: Resulting state after action
            prior: Prior probability from policy network
            messages: Conversation history for LLM context

        Returns:
            New child node
        """
        child = Node(
            state=new_state,
            action=action,
            parent=self,
            prior=prior,
            messages=messages or [],
        )
        self.children.append(child)
        return child

    def backpropagate(self, value: float, discount: float = 0.99) -> None:
        """
        Backpropagate value up the tree.

        Args:
            value: Value to propagate (Sharpe ratio or other reward)
            discount: Discount factor for future rewards
        """
        node: Node | None = self
        current_value = value

        while node is not None:
            node.visits += 1
            node.value_sum += current_value
            node.value = node.mean_value

            # Update Q-value with discounting
            if node.visits == 1:
                node.q_value = current_value
            else:
                # Incremental mean update
                node.q_value += (current_value - node.q_value) / node.visits

            # Apply discount for parent
            current_value *= discount
            node = node.parent

    def best_child(self, exploration_weight: float = 1.414) -> Node | None:
        """
        Select best child using UCB1.

        Args:
            exploration_weight: Exploration constant (sqrt(2) by default)

        Returns:
            Best child node or None if no children
        """
        if not self.children:
            return None

        def ucb_score(child: Node) -> float:
            if child.visits == 0:
                return float("inf")

            exploitation = child.mean_value
            exploration = exploration_weight * math.sqrt(
                math.log(self.visits) / child.visits
            )
            return exploitation + exploration

        return max(self.children, key=ucb_score)

    def best_action_child(self) -> Node | None:
        """
        Select best child by visit count (for final action selection).

        Returns:
            Most visited child node
        """
        if not self.children:
            return None

        return max(self.children, key=lambda c: c.visits)

    def most_confident_child(self) -> Node | None:
        """
        Select child with highest value (most confident action).

        Returns:
            Child with highest mean value
        """
        if not self.children:
            return None

        return max(self.children, key=lambda c: c.mean_value)

    def get_path_to_root(self) -> list[Node]:
        """Get path from this node to root."""
        path = [self]
        node = self.parent
        while node is not None:
            path.append(node)
            node = node.parent
        return list(reversed(path))

    def get_action_sequence(self) -> list[TradingAction]:
        """Get sequence of actions from root to this node."""
        path = self.get_path_to_root()
        return [node.action for node in path[1:] if node.action is not None]

    def to_dict(self) -> dict[str, Any]:
        """Convert node to dictionary for serialization."""
        return {
            "id": self.id,
            "action": self.action.to_dict() if self.action else None,
            "value": self.value,
            "visits": self.visits,
            "q_value": self.q_value,
            "prior": self.prior,
            "depth": self.depth,
            "is_terminal": self.is_terminal,
            "is_solved": self.is_solved,
            "reflection": self.reflection,
            "num_children": len(self.children),
        }

    def __repr__(self) -> str:
        """String representation."""
        action_str = (
            f"{self.action.direction.value}" if self.action else "root"
        )
        return (
            f"Node({action_str}, "
            f"visits={self.visits}, "
            f"value={self.mean_value:.3f}, "
            f"children={len(self.children)})"
        )

    def __hash__(self) -> int:
        """Hash based on id."""
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        """Equality based on id."""
        if not isinstance(other, Node):
            return NotImplemented
        return self.id == other.id
