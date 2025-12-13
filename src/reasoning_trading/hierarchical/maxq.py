"""
MAXQ Value Decomposition for Hierarchical MCTS.

Implements the MAXQ-Q value decomposition framework:
Q^π(i, s, a) = V^π(a, s) + C^π(i, s, a)

Where:
- V^π(a, s) is the projected value of completing subtask a from state s
- C^π(i, s, a) is the completion function - expected reward after subtask a terminates

This enables context-free subtask learning where execution strategies can be
developed independently from strategic objectives.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, Callable
import hashlib

import numpy as np
from numpy.typing import NDArray
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

if TYPE_CHECKING:
    from reasoning_trading.hierarchical.levels import LevelAction, LevelState, HierarchyLevel


class MAXQConfig(BaseSettings):
    """Configuration for MAXQ decomposition."""

    model_config = SettingsConfigDict(
        env_prefix="MAXQ_",
        case_sensitive=False,
        extra="ignore",
    )

    discount_factor: float = Field(
        default=0.99,
        ge=0.0,
        le=1.0,
        description="Discount factor for future rewards",
    )
    completion_learning_rate: float = Field(
        default=0.01,
        ge=0.0001,
        le=1.0,
        description="Learning rate for completion function updates",
    )
    value_learning_rate: float = Field(
        default=0.01,
        ge=0.0001,
        le=1.0,
        description="Learning rate for subtask value updates",
    )
    eligibility_trace_decay: float = Field(
        default=0.9,
        ge=0.0,
        le=1.0,
        description="Eligibility trace decay for temporal credit assignment",
    )
    use_all_goals: bool = Field(
        default=True,
        description="Use all-goals MAXQ update (more sample efficient)",
    )


@dataclass
class SubtaskValue:
    """
    Value estimate for completing a subtask.

    Stores V^π(a, s) - the projected value of completing subtask a from state s.
    """

    subtask_id: str
    state_hash: str
    value: float = 0.0
    visits: int = 0
    last_updated: datetime = field(default_factory=datetime.now)

    def update(self, new_value: float, learning_rate: float = 0.01) -> None:
        """Update value estimate with new observation."""
        if self.visits == 0:
            self.value = new_value
        else:
            self.value += learning_rate * (new_value - self.value)
        self.visits += 1
        self.last_updated = datetime.now()


@dataclass
class CompletionFunction:
    """
    Completion function C^π(i, s, a) for MAXQ decomposition.

    Represents the expected reward after subtask a terminates, given that
    we're executing parent task i from state s.
    """

    parent_task_id: str
    subtask_id: str
    state_hash: str
    value: float = 0.0
    visits: int = 0
    last_updated: datetime = field(default_factory=datetime.now)

    def update(self, new_value: float, learning_rate: float = 0.01) -> None:
        """Update completion function with new observation."""
        if self.visits == 0:
            self.value = new_value
        else:
            self.value += learning_rate * (new_value - self.value)
        self.visits += 1
        self.last_updated = datetime.now()


class MAXQValueDecomposition:
    """
    MAXQ Value Decomposition for hierarchical trading decisions.

    The Q-value for selecting action a in task i decomposes as:
    Q^π(i, s, a) = V^π(a, s) + C^π(i, s, a)

    This enables:
    1. Context-free subtask learning (execution strategies independent of strategy)
    2. Hierarchical credit assignment
    3. Efficient value function approximation
    """

    def __init__(self, config: MAXQConfig | None = None):
        """Initialize MAXQ decomposition."""
        self.config = config or MAXQConfig()

        # Subtask value tables: subtask_id -> state_hash -> SubtaskValue
        self._subtask_values: dict[str, dict[str, SubtaskValue]] = {}

        # Completion function tables: (parent_id, subtask_id) -> state_hash -> CompletionFunction
        self._completion_functions: dict[tuple[str, str], dict[str, CompletionFunction]] = {}

        # Eligibility traces for temporal credit assignment
        self._eligibility_traces: dict[str, float] = {}

    def _hash_state(self, state: LevelState) -> str:
        """Create hash of state for table lookup."""
        # Discretize features for hashing
        discretized = np.round(state.features * 10) / 10
        return hashlib.md5(discretized.tobytes()).hexdigest()[:16]

    def get_subtask_value(self, subtask_id: str, state: LevelState) -> float:
        """
        Get V^π(a, s) - projected value of completing subtask from state.

        Args:
            subtask_id: Identifier for the subtask
            state: Current state

        Returns:
            Estimated value of completing subtask
        """
        state_hash = self._hash_state(state)

        if subtask_id not in self._subtask_values:
            return 0.0

        subtask_table = self._subtask_values[subtask_id]
        if state_hash not in subtask_table:
            return 0.0

        return subtask_table[state_hash].value

    def get_completion_value(
        self,
        parent_task_id: str,
        subtask_id: str,
        state: LevelState,
    ) -> float:
        """
        Get C^π(i, s, a) - completion function value.

        Args:
            parent_task_id: Identifier for parent task
            subtask_id: Identifier for subtask
            state: Current state

        Returns:
            Expected reward after subtask terminates
        """
        state_hash = self._hash_state(state)
        key = (parent_task_id, subtask_id)

        if key not in self._completion_functions:
            return 0.0

        completion_table = self._completion_functions[key]
        if state_hash not in completion_table:
            return 0.0

        return completion_table[state_hash].value

    def get_q_value(
        self,
        parent_task_id: str,
        subtask_id: str,
        state: LevelState,
    ) -> float:
        """
        Get Q^π(i, s, a) = V^π(a, s) + C^π(i, s, a).

        The full hierarchical Q-value combining subtask value and completion function.

        Args:
            parent_task_id: Identifier for parent task
            subtask_id: Identifier for subtask
            state: Current state

        Returns:
            Hierarchical Q-value
        """
        v_value = self.get_subtask_value(subtask_id, state)
        c_value = self.get_completion_value(parent_task_id, subtask_id, state)
        return v_value + c_value

    def update_subtask_value(
        self,
        subtask_id: str,
        state: LevelState,
        value: float,
    ) -> None:
        """
        Update V^π(a, s) with new value estimate.

        Args:
            subtask_id: Subtask identifier
            state: State where subtask was executed
            value: Observed value (return)
        """
        state_hash = self._hash_state(state)

        if subtask_id not in self._subtask_values:
            self._subtask_values[subtask_id] = {}

        if state_hash not in self._subtask_values[subtask_id]:
            self._subtask_values[subtask_id][state_hash] = SubtaskValue(
                subtask_id=subtask_id,
                state_hash=state_hash,
            )

        self._subtask_values[subtask_id][state_hash].update(
            value,
            learning_rate=self.config.value_learning_rate,
        )

    def update_completion_function(
        self,
        parent_task_id: str,
        subtask_id: str,
        state: LevelState,
        value: float,
    ) -> None:
        """
        Update C^π(i, s, a) with new completion value estimate.

        Args:
            parent_task_id: Parent task identifier
            subtask_id: Subtask identifier
            state: State where subtask terminated
            value: Observed completion value
        """
        state_hash = self._hash_state(state)
        key = (parent_task_id, subtask_id)

        if key not in self._completion_functions:
            self._completion_functions[key] = {}

        if state_hash not in self._completion_functions[key]:
            self._completion_functions[key][state_hash] = CompletionFunction(
                parent_task_id=parent_task_id,
                subtask_id=subtask_id,
                state_hash=state_hash,
            )

        self._completion_functions[key][state_hash].update(
            value,
            learning_rate=self.config.completion_learning_rate,
        )

    def hierarchical_update(
        self,
        trajectory: list[tuple[str, LevelState, LevelAction, float]],
    ) -> None:
        """
        Perform hierarchical MAXQ update on a trajectory.

        Uses the "all-goals" MAXQ-Q learning update for sample efficiency.

        Args:
            trajectory: List of (task_id, state, action, reward) tuples
        """
        if not trajectory:
            return

        # Compute returns with discounting
        returns: list[float] = []
        g = 0.0

        for _, _, _, reward in reversed(trajectory):
            g = reward + self.config.discount_factor * g
            returns.insert(0, g)

        # Update value functions
        for i, (task_id, state, action, _) in enumerate(trajectory):
            subtask_id = action.subtask_id or action.action_type

            # Update subtask value with return from this point
            self.update_subtask_value(subtask_id, state, returns[i])

            # Update completion function for parent-child relationships
            if i > 0:
                parent_task_id = trajectory[i - 1][2].subtask_id or trajectory[i - 1][2].action_type
                completion_value = sum(
                    self.config.discount_factor ** (j - i) * trajectory[j][3]
                    for j in range(i, len(trajectory))
                )
                self.update_completion_function(parent_task_id, subtask_id, state, completion_value)

    def select_subtask(
        self,
        parent_task_id: str,
        state: LevelState,
        candidate_subtasks: list[str],
        exploration_constant: float = 1.414,
    ) -> str:
        """
        Select best subtask using hierarchical Q-values.

        Uses UCB-style exploration for subtask selection.

        Args:
            parent_task_id: Parent task identifier
            state: Current state
            candidate_subtasks: Available subtask IDs
            exploration_constant: UCB exploration weight

        Returns:
            Selected subtask ID
        """
        if not candidate_subtasks:
            raise ValueError("No candidate subtasks provided")

        best_subtask = candidate_subtasks[0]
        best_score = float("-inf")

        # Count total visits for UCB exploration term
        total_visits = sum(
            self._get_subtask_visits(subtask_id, state)
            for subtask_id in candidate_subtasks
        )

        for subtask_id in candidate_subtasks:
            q_value = self.get_q_value(parent_task_id, subtask_id, state)
            visits = self._get_subtask_visits(subtask_id, state)

            # UCB exploration bonus
            if visits == 0:
                exploration_bonus = float("inf")
            else:
                exploration_bonus = exploration_constant * np.sqrt(
                    np.log(total_visits + 1) / visits
                )

            score = q_value + exploration_bonus

            if score > best_score:
                best_score = score
                best_subtask = subtask_id

        return best_subtask

    def _get_subtask_visits(self, subtask_id: str, state: LevelState) -> int:
        """Get visit count for a subtask in a state."""
        state_hash = self._hash_state(state)

        if subtask_id not in self._subtask_values:
            return 0

        if state_hash not in self._subtask_values[subtask_id]:
            return 0

        return self._subtask_values[subtask_id][state_hash].visits

    def get_policy_distribution(
        self,
        parent_task_id: str,
        state: LevelState,
        candidate_subtasks: list[str],
        temperature: float = 1.0,
    ) -> dict[str, float]:
        """
        Get softmax policy distribution over subtasks.

        Args:
            parent_task_id: Parent task identifier
            state: Current state
            candidate_subtasks: Available subtask IDs
            temperature: Softmax temperature (lower = more greedy)

        Returns:
            Dictionary mapping subtask IDs to probabilities
        """
        if not candidate_subtasks:
            return {}

        q_values = [
            self.get_q_value(parent_task_id, subtask_id, state)
            for subtask_id in candidate_subtasks
        ]

        # Softmax with temperature
        q_array = np.array(q_values)
        q_array = q_array - np.max(q_array)  # Numerical stability
        exp_q = np.exp(q_array / temperature)
        probs = exp_q / np.sum(exp_q)

        return dict(zip(candidate_subtasks, probs.tolist()))

    def get_statistics(self) -> dict[str, Any]:
        """Get statistics about learned value functions."""
        total_subtask_entries = sum(
            len(table) for table in self._subtask_values.values()
        )
        total_completion_entries = sum(
            len(table) for table in self._completion_functions.values()
        )

        return {
            "num_subtasks": len(self._subtask_values),
            "total_subtask_entries": total_subtask_entries,
            "num_parent_subtask_pairs": len(self._completion_functions),
            "total_completion_entries": total_completion_entries,
        }

    def save_state(self) -> dict[str, Any]:
        """Save value function state for persistence."""
        subtask_data = {}
        for subtask_id, table in self._subtask_values.items():
            subtask_data[subtask_id] = {
                state_hash: {
                    "value": sv.value,
                    "visits": sv.visits,
                }
                for state_hash, sv in table.items()
            }

        completion_data = {}
        for (parent_id, subtask_id), table in self._completion_functions.items():
            key = f"{parent_id}::{subtask_id}"
            completion_data[key] = {
                state_hash: {
                    "value": cf.value,
                    "visits": cf.visits,
                }
                for state_hash, cf in table.items()
            }

        return {
            "subtask_values": subtask_data,
            "completion_functions": completion_data,
            "config": {
                "discount_factor": self.config.discount_factor,
                "completion_learning_rate": self.config.completion_learning_rate,
                "value_learning_rate": self.config.value_learning_rate,
            },
        }

    def load_state(self, state_dict: dict[str, Any]) -> None:
        """Load value function state from saved data."""
        # Load subtask values
        for subtask_id, table_data in state_dict.get("subtask_values", {}).items():
            self._subtask_values[subtask_id] = {}
            for state_hash, entry in table_data.items():
                self._subtask_values[subtask_id][state_hash] = SubtaskValue(
                    subtask_id=subtask_id,
                    state_hash=state_hash,
                    value=entry["value"],
                    visits=entry["visits"],
                )

        # Load completion functions
        for key, table_data in state_dict.get("completion_functions", {}).items():
            parent_id, subtask_id = key.split("::")
            self._completion_functions[(parent_id, subtask_id)] = {}
            for state_hash, entry in table_data.items():
                self._completion_functions[(parent_id, subtask_id)][state_hash] = CompletionFunction(
                    parent_task_id=parent_id,
                    subtask_id=subtask_id,
                    state_hash=state_hash,
                    value=entry["value"],
                    visits=entry["visits"],
                )
