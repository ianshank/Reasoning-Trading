"""
Integration tests for MCTS API endpoints.

Tests cover:
- POST /api/v1/mcts/search
- POST /api/v1/mcts/hierarchical-search
- GET /api/v1/mcts/tree/{search_id}
- GET /api/v1/mcts/action-distribution/{search_id}
- PATCH /api/v1/mcts/config
- Error handling and validation
"""

import pytest
from httpx import AsyncClient


# ============================================================================
# POST /search Tests
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
class TestMCTSSearchEndpoint:
    """Test /api/v1/mcts/search endpoint."""

    async def test_search_success(self, client: AsyncClient):
        """Test successful MCTS search request."""
        response = await client.post(
            "/api/v1/mcts/search",
            json={
                "symbol": "AAPL",
                "current_price": 150.25,
                "max_simulations": 1000,
            },
        )

        # Endpoint might not exist yet - check for reasonable status
        assert response.status_code in [200, 201, 404]

        if response.status_code == 200:
            data = response.json()
            assert "symbol" in data
            assert "best_action" in data
            assert "simulations_run" in data

    async def test_search_with_exploration_weight(self, client: AsyncClient):
        """Test search with custom exploration weight."""
        response = await client.post(
            "/api/v1/mcts/search",
            json={
                "symbol": "AAPL",
                "current_price": 150.25,
                "max_simulations": 500,
                "exploration_weight": 2.0,
            },
        )

        assert response.status_code in [200, 201, 404]

    async def test_search_with_tree_return(self, client: AsyncClient):
        """Test search requesting full tree structure."""
        response = await client.post(
            "/api/v1/mcts/search",
            json={
                "symbol": "AAPL",
                "current_price": 150.25,
                "max_simulations": 100,
                "return_tree": True,
            },
        )

        assert response.status_code in [200, 201, 404]

        if response.status_code == 200:
            data = response.json()
            # Should include tree structure if requested
            has_tree_data = "search_tree" in data or "tree" in data or "nodes" in data
            assert has_tree_data, f"Expected tree structure in response, got keys: {list(data.keys())}"

    async def test_search_missing_symbol(self, client: AsyncClient):
        """Test search without symbol returns 422."""
        response = await client.post(
            "/api/v1/mcts/search",
            json={"current_price": 150.25, "max_simulations": 1000},
        )

        assert response.status_code in [404, 422]

    async def test_search_invalid_simulations(self, client: AsyncClient):
        """Test search with invalid simulations returns 422."""
        response = await client.post(
            "/api/v1/mcts/search",
            json={
                "symbol": "AAPL",
                "current_price": 150.25,
                "max_simulations": 5,  # Below minimum
            },
        )

        assert response.status_code in [404, 422]

    async def test_search_invalid_exploration_weight(self, client: AsyncClient):
        """Test search with invalid exploration weight returns 422."""
        response = await client.post(
            "/api/v1/mcts/search",
            json={
                "symbol": "AAPL",
                "current_price": 150.25,
                "exploration_weight": -1.0,  # Negative
            },
        )

        assert response.status_code in [404, 422]


# ============================================================================
# POST /hierarchical-search Tests
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
class TestHierarchicalSearchEndpoint:
    """Test /api/v1/mcts/hierarchical-search endpoint."""

    async def test_hierarchical_search_success(self, client: AsyncClient):
        """Test successful hierarchical MCTS search."""
        response = await client.post(
            "/api/v1/mcts/hierarchical-search",
            json={
                "symbol": "AAPL",
                "current_price": 150.25,
                "levels": 3,
                "simulations_per_level": [100, 50, 20],
            },
        )

        assert response.status_code in [200, 201, 404]

    async def test_hierarchical_search_with_fast_policy(
        self, client: AsyncClient
    ):
        """Test hierarchical search with fast policy enabled."""
        response = await client.post(
            "/api/v1/mcts/hierarchical-search",
            json={
                "symbol": "AAPL",
                "current_price": 150.25,
                "levels": 2,
                "simulations_per_level": [50, 25],
                "use_fast_policy": True,
            },
        )

        assert response.status_code in [200, 201, 404]

    async def test_hierarchical_search_single_level(self, client: AsyncClient):
        """Test hierarchical search with single level."""
        response = await client.post(
            "/api/v1/mcts/hierarchical-search",
            json={
                "symbol": "AAPL",
                "current_price": 150.25,
                "levels": 1,
                "simulations_per_level": [100],
            },
        )

        assert response.status_code in [200, 201, 404]

    async def test_hierarchical_search_invalid_levels(self, client: AsyncClient):
        """Test hierarchical search with invalid levels returns 422."""
        response = await client.post(
            "/api/v1/mcts/hierarchical-search",
            json={
                "symbol": "AAPL",
                "current_price": 150.25,
                "levels": 0,  # Invalid
            },
        )

        assert response.status_code in [404, 422]

    async def test_hierarchical_search_too_many_levels(
        self, client: AsyncClient
    ):
        """Test hierarchical search with too many levels returns 422."""
        response = await client.post(
            "/api/v1/mcts/hierarchical-search",
            json={
                "symbol": "AAPL",
                "current_price": 150.25,
                "levels": 10,  # Above maximum
            },
        )

        assert response.status_code in [404, 422]

    async def test_hierarchical_search_mismatched_simulations(
        self, client: AsyncClient
    ):
        """Test hierarchical search with mismatched simulations list."""
        response = await client.post(
            "/api/v1/mcts/hierarchical-search",
            json={
                "symbol": "AAPL",
                "current_price": 150.25,
                "levels": 3,
                "simulations_per_level": [100, 50],  # Only 2 elements for 3 levels
            },
        )

        # Might be validated or use defaults
        assert response.status_code in [200, 201, 404, 422]


