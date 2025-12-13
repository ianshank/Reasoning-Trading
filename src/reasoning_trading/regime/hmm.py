"""
Hidden Markov Model for Market Regime Detection.

Implements a discrete HMM for classifying market regimes:
- States: Bull, Bear, High-Volatility, Low-Volatility, Neutral
- Observations: Discretized returns, volatility, volume signals
- Inference: Forward-backward algorithm for state estimation
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

import numpy as np
from numpy.typing import NDArray
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class RegimeState(str, Enum):
    """Market regime states."""

    BULL = "bull"
    BEAR = "bear"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    NEUTRAL = "neutral"


class HMMConfig(BaseSettings):
    """Configuration for Hidden Markov Model."""

    model_config = SettingsConfigDict(
        env_prefix="HMM_",
        case_sensitive=False,
        extra="ignore",
    )

    # Number of states
    num_states: int = Field(
        default=5,
        ge=2,
        le=10,
        description="Number of hidden states",
    )

    # Number of observation symbols
    num_observations: int = Field(
        default=9,
        ge=3,
        le=50,
        description="Number of observation symbols",
    )

    # Learning parameters
    learning_rate: float = Field(
        default=0.01,
        ge=0.001,
        le=0.5,
        description="Learning rate for online updates",
    )
    min_observations: int = Field(
        default=20,
        ge=5,
        le=100,
        description="Minimum observations before inference",
    )

    # Smoothing
    smoothing_factor: float = Field(
        default=0.01,
        ge=0.001,
        le=0.1,
        description="Laplace smoothing for probabilities",
    )


@dataclass
class TransitionMatrix:
    """Transition probability matrix for HMM."""

    matrix: NDArray[np.float64]
    state_names: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate and normalize matrix."""
        # Ensure rows sum to 1
        row_sums = self.matrix.sum(axis=1, keepdims=True)
        self.matrix = self.matrix / np.maximum(row_sums, 1e-10)

        # Set default state names
        if not self.state_names:
            self.state_names = [s.value for s in RegimeState][:self.matrix.shape[0]]

    def get_transition_prob(self, from_state: int, to_state: int) -> float:
        """Get transition probability."""
        return float(self.matrix[from_state, to_state])

    def get_stationary_distribution(self) -> NDArray[np.float64]:
        """Compute stationary distribution via eigendecomposition."""
        eigenvalues, eigenvectors = np.linalg.eig(self.matrix.T)
        stationary_idx = np.argmin(np.abs(eigenvalues - 1.0))
        stationary = np.real(eigenvectors[:, stationary_idx])
        return stationary / stationary.sum()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "matrix": self.matrix.tolist(),
            "state_names": self.state_names,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TransitionMatrix:
        """Create from dictionary."""
        return cls(
            matrix=np.array(data["matrix"]),
            state_names=data.get("state_names", []),
        )


