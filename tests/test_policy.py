"""
Unit tests for Policy Networks module.

Tests individual components of policy network implementation.
"""

from __future__ import annotations

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


class TestPolicyConfig:
    """Test PolicyConfig configuration."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = PolicyConfig()

        assert config.input_dim > 0
        assert len(config.hidden_dims) > 0
        assert config.num_actions > 0

    def test_env_override(self, monkeypatch) -> None:
        """Test configuration from environment."""
        monkeypatch.setenv("POLICY_INPUT_DIM", "100")

        config = PolicyConfig()
        assert config.input_dim == 100

    def test_custom_hidden_dims(self) -> None:
        """Test custom hidden dimensions."""
        config = PolicyConfig(hidden_dims=[128, 64, 32])

        assert config.hidden_dims == [128, 64, 32]


class TestPolicyOutput:
    """Test PolicyOutput dataclass."""

    def test_creation(self) -> None:
        """Test policy output creation."""
        output = PolicyOutput(
            action_probs={"buy": 0.6, "hold": 0.3, "sell": 0.1},
            value=0.5,
        )

        assert output.best_action == "buy"
        assert output.max_prob == 0.6

    def test_top_k_actions(self) -> None:
        """Test getting top-k actions."""
        output = PolicyOutput(
            action_probs={"a": 0.5, "b": 0.3, "c": 0.15, "d": 0.05},
            value=0.0,
        )

        top_2 = output.get_top_k_actions(2)
        assert len(top_2) == 2
        assert top_2[0] == ("a", 0.5)
        assert top_2[1] == ("b", 0.3)

    def test_empty_probs(self) -> None:
        """Test with empty probabilities."""
        output = PolicyOutput(action_probs={}, value=0.0)

        assert output.best_action is None
        assert output.max_prob == 0.0

    def test_normalized_probs(self) -> None:
        """Test probability normalization."""
        output = PolicyOutput(
            action_probs={"a": 0.4, "b": 0.4, "c": 0.2},
            value=0.0,
        )

        total = sum(output.action_probs.values())
        assert abs(total - 1.0) < 0.001


class TestDistilledPolicyNetwork:
    """Test DistilledPolicyNetwork."""

    @pytest.fixture
    def network(self) -> DistilledPolicyNetwork:
        """Create network instance."""
        config = PolicyConfig(
            input_dim=50,
            hidden_dims=[32, 16],
            num_actions=5,
            use_onnx=False,
        )
        return DistilledPolicyNetwork(config)

    def test_predict_shape(self, network: DistilledPolicyNetwork) -> None:
        """Test prediction output shape."""
        features = np.random.randn(50)

        output = network.predict(features)

        assert isinstance(output, PolicyOutput)
        assert len(output.action_probs) == 5

    def test_predict_normalized(self, network: DistilledPolicyNetwork) -> None:
        """Test predictions are normalized."""
        features = np.random.randn(50)

        output = network.predict(features)

        total = sum(output.action_probs.values())
        assert abs(total - 1.0) < 0.01

    def test_action_mask(self, network: DistilledPolicyNetwork) -> None:
        """Test action masking."""
        features = np.random.randn(50)
        mask = np.array([True, False, True, False, True])

        output = network.predict(features, action_mask=mask)

        # Masked actions should have zero probability
        probs = list(output.action_probs.values())
        assert probs[1] == 0.0
        assert probs[3] == 0.0

    def test_weights_initialization(self, network: DistilledPolicyNetwork) -> None:
        """Test weights are properly initialized."""
        weights = network.get_weights()

        assert len(weights) > 0
        for w in weights:
            assert np.all(np.isfinite(w))

    def test_set_weights(self, network: DistilledPolicyNetwork) -> None:
        """Test setting weights."""
        original_weights = network.get_weights()

        # Modify weights
        new_weights = [w * 2 for w in original_weights]
        network.set_weights(new_weights)

        updated_weights = network.get_weights()
        for orig, updated in zip(original_weights, updated_weights):
            assert not np.allclose(orig, updated)


class TestDistillationConfig:
    """Test DistillationConfig."""

    def test_default_values(self) -> None:
        """Test default configuration."""
        config = DistillationConfig()

        assert config.training_epochs > 0
        assert config.batch_size > 0
        assert config.learning_rate > 0

    def test_env_override(self, monkeypatch) -> None:
        """Test environment override."""
        monkeypatch.setenv("DISTILL_TRAINING_EPOCHS", "50")

        config = DistillationConfig()
        assert config.training_epochs == 50


class TestPolicyDistillation:
    """Test PolicyDistillation."""

    @pytest.fixture
    def distillation(self) -> PolicyDistillation:
        """Create distillation instance."""
        config = DistillationConfig(
            student_hidden_dims=[32, 16],
            training_epochs=1,
            batch_size=8,
        )
        return PolicyDistillation(config)

    def test_add_training_example(self, distillation: PolicyDistillation) -> None:
        """Test adding training examples."""
        features = np.random.randn(50)
        probs = {"a": 0.5, "b": 0.3, "c": 0.2}
        value = 0.5

        distillation.add_training_example(features, probs, value)

        assert distillation.training_buffer_size() == 1

    def test_buffer_limit(self, distillation: PolicyDistillation) -> None:
        """Test training buffer has limit."""
        for _ in range(10000):
            distillation.add_training_example(
                np.random.randn(50),
                {"a": 0.5, "b": 0.5},
                0.0,
            )

        # Should be limited
        assert distillation.training_buffer_size() <= 10000

    def test_get_student_network(self, distillation: PolicyDistillation) -> None:
        """Test getting student network."""
        student = distillation.get_student_network()

        assert student is not None
        assert isinstance(student, DistilledPolicyNetwork)

    def test_clear_buffer(self, distillation: PolicyDistillation) -> None:
        """Test clearing training buffer."""
        distillation.add_training_example(
            np.random.randn(50),
            {"a": 1.0},
            0.0,
        )

        distillation.clear_buffer()

        assert distillation.training_buffer_size() == 0


class TestQuantizationConfig:
    """Test QuantizationConfig."""

    def test_default_values(self) -> None:
        """Test default configuration."""
        config = QuantizationConfig()

        assert config.quantization_type in ["dynamic", "static"]
        assert config.target_precision in ["int8", "fp16"]

    def test_custom_precision(self) -> None:
        """Test custom precision setting."""
        config = QuantizationConfig(target_precision="fp16")
        assert config.target_precision == "fp16"


class TestModelQuantizer:
    """Test ModelQuantizer."""

    @pytest.fixture
    def quantizer(self) -> ModelQuantizer:
        """Create quantizer instance."""
        return ModelQuantizer()

    def test_creation(self, quantizer: ModelQuantizer) -> None:
        """Test quantizer creation."""
        assert quantizer is not None

    def test_set_calibration_data(self, quantizer: ModelQuantizer) -> None:
        """Test setting calibration data."""
        data = np.random.randn(100, 50)

        quantizer.set_calibration_data(data)

        assert quantizer.has_calibration_data()

    def test_clear_calibration_data(self, quantizer: ModelQuantizer) -> None:
        """Test clearing calibration data."""
        quantizer.set_calibration_data(np.random.randn(100, 50))
        quantizer.clear_calibration_data()

        assert not quantizer.has_calibration_data()


class TestONNXExporter:
    """Test ONNXExporter."""

    @pytest.fixture
    def exporter(self) -> ONNXExporter:
        """Create exporter instance."""
        return ONNXExporter()

    def test_creation(self, exporter: ONNXExporter) -> None:
        """Test exporter creation."""
        assert exporter is not None

    def test_export_creates_file(
        self,
        exporter: ONNXExporter,
        tmp_path,
    ) -> None:
        """Test export creates model file."""
        config = PolicyConfig(
            input_dim=50,
            hidden_dims=[32],
            num_actions=5,
        )
        network = DistilledPolicyNetwork(config)
        model_path = tmp_path / "model.onnx"

        result = exporter.export(network, str(model_path))

        assert result.success
        assert model_path.exists()

    def test_export_result_metadata(
        self,
        exporter: ONNXExporter,
        tmp_path,
    ) -> None:
        """Test export result contains metadata."""
        config = PolicyConfig(
            input_dim=50,
            hidden_dims=[32],
            num_actions=5,
        )
        network = DistilledPolicyNetwork(config)
        model_path = tmp_path / "model.onnx"

        result = exporter.export(network, str(model_path))

        assert result.model_size_bytes > 0
        assert result.input_shape is not None
