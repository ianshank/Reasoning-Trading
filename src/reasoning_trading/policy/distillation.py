"""
Policy Distillation for MCTS.

Implements the Expert Iteration (ExIt) training loop:
1. Expert (MCTS) performs slow, deliberate search
2. Apprentice (neural network) trains via supervised learning
3. Neural network improves MCTS by providing better priors

The distillation loss combines:
- KL divergence between teacher and student policies
- MSE loss between teacher and student values
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterator

import numpy as np
from numpy.typing import NDArray
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

if TYPE_CHECKING:
    from reasoning_trading.core.state import TradingState
    from reasoning_trading.hierarchical.tree import HierarchicalMCTSTree, HierarchicalMCTSResult
    from reasoning_trading.policy.network import PolicyNetwork


class DistillationConfig(BaseSettings):
    """Configuration for policy distillation."""

    model_config = SettingsConfigDict(
        env_prefix="DISTILL_",
        case_sensitive=False,
        extra="ignore",
    )

    # Training settings
    batch_size: int = Field(
        default=64,
        ge=8,
        le=512,
        description="Training batch size",
    )
    learning_rate: float = Field(
        default=0.001,
        ge=1e-6,
        le=0.1,
        description="Learning rate",
    )
    num_epochs: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Number of training epochs",
    )
    validation_split: float = Field(
        default=0.1,
        ge=0.0,
        le=0.5,
        description="Validation data fraction",
    )

    # Loss weights
    policy_loss_weight: float = Field(
        default=1.0,
        ge=0.0,
        le=10.0,
        description="Weight for policy KL divergence loss",
    )
    value_loss_weight: float = Field(
        default=1.0,
        ge=0.0,
        le=10.0,
        description="Weight for value MSE loss",
    )
    entropy_weight: float = Field(
        default=0.01,
        ge=0.0,
        le=1.0,
        description="Weight for entropy regularization",
    )

    # Expert iteration settings
    mcts_simulations: int = Field(
        default=800,
        ge=100,
        le=10000,
        description="MCTS simulations for teacher",
    )
    temperature: float = Field(
        default=1.0,
        ge=0.1,
        le=5.0,
        description="Temperature for policy sampling",
    )
    num_expert_games: int = Field(
        default=100,
        ge=10,
        le=10000,
        description="Number of games to play for data generation",
    )

    # Data settings
    max_buffer_size: int = Field(
        default=100000,
        ge=1000,
        le=10000000,
        description="Maximum replay buffer size",
    )
    min_samples_before_training: int = Field(
        default=1000,
        ge=100,
        le=10000,
        description="Minimum samples before training starts",
    )

    # Model paths
    teacher_checkpoint_path: str = Field(
        default="checkpoints/teacher",
        description="Path for teacher model checkpoints",
    )
    student_checkpoint_path: str = Field(
        default="checkpoints/student",
        description="Path for student model checkpoints",
    )


@dataclass
class DistillationSample:
    """Single sample for distillation training."""

    # State representation
    state_features: NDArray[np.float64]
    state_hash: str = ""

    # Teacher outputs
    teacher_policy: dict[str, float] = field(default_factory=dict)
    teacher_value: float = 0.0
    teacher_visits: int = 0

    # Game outcome
    game_outcome: float | None = None

    # Metadata
    hierarchy_level: str = "strategic"
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "state_features": self.state_features.tolist(),
            "state_hash": self.state_hash,
            "teacher_policy": self.teacher_policy,
            "teacher_value": self.teacher_value,
            "teacher_visits": self.teacher_visits,
            "game_outcome": self.game_outcome,
            "hierarchy_level": self.hierarchy_level,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DistillationSample:
        """Create from dictionary."""
        return cls(
            state_features=np.array(data["state_features"]),
            state_hash=data.get("state_hash", ""),
            teacher_policy=data.get("teacher_policy", {}),
            teacher_value=data.get("teacher_value", 0.0),
            teacher_visits=data.get("teacher_visits", 0),
            game_outcome=data.get("game_outcome"),
            hierarchy_level=data.get("hierarchy_level", "strategic"),
        )


class DistillationDataset:
    """
    Dataset for policy distillation.

    Stores (state, teacher_policy, teacher_value, outcome) tuples
    for training the student network.
    """

    def __init__(self, config: DistillationConfig | None = None):
        """Initialize dataset."""
        self.config = config or DistillationConfig()
        self.samples: list[DistillationSample] = []
        self._index = 0

    def add_sample(self, sample: DistillationSample) -> None:
        """Add a sample to the dataset."""
        self.samples.append(sample)

        # Trim if exceeding buffer size
        if len(self.samples) > self.config.max_buffer_size:
            # Remove oldest samples
            excess = len(self.samples) - self.config.max_buffer_size
            self.samples = self.samples[excess:]

    def add_from_mcts_result(
        self,
        state_features: NDArray[np.float64],
        result: HierarchicalMCTSResult,
        game_outcome: float | None = None,
    ) -> None:
        """
        Add samples from MCTS search result.

        Args:
            state_features: State feature vector
            result: MCTS search result
            game_outcome: Optional final game outcome
        """
        import hashlib

        state_hash = hashlib.md5(state_features.tobytes()).hexdigest()[:16]

        # Extract teacher policy from MCTS action distribution
        if result.strategic_node is not None:
            teacher_policy = {}
            for child in result.strategic_node.parent.children if result.strategic_node.parent else [result.strategic_node]:
                if child.action is not None:
                    action_name = child.action.action_type
                    prob = child.visits / max(result.total_simulations, 1)
                    teacher_policy[action_name] = prob

            sample = DistillationSample(
                state_features=state_features,
                state_hash=state_hash,
                teacher_policy=teacher_policy,
                teacher_value=result.strategic_value,
                teacher_visits=result.total_simulations,
                game_outcome=game_outcome,
                hierarchy_level="strategic",
            )
            self.add_sample(sample)

    def __len__(self) -> int:
        """Get number of samples."""
        return len(self.samples)

    def __iter__(self) -> Iterator[DistillationSample]:
        """Iterate over samples."""
        return iter(self.samples)

    def get_batch(self, batch_size: int) -> list[DistillationSample]:
        """Get a random batch of samples."""
        if len(self.samples) < batch_size:
            return self.samples.copy()

        indices = np.random.choice(len(self.samples), batch_size, replace=False)
        return [self.samples[i] for i in indices]

    def prepare_training_data(
        self,
        action_names: list[str],
    ) -> tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.float64]]:
        """
        Prepare data for training.

        Args:
            action_names: List of action names (determines output dimension)

        Returns:
            Tuple of (states, policies, values) numpy arrays
        """
        if not self.samples:
            raise ValueError("No samples in dataset")

        # Stack states
        states = np.stack([s.state_features for s in self.samples])

        # Convert policies to aligned array
        num_actions = len(action_names)
        policies = np.zeros((len(self.samples), num_actions))

        action_to_idx = {name: i for i, name in enumerate(action_names)}

        for i, sample in enumerate(self.samples):
            for action_name, prob in sample.teacher_policy.items():
                if action_name in action_to_idx:
                    policies[i, action_to_idx[action_name]] = prob
                else:
                    # Try partial match
                    for name, idx in action_to_idx.items():
                        if action_name.lower() in name.lower():
                            policies[i, idx] = prob
                            break

            # Normalize
            if policies[i].sum() > 0:
                policies[i] /= policies[i].sum()
            else:
                # Uniform if no policy
                policies[i] = 1.0 / num_actions

        # Values
        values = np.array([
            s.game_outcome if s.game_outcome is not None else s.teacher_value
            for s in self.samples
        ])

        return states, policies, values

    def split_train_val(
        self,
        val_fraction: float = 0.1,
    ) -> tuple[DistillationDataset, DistillationDataset]:
        """Split into training and validation sets."""
        n_val = int(len(self.samples) * val_fraction)
        n_train = len(self.samples) - n_val

        # Shuffle
        indices = np.random.permutation(len(self.samples))
        train_indices = indices[:n_train]
        val_indices = indices[n_train:]

        train_dataset = DistillationDataset(self.config)
        val_dataset = DistillationDataset(self.config)

        for i in train_indices:
            train_dataset.add_sample(self.samples[i])
        for i in val_indices:
            val_dataset.add_sample(self.samples[i])

        return train_dataset, val_dataset

    def save(self, path: Path) -> None:
        """Save dataset to file."""
        import json

        data = {
            "samples": [s.to_dict() for s in self.samples],
            "config": {
                "max_buffer_size": self.config.max_buffer_size,
            },
        }

        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f)

    def load(self, path: Path) -> None:
        """Load dataset from file."""
        import json

        with open(path) as f:
            data = json.load(f)

        self.samples = [
            DistillationSample.from_dict(s)
            for s in data["samples"]
        ]


class PolicyDistillation:
    """
    Policy distillation trainer.

    Trains student network to match teacher (MCTS) outputs using:
    - KL divergence for policy
    - MSE for value
    - Entropy regularization
    """

    def __init__(
        self,
        config: DistillationConfig | None = None,
        action_names: list[str] | None = None,
    ):
        """Initialize distillation trainer."""
        self.config = config or DistillationConfig()
        self.action_names = action_names or []
        self.dataset = DistillationDataset(self.config)

        # Training state
        self._training_step = 0
        self._best_val_loss = float("inf")

    def add_training_samples(
        self,
        states: list[NDArray[np.float64]],
        policies: list[dict[str, float]],
        values: list[float],
        outcomes: list[float | None] | None = None,
    ) -> None:
        """
        Add training samples from external source.

        Args:
            states: List of state feature vectors
            policies: List of teacher policy distributions
            values: List of teacher value estimates
            outcomes: Optional list of game outcomes
        """
        if outcomes is None:
            outcomes = [None] * len(states)

        for state, policy, value, outcome in zip(states, policies, values, outcomes):
            sample = DistillationSample(
                state_features=state,
                teacher_policy=policy,
                teacher_value=value,
                game_outcome=outcome,
            )
            self.dataset.add_sample(sample)

    def compute_loss(
        self,
        student_policy: NDArray[np.float64],
        student_value: NDArray[np.float64],
        teacher_policy: NDArray[np.float64],
        teacher_value: NDArray[np.float64],
    ) -> tuple[float, dict[str, float]]:
        """
        Compute distillation loss.

        L = α × KL(π_teacher || π_student) + β × MSE(v_teacher, v_student) - γ × H(π_student)

        Args:
            student_policy: Student policy logits
            student_value: Student value predictions
            teacher_policy: Teacher policy distribution
            teacher_value: Teacher value estimates

        Returns:
            Tuple of (total_loss, component_losses)
        """
        # KL divergence: KL(P || Q) = Σ P(x) log(P(x)/Q(x))
        # For numerical stability, use log softmax
        student_log_probs = student_policy - np.log(
            np.sum(np.exp(student_policy), axis=-1, keepdims=True)
        )

        # Avoid log(0)
        teacher_policy = np.clip(teacher_policy, 1e-10, 1.0)
        teacher_log_probs = np.log(teacher_policy)

        kl_div = np.sum(
            teacher_policy * (teacher_log_probs - student_log_probs),
            axis=-1,
        ).mean()

        # Value MSE
        value_mse = np.mean((student_value - teacher_value) ** 2)

        # Entropy bonus (encourage exploration)
        student_probs = np.exp(student_log_probs)
        entropy = -np.sum(student_probs * student_log_probs, axis=-1).mean()

        # Total loss
        total_loss = (
            self.config.policy_loss_weight * kl_div
            + self.config.value_loss_weight * value_mse
            - self.config.entropy_weight * entropy
        )

        return total_loss, {
            "kl_divergence": kl_div,
            "value_mse": value_mse,
            "entropy": entropy,
            "total": total_loss,
        }

    def train_step(
        self,
        student_model: Any,
        optimizer: Any,
        batch: list[DistillationSample],
    ) -> dict[str, float]:
        """
        Run one training step.

        This is a framework-agnostic interface. Actual implementation
        depends on whether using PyTorch, JAX, etc.

        Args:
            student_model: Student model
            optimizer: Optimizer
            batch: Training batch

        Returns:
            Loss metrics
        """
        # Prepare batch data
        states = np.stack([s.state_features for s in batch])
        teacher_policies = np.zeros((len(batch), len(self.action_names)))
        teacher_values = np.array([s.teacher_value for s in batch])

        action_to_idx = {name: i for i, name in enumerate(self.action_names)}
        for i, sample in enumerate(batch):
            for action_name, prob in sample.teacher_policy.items():
                if action_name in action_to_idx:
                    teacher_policies[i, action_to_idx[action_name]] = prob

            if teacher_policies[i].sum() > 0:
                teacher_policies[i] /= teacher_policies[i].sum()
            else:
                teacher_policies[i] = 1.0 / len(self.action_names)

        # This would be implemented by framework-specific subclass
        # For now, return dummy metrics
        self._training_step += 1

        return {
            "step": self._training_step,
            "loss": 0.0,
            "kl_divergence": 0.0,
            "value_mse": 0.0,
        }


class ExpertIteration:
    """
    Expert Iteration (ExIt) training loop.

    The "virtuous cycle":
    1. Expert (MCTS) performs deep search
    2. Apprentice (student) learns from expert
    3. Improved apprentice provides better priors for MCTS
    4. Repeat
    """

    def __init__(
        self,
        mcts_tree: HierarchicalMCTSTree | None = None,
        student_network: PolicyNetwork | None = None,
        config: DistillationConfig | None = None,
    ):
        """Initialize Expert Iteration."""
        self.mcts_tree = mcts_tree
        self.student_network = student_network
        self.config = config or DistillationConfig()

        self.distillation = PolicyDistillation(config)
        self._iteration = 0

    async def generate_expert_data(
        self,
        states: list[TradingState],
    ) -> DistillationDataset:
        """
        Generate training data using MCTS expert.

        Args:
            states: List of trading states to analyze

        Returns:
            Dataset with expert trajectories
        """
        dataset = DistillationDataset(self.config)

        if self.mcts_tree is None:
            return dataset

        for state in states:
            # Run MCTS search
            result = await self.mcts_tree.search(state)

            # Extract state features
            state_features = state.to_feature_vector()

            # Add to dataset
            dataset.add_from_mcts_result(
                state_features=state_features,
                result=result,
            )

        return dataset

    async def run_iteration(
        self,
        training_states: list[TradingState],
    ) -> dict[str, float]:
        """
        Run one Expert Iteration cycle.

        Args:
            training_states: States for training

        Returns:
            Metrics from this iteration
        """
        self._iteration += 1

        # Phase 1: Generate expert data
        dataset = await self.generate_expert_data(training_states)

        # Phase 2: Add to distillation dataset
        for sample in dataset:
            self.distillation.dataset.add_sample(sample)

        # Phase 3: Train student (would be implemented by subclass)
        # train_metrics = self.distillation.train(self.student_network)

        # Phase 4: Update MCTS with improved policy
        # self.mcts_tree.policy_network = self.student_network

        return {
            "iteration": self._iteration,
            "samples_generated": len(dataset),
            "total_samples": len(self.distillation.dataset),
        }

    def get_training_progress(self) -> dict[str, Any]:
        """Get training progress metrics."""
        return {
            "iteration": self._iteration,
            "dataset_size": len(self.distillation.dataset),
            "training_step": self.distillation._training_step,
            "best_val_loss": self.distillation._best_val_loss,
        }
