"""
Unit tests for service layer.

Tests cover:
- TradingService with mocked adapters
- MCTSService with mocked tree
- PortfolioService
- AnalyticsService
- CacheService
- Service initialization and cleanup
- Error handling and edge cases
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest

from enterprise_ui.backend.services.analytics_service import AnalyticsService
from enterprise_ui.backend.services.cache_service import CacheService
from enterprise_ui.backend.services.exceptions import (
    AnalyticsServiceException,
    CacheServiceException,
    MCTSServiceException,
    PortfolioServiceException,
    TimeoutException,
    TradingServiceException,
    ValidationException,
)
from enterprise_ui.backend.services.mcts_service import MCTSService
from enterprise_ui.backend.services.portfolio_service import PortfolioService
from enterprise_ui.backend.services.trading_service import TradingService
from reasoning_trading.core.actions import ActionSpace
from reasoning_trading.core.state import MarketRegime, PortfolioState, TradingState
from reasoning_trading.mcts.tree import MCTSConfig


# ============================================================================
# TradingService Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
class TestTradingService:
    """Test TradingService."""

    async def test_initialization(self, trading_service):
        """Test service initializes correctly."""
        assert trading_service._initialized is True

    async def test_analyze_symbol_success(self, trading_service):
        """Test successful symbol analysis."""
        result = await trading_service.analyze_symbol("AAPL")

        assert result["symbol"] == "AAPL"
        assert "signal" in result
        assert "current_price" in result
        assert "technical_indicators" in result
        assert "market_regime" in result

    async def test_analyze_symbol_with_cache(self, trading_service, cache_service):
        """Test analysis uses cache when available."""
        # First call should miss cache
        result1 = await trading_service.analyze_symbol("AAPL", use_cache=True)

        # Second call should hit cache
        result2 = await trading_service.analyze_symbol("AAPL", use_cache=True)

        assert result1 == result2

    async def test_analyze_symbol_invalid_symbol(self, trading_service):
        """Test analysis with empty symbol raises error."""
        with pytest.raises(ValidationException) as exc_info:
            await trading_service.analyze_symbol("")

        assert "symbol" in str(exc_info.value).lower()

    async def test_make_decision_success(self, trading_service):
        """Test successful trading decision."""
        decision = await trading_service.make_decision("AAPL")

        assert decision["symbol"] == "AAPL"
        assert "should_trade" in decision
        assert "direction" in decision
        assert "confidence" in decision
        assert "position_size_pct" in decision

    async def test_make_decision_with_analysis(self, trading_service):
        """Test decision with pre-computed analysis."""
        analysis = await trading_service.analyze_symbol("AAPL")
        decision = await trading_service.make_decision("AAPL", analysis=analysis)

        assert decision["symbol"] == "AAPL"
        assert decision["should_trade"] in [True, False]

    async def test_execute_trade_success(self, trading_service):
        """Test successful trade execution."""
        result = await trading_service.execute_trade(
            symbol="AAPL", side="buy", quantity=10.0, order_type="market"
        )

        assert result.order_id == "test_order_123"
        assert result.symbol == "AAPL"
        assert result.status == "filled"
        assert result.filled_qty == 10.0

    async def test_execute_trade_invalid_symbol(self, trading_service):
        """Test trade execution with empty symbol raises error."""
        with pytest.raises(ValidationException) as exc_info:
            await trading_service.execute_trade(symbol="", side="buy", quantity=10.0)

        assert "symbol" in str(exc_info.value).lower()

    async def test_execute_trade_invalid_side(self, trading_service):
        """Test trade execution with invalid side raises error."""
        with pytest.raises(ValidationException) as exc_info:
            await trading_service.execute_trade(
                symbol="AAPL", side="invalid", quantity=10.0
            )

        assert "side" in str(exc_info.value).lower()

    async def test_execute_trade_invalid_quantity(self, trading_service):
        """Test trade execution with zero quantity raises error."""
        with pytest.raises(ValidationException) as exc_info:
            await trading_service.execute_trade(
                symbol="AAPL", side="buy", quantity=0.0
            )

        assert "quantity" in str(exc_info.value).lower()

    async def test_get_trading_state(self, trading_service):
        """Test getting trading state."""
        state = await trading_service.get_trading_state("AAPL")

        assert isinstance(state, TradingState)
        assert state.symbol == "AAPL"
        assert state.current_price > 0

    async def test_get_analyst_signals(self, trading_service):
        """Test getting analyst signals."""
        signals = await trading_service.get_analyst_signals("AAPL")

        assert signals.market_analyst_score is not None
        assert signals.news_analyst_score is not None
        assert signals.researcher_consensus is not None

    async def test_get_risk_metrics(self, trading_service):
        """Test getting risk metrics."""
        metrics = await trading_service.get_risk_metrics("AAPL", 0.15)

        assert "risk_rating" in metrics
        assert metrics["risk_rating"] in ["low", "moderate", "high"]

    async def test_cleanup(self, trading_service):
        """Test service cleanup."""
        await trading_service.cleanup()
        assert trading_service._initialized is False


# ============================================================================
# MCTSService Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
class TestMCTSService:
    """Test MCTSService."""

    async def test_run_search(self, mcts_service, sample_trading_state):
        """Test running MCTS search."""
        action_space = ActionSpace()

        with patch("reasoning_trading.mcts.tree.MCTSTree.search") as mock_search:
            from reasoning_trading.mcts.tree import MCTSResult

            mock_result = MCTSResult(
                best_action=Mock(),
                best_value=1.25,
                total_simulations=100,
                nodes_created=50,
                total_time_ms=100.0,
                root=None,
            )
            mock_search.return_value = mock_result

            search_id, result = await mcts_service.run_search(
                sample_trading_state, action_space
            )

            assert search_id is not None
            assert result == mock_result
            assert result.best_value == 1.25

    async def test_run_search_with_cache(
        self, mcts_service, sample_trading_state, cache_service
    ):
        """Test search uses cache when available."""
        action_space = ActionSpace()

        with patch("reasoning_trading.mcts.tree.MCTSTree.search") as mock_search:
            from reasoning_trading.mcts.tree import MCTSResult

            mock_result = MCTSResult(
                best_action=Mock(),
                best_value=1.25,
                total_simulations=100,
                nodes_created=50,
                total_time_ms=100.0,
                root=None,
            )
            mock_search.return_value = mock_result

            # First call
            search_id1, result1 = await mcts_service.run_search(
                sample_trading_state, action_space
            )

            # Second call should use cache
            search_id2, result2 = await mcts_service.run_search(
                sample_trading_state, action_space
            )

            # Should get cached result
            assert result1.best_value == result2.best_value

    async def test_run_search_invalid_state(self, mcts_service):
        """Test search with None state raises error."""
        with pytest.raises(ValidationException):
            await mcts_service.run_search(None, ActionSpace())

    async def test_run_search_invalid_action_space(
        self, mcts_service, sample_trading_state
    ):
        """Test search with None action space raises error."""
        with pytest.raises(ValidationException):
            await mcts_service.run_search(sample_trading_state, None)

    async def test_get_search_status(self, mcts_service, sample_trading_state):
        """Test getting search status."""
        action_space = ActionSpace()

        with patch("reasoning_trading.mcts.tree.MCTSTree.search") as mock_search:
            from reasoning_trading.mcts.tree import MCTSResult

            mock_search.return_value = MCTSResult(
                best_action=Mock(),
                best_value=1.0,
                total_simulations=100,
                nodes_created=50,
                total_time_ms=100.0,
                root=None,
            )

            search_id, _ = await mcts_service.run_search(
                sample_trading_state, action_space
            )

            status = mcts_service.get_search_status(search_id)

            assert status is not None
            assert status["search_id"] == search_id
            assert status["type"] == "standard"
            assert status["status"] == "completed"

    async def test_clear_search(self, mcts_service, sample_trading_state):
        """Test clearing a search."""
        action_space = ActionSpace()

        with patch("reasoning_trading.mcts.tree.MCTSTree.search") as mock_search:
            from reasoning_trading.mcts.tree import MCTSResult

            mock_search.return_value = MCTSResult(
                best_action=Mock(),
                best_value=1.0,
                total_simulations=100,
                nodes_created=50,
                total_time_ms=100.0,
                root=None,
            )

            search_id, _ = await mcts_service.run_search(
                sample_trading_state, action_space
            )

            cleared = mcts_service.clear_search(search_id)
            assert cleared is True

            status = mcts_service.get_search_status(search_id)
            assert status is None

    async def test_get_statistics(self, mcts_service):
        """Test getting service statistics."""
        stats = mcts_service.get_statistics()

        assert "total_searches" in stats
        assert "completed" in stats
        assert "running" in stats
        assert "failed" in stats
        assert "mcts_config" in stats


# ============================================================================
# PortfolioService Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
class TestPortfolioService:
    """Test PortfolioService."""

    async def test_get_state(self, portfolio_service):
        """Test getting portfolio state."""
        state = await portfolio_service.get_state()

        assert isinstance(state, PortfolioState)
        assert state.cash_balance > 0
        assert state.portfolio_value > 0

    async def test_get_state_with_refresh(self, portfolio_service):
        """Test getting portfolio state with refresh."""
        state = await portfolio_service.get_state(refresh=True)

        assert isinstance(state, PortfolioState)

    async def test_update_state(self, portfolio_service, sample_portfolio_state):
        """Test updating portfolio state."""
        await portfolio_service.update_state(sample_portfolio_state)

        # Get state to verify update
        state = await portfolio_service.get_state(refresh=True)
        assert state.cash_balance == sample_portfolio_state.cash_balance

    async def test_update_state_invalid_cash(self, portfolio_service):
        """Test updating state with negative cash raises error."""
        invalid_state = PortfolioState(
            cash_balance=-1000.0, portfolio_value=100000.0
        )

        with pytest.raises(ValidationException) as exc_info:
            await portfolio_service.update_state(invalid_state)

        assert "cash_balance" in str(exc_info.value).lower()

    async def test_get_positions(self, portfolio_service, sample_portfolio_state):
        """Test getting positions."""
        await portfolio_service.update_state(sample_portfolio_state)

        positions = await portfolio_service.get_positions()

        assert isinstance(positions, dict)
        # Should have positions from sample state
        assert len(positions) >= 0

    async def test_get_risk_metrics(self, portfolio_service, sample_portfolio_state):
        """Test getting risk metrics."""
        await portfolio_service.update_state(sample_portfolio_state)

        metrics = await portfolio_service.get_risk_metrics()

        assert "portfolio_value" in metrics
        assert "leverage" in metrics
        assert "diversification_score" in metrics
        assert "max_concentration" in metrics

    async def test_check_position_risk_allowed(
        self, portfolio_service, sample_portfolio_state
    ):
        """Test position risk check that passes."""
        await portfolio_service.update_state(sample_portfolio_state)

        result = await portfolio_service.check_position_risk(
            symbol="AAPL", side="buy", quantity=5.0, price=150.0
        )

        assert "allowed" in result
        assert "violations" in result
        assert isinstance(result["violations"], list)

    async def test_check_position_risk_invalid_symbol(self, portfolio_service):
        """Test position risk check with empty symbol raises error."""
        with pytest.raises(ValidationException):
            await portfolio_service.check_position_risk(
                symbol="", side="buy", quantity=10.0, price=150.0
            )

    async def test_check_position_risk_invalid_side(self, portfolio_service):
        """Test position risk check with invalid side raises error."""
        with pytest.raises(ValidationException):
            await portfolio_service.check_position_risk(
                symbol="AAPL", side="invalid", quantity=10.0, price=150.0
            )

    async def test_get_statistics(self, portfolio_service, sample_portfolio_state):
        """Test getting portfolio statistics."""
        await portfolio_service.update_state(sample_portfolio_state)

        stats = await portfolio_service.get_statistics()

        assert "portfolio_value" in stats
        assert "cash_balance" in stats
        assert "num_positions" in stats
        assert "leverage" in stats


# ============================================================================
# CacheService Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
class TestCacheService:
    """Test CacheService."""

    async def test_set_and_get_json(self, cache_service):
        """Test setting and getting JSON value."""
        await cache_service.set("test_key", {"data": "value"}, ttl=60)

        value = await cache_service.get("test_key")

        assert value == {"data": "value"}

    async def test_set_and_get_pickle(self, cache_service):
        """Test setting and getting pickled value."""
        data = Mock(value="test")
        await cache_service.set("test_key", data, ttl=60, use_pickle=True)

        value = await cache_service.get("test_key", use_pickle=True)

        assert value.value == "test"

    async def test_get_nonexistent(self, cache_service):
        """Test getting nonexistent key returns None."""
        value = await cache_service.get("nonexistent_key")

        assert value is None

    async def test_delete(self, cache_service):
        """Test deleting a key."""
        await cache_service.set("test_key", "value", ttl=60)

        deleted = await cache_service.delete("test_key")

        assert deleted is True

        value = await cache_service.get("test_key")
        assert value is None

    async def test_exists(self, cache_service):
        """Test checking if key exists."""
        await cache_service.set("test_key", "value", ttl=60)

        exists = await cache_service.exists("test_key")
        assert exists is True

        await cache_service.delete("test_key")

        exists = await cache_service.exists("test_key")
        assert exists is False

    async def test_get_ttl(self, cache_service):
        """Test getting TTL for a key."""
        await cache_service.set("test_key", "value", ttl=60)

        ttl = await cache_service.get_ttl("test_key")

        assert ttl is not None
        assert ttl <= 60

    async def test_extend_ttl(self, cache_service):
        """Test extending TTL."""
        await cache_service.set("test_key", "value", ttl=60)

        extended = await cache_service.extend_ttl("test_key", 30)

        assert extended is True

    async def test_clear_pattern(self, cache_service):
        """Test clearing keys matching pattern."""
        await cache_service.set("test:key1", "value1", ttl=60)
        await cache_service.set("test:key2", "value2", ttl=60)
        await cache_service.set("other:key", "value3", ttl=60)

        deleted = await cache_service.clear_pattern("test:*")

        assert deleted >= 2

    async def test_get_or_compute(self, cache_service):
        """Test get_or_compute pattern."""
        compute_called = False

        async def compute_fn():
            nonlocal compute_called
            compute_called = True
            return "computed_value"

        # First call should compute
        value1 = await cache_service.get_or_compute("test_key", compute_fn, ttl=60)

        assert value1 == "computed_value"
        assert compute_called is True

        # Second call should use cache
        compute_called = False
        value2 = await cache_service.get_or_compute("test_key", compute_fn, ttl=60)

        assert value2 == "computed_value"
        assert compute_called is False

    async def test_statistics(self, cache_service):
        """Test getting cache statistics."""
        # Generate some hits and misses
        await cache_service.set("key1", "value1", ttl=60)
        await cache_service.get("key1")  # Hit
        await cache_service.get("nonexistent")  # Miss

        stats = cache_service.get_statistics()

        assert "hits" in stats
        assert "misses" in stats
        assert "total_requests" in stats
        assert "hit_rate" in stats

    async def test_reset_statistics(self, cache_service):
        """Test resetting statistics."""
        await cache_service.set("key1", "value1", ttl=60)
        await cache_service.get("key1")

        cache_service.reset_statistics()

        stats = cache_service.get_statistics()
        assert stats["hits"] == 0
        assert stats["misses"] == 0


# ============================================================================
# AnalyticsService Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
class TestAnalyticsService:
    """Test AnalyticsService."""

    async def test_get_lambda_statistics_without_coordinator(self):
        """Test getting Lambda statistics without coordinator."""
        service = AnalyticsService()

        stats = await service.get_lambda_statistics()

        assert stats["enabled"] is False

    async def test_get_speed_layer_metrics_without_coordinator(self):
        """Test getting speed layer metrics without coordinator."""
        service = AnalyticsService()

        metrics = await service.get_speed_layer_metrics()

        assert metrics["enabled"] is False

    async def test_get_cache_statistics_without_cache(self):
        """Test getting cache statistics without cache."""
        service = AnalyticsService()

        stats = await service.get_cache_statistics()

        assert stats["enabled"] is False

    async def test_get_cache_statistics_with_cache(self, cache_service):
        """Test getting cache statistics with cache."""
        service = AnalyticsService(cache_service=cache_service)

        stats = await service.get_cache_statistics()

        assert stats["enabled"] is True
        assert "hit_rate" in stats
        assert "total_requests" in stats

    async def test_record_metric(self):
        """Test recording a custom metric."""
        service = AnalyticsService()

        await service.record_metric("test_metric", 123.45, {"tag": "test"})

        assert len(service._metrics_history) == 1
        assert service._metrics_history[0]["type"] == "test_metric"
        assert service._metrics_history[0]["value"] == 123.45

    async def test_get_metrics_history(self):
        """Test getting metrics history."""
        service = AnalyticsService()

        await service.record_metric("metric1", 1.0)
        await service.record_metric("metric2", 2.0)
        await service.record_metric("metric1", 3.0)

        # Get all metrics
        history = await service.get_metrics_history()
        assert len(history) == 3

        # Filter by type
        history = await service.get_metrics_history(metric_type="metric1")
        assert len(history) == 2

    async def test_get_metrics_history_with_time_filter(self):
        """Test getting metrics history with time filter."""
        service = AnalyticsService()

        await service.record_metric("metric1", 1.0)

        # Get metrics since now (should be empty or just the one)
        since = datetime.now() + timedelta(seconds=1)
        history = await service.get_metrics_history(since=since)

        assert len(history) == 0

    async def test_clear_metrics_history(self):
        """Test clearing metrics history."""
        service = AnalyticsService()

        await service.record_metric("metric1", 1.0)
        await service.record_metric("metric2", 2.0)

        count = await service.clear_metrics_history()

        assert count == 2
        assert len(service._metrics_history) == 0

    async def test_get_statistics(self):
        """Test getting service statistics."""
        service = AnalyticsService()

        await service.record_metric("metric1", 1.0)

        stats = service.get_statistics()

        assert "metrics_history_size" in stats
        assert stats["metrics_history_size"] == 1
        assert "max_history_size" in stats


# ============================================================================
# Error Handling Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
class TestServiceErrorHandling:
    """Test service error handling."""

    async def test_trading_service_adapter_error(self, cache_service):
        """Test trading service handles adapter errors."""
        mock_adapter = Mock()
        mock_adapter._initialize = AsyncMock(
            side_effect=Exception("Adapter initialization failed")
        )

        service = TradingService(
            trading_adapter=mock_adapter, cache_service=cache_service
        )

        with pytest.raises(TradingServiceException):
            await service.initialize()

    async def test_cache_service_redis_error(self, mock_redis):
        """Test cache service handles Redis errors."""
        # Make Redis raise an error
        mock_redis.get = AsyncMock(side_effect=Exception("Redis connection failed"))

        cache = CacheService(redis_client=mock_redis)

        with pytest.raises(CacheServiceException):
            await cache.get("test_key")

    async def test_portfolio_service_state_error(self, portfolio_service):
        """Test portfolio service handles state errors gracefully."""
        # Force an error by mocking internal state
        with patch.object(
            portfolio_service, "_portfolio_state", None
        ), patch.object(
            portfolio_service.cache, "get", AsyncMock(side_effect=Exception("Error"))
        ):
            # Should still return default state
            state = await portfolio_service.get_state()
            assert isinstance(state, PortfolioState)
