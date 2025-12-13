"""
Unit tests for Regime Detection module.

Tests HMM, feature extraction, and regime detection components.
"""

from __future__ import annotations

import numpy as np
import pytest

from reasoning_trading.regime import (
    HiddenMarkovModel,
    HMMConfig,
    RegimeClassification,
    RegimeDetector,
    RegimeDetectorConfig,
    RegimeFeatureExtractor,
    RegimeFeatures,
    RegimeHistory,
    RegimeState,
    TransitionMatrix,
)
from reasoning_trading.regime.features import RegimeFeatureConfig


class TestHMMConfig:
    """Test HMMConfig configuration."""

    def test_default_values(self) -> None:
        """Test default configuration."""
        config = HMMConfig()

        assert config.num_states == 5
        assert config.num_observations == 9
        assert config.min_observations > 0

    def test_env_override(self, monkeypatch) -> None:
        """Test environment override."""
        monkeypatch.setenv("HMM_NUM_STATES", "3")

        config = HMMConfig()
        assert config.num_states == 3

    def test_validation(self) -> None:
        """Test configuration validation."""
        # Should accept valid values
        config = HMMConfig(num_states=4, num_observations=5)
        assert config.num_states == 4

        # Should reject invalid values
        with pytest.raises(ValueError):
            HMMConfig(num_states=1)  # Too few states


class TestRegimeState:
    """Test RegimeState enum."""

    def test_regime_values(self) -> None:
        """Test regime state values."""
        assert RegimeState.BULL.value == "bull"
        assert RegimeState.BEAR.value == "bear"
        assert RegimeState.HIGH_VOLATILITY.value == "high_volatility"
        assert RegimeState.LOW_VOLATILITY.value == "low_volatility"
        assert RegimeState.NEUTRAL.value == "neutral"

    def test_all_regimes_present(self) -> None:
        """Test all expected regimes exist."""
        regimes = [r.value for r in RegimeState]
        assert "bull" in regimes
        assert "bear" in regimes
        assert "neutral" in regimes


class TestTransitionMatrix:
    """Test TransitionMatrix class."""

    def test_normalization(self) -> None:
        """Test matrix normalization."""
        matrix = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]], dtype=float)

        tm = TransitionMatrix(matrix=matrix)

        # Rows should sum to 1
        for row in tm.matrix:
            assert abs(row.sum() - 1.0) < 0.001

    def test_transition_prob(self) -> None:
        """Test getting transition probability."""
        matrix = np.array([[0.8, 0.1, 0.1], [0.1, 0.8, 0.1], [0.1, 0.1, 0.8]])

        tm = TransitionMatrix(matrix=matrix)

        assert abs(tm.get_transition_prob(0, 0) - 0.8) < 0.001
        assert abs(tm.get_transition_prob(0, 1) - 0.1) < 0.001

    def test_stationary_distribution(self) -> None:
        """Test stationary distribution."""
        matrix = np.array([[0.9, 0.05, 0.05], [0.1, 0.8, 0.1], [0.1, 0.1, 0.8]])

        tm = TransitionMatrix(matrix=matrix)
        stationary = tm.get_stationary_distribution()

        assert abs(stationary.sum() - 1.0) < 0.01
        assert len(stationary) == 3

    def test_serialization(self) -> None:
        """Test matrix serialization."""
        matrix = np.array([[0.5, 0.5], [0.5, 0.5]])
        tm = TransitionMatrix(matrix=matrix, state_names=["a", "b"])

        data = tm.to_dict()
        restored = TransitionMatrix.from_dict(data)

        np.testing.assert_array_almost_equal(tm.matrix, restored.matrix)
        assert tm.state_names == restored.state_names