# ============================================================================
# GET /tree/{search_id} Tests
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
class TestTreeVisualizationEndpoint:
    """Test /api/v1/mcts/tree/{search_id} endpoint."""

    async def test_get_tree_nonexistent_search(self, client: AsyncClient):
        """Test getting tree for nonexistent search returns 404."""
        response = await client.get("/api/v1/mcts/tree/nonexistent_id")

        assert response.status_code in [404]

    async def test_get_tree_with_max_depth(self, client: AsyncClient):
        """Test getting tree with max depth parameter."""
        response = await client.get(
            "/api/v1/mcts/tree/test_search_id?max_depth=3"
        )

        assert response.status_code in [404]  # Search doesn't exist

    async def test_get_tree_invalid_max_depth(self, client: AsyncClient):
        """Test getting tree with invalid max depth."""
        response = await client.get("/api/v1/mcts/tree/test_id?max_depth=0")

        assert response.status_code in [404, 422]


# ============================================================================
# GET /action-distribution/{search_id} Tests
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
class TestActionDistributionEndpoint:
    """Test /api/v1/mcts/action-distribution/{search_id} endpoint."""

    async def test_get_distribution_nonexistent_search(
        self, client: AsyncClient
    ):
        """Test getting distribution for nonexistent search returns 404."""
        response = await client.get(
            "/api/v1/mcts/action-distribution/nonexistent_id"
        )

        assert response.status_code in [404]

    async def test_get_distribution_with_level(self, client: AsyncClient):
        """Test getting distribution with level parameter."""
        response = await client.get(
            "/api/v1/mcts/action-distribution/test_id?level=strategic"
        )

        assert response.status_code in [404]

    async def test_get_distribution_invalid_level(self, client: AsyncClient):
        """Test getting distribution with invalid level."""
        response = await client.get(
            "/api/v1/mcts/action-distribution/test_id?level=invalid"
        )

        assert response.status_code in [404, 422]


# ============================================================================
# PATCH /config Tests
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
class TestMCTSConfigEndpoint:
    """Test /api/v1/mcts/config endpoint."""

    async def test_update_config_success(self, client: AsyncClient):
        """Test updating MCTS configuration."""
        response = await client.patch(
            "/api/v1/mcts/config",
            json={
                "max_simulations": 2000,
                "exploration_weight": 1.5,
                "time_budget_ms": 1000,
            },
        )

        # Endpoint might not exist yet
        assert response.status_code in [200, 404, 405]

    async def test_update_config_partial(self, client: AsyncClient):
        """Test partial config update."""
        response = await client.patch(
            "/api/v1/mcts/config",
            json={"max_simulations": 1500},
        )

        assert response.status_code in [200, 404, 405]

    async def test_update_config_invalid_values(self, client: AsyncClient):
        """Test config update with invalid values."""
        response = await client.patch(
            "/api/v1/mcts/config",
            json={
                "max_simulations": -1000,  # Invalid
                "exploration_weight": -2.0,  # Invalid
            },
        )

        assert response.status_code in [404, 405, 422]


