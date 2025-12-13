"""
Integration tests for Policy Networks and Distillation.

Tests fast policy inference, distillation training, and quantization.
"""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING

import numpy as np
import pytest

from reasoning_trading.policy import (
    DistilledPolicyNetwork,
    DistillationConfig,
    ModelQuantizer,
    ONNXExporter,
    PolicyConfig,
    PolicyDistillation,
    PolicyOutput,
    QuantizationConfig,
)

if TYPE_CHECKING:
    from tests.config import TestConfig
    from tests.factories import TradingStateFactory


class TestDistilledPolicyNetwork:
    """Test distilled policy network inference."""

    @pytest.fixture
    def policy_config(self) -> PolicyConfig:
        """Create policy configuration for tests."""
        return PolicyConfig(
            input_dim=50,
            hidden_dims=[64, 32],
            num_actions=7,
            use_onnx=False,  # CPU-only for tests
        )

    @pytest.fixture
    def policy_network(self, policy_config: PolicyConfig) -> DistilledPolicyNetwork:
        """Create policy network instance."""
        return DistilledPolicyNetwork(policy_config)

    def test_policy_output_structure(
        self,
        policy_network: DistilledPolicyNetwork,
        trading_state_factory: TradingStateFactory,
    ) -> None:
        """Test that policy output has correct structure."""
        state = trading_state_factory.create()
        features = state.to_feature_vector()

        # Adjust to expected input dimension
        if len(features) < 50:
            features = np.pad(features, (0, 50 - len(features)))
        else:
            features = features[:50]

        output = policy_network.predict(features)

        assert isinstance(output, PolicyOutput)
        assert output.best_action is not None
        assert len(output.action_probs) > 0
        assert output.max_prob > 0

    def test_policy_probabilities_normalized(
        self,
        policy_network: DistilledPolicyNetwork,
        trading_state_factory: TradingStateFactory,
    ) -> None:
        """Test that action probabilities sum to 1."""
        state = trading_state_factory.create()
        features = state.to_feature_vector()

        if len(features) < 50:
            features = np.pad(features, (0, 50 - len(features)))
        else:
            features = features[:50]

        output = policy_network.predict(features)

        total_prob = sum(output.action_probs.values())
        assert abs(total_prob - 1.0) < 0.01

    def test_inference_latency(
        self,
        policy_network: DistilledPolicyNetwork,
        trading_state_factory: TradingStateFactory,
        test_config: TestConfig,
    ) -> None:
        """Test that inference meets latency requirements."""
        state = trading_state_factory.create()
        features = state.to_feature_vector()

        if len(features) < 50:
            features = np.pad(features, (0, 50 - len(features)))
        else:
            features = features[:50]

        # Warm up
        for _ in range(5):
            policy_network.predict(features)

        # Measure latency
        start = time.perf_counter()
        for _ in range(100):
            policy_network.predict(features)
        elapsed_ms = (time.perf_counter() - start) * 1000 / 100

        # Should be fast (< 10ms per inference)
        assert elapsed_ms < 10.0

    def test_top_k_actions(
        self,
        policy_network: DistilledPolicyNetwork,
        trading_state_factory: TradingStateFactory,
    ) -> None:
        """Test getting top-k actions."""
        state = trading_state_factory.create()
        features = state.to_feature_vector()

        if len(features) < 50:
            features = np.pad(features, (0, 50 - len(features)))
        else:
            features = features[:50]

        output = policy_network.predict(features)
        top_3 = output.get_top_k_actions(3)

        assert len(top_3) == 3
        # Should be sorted by probability (descending)
        probs = [p for _, p in top_3]
        assert probs == sorted(probs, reverse=True)

    @pytest.mark.asyncio
    async def test_batch_inference(
        self,
        policy_network: DistilledPolicyNetwork,
        trading_state_factory: TradingStateFactory,
    ) -> None:
        """Test batched inference."""
        states = [trading_state_factory.create() for _ in range(10)]
        features_list = []

        for state in states:
            features = state.to_feature_vector()
            if len(features) < 50:
                features = np.pad(features, (0, 50 - len(features)))
            else:
                features = features[:50]
            features_list.append(features)

        outputs = await policy_network.predict_batch(features_list)

        assert len(outputs) == 10
        for output in outputs:
            assert output.best_action is not None
            assert abs(sum(output.action_probs.values()) - 1.0) < 0.01


class TestPolicyDistillation:
    """Test policy distillation from MCTS to neural network."""

    @pytest.fixture
    def distillation_config(self) -> DistillationConfig:
        """Create distillation configuration."""
        return DistillationConfig(
            student_hidden_dims=[64, 32],
            training_epochs=2,  # Fewer for tests
            batch_size=16,
            learning_rate=0.001,
        )

    def test_distillation_training_data(
        self,
        distillation_config: DistillationConfig,
        trading_state_factory: TradingStateFactory,
    ) -> None:
        """Test training data generation for distillation."""
        distillation = PolicyDistillation(distillation_config)

        # Generate sample training data
        training_data = []
        for _ in range(20):
            state = trading_state_factory.create()
            features = state.to_feature_vector()

            # Simulate MCTS output
            action_probs = {
                "hold_position": 0.3,
                "enter_long_position": 0.4,
                "exit_long_position": 0.1,
                "scale_in_position": 0.1,
                "scale_out_position": 0.1,
            }
            value = np.random.uniform(-1, 1)

            training_data.append((features, action_probs, value))

        # Should be able to add training data
        for features, probs, value in training_data:
            distillation.add_training_example(features, probs, value)

        assert distillation.training_buffer_size() == 20

    def test_student_initialization(
        self,
        distillation_config: DistillationConfig,
    ) -> None:
        """Test student network initialization."""
        distillation = PolicyDistillation(distillation_config)

        student = distillation.get_student_network()

        assert student is not None
        assert student.config.hidden_dims == [64, 32]


