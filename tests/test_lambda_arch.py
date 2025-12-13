"""
Unit tests for Lambda Architecture module.

Tests batch layer, speed layer, serving layer, and coordinator components.
"""

from __future__ import annotations

from datetime import datetime

import numpy as np
import pytest

from reasoning_trading.lambda_arch import (
    BatchLayer,
    BatchLayerConfig,
    LambdaCoordinator,
    LambdaCoordinatorConfig,
    PolicyCache,
    PolicyCacheConfig,
    ServingLayer,
    ServingLayerConfig,
    SpeedLayer,
    SpeedLayerConfig,
)
from reasoning_trading.lambda_arch.speed_layer import (
    DecisionSource,
    RealtimeDecision,
    SpeedLayerMetrics,
)


class TestBatchLayerConfig:
    """Test BatchLayerConfig configuration."""

    def test_default_values(self) -> None:
        """Test default configuration."""
        config = BatchLayerConfig()

        assert config.strategic_simulations > 0
        assert config.precompute_states > 0
        assert config.batch_timeout_seconds > 0

    def test_env_override(self, monkeypatch) -> None:
        """Test environment override."""
        monkeypatch.setenv("BATCH_STRATEGIC_SIMULATIONS", "1000")

        config = BatchLayerConfig()
        assert config.strategic_simulations == 1000


class TestBatchLayer:
    """Test BatchLayer."""

    @pytest.fixture
    def batch_layer(self) -> BatchLayer:
        """Create batch layer instance."""
        return BatchLayer()

    def test_creation(self, batch_layer: BatchLayer) -> None:
        """Test batch layer creation."""
        assert batch_layer is not None

    def test_schedule_job(self, batch_layer: BatchLayer) -> None:
        """Test job scheduling."""
        job_id = batch_layer.schedule_job(
            job_type="strategic_mcts",
            priority=1,
        )

        assert job_id is not None
        assert batch_layer.has_pending_jobs()

    def test_get_pending_jobs(self, batch_layer: BatchLayer) -> None:
        """Test getting pending jobs."""
        batch_layer.schedule_job("type1", 1)
        batch_layer.schedule_job("type2", 2)

        jobs = batch_layer.get_pending_jobs()
        assert len(jobs) == 2


class TestSpeedLayerConfig:
    """Test SpeedLayerConfig configuration."""

    def test_default_values(self) -> None:
        """Test default configuration."""
        config = SpeedLayerConfig()

        assert config.target_latency_ms > 0
        assert config.max_latency_ms > config.target_latency_ms
        assert config.policy_inference_timeout_ms > 0

    def test_latency_bounds(self) -> None:
        """Test latency bounds are reasonable."""
        config = SpeedLayerConfig()

        assert config.target_latency_ms >= 1.0
        assert config.max_latency_ms <= 5000.0


class TestDecisionSource:
    """Test DecisionSource enum."""

    def test_all_sources(self) -> None:
        """Test all decision sources exist."""
        sources = [s.value for s in DecisionSource]

        assert "policy_network" in sources
        assert "cache_hit" in sources
        assert "heuristic" in sources
        assert "mcts_lite" in sources


class TestRealtimeDecision:
    """Test RealtimeDecision dataclass."""

    def test_creation(self) -> None:
        """Test decision creation."""
        decision = RealtimeDecision(
            action_type="hold_position",
            confidence=0.8,
            source=DecisionSource.POLICY_NETWORK,
        )

        assert decision.action_type == "hold_position"
        assert decision.confidence == 0.8
        assert decision.source == DecisionSource.POLICY_NETWORK

    def test_to_dict(self) -> None:
        """Test serialization."""
        decision = RealtimeDecision(
            action_type="buy",
            confidence=0.9,
            latency_ms=5.0,
        )

        data = decision.to_dict()

        assert data["action_type"] == "buy"
        assert data["confidence"] == 0.9
        assert data["latency_ms"] == 5.0


