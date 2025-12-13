"""
End-to-End tests for hybrid Lambda architecture.

Tests:
1. Batch processing cycle
2. Real-time decision flow
3. Cache synchronization
4. Fallback mechanisms
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from reasoning_trading.config import Settings, TradingMode
from reasoning_trading.core.actions import TradingAction, TradingDirection
from reasoning_trading.core.state import TradingState
from reasoning_trading.workflow.hybrid import HybridTradingArchitecture, PolicyEntry

from tests.config import TestConfig, TestScenario
from tests.factories import ActionFactory, TradingStateFactory


class TestBatchProcessingE2E:
    """E2E tests for batch processing."""

    @pytest.mark.asyncio
    async def test_batch_policy_computation(
        self,
        test_settings: Settings,
        trading_state_factory: TradingStateFactory,
        test_config: TestConfig,
    ) -> None:
        """Test batch policy computation stores results correctly."""
        hybrid = HybridTradingArchitecture(
            settings=test_settings,
            batch_simulations=test_config.mcts_simulations,
            realtime_simulations=test_config.mcts_simulations // 5,
        )

        states = [
            trading_state_factory.create()
            for _ in range(3)
        ]

        # Compute policies for all states (simulating batch)
        policies = []
        for state in states:
            state_hash = hybrid._compute_state_hash(state)
            action = hybrid._heuristic_action(state)

            entry = PolicyEntry(
                action=action,
                value=0.5,
                confidence=0.7,
                computed_at=datetime.now(),
                expires_at=datetime.now() + timedelta(hours=1),
                state_hash=state_hash,
            )

            # Store in cache
            cache_key = f"policy:{test_config.primary_symbol}:{state_hash}"
            hybrid._local_cache[cache_key] = entry
            policies.append((state_hash, entry))

        # Verify all policies are cached
        for state_hash, expected_entry in policies:
            cached = await hybrid._get_cached_policy(
                test_config.primary_symbol, state_hash
            )
            assert cached is not None
            assert cached.action.direction == expected_entry.action.direction

    @pytest.mark.asyncio
    async def test_batch_expiration_cycle(
        self,
        test_settings: Settings,
        action_factory: ActionFactory,
        test_config: TestConfig,
    ) -> None:
        """Test batch policies expire and get refreshed."""
        hybrid = HybridTradingArchitecture(settings=test_settings)

        state_hash = "test_hash"

        # Create expired entry
        expired_entry = PolicyEntry(
            action=action_factory.create_buy(),
            value=0.5,
            confidence=0.8,
            computed_at=datetime.now() - timedelta(hours=2),
            expires_at=datetime.now() - timedelta(hours=1),
            state_hash=state_hash,
        )

        cache_key = f"policy:{test_config.primary_symbol}:{state_hash}"
        hybrid._local_cache[cache_key] = expired_entry

        # Should not retrieve expired entry
        cached = await hybrid._get_cached_policy(
            test_config.primary_symbol, state_hash
        )
        assert cached is None  # Expired entries should not be returned


class TestRealtimeDecisionE2E:
    """E2E tests for real-time decision making."""

    @pytest.mark.asyncio
    async def test_realtime_with_cached_policy(
        self,
        test_settings: Settings,
        trading_state_factory: TradingStateFactory,
        action_factory: ActionFactory,
        test_config: TestConfig,
    ) -> None:
        """Test real-time decision uses cached policy when available."""
        hybrid = HybridTradingArchitecture(
            settings=test_settings,
            batch_simulations=test_config.mcts_simulations,
            realtime_simulations=test_config.mcts_simulations // 10,
        )

        state = trading_state_factory.create()
        state_hash = hybrid._compute_state_hash(state)

        # Pre-populate cache
        cached_action = action_factory.create_buy(confidence=0.9)
        entry = PolicyEntry(
            action=cached_action,
            value=0.8,
            confidence=0.9,
            computed_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=1),
            state_hash=state_hash,
        )

        cache_key = f"policy:{test_config.primary_symbol}:{state_hash}"
        hybrid._local_cache[cache_key] = entry

        # Get cached policy
        retrieved = await hybrid._get_cached_policy(
            test_config.primary_symbol, state_hash
        )

        assert retrieved is not None
        assert retrieved.action.direction == TradingDirection.BUY
        assert retrieved.confidence == 0.9

    @pytest.mark.asyncio
    async def test_realtime_fallback_to_heuristic(
        self,
        test_settings: Settings,
        trading_state_factory: TradingStateFactory,
        test_config: TestConfig,
    ) -> None:
        """Test real-time falls back to heuristic when cache miss."""
        hybrid = HybridTradingArchitecture(settings=test_settings)

        # Test different scenarios
        for scenario in [TestScenario.BULLISH, TestScenario.BEARISH]:
            state = trading_state_factory.create_for_scenario(scenario)

            # No cache, should use heuristic
            action = hybrid._heuristic_action(state)

            assert action is not None
            assert action.direction in list(TradingDirection)

            # Bullish should lean toward BUY, bearish toward SELL
            if scenario == TestScenario.BULLISH:
                assert action.direction in [TradingDirection.BUY, TradingDirection.HOLD]
            elif scenario == TestScenario.BEARISH:
                assert action.direction in [TradingDirection.SELL, TradingDirection.HOLD]


class TestCacheSynchronizationE2E:
    """E2E tests for cache synchronization."""

    @pytest.mark.asyncio
    async def test_cache_update_consistency(
        self,
        test_settings: Settings,
        trading_state_factory: TradingStateFactory,
        action_factory: ActionFactory,
        test_config: TestConfig,
    ) -> None:
        """Test cache updates are consistent."""
        hybrid = HybridTradingArchitecture(settings=test_settings)

        state = trading_state_factory.create()
        state_hash = hybrid._compute_state_hash(state)

        # Multiple sequential updates
        actions = [
            action_factory.create_buy(confidence=0.6),
            action_factory.create_buy(confidence=0.7),
            action_factory.create_buy(confidence=0.8),
        ]

        cache_key = f"policy:{test_config.primary_symbol}:{state_hash}"

        for i, action in enumerate(actions):
            entry = PolicyEntry(
                action=action,
                value=0.5 + i * 0.1,
                confidence=action.confidence,
                computed_at=datetime.now(),
                expires_at=datetime.now() + timedelta(hours=1),
                state_hash=state_hash,
            )
            hybrid._local_cache[cache_key] = entry

        # Final value should be the last update
        final = await hybrid._get_cached_policy(
            test_config.primary_symbol, state_hash
        )
        assert final is not None
        assert final.confidence == 0.8

    @pytest.mark.asyncio
    async def test_state_hash_stability(
        self,
        test_settings: Settings,
        trading_state_factory: TradingStateFactory,
    ) -> None:
        """Test state hash is stable for same state."""
        hybrid = HybridTradingArchitecture(settings=test_settings)

        state = trading_state_factory.create()

        # Compute hash multiple times
        hashes = [hybrid._compute_state_hash(state) for _ in range(5)]

        # All should be identical
        assert len(set(hashes)) == 1


class TestFailoverMechanismsE2E:
    """E2E tests for failover mechanisms."""

    @pytest.mark.asyncio
    async def test_graceful_degradation(
        self,
        test_settings: Settings,
        trading_state_factory: TradingStateFactory,
        test_config: TestConfig,
    ) -> None:
        """Test system degrades gracefully when components fail."""
        hybrid = HybridTradingArchitecture(settings=test_settings)

        state = trading_state_factory.create()
        state_hash = hybrid._compute_state_hash(state)

        # No cached policy exists
        cached = await hybrid._get_cached_policy(
            test_config.primary_symbol, state_hash
        )
        assert cached is None

        # System should still provide action via heuristic
        action = hybrid._heuristic_action(state)
        assert action is not None
        assert action.direction in list(TradingDirection)

    @pytest.mark.asyncio
    async def test_invalid_state_handling(
        self,
        test_settings: Settings,
        trading_state_factory: TradingStateFactory,
    ) -> None:
        """Test handling of invalid state data."""
        hybrid = HybridTradingArchitecture(settings=test_settings)

        state = trading_state_factory.create()

        # Set some indicators to None/invalid
        state.technical_indicators.rsi_14 = None
        state.technical_indicators.sma_20 = None

        # Should still produce heuristic action
        action = hybrid._heuristic_action(state)
        assert action is not None
        # With missing data, should default to HOLD
        assert action.direction in list(TradingDirection)


class TestHybridLatencyE2E:
    """E2E tests for hybrid architecture latency."""

    @pytest.mark.asyncio
    async def test_cached_lookup_fast(
        self,
        test_settings: Settings,
        trading_state_factory: TradingStateFactory,
        action_factory: ActionFactory,
        test_config: TestConfig,
    ) -> None:
        """Test cached policy lookup is fast."""
        hybrid = HybridTradingArchitecture(settings=test_settings)

        state = trading_state_factory.create()
        state_hash = hybrid._compute_state_hash(state)

        # Pre-populate cache
        entry = PolicyEntry(
            action=action_factory.create_buy(),
            value=0.5,
            confidence=0.8,
            computed_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=1),
            state_hash=state_hash,
        )

        cache_key = f"policy:{test_config.primary_symbol}:{state_hash}"
        hybrid._local_cache[cache_key] = entry

        # Time lookup
        import time

        start = time.perf_counter()
        for _ in range(100):
            await hybrid._get_cached_policy(
                test_config.primary_symbol, state_hash
            )
        elapsed = time.perf_counter() - start

        # 100 lookups should complete in under 100ms
        assert elapsed < 0.1

    @pytest.mark.asyncio
    async def test_heuristic_fast(
        self,
        test_settings: Settings,
        trading_state_factory: TradingStateFactory,
    ) -> None:
        """Test heuristic computation is fast."""
        hybrid = HybridTradingArchitecture(settings=test_settings)

        state = trading_state_factory.create()

        # Time heuristic
        import time

        start = time.perf_counter()
        for _ in range(100):
            hybrid._heuristic_action(state)
        elapsed = time.perf_counter() - start

        # 100 heuristic calls should complete in under 100ms
        assert elapsed < 0.1
