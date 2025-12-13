"""
Hierarchical MCTS Node implementation.

Extends the base Node class to support hierarchical task decomposition
with subtasks, completion functions, and multi-level value estimates.
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
    from reasoning_trading.hierarchical.levels import HierarchyLevelType, LevelAction, LevelState


@dataclass
class HierarchicalNode:
    """
    Hierarchical MCTS tree node for trading decisions.

    Extends the basic Node with:
    - Multi-level hierarchy support
    - Subtask tracking
    - MAXQ value decomposition support
    - Level-specific statistics
    """

    # Unique identifier
    id: str = field(default_factory=lambda: str(uuid4()))

    # Hierarchy information
    level: str = "strategic"  # strategic, tactical, execution
    task_id: str = ""  # Identifier for this task/subtask

    # State representation at this node's level
    level_state: LevelState | None = None
    raw_state: TradingState | None = None

    # Action that led to this node
    action: LevelAction | None = None

    # Tree structure
    parent: HierarchicalNode | None = None
    children: list[HierarchicalNode] = field(default_factory=list)

    # Subtask information
    subtasks: list[HierarchicalNode] = field(default_factory=list)
    is_subtask_complete: bool = False
    subtask_return: float = 0.0

    # Conversation history (for LLM context)
    messages: list[BaseMessage] = field(default_factory=list)

    # Self-evaluation from LLM
    reflection: str = ""

    # Value estimates
    value: float = 0.0  # V^π(s) - state value
    q_value: float = 0.0  # Q^π(s, a) - action value
    subtask_value: float = 0.0  # V^π(a, s) - subtask value
    completion_value: float = 0.0  # C^π(i, s, a) - completion function

    # Visit statistics
    visits: int = 0
    value_sum: float = 0.0

    # Prior probability from policy network (0-1)
    prior: float = 0.0

    # Terminal state flags
    is_solved: bool = False
    is_terminal: bool = False
    is_primitive: bool = False  # True if this is a primitive action

    # Metadata
    depth: int = 0
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        """Initialize depth based on parent."""
        if self.parent is not None:
            self.depth = self.parent.depth + 1

        # Generate task_id if not provided
        if not self.task_id:
            self.task_id = f"{self.level}_{self.id[:8]}"

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
    def hierarchical_q_value(self) -> float:
        """
        Get hierarchical Q-value: Q^π(i, s, a) = V^π(a, s) + C^π(i, s, a).

        This is the MAXQ decomposition value.
        """
        return self.subtask_value + self.completion_value

    def ucb_hierarchical(
        self,
        c_puct: float = 1.414,
        use_prior: bool = True,
    ) -> float:
        """
        Calculate hierarchical UCB value with PUCT.

        Combines:
        - Hierarchical Q-value (MAXQ decomposition)
        - Exploration bonus with optional policy prior

        Args:
            c_puct: Exploration constant
            use_prior: Whether to use policy prior in exploration

        Returns:
            UCB score for node selection
        """
        if self.parent is None:
            return self.hierarchical_q_value

        # Exploitation term
        exploitation = self.hierarchical_q_value

        # Exploration term
        if self.visits == 0:
            exploration = float("inf")
        else:
            if use_prior and self.prior > 0:
                # PUCT formula with prior
                exploration = (
                    c_puct
                    * self.prior
                    * math.sqrt(self.parent.visits)
                    / (1 + self.visits)
                )
            else:
                # Standard UCB
                exploration = c_puct * math.sqrt(
                    math.log(self.parent.visits + 1) / self.visits
                )

        return exploitation + exploration

    def expand_with_subtask(
        self,
        action: LevelAction,
        level_state: LevelState,
        raw_state: TradingState | None = None,
        prior: float = 0.0,
        messages: list[BaseMessage] | None = None,
    ) -> HierarchicalNode:
        """
        Expand this node with a subtask.

        Args:
            action: Level action to execute
            level_state: State at the subtask's level
            raw_state: Full trading state
            prior: Prior probability from policy network
            messages: Conversation history

        Returns:
            New child node for the subtask
        """
        child = HierarchicalNode(
            level=action.level.value if hasattr(action.level, "value") else str(action.level),
            task_id=action.subtask_id or f"{action.action_type}_{str(uuid4())[:8]}",
            level_state=level_state,
            raw_state=raw_state,
            action=action,
            parent=self,
            prior=prior,
            messages=messages or [],
            is_primitive=action.subtask_id is None,  # No subtask_id means primitive
        )
        self.children.append(child)
        self.subtasks.append(child)
        return child

    def complete_subtask(self, return_value: float) -> None:
        """
        Mark this subtask as complete with final return.

        Args:
            return_value: Total return from this subtask
        """
        self.is_subtask_complete = True
        self.subtask_return = return_value

        # Update parent's completion value
        if self.parent is not None:
            self.parent.update_completion_value(self.task_id, return_value)

    def update_completion_value(
        self,
        subtask_id: str,
        subtask_return: float,
        learning_rate: float = 0.01,
    ) -> None:
        """
        Update completion value based on subtask completion.

        Args:
            subtask_id: ID of completed subtask
            subtask_return: Return from the subtask
            learning_rate: Learning rate for update
        """
        # Simple incremental update
        self.completion_value += learning_rate * (subtask_return - self.completion_value)

    def backpropagate_hierarchical(
        self,
        value: float,
        discount: float = 0.99,
    ) -> None:
        """
        Hierarchical backpropagation up the tree.

        Updates both standard statistics and MAXQ decomposition values.

        Args:
            value: Value to propagate
            discount: Discount factor for future rewards
        """
        node: HierarchicalNode | None = self
        current_value = value

        while node is not None:
            # Update visit statistics
            node.visits += 1
            node.value_sum += current_value
            node.value = node.mean_value

            # Update Q-value
            if node.visits == 1:
                node.q_value = current_value
            else:
                node.q_value += (current_value - node.q_value) / node.visits

            # Update subtask value (for MAXQ)
            node.subtask_value = node.q_value

            # Apply discount for parent
            current_value *= discount
            node = node.parent

    def best_child_hierarchical(
        self,
        c_puct: float = 1.414,
        use_prior: bool = True,
    ) -> HierarchicalNode | None:
        """
        Select best child using hierarchical UCB.

        Args:
            c_puct: Exploration constant
            use_prior: Whether to use policy prior

        Returns:
            Best child node or None if no children
        """
        if not self.children:
            return None

        return max(
            self.children,
            key=lambda c: c.ucb_hierarchical(c_puct=c_puct, use_prior=use_prior),
        )

    def best_subtask(self) -> HierarchicalNode | None:
        """
        Select best subtask by visit count.

        Returns:
            Most visited subtask node
        """
        if not self.subtasks:
            return None

        return max(self.subtasks, key=lambda s: s.visits)

    def get_subtask_distribution(self) -> dict[str, float]:
        """
        Get probability distribution over subtasks based on visits.

        Returns:
            Dictionary mapping subtask IDs to probabilities
        """
        if not self.subtasks:
            return {}

        total_visits = sum(s.visits for s in self.subtasks)
        if total_visits == 0:
            return {s.task_id: 1.0 / len(self.subtasks) for s in self.subtasks}

        return {
            s.task_id: s.visits / total_visits
            for s in self.subtasks
        }

    def get_path_to_root(self) -> list[HierarchicalNode]:
        """Get path from this node to root."""
        path = [self]
        node = self.parent
        while node is not None:
            path.append(node)
            node = node.parent
        return list(reversed(path))

    def get_action_sequence(self) -> list[LevelAction]:
        """Get sequence of actions from root to this node."""
        path = self.get_path_to_root()
        return [node.action for node in path[1:] if node.action is not None]

    def get_level_path(self) -> list[str]:
        """Get sequence of levels from root to this node."""
        path = self.get_path_to_root()
        return [node.level for node in path]

    def to_dict(self) -> dict[str, Any]:
        """Convert node to dictionary for serialization."""
        return {
            "id": self.id,
            "task_id": self.task_id,
            "level": self.level,
            "action": self.action.to_dict() if self.action else None,
            "value": self.value,
            "q_value": self.q_value,
            "subtask_value": self.subtask_value,
            "completion_value": self.completion_value,
            "hierarchical_q_value": self.hierarchical_q_value,
            "visits": self.visits,
            "prior": self.prior,
            "depth": self.depth,
            "is_terminal": self.is_terminal,
            "is_primitive": self.is_primitive,
            "is_subtask_complete": self.is_subtask_complete,
            "subtask_return": self.subtask_return,
            "reflection": self.reflection,
            "num_children": len(self.children),
            "num_subtasks": len(self.subtasks),
        }

    def __repr__(self) -> str:
        """String representation."""
        action_str = self.action.action_type if self.action else "root"
        return (
            f"HierarchicalNode({self.level}/{action_str}, "
            f"visits={self.visits}, "
            f"h_q={self.hierarchical_q_value:.3f}, "
            f"children={len(self.children)})"
        )

    def __hash__(self) -> int:
        """Hash based on id."""
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        """Equality based on id."""
        if not isinstance(other, HierarchicalNode):
            return NotImplemented
        return self.id == other.id