class TestQuantization:
    """Test model quantization for faster inference."""

    @pytest.fixture
    def quantization_config(self) -> QuantizationConfig:
        """Create quantization configuration."""
        return QuantizationConfig(
            quantization_type="dynamic",
            target_precision="int8",
        )

    @pytest.fixture
    def quantizer(self, quantization_config: QuantizationConfig) -> ModelQuantizer:
        """Create quantizer instance."""
        return ModelQuantizer(quantization_config)

    def test_quantizer_creation(self, quantizer: ModelQuantizer) -> None:
        """Test quantizer can be created."""
        assert quantizer is not None
        assert quantizer.config.target_precision == "int8"

    def test_calibration_data_collection(
        self,
        quantizer: ModelQuantizer,
        trading_state_factory: TradingStateFactory,
    ) -> None:
        """Test calibration data collection for quantization."""
        # Generate calibration data
        calibration_data = []
        for _ in range(50):
            state = trading_state_factory.create()
            features = state.to_feature_vector()
            calibration_data.append(features)

        # Should be able to set calibration data
        quantizer.set_calibration_data(np.array(calibration_data))

        assert quantizer.has_calibration_data()


class TestONNXExport:
    """Test ONNX model export."""

    @pytest.fixture
    def exporter(self) -> ONNXExporter:
        """Create ONNX exporter."""
        return ONNXExporter()

    @pytest.fixture
    def policy_network(self) -> DistilledPolicyNetwork:
        """Create policy network to export."""
        config = PolicyConfig(
            input_dim=50,
            hidden_dims=[64, 32],
            num_actions=7,
        )
        return DistilledPolicyNetwork(config)

    def test_export_creates_model(
        self,
        exporter: ONNXExporter,
        policy_network: DistilledPolicyNetwork,
        tmp_path,
    ) -> None:
        """Test that ONNX export creates a model file."""
        model_path = tmp_path / "policy.onnx"

        result = exporter.export(policy_network, str(model_path))

        assert result.success
        assert model_path.exists()
        assert result.model_size_bytes > 0

    def test_exported_model_inference(
        self,
        exporter: ONNXExporter,
        policy_network: DistilledPolicyNetwork,
        trading_state_factory: TradingStateFactory,
        tmp_path,
    ) -> None:
        """Test that exported model produces same output."""
        model_path = tmp_path / "policy.onnx"
        exporter.export(policy_network, str(model_path))

        # Create test input
        state = trading_state_factory.create()
        features = state.to_feature_vector()
        if len(features) < 50:
            features = np.pad(features, (0, 50 - len(features)))
        else:
            features = features[:50]

        # Get outputs from both
        original_output = policy_network.predict(features)
        onnx_output = exporter.run_inference(str(model_path), features)

        # Should be close (may have small numerical differences)
        assert original_output.best_action == onnx_output.best_action


class TestPolicyNetworkIntegration:
    """Integration tests for policy network pipeline."""

    @pytest.mark.asyncio
    async def test_full_distillation_pipeline(
        self,
        trading_state_factory: TradingStateFactory,
    ) -> None:
        """Test complete distillation pipeline."""
        # Create distillation instance
        config = DistillationConfig(
            student_hidden_dims=[32, 16],
            training_epochs=1,
            batch_size=8,
        )
        distillation = PolicyDistillation(config)

        # Generate training data
        for _ in range(50):
            state = trading_state_factory.create()
            features = state.to_feature_vector()

            # Simulated MCTS output
            probs = {
                "hold": 0.3 + np.random.uniform(-0.1, 0.1),
                "buy": 0.4 + np.random.uniform(-0.1, 0.1),
                "sell": 0.3 + np.random.uniform(-0.1, 0.1),
            }
            # Normalize
            total = sum(probs.values())
            probs = {k: v / total for k, v in probs.items()}

            value = np.random.uniform(-1, 1)
            distillation.add_training_example(features, probs, value)

        # Train
        metrics = await distillation.train_student()

        assert "loss" in metrics
        assert metrics["loss"] < 10  # Should improve from random

        # Get trained student
        student = distillation.get_student_network()
        assert student is not None

    @pytest.mark.asyncio
    async def test_inference_consistency(
        self,
        trading_state_factory: TradingStateFactory,
    ) -> None:
        """Test inference produces consistent results."""
        config = PolicyConfig(
            input_dim=50,
            hidden_dims=[32, 16],
            num_actions=5,
        )
        network = DistilledPolicyNetwork(config)

        state = trading_state_factory.create()
        features = state.to_feature_vector()
        if len(features) < 50:
            features = np.pad(features, (0, 50 - len(features)))
        else:
            features = features[:50]

        # Multiple inferences should be identical
        outputs = [network.predict(features) for _ in range(5)]

        for output in outputs[1:]:
            assert output.best_action == outputs[0].best_action
            for action in output.action_probs:
                assert abs(output.action_probs[action] - outputs[0].action_probs[action]) < 0.001