class TestHiddenMarkovModel:
    """Test HiddenMarkovModel."""

    @pytest.fixture
    def hmm(self) -> HiddenMarkovModel:
        """Create HMM instance."""
        return HiddenMarkovModel()

    def test_initialization(self, hmm: HiddenMarkovModel) -> None:
        """Test HMM initialization."""
        assert len(hmm.state_names) == 5
        assert hmm._pi.shape[0] == 5
        assert hmm._A.shape == (5, 5)

    def test_discretize_observation_boundaries(self, hmm: HiddenMarkovModel) -> None:
        """Test observation discretization at boundaries."""
        # Extreme values
        obs_neg = hmm.discretize_observation(-0.05, 0.05)
        obs_pos = hmm.discretize_observation(0.05, 0.05)
        obs_neutral = hmm.discretize_observation(0.0, 0.02)

        assert 0 <= obs_neg <= 8
        assert 0 <= obs_pos <= 8
        assert 0 <= obs_neutral <= 8

    def test_forward_algorithm_shape(self, hmm: HiddenMarkovModel) -> None:
        """Test forward algorithm output shape."""
        obs = [4, 5, 6, 4, 5]

        alpha, ll = hmm.forward(obs)

        assert alpha.shape == (5, 5)
        assert np.isfinite(ll)

    def test_forward_normalized(self, hmm: HiddenMarkovModel) -> None:
        """Test forward probabilities are normalized."""
        obs = list(range(9))

        alpha, _ = hmm.forward(obs)

        for row in alpha:
            assert abs(row.sum() - 1.0) < 0.01

    def test_viterbi_path_length(self, hmm: HiddenMarkovModel) -> None:
        """Test Viterbi path has correct length."""
        obs = [4, 5, 6, 4, 5, 6, 4]

        path = hmm.viterbi(obs)

        assert len(path) == 7
        assert all(0 <= s < 5 for s in path)

    def test_backward_algorithm(self, hmm: HiddenMarkovModel) -> None:
        """Test backward algorithm."""
        obs = [4, 5, 6, 4, 5]

        beta = hmm.backward(obs)

        assert beta.shape == (5, 5)
        assert np.all(np.isfinite(beta))

    def test_update_increments_observations(self, hmm: HiddenMarkovModel) -> None:
        """Test update adds to observation history."""
        initial_len = len(hmm._observations)

        hmm.update(5)

        assert len(hmm._observations) == initial_len + 1

    def test_state_probabilities_sum_to_one(self, hmm: HiddenMarkovModel) -> None:
        """Test state probabilities sum to 1."""
        # Add enough observations
        for _ in range(25):
            hmm.update(np.random.randint(0, 9))

        probs = hmm.get_state_probabilities()

        assert abs(sum(probs.values()) - 1.0) < 0.01

    def test_save_load_state(self, hmm: HiddenMarkovModel) -> None:
        """Test state persistence."""
        for _ in range(10):
            hmm.update(np.random.randint(0, 9))

        saved = hmm.save_state()
        new_hmm = HiddenMarkovModel()
        new_hmm.load_state(saved)

        assert len(new_hmm._observations) == len(hmm._observations)
        np.testing.assert_array_almost_equal(new_hmm._A, hmm._A)


class TestRegimeFeatureConfig:
    """Test RegimeFeatureConfig."""

    def test_default_values(self) -> None:
        """Test default configuration."""
        config = RegimeFeatureConfig()

        assert config.short_lookback > 0
        assert config.medium_lookback > config.short_lookback
        assert config.long_lookback > config.medium_lookback

    def test_normalization_settings(self) -> None:
        """Test normalization settings."""
        config = RegimeFeatureConfig()

        assert isinstance(config.normalize_features, bool)
        assert isinstance(config.clip_outliers, bool)


class TestRegimeFeatures:
    """Test RegimeFeatures dataclass."""

    def test_default_values(self) -> None:
        """Test default feature values."""
        features = RegimeFeatures()

        assert features.returns_short == 0.0
        assert features.volatility_short == 0.0
        assert features.volume_ratio == 0.0

    def test_to_array(self) -> None:
        """Test conversion to numpy array."""
        features = RegimeFeatures(
            returns_short=0.01,
            volatility_short=0.02,
            trend_strength=0.5,
        )

        array = features.to_array()

        assert isinstance(array, np.ndarray)
        assert len(array) == 18

    def test_to_dict(self) -> None:
        """Test conversion to dictionary."""
        features = RegimeFeatures(
            returns_short=0.01,
            symbol="TEST",
        )

        data = features.to_dict()

        assert data["returns_short"] == 0.01
        assert data["symbol"] == "TEST"


