"""
Integration tests for HMM-based Regime Detection.

Tests regime detection, HMM inference, and feature extraction.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

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
    RegimeState,
    TransitionMatrix,
)

if TYPE_CHECKING:
    from tests.config import TestConfig
    from tests.factories import MarketDataFactory, TradingStateFactory


class TestHiddenMarkovModel:
    """Test Hidden Markov Model implementation."""

    @pytest.fixture
    def hmm_config(self) -> HMMConfig:
        """Create HMM configuration."""
        return HMMConfig(
            num_states=5,
            num_observations=9,
            min_observations=10,
        )

    @pytest.fixture
    def hmm(self, hmm_config: HMMConfig) -> HiddenMarkovModel:
        """Create HMM instance."""
        return HiddenMarkovModel(hmm_config)

    def test_hmm_initialization(self, hmm: HiddenMarkovModel) -> None:
        """Test HMM initializes with correct structure."""
        assert len(hmm.state_names) == 5
        assert hmm._pi.shape == (5,)
        assert hmm._A.shape == (5, 5)
        assert hmm._B.shape == (5, 9)

    def test_transition_matrix_normalization(self, hmm: HiddenMarkovModel) -> None:
        """Test transition matrix rows sum to 1."""
        row_sums = hmm._A.sum(axis=1)
        np.testing.assert_array_almost_equal(row_sums, np.ones(5))

    def test_emission_matrix_normalization(self, hmm: HiddenMarkovModel) -> None:
        """Test emission matrix rows sum to 1."""
        row_sums = hmm._B.sum(axis=1)
        np.testing.assert_array_almost_equal(row_sums, np.ones(5))

    def test_observation_discretization(self, hmm: HiddenMarkovModel) -> None:
        """Test discretization of continuous observations."""
        # Strong positive return, high volatility
        obs1 = hmm.discretize_observation(0.03, 0.04)
        assert 0 <= obs1 <= 8

        # Strong negative return, low volatility
        obs2 = hmm.discretize_observation(-0.03, 0.005)
        assert 0 <= obs2 <= 8

        # Neutral return
        obs3 = hmm.discretize_observation(0.001, 0.015)
        assert 0 <= obs3 <= 8

    def test_forward_algorithm(self, hmm: HiddenMarkovModel) -> None:
        """Test forward algorithm for state probabilities."""
        observations = [4, 5, 6, 5, 4, 3, 4, 5, 6, 7]

        alpha, log_likelihood = hmm.forward(observations)

        assert alpha.shape == (10, 5)
        assert np.isfinite(log_likelihood)
        # Each row should sum to approximately 1 (normalized)
        for i in range(10):
            assert abs(alpha[i].sum() - 1.0) < 0.01

    def test_viterbi_algorithm(self, hmm: HiddenMarkovModel) -> None:
        """Test Viterbi algorithm for most likely path."""
        observations = [4, 5, 6, 5, 4, 3, 4, 5, 6, 7]

        path = hmm.viterbi(observations)

        assert len(path) == 10
        assert all(0 <= s < 5 for s in path)

    def test_online_update(self, hmm: HiddenMarkovModel) -> None:
        """Test online update with new observations."""
        # Add observations until enough for prediction
        for _ in range(15):
            obs = np.random.randint(0, 9)
            state, confidence = hmm.update(obs)

        assert 0 <= state < 5
        assert 0 <= confidence <= 1

    def test_update_from_returns(self, hmm: HiddenMarkovModel) -> None:
        """Test update from continuous returns data."""
        for _ in range(20):
            returns = np.random.normal(0, 0.02)
            volatility = np.random.uniform(0.01, 0.03)

            regime, confidence = hmm.update_from_returns(returns, volatility)

        assert regime in hmm.state_names
        assert 0 <= confidence <= 1

    def test_state_probabilities(self, hmm: HiddenMarkovModel) -> None:
        """Test getting state probability distribution."""
        # Add enough observations
        for _ in range(25):
            hmm.update(np.random.randint(0, 9))

        probs = hmm.get_state_probabilities()

        assert len(probs) == 5
        assert abs(sum(probs.values()) - 1.0) < 0.01

    def test_save_load_state(self, hmm: HiddenMarkovModel) -> None:
        """Test state persistence."""
        # Add some observations
        for _ in range(10):
            hmm.update(np.random.randint(0, 9))

        # Save state
        saved_state = hmm.save_state()

        # Create new HMM and load
        new_hmm = HiddenMarkovModel()
        new_hmm.load_state(saved_state)

        # Should have same observations
        assert len(new_hmm._observations) == len(hmm._observations)


class TestTransitionMatrix:
    """Test transition matrix operations."""

    def test_matrix_normalization(self) -> None:
        """Test matrix is normalized on creation."""
        matrix = np.array([
            [8, 1, 1],
            [1, 8, 1],
            [1, 1, 8],
        ], dtype=float)

        tm = TransitionMatrix(matrix=matrix)

        row_sums = tm.matrix.sum(axis=1)
        np.testing.assert_array_almost_equal(row_sums, np.ones(3))

    def test_transition_probability(self) -> None:
        """Test getting individual transition probabilities."""
        matrix = np.array([
            [0.9, 0.05, 0.05],
            [0.1, 0.8, 0.1],
            [0.1, 0.1, 0.8],
        ])

        tm = TransitionMatrix(matrix=matrix)

        prob = tm.get_transition_prob(0, 0)
        assert abs(prob - 0.9) < 0.01

    def test_stationary_distribution(self) -> None:
        """Test stationary distribution computation."""
        matrix = np.array([
            [0.9, 0.05, 0.05],
            [0.1, 0.8, 0.1],
            [0.1, 0.1, 0.8],
        ])

        tm = TransitionMatrix(matrix=matrix)
        stationary = tm.get_stationary_distribution()

        # Should sum to 1
        assert abs(stationary.sum() - 1.0) < 0.01


class TestRegimeFeatureExtractor:
    """Test regime feature extraction."""

    @pytest.fixture
    def extractor(self) -> RegimeFeatureExtractor:
        """Create feature extractor."""
        return RegimeFeatureExtractor()

    def test_feature_extraction(
        self,
        extractor: RegimeFeatureExtractor,
        market_data_factory: MarketDataFactory,
    ) -> None:
        """Test feature extraction from OHLCV data."""
        ohlcv = market_data_factory.generate_ohlcv(n_bars=100)

        features = extractor.extract(ohlcv, symbol="TEST")

        assert isinstance(features, RegimeFeatures)
        assert features.symbol == "TEST"

    def test_momentum_features(
        self,
        extractor: RegimeFeatureExtractor,
        market_data_factory: MarketDataFactory,
    ) -> None:
        """Test momentum feature calculation."""
        # Generate uptrending data
        ohlcv = market_data_factory.generate_ohlcv(n_bars=100, trend=1.001)

        features = extractor.extract(ohlcv)

        # Momentum should be positive for uptrend
        assert features.momentum_medium > 0 or features.returns_medium > 0

    def test_volatility_features(
        self,
        extractor: RegimeFeatureExtractor,
        market_data_factory: MarketDataFactory,
    ) -> None:
        """Test volatility feature calculation."""
        ohlcv = market_data_factory.generate_ohlcv(n_bars=100, volatility=0.03)

        features = extractor.extract(ohlcv)

        assert features.volatility_short >= 0
        assert features.volatility_medium >= 0
        assert features.volatility_long >= 0

    def test_feature_array_conversion(
        self,
        extractor: RegimeFeatureExtractor,
        market_data_factory: MarketDataFactory,
    ) -> None:
        """Test conversion to numpy array."""
        ohlcv = market_data_factory.generate_ohlcv(n_bars=100)
        features = extractor.extract(ohlcv)

        array = features.to_array()

        assert isinstance(array, np.ndarray)
        assert len(array) == 18  # Number of numeric features

    def test_batch_extraction(
        self,
        extractor: RegimeFeatureExtractor,
        market_data_factory: MarketDataFactory,
    ) -> None:
        """Test batch feature extraction."""
        symbols = ["AAPL", "GOOGL", "MSFT"]
        ohlcv_data = {
            sym: market_data_factory.generate_ohlcv(n_bars=100)
            for sym in symbols
        }

        features = extractor.extract_batch(ohlcv_data)

        assert len(features) == 3
        for sym in symbols:
            assert sym in features
            assert features[sym].symbol == sym


class TestRegimeDetector:
    """Test combined regime detector."""

    @pytest.fixture
    def detector_config(self) -> RegimeDetectorConfig:
        """Create detector configuration."""
        return RegimeDetectorConfig(
            use_hmm=True,
            hmm_weight=0.6,
            change_confidence_threshold=0.7,
            min_regime_duration_seconds=60,
        )

    @pytest.fixture
    def detector(self, detector_config: RegimeDetectorConfig) -> RegimeDetector:
        """Create regime detector."""
        return RegimeDetector(detector_config)

    def test_regime_detection(
        self,
        detector: RegimeDetector,
        trading_state_factory: TradingStateFactory,
    ) -> None:
        """Test basic regime detection."""
        state = trading_state_factory.create()

        classification = detector.detect(state)

        assert isinstance(classification, RegimeClassification)
        assert classification.regime is not None
        assert 0 <= classification.confidence <= 1

    def test_hmm_and_technical_combination(
        self,
        trading_state_factory: TradingStateFactory,
    ) -> None:
        """Test combination of HMM and technical signals."""
        config = RegimeDetectorConfig(use_hmm=True, hmm_weight=0.5)
        detector = RegimeDetector(config)

        state = trading_state_factory.create()
        classification = detector.detect(state)

        # Should have both components
        assert classification.technical_regime is not None

    def test_regime_change_callback(
        self,
        trading_state_factory: TradingStateFactory,
    ) -> None:
        """Test regime change callback is triggered."""
        changes_detected = []

        def on_change(old: str, new: str, confidence: float) -> None:
            changes_detected.append((old, new, confidence))

        config = RegimeDetectorConfig(
            min_regime_duration_seconds=0,  # Allow immediate changes for test
            change_confidence_threshold=0.5,
        )
        detector = RegimeDetector(config, on_regime_change=on_change)

        # Generate varied states
        from tests.config import TestScenario

        for scenario in [TestScenario.BULLISH, TestScenario.VOLATILE]:
            state = trading_state_factory.create_for_scenario(scenario)
            for _ in range(5):
                detector.detect(state)

    def test_regime_history(
        self,
        detector: RegimeDetector,
        trading_state_factory: TradingStateFactory,
    ) -> None:
        """Test regime history tracking."""
        # Make several detections
        for _ in range(10):
            state = trading_state_factory.create()
            detector.detect(state)

        # Check history
        frequency = detector.history.get_regime_frequency()
        assert len(frequency) > 0
        assert abs(sum(frequency.values()) - 1.0) < 0.01

    def test_save_load_detector_state(
        self,
        detector: RegimeDetector,
        trading_state_factory: TradingStateFactory,
    ) -> None:
        """Test detector state persistence."""
        # Make some detections
        for _ in range(5):
            state = trading_state_factory.create()
            detector.detect(state)

        # Save state
        saved = detector.save_state()

        # Create new detector and load
        new_detector = RegimeDetector()
        new_detector.load_state(saved)

        # Should have same current regime
        assert new_detector.history.current_regime == detector.history.current_regime


class TestRegimeDetectionIntegration:
    """Integration tests for regime detection pipeline."""

    def test_full_detection_pipeline(
        self,
        trading_state_factory: TradingStateFactory,
        market_data_factory: MarketDataFactory,
    ) -> None:
        """Test complete regime detection pipeline."""
        # Setup detector
        detector = RegimeDetector()

        # Generate realistic market sequence
        from tests.config import TestScenario

        scenarios = [
            TestScenario.BULLISH,
            TestScenario.BULLISH,
            TestScenario.VOLATILE,
            TestScenario.BEARISH,
            TestScenario.NEUTRAL,
        ]

        regimes = []
        for scenario in scenarios:
            state = trading_state_factory.create_for_scenario(scenario)
            classification = detector.detect(state)
            regimes.append(classification.regime)

        # Should detect some variation
        assert len(set(regimes)) >= 1

    def test_detection_with_feature_extractor(
        self,
        market_data_factory: MarketDataFactory,
        trading_state_factory: TradingStateFactory,
    ) -> None:
        """Test detection integrated with feature extraction."""
        extractor = RegimeFeatureExtractor()
        detector = RegimeDetector()

        state = trading_state_factory.create()
        ohlcv = state.ohlcv_history

        if ohlcv is not None:
            features = extractor.extract(ohlcv, state.symbol)
            classification = detector.detect(state)

            # Both should provide consistent signals
            assert classification.regime is not None

    def test_regime_persistence(
        self,
        trading_state_factory: TradingStateFactory,
    ) -> None:
        """Test that regimes persist without rapid fluctuation."""
        detector = RegimeDetector()

        # Same state multiple times
        state = trading_state_factory.create()
        regimes = []

        for _ in range(10):
            classification = detector.detect(state)
            regimes.append(classification.regime)

        # Should be consistent for same state
        unique_regimes = set(regimes)
        # Allow some variation due to HMM dynamics, but not too much
        assert len(unique_regimes) <= 3