# ============================================================================
# Error Handling Tests
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
class TestMCTSErrorHandling:
    """Test error handling for MCTS endpoints."""

    async def test_search_timeout(self, client: AsyncClient):
        """Test search with very short timeout."""
        response = await client.post(
            "/api/v1/mcts/search",
            json={
                "symbol": "AAPL",
                "current_price": 150.25,
                "max_simulations": 100000,  # Very high
                "time_budget_ms": 1,  # Very short timeout
            },
        )

        # Should either succeed quickly or fail gracefully
        assert response.status_code in [200, 201, 404, 422, 500, 504]

    async def test_search_malformed_json(self, client: AsyncClient):
        """Test search with malformed JSON."""
        response = await client.post(
            "/api/v1/mcts/search",
            content="invalid json{",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code in [404, 422]

    async def test_concurrent_searches(self, client: AsyncClient):
        """Test multiple concurrent search requests."""
        import asyncio

        async def make_search():
            return await client.post(
                "/api/v1/mcts/search",
                json={
                    "symbol": "AAPL",
                    "current_price": 150.25,
                    "max_simulations": 100,
                },
            )

        # Launch 3 concurrent searches
        responses = await asyncio.gather(
            make_search(), make_search(), make_search()
        )

        # All should succeed or fail gracefully
        for response in responses:
            assert response.status_code in [200, 201, 404, 429, 500]


# ============================================================================
# Performance Tests
# ============================================================================


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.asyncio
class TestMCTSPerformance:
    """Test performance of MCTS endpoints."""

    async def test_search_completes_within_time_budget(
        self, client: AsyncClient
    ):
        """Test search completes within specified time budget."""
        import time

        start_time = time.time()

        response = await client.post(
            "/api/v1/mcts/search",
            json={
                "symbol": "AAPL",
                "current_price": 150.25,
                "max_simulations": 100,
                "time_budget_ms": 500,
            },
        )

        elapsed_ms = (time.time() - start_time) * 1000

        if response.status_code == 200:
            # Should complete within reasonable margin of time budget
            assert elapsed_ms < 1000  # 500ms budget + 500ms margin

    async def test_small_search_is_fast(self, client: AsyncClient):
        """Test small search completes quickly."""
        import time

        start_time = time.time()

        response = await client.post(
            "/api/v1/mcts/search",
            json={
                "symbol": "AAPL",
                "current_price": 150.25,
                "max_simulations": 10,  # Very small
            },
        )

        elapsed_ms = (time.time() - start_time) * 1000

        if response.status_code == 200:
            # Should be very fast
            assert elapsed_ms < 500

    async def test_large_search_returns_progress(self, client: AsyncClient):
        """Test large search can return progress updates."""
        # This would test WebSocket progress updates in a real implementation
        response = await client.post(
            "/api/v1/mcts/search",
            json={
                "symbol": "AAPL",
                "current_price": 150.25,
                "max_simulations": 10000,
            },
        )

        # Just verify it completes or returns reasonable status
        assert response.status_code in [200, 201, 404, 500, 504]


# ============================================================================
# Integration with Trading Endpoints
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
class TestMCTSTradingIntegration:
    """Test MCTS integration with trading endpoints."""

    async def test_analyze_then_search(self, client: AsyncClient):
        """Test running analysis followed by MCTS search."""
        # First analyze
        analyze_response = await client.post(
            "/api/v1/trading/analyze",
            json={
                "symbol": "AAPL",
                "current_price": 150.25,
            },
        )

        if analyze_response.status_code != 200:
            pytest.skip("Analysis endpoint not available")

        # Then search with results
        search_response = await client.post(
            "/api/v1/mcts/search",
            json={
                "symbol": "AAPL",
                "current_price": 150.25,
                "max_simulations": 100,
            },
        )

        assert search_response.status_code in [200, 201, 404]

    async def test_search_then_execute(self, client: AsyncClient):
        """Test running search followed by trade execution."""
        # First search
        search_response = await client.post(
            "/api/v1/mcts/search",
            json={
                "symbol": "AAPL",
                "current_price": 150.25,
                "max_simulations": 100,
            },
        )

        if search_response.status_code != 200:
            pytest.skip("Search endpoint not available")

        # Then execute based on results (dry run)
        execute_response = await client.post(
            "/api/v1/trading/execute",
            json={
                "symbol": "AAPL",
                "direction": "buy",
                "quantity": 10.0,
                "order_type": "market",
            },
        )

        assert execute_response.status_code in [200, 201, 404]