class TestRegimeFeatureExtractor:
    """Test RegimeFeatureExtractor."""

    @pytest.fixture
    def extractor(self) -> RegimeFeatureExtractor:
        """Create extractor instance."""
        return RegimeFeatureExtractor()

    def test_extract_with_sufficient_data(self, extractor: RegimeFeatureExtractor) -> None:
        """Test extraction with enough data."""
        # Generate OHLCV data
        n = 100
        prices = np.cumsum(np.random.randn(n) * 0.01) + 100
        ohlcv = np.column_stack([
            prices,  # Open
            prices + np.abs(np.random.randn(n) * 0.5),  # High
            prices - np.abs(np.random.randn(n) * 0.5),  # Low
            prices,  # Close
            np.random.randint(100000, 1000000, n),  # Volume
        ])

        features = extractor.extract(ohlcv, "TEST")

        assert isinstance(features, RegimeFeatures)
        assert features.symbol == "TEST"

    def test_extract_with_insufficient_data(self, extractor: RegimeFeatureExtractor) -> None:
        """Test extraction with insufficient data."""
        ohlcv = np.random.randn(5, 5)  # Too few bars

        features = extractor.extract(ohlcv, "TEST")

        # Should return defaults
        assert features.returns_short == 0.0
        assert features.symbol == "TEST"

    def test_extract_batch(self, extractor: RegimeFeatureExtractor) -> None:
        """Test batch extraction."""
        n = 100
        data = {}
        for sym in ["A", "B", "C"]:
            prices = np.cumsum(np.random.randn(n) * 0.01) + 100
            data[sym] = np.column_stack([
                prices, prices + 0.5, prices - 0.5, prices,
                np.random.randint(100000, 1000000, n),
            ])

        features = extractor.extract_batch(data)

        assert len(features) == 3
        for sym in ["A", "B", "C"]:
            assert sym in features


class TestRegimeHistory:
    """Test RegimeHistory."""

    @pytest.fixture
    def history(self) -> RegimeHistory:
        """Create history instance."""
        return RegimeHistory()

    def test_add_classification(self, history: RegimeHistory) -> None:
        """Test adding classification."""
        classification = RegimeClassification(
            regime="bull",
            confidence=0.8,
        )

        history.add_classification(classification)

        assert len(history.classifications) == 1

    def test_regime_change_tracking(self, history: RegimeHistory) -> None:
        """Test regime change is tracked."""
        c1 = RegimeClassification(regime="bull", confidence=0.8)
        c2 = RegimeClassification(regime="bear", confidence=0.7)

        history.add_classification(c1)
        history.add_classification(c2)

        assert history.current_regime == "bear"

    def test_regime_frequency(self, history: RegimeHistory) -> None:
        """Test regime frequency calculation."""
        for regime in ["bull", "bull", "bear", "neutral"]:
            history.add_classification(
                RegimeClassification(regime=regime, confidence=0.7)
            )

        freq = history.get_regime_frequency()

        assert abs(freq["bull"] - 0.5) < 0.01
        assert abs(freq["bear"] - 0.25) < 0.01
        assert abs(freq["neutral"] - 0.25) < 0.01


class TestRegimeDetectorConfig:
    """Test RegimeDetectorConfig."""

    def test_default_values(self) -> None:
        """Test default configuration."""
        config = RegimeDetectorConfig()

        assert config.use_hmm is True
        assert 0 < config.hmm_weight <= 1
        assert config.change_confidence_threshold > 0

    def test_threshold_bounds(self) -> None:
        """Test threshold bounds."""
        config = RegimeDetectorConfig()

        assert 0 <= config.change_confidence_threshold <= 1
        assert config.min_regime_duration_seconds >= 0


class TestRegimeClassification:
    """Test RegimeClassification dataclass."""

    def test_creation(self) -> None:
        """Test classification creation."""
        classification = RegimeClassification(
            regime="bull",
            confidence=0.85,
            hmm_regime="bull",
            hmm_confidence=0.9,
            technical_regime="bull",
            technical_confidence=0.8,
        )

        assert classification.regime == "bull"
        assert classification.confidence == 0.85

    def test_to_dict(self) -> None:
        """Test serialization."""
        classification = RegimeClassification(
            regime="bear",
            confidence=0.7,
            symbol="TEST",
        )

        data = classification.to_dict()

        assert data["regime"] == "bear"
        assert data["confidence"] == 0.7
        assert data["symbol"] == "TEST"
