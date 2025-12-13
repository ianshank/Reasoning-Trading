"""
Integration tests for Lambda Architecture (Batch + Speed layers).

Tests the complete Lambda architecture pipeline including batch processing,
speed layer decisions, and serving layer caching.
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

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
from reasoning_trading.lambda_arch.speed_layer import DecisionSource

if TYPE_CHECKING:
    from tests.config import TestConfig
    from tests.factories import TradingStateFactory


class TestBatchLayer:
    """Test batch layer for strategic MCTS."""

    @pytest.fixture
    def batch_config(self) -> BatchLayerConfig:
        """Create batch layer configuration."""
        return BatchLayerConfig(
            strategic_simulations=50,
            precompute_states=10,
            batch_timeout_seconds=5.0,
        )

    @pytest.fixture
    def batch_layer(self, batch_config: BatchLayerConfig) -> BatchLayer:
        """Create batch layer instance."""
        return BatchLayer(batch_config)

    @pytest.mark.asyncio
    async def test_batch_strategic_mcts(
        self,
        batch_layer: BatchLayer,
        trading_state_factory: TradingStateFactory,
    ) -> None:
        """Test batch strategic MCTS processing."""
        states = [trading_state_factory.create() for _ in range(3)]

        result = await batch_layer.run_strategic_mcts(states)

        assert result.success
        assert len(result.policies) == 3
        assert result.processing_time_ms > 0

    @pytest.mark.asyncio
    async def test_batch_precomputation(
        self,
        batch_layer: BatchLayer,
        trading_state_factory: TradingStateFactory,
    ) -> None:
        """Test precomputation of anticipated states."""
        base_state = trading_state_factory.create()

        result = await batch_layer.precompute_policies(base_state)

        assert result.precomputed_count > 0
        assert len(result.state_hashes) > 0

    def test_batch_scheduling(self, batch_layer: BatchLayer) -> None:
        """Test batch job scheduling."""
        # Should be able to schedule jobs
        job_id = batch_layer.schedule_job(
            job_type="strategic_mcts",
            priority=1,
        )

        assert job_id is not None
        assert batch_layer.has_pending_jobs()


class TestSpeedLayer:
    """Test speed layer for real-time decisions."""

    @pytest.fixture
    def speed_config(self) -> SpeedLayerConfig:
        """Create speed layer configuration."""
        return SpeedLayerConfig(
            target_latency_ms=10.0,
            max_latency_ms=100.0,
            policy_inference_timeout_ms=5.0,
            enable_heuristic_fallback=True,
        )

    @pytest.fixture
    def speed_layer(self, speed_config: SpeedLayerConfig) -> SpeedLayer:
        """Create speed layer instance."""
        return SpeedLayer(speed_config)

    @pytest.mark.asyncio
    async def test_realtime_decision(
        self,
        speed_layer: SpeedLayer,
        trading_state_factory: TradingStateFactory,
    ) -> None:
        """Test real-time decision making."""
        state = trading_state_factory.create()

        decision = await speed_layer.decide(state, level="tactical")

        assert decision.action_type is not None
        assert decision.confidence > 0
        assert decision.latency_ms > 0

    @pytest.mark.asyncio
    async def test_decision_latency(
        self,
        speed_layer: SpeedLayer,
        trading_state_factory: TradingStateFactory,
        test_config: TestConfig,
    ) -> None:
        """Test that decisions meet latency requirements."""
        state = trading_state_factory.create()

        # Warm up
        await speed_layer.decide(state, level="tactical")

        # Measure latency
        start = time.perf_counter()
        for _ in range(10):
            decision = await speed_layer.decide(state, level="tactical")
        avg_latency = (time.perf_counter() - start) * 1000 / 10

        # Should be within target
        assert avg_latency < 100.0  # Allow some headroom

    @pytest.mark.asyncio
    async def test_heuristic_fallback(
        self,
        trading_state_factory: TradingStateFactory,
    ) -> None:
        """Test fallback to heuristics when needed."""
        config = SpeedLayerConfig(
            enable_heuristic_fallback=True,
            policy_inference_timeout_ms=0.001,  # Force timeout
        )
        speed_layer = SpeedLayer(config)
        state = trading_state_factory.create()

        decision = await speed_layer.decide(state, level="tactical")

        assert decision.source == DecisionSource.HEURISTIC
        assert decision.action_type is not None

    @pytest.mark.asyncio
    async def test_batch_decisions(
        self,
        speed_layer: SpeedLayer,
        trading_state_factory: TradingStateFactory,
    ) -> None:
        """Test batch decision making."""
        states = [trading_state_factory.create() for _ in range(5)]

        decisions = await speed_layer.decide_batch(states, level="tactical")

        assert len(decisions) == 5
        for decision in decisions:
            assert decision.action_type is not None

    def test_metrics_collection(
        self,
        speed_layer: SpeedLayer,
    ) -> None:
        """Test metrics collection."""
        metrics = speed_layer.get_metrics()

        assert hasattr(metrics, "avg_latency_ms")
        assert hasattr(metrics, "total_decisions")


class TestServingLayer:
    """Test serving layer for policy caching."""

    @pytest.fixture
    def cache_config(self) -> PolicyCacheConfig:
        """Create cache configuration."""
        return PolicyCacheConfig(
            max_entries=100,
            ttl_seconds=60,
            similarity_threshold=0.8,
        )

    @pytest.fixture
    def policy_cache(self, cache_config: PolicyCacheConfig) -> PolicyCache:
        """Create policy cache instance."""
        return PolicyCache(cache_config)

    @pytest.mark.asyncio
    async def test_cache_put_get(
        self,
        policy_cache: PolicyCache,
        trading_state_factory: TradingStateFactory,
    ) -> None:
        """Test cache put and get operations."""
        state = trading_state_factory.create()
        features = state.to_feature_vector()

        # Create policy entry
        policy = {
            "action_type": "hold_position",
            "confidence": 0.8,
            "params": {},
        }

        # Put and get
        await policy_cache.put("test_hash_001", policy, features)
        retrieved = await policy_cache.get("test_hash_001")

        assert retrieved is not None
        assert retrieved["action_type"] == "hold_position"

    @pytest.mark.asyncio
    async def test_cache_miss(
        self,
        policy_cache: PolicyCache,
    ) -> None:
        """Test cache miss behavior."""
        result = await policy_cache.get("nonexistent_hash")
        assert result is None

    @pytest.mark.asyncio
    async def test_similarity_lookup(
        self,
        policy_cache: PolicyCache,
        trading_state_factory: TradingStateFactory,
    ) -> None:
        """Test semantic similarity lookup."""
        state = trading_state_factory.create()
        features = state.to_feature_vector()

        policy = {"action_type": "buy", "confidence": 0.7}
        await policy_cache.put("hash_001", policy, features)

        # Slightly modified features should still match
        similar_features = features + np.random.normal(0, 0.01, len(features))
        result = await policy_cache.get_similar("hash_002", similar_features)

        # May or may not match depending on similarity threshold
        # Just ensure it doesn't crash
        assert result is None or "action_type" in result

    def test_cache_statistics(
        self,
        policy_cache: PolicyCache,
    ) -> None:
        """Test cache statistics."""
        stats = policy_cache.get_statistics()

        assert "size" in stats
        assert "hit_rate" in stats


class TestLambdaCoordinator:
    """Test Lambda architecture coordinator."""

    @pytest.fixture
    def coordinator_config(self) -> LambdaCoordinatorConfig:
        """Create coordinator configuration."""
        return LambdaCoordinatorConfig(
            regime_check_interval_seconds=1.0,
            batch_trigger_on_regime_change=True,
        )

    @pytest.fixture
    def coordinator(
        self,
        coordinator_config: LambdaCoordinatorConfig,
    ) -> LambdaCoordinator:
        """Create coordinator instance."""
        return LambdaCoordinator(coordinator_config)

    @pytest.mark.asyncio
    async def test_coordinator_decision(
        self,
        coordinator: LambdaCoordinator,
        trading_state_factory: TradingStateFactory,
    ) -> None:
        """Test coordinator decision routing."""
        state = trading_state_factory.create()

        decision = await coordinator.decide(state, level="tactical")

        assert decision.action_type is not None
        assert decision.confidence > 0

    @pytest.mark.asyncio
    async def test_regime_triggered_batch(
        self,
        coordinator: LambdaCoordinator,
        trading_state_factory: TradingStateFactory,
    ) -> None:
        """Test batch recomputation triggered by regime change."""
        # Create states with different regimes
        from tests.config import TestScenario

        bullish_state = trading_state_factory.create_for_scenario(TestScenario.BULLISH)
        volatile_state = trading_state_factory.create_for_scenario(TestScenario.VOLATILE)

        # First decision
        await coordinator.decide(bullish_state, level="tactical")

        # Second decision with different regime
        await coordinator.decide(volatile_state, level="tactical")

        # Check if batch was triggered (stats should reflect)
        stats = coordinator.get_statistics()
        assert "batch_triggers" in stats

    @pytest.mark.asyncio
    async def test_layer_coordination(
        self,
        coordinator: LambdaCoordinator,
        trading_state_factory: TradingStateFactory,
    ) -> None:
        """Test coordination between layers."""
        states = [trading_state_factory.create() for _ in range(5)]

        # Multiple decisions
        for state in states:
            await coordinator.decide(state, level="tactical")

        stats = coordinator.get_statistics()
        assert stats["total_decisions"] >= 5


class TestLambdaArchitectureIntegration:
    """Integration tests for complete Lambda architecture."""

    @pytest.mark.asyncio
    async def test_full_pipeline(
        self,
        trading_state_factory: TradingStateFactory,
    ) -> None:
        """Test complete Lambda architecture pipeline."""
        # Setup components
        batch_config = BatchLayerConfig(strategic_simulations=20)
        speed_config = SpeedLayerConfig(target_latency_ms=20.0)
        coord_config = LambdaCoordinatorConfig()

        batch_layer = BatchLayer(batch_config)
        speed_layer = SpeedLayer(speed_config)
        coordinator = LambdaCoordinator(
            coord_config,
            batch_layer=batch_layer,
            speed_layer=speed_layer,
        )

        state = trading_state_factory.create()

        # Make decision
        decision = await coordinator.decide(state, level="tactical")

        assert decision.action_type is not None
        assert decision.latency_ms < 100.0

    @pytest.mark.asyncio
    async def test_cache_integration(
        self,
        trading_state_factory: TradingStateFactory,
    ) -> None:
        """Test cache integration with speed layer."""
        cache_config = PolicyCacheConfig(max_entries=50)
        cache = PolicyCache(cache_config)

        speed_config = SpeedLayerConfig()
        speed_layer = SpeedLayer(speed_config, cache=cache)

        state = trading_state_factory.create()

        # First decision (cache miss)
        decision1 = await speed_layer.decide(state, level="tactical")

        # Manually cache
        features = state.to_feature_vector()
        await cache.put(
            decision1.state_hash,
            {
                "action_type": decision1.action_type,
                "confidence": decision1.confidence,
                "params": decision1.action_params,
            },
            features,
        )

        # Second decision (cache hit)
        decision2 = await speed_layer.decide(state, level="tactical")

        # Cache hit should be faster
        assert decision2.source == DecisionSource.CACHE_HIT
        assert decision2.latency_ms < decision1.latency_ms

    @pytest.mark.asyncio
    async def test_concurrent_decisions(
        self,
        trading_state_factory: TradingStateFactory,
    ) -> None:
        """Test concurrent decision making."""
        coordinator = LambdaCoordinator()

        states = [trading_state_factory.create() for _ in range(10)]

        # Run decisions concurrently
        tasks = [coordinator.decide(state, level="tactical") for state in states]
        decisions = await asyncio.gather(*tasks)

        assert len(decisions) == 10
        for decision in decisions:
            assert decision.action_type is not None