class TestSpeedLayerMetrics:
    """Test SpeedLayerMetrics dataclass."""

    def test_default_values(self) -> None:
        """Test default metric values."""
        metrics = SpeedLayerMetrics()

        assert metrics.avg_latency_ms == 0.0
        assert metrics.total_decisions == 0

    def test_to_dict(self) -> None:
        """Test serialization."""
        metrics = SpeedLayerMetrics(
            avg_latency_ms=5.0,
            p95_latency_ms=10.0,
            total_decisions=100,
        )

        data = metrics.to_dict()

        assert data["avg_latency_ms"] == 5.0
        assert data["total_decisions"] == 100


class TestSpeedLayer:
    """Test SpeedLayer."""

    @pytest.fixture
    def speed_layer(self) -> SpeedLayer:
        """Create speed layer instance."""
        return SpeedLayer()

    def test_creation(self, speed_layer: SpeedLayer) -> None:
        """Test speed layer creation."""
        assert speed_layer is not None

    def test_get_metrics(self, speed_layer: SpeedLayer) -> None:
        """Test getting metrics."""
        metrics = speed_layer.get_metrics()

        assert isinstance(metrics, SpeedLayerMetrics)

    def test_reset_metrics(self, speed_layer: SpeedLayer) -> None:
        """Test resetting metrics."""
        speed_layer.reset_metrics()

        metrics = speed_layer.get_metrics()
        assert metrics.total_decisions == 0


class TestPolicyCacheConfig:
    """Test PolicyCacheConfig configuration."""

    def test_default_values(self) -> None:
        """Test default configuration."""
        config = PolicyCacheConfig()

        assert config.max_entries > 0
        assert config.ttl_seconds > 0
        assert 0 <= config.similarity_threshold <= 1


class TestPolicyCache:
    """Test PolicyCache."""

    @pytest.fixture
    def cache(self) -> PolicyCache:
        """Create cache instance."""
        return PolicyCache()

    @pytest.mark.asyncio
    async def test_put_get(self, cache: PolicyCache) -> None:
        """Test cache put and get."""
        policy = {"action": "buy", "confidence": 0.8}
        features = np.random.randn(50)

        await cache.put("key1", policy, features)
        result = await cache.get("key1")

        assert result is not None
        assert result["action"] == "buy"

    @pytest.mark.asyncio
    async def test_cache_miss(self, cache: PolicyCache) -> None:
        """Test cache miss."""
        result = await cache.get("nonexistent")

        assert result is None

    def test_get_statistics(self, cache: PolicyCache) -> None:
        """Test getting cache statistics."""
        stats = cache.get_statistics()

        assert "size" in stats
        assert "hit_rate" in stats


class TestServingLayerConfig:
    """Test ServingLayerConfig configuration."""

    def test_default_values(self) -> None:
        """Test default configuration."""
        config = ServingLayerConfig()

        assert config.cache_max_entries > 0
        assert config.cache_ttl_seconds > 0


class TestServingLayer:
    """Test ServingLayer."""

    @pytest.fixture
    def serving_layer(self) -> ServingLayer:
        """Create serving layer instance."""
        return ServingLayer()

    def test_creation(self, serving_layer: ServingLayer) -> None:
        """Test serving layer creation."""
        assert serving_layer is not None


class TestLambdaCoordinatorConfig:
    """Test LambdaCoordinatorConfig configuration."""

    def test_default_values(self) -> None:
        """Test default configuration."""
        config = LambdaCoordinatorConfig()

        assert config.regime_check_interval_seconds > 0
        assert isinstance(config.batch_trigger_on_regime_change, bool)


class TestLambdaCoordinator:
    """Test LambdaCoordinator."""

    @pytest.fixture
    def coordinator(self) -> LambdaCoordinator:
        """Create coordinator instance."""
        return LambdaCoordinator()

    def test_creation(self, coordinator: LambdaCoordinator) -> None:
        """Test coordinator creation."""
        assert coordinator is not None

    def test_get_statistics(self, coordinator: LambdaCoordinator) -> None:
        """Test getting statistics."""
        stats = coordinator.get_statistics()

        assert "total_decisions" in stats
        assert "batch_triggers" in stats

    def test_clear_cache(self, coordinator: LambdaCoordinator) -> None:
        """Test clearing cache."""
        # Should not raise
        coordinator.clear_cache()