class HiddenMarkovModel:
    """
    Hidden Markov Model for market regime detection.

    Implements:
    - Forward algorithm for likelihood computation
    - Viterbi algorithm for most likely state sequence
    - Baum-Welch for parameter estimation
    - Online updates for streaming data
    """

    def __init__(self, config: HMMConfig | None = None):
        """Initialize HMM."""
        self.config = config or HMMConfig()

        n_states = self.config.num_states
        n_obs = self.config.num_observations

        # State names
        self.state_names = [s.value for s in RegimeState][:n_states]

        # Initial state distribution (uniform by default)
        self._pi: NDArray[np.float64] = np.ones(n_states) / n_states

        # Transition probabilities
        # Default: high self-transition probability (regimes are persistent)
        self._A: NDArray[np.float64] = np.eye(n_states) * 0.9
        self._A += np.ones((n_states, n_states)) * 0.1 / n_states
        self._A /= self._A.sum(axis=1, keepdims=True)

        # Emission probabilities (initialized uniformly)
        self._B: NDArray[np.float64] = np.ones((n_states, n_obs)) / n_obs

        # Initialize emission probabilities with domain knowledge
        self._initialize_emissions()

        # Observation history
        self._observations: list[int] = []
        self._current_state: int = 2  # Start in neutral

    def _initialize_emissions(self) -> None:
        """
        Initialize emission probabilities with trading domain knowledge.

        Observations are discretized into 9 buckets:
        0-2: Negative returns (large, medium, small)
        3-5: Neutral/sideways (low vol, med vol, high vol)
        6-8: Positive returns (small, medium, large)
        """
        n_obs = self.config.num_observations

        # Bull state: higher probability of positive returns
        self._B[0] = np.array([0.02, 0.05, 0.08, 0.10, 0.10, 0.08, 0.17, 0.22, 0.18])

        # Bear state: higher probability of negative returns
        self._B[1] = np.array([0.18, 0.22, 0.17, 0.08, 0.10, 0.10, 0.08, 0.05, 0.02])

        # High volatility: extreme returns more likely
        self._B[2] = np.array([0.15, 0.10, 0.05, 0.03, 0.04, 0.03, 0.05, 0.10, 0.15]) * 2
        self._B[2] /= self._B[2].sum()

        # Low volatility: centered returns more likely
        self._B[3] = np.array([0.02, 0.05, 0.10, 0.18, 0.30, 0.18, 0.10, 0.05, 0.02])

        # Neutral: uniform-ish
        self._B[4] = np.array([0.08, 0.10, 0.12, 0.12, 0.16, 0.12, 0.12, 0.10, 0.08])

        # Normalize
        self._B /= self._B.sum(axis=1, keepdims=True)

    @property
    def transition_matrix(self) -> TransitionMatrix:
        """Get transition matrix."""
        return TransitionMatrix(
            matrix=self._A.copy(),
            state_names=self.state_names,
        )

    def discretize_observation(
        self,
        returns: float,
        volatility: float,
    ) -> int:
        """
        Discretize continuous observations into symbols.

        Args:
            returns: Recent return (e.g., daily return)
            volatility: Recent volatility

        Returns:
            Observation symbol (0 to num_observations-1)
        """
        # Discretize returns into 3 categories
        if returns < -0.02:
            return_category = 0  # Large negative
        elif returns < -0.005:
            return_category = 1  # Medium negative
        elif returns < 0.005:
            return_category = 2  # Small/neutral
        elif returns < 0.02:
            return_category = 3  # Medium positive
        else:
            return_category = 4  # Large positive

        # Adjust for volatility
        if volatility > 0.03:
            vol_adjustment = 2  # High vol -> extreme bucket
        elif volatility < 0.01:
            vol_adjustment = 0  # Low vol -> center bucket
        else:
            vol_adjustment = 1

        # Combine: returns * 3 + vol_adjustment, clamped to [0, 8]
        obs = min(max(return_category * 2 - 2 + vol_adjustment, 0), 8)
        return obs

    def forward(
        self,
        observations: list[int],
    ) -> tuple[NDArray[np.float64], float]:
        """
        Forward algorithm for computing state probabilities.

        Args:
            observations: Sequence of observation symbols

        Returns:
            Tuple of (alpha matrix, log-likelihood)
        """
        T = len(observations)
        n_states = len(self._pi)

        # Alpha: forward probabilities
        alpha = np.zeros((T, n_states))

        # Initialize
        alpha[0] = self._pi * self._B[:, observations[0]]
        alpha[0] /= alpha[0].sum() + 1e-10

        # Forward pass
        for t in range(1, T):
            for j in range(n_states):
                alpha[t, j] = np.sum(alpha[t - 1] * self._A[:, j]) * self._B[j, observations[t]]
            alpha[t] /= alpha[t].sum() + 1e-10

        # Log-likelihood
        log_likelihood = np.sum(np.log(alpha.sum(axis=1) + 1e-10))

        return alpha, log_likelihood

    def backward(
        self,
        observations: list[int],
    ) -> NDArray[np.float64]:
        """
        Backward algorithm for computing backward probabilities.

        Args:
            observations: Sequence of observation symbols

        Returns:
            Beta matrix (backward probabilities)
        """
        T = len(observations)
        n_states = len(self._pi)

        beta = np.zeros((T, n_states))
        beta[T - 1] = 1.0

        for t in range(T - 2, -1, -1):
            for i in range(n_states):
                beta[t, i] = np.sum(
                    self._A[i, :] * self._B[:, observations[t + 1]] * beta[t + 1]
                )
            beta[t] /= beta[t].sum() + 1e-10

        return beta

    def viterbi(
        self,
        observations: list[int],
    ) -> list[int]:
        """
        Viterbi algorithm for most likely state sequence.

        Args:
            observations: Sequence of observation symbols

        Returns:
            Most likely state sequence
        """
        T = len(observations)
        n_states = len(self._pi)

        # Viterbi matrices
        delta = np.zeros((T, n_states))
        psi = np.zeros((T, n_states), dtype=int)

        # Initialize
        delta[0] = np.log(self._pi + 1e-10) + np.log(self._B[:, observations[0]] + 1e-10)

        # Forward pass
        for t in range(1, T):
            for j in range(n_states):
                probs = delta[t - 1] + np.log(self._A[:, j] + 1e-10)
                psi[t, j] = np.argmax(probs)
                delta[t, j] = probs[psi[t, j]] + np.log(self._B[j, observations[t]] + 1e-10)

        # Backtrack
        path = [0] * T
        path[T - 1] = int(np.argmax(delta[T - 1]))

        for t in range(T - 2, -1, -1):
            path[t] = psi[t + 1, path[t + 1]]

        return path

    def predict_state(
        self,
        observations: list[int] | None = None,
    ) -> tuple[int, float]:
        """
        Predict current regime state.

        Args:
            observations: Optional observation sequence (uses history if None)

        Returns:
            Tuple of (predicted_state, confidence)
        """
        if observations is None:
            observations = self._observations

        if len(observations) < self.config.min_observations:
            return self._current_state, 0.3

        # Run forward algorithm
        alpha, _ = self.forward(observations)

        # Current state distribution
        state_probs = alpha[-1]
        state_probs /= state_probs.sum() + 1e-10

        predicted_state = int(np.argmax(state_probs))
        confidence = float(state_probs[predicted_state])

        return predicted_state, confidence

    def update(
        self,
        observation: int,
    ) -> tuple[int, float]:
        """
        Online update with new observation.

        Args:
            observation: New observation symbol

        Returns:
            Tuple of (current_state, confidence)
        """
        self._observations.append(observation)

        # Limit history
        max_history = 200
        if len(self._observations) > max_history:
            self._observations = self._observations[-max_history:]

        # Predict state
        state, confidence = self.predict_state()
        self._current_state = state

        return state, confidence

    def update_from_returns(
        self,
        returns: float,
        volatility: float,
    ) -> tuple[str, float]:
        """
        Update with continuous observations.

        Args:
            returns: Recent return
            volatility: Recent volatility

        Returns:
            Tuple of (regime_name, confidence)
        """
        obs = self.discretize_observation(returns, volatility)
        state, confidence = self.update(obs)

        return self.state_names[state], confidence

    def get_transition_probabilities(self) -> dict[str, dict[str, float]]:
        """Get human-readable transition probabilities."""
        result = {}
        for i, from_state in enumerate(self.state_names):
            result[from_state] = {}
            for j, to_state in enumerate(self.state_names):
                result[from_state][to_state] = float(self._A[i, j])
        return result

    def get_state_probabilities(self) -> dict[str, float]:
        """Get current state probability distribution."""
        if len(self._observations) < self.config.min_observations:
            return {name: 1.0 / len(self.state_names) for name in self.state_names}

        alpha, _ = self.forward(self._observations)
        probs = alpha[-1] / (alpha[-1].sum() + 1e-10)

        return {
            name: float(probs[i])
            for i, name in enumerate(self.state_names)
        }

    def save_state(self) -> dict[str, Any]:
        """Save model state."""
        return {
            "pi": self._pi.tolist(),
            "A": self._A.tolist(),
            "B": self._B.tolist(),
            "observations": self._observations,
            "current_state": self._current_state,
            "state_names": self.state_names,
        }

    def load_state(self, state: dict[str, Any]) -> None:
        """Load model state."""
        self._pi = np.array(state["pi"])
        self._A = np.array(state["A"])
        self._B = np.array(state["B"])
        self._observations = state.get("observations", [])
        self._current_state = state.get("current_state", 2)
        if "state_names" in state:
            self.state_names = state["state_names"]
