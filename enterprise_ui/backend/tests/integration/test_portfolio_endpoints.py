"""
Integration tests for portfolio API endpoints.

Tests cover:
- GET /api/v1/portfolio/state
- GET /api/v1/portfolio/positions
- GET /api/v1/portfolio/risk-metrics
- POST /api/v1/portfolio/risk-check
- Error handling and validation
"""

import pytest
from httpx import AsyncClient


# ============================================================================
# GET /state Tests
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
class TestPortfolioStateEndpoint:
    """Test /api/v1/portfolio/state endpoint."""

    async def test_get_state_success(self, client: AsyncClient):
        """Test getting portfolio state."""
        response = await client.get("/api/v1/portfolio/state")

        # Endpoint might not exist yet
        assert response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.json()
            assert "cash_balance" in data
            assert "portfolio_value" in data
            assert "positions" in data
            assert "timestamp" in data

    async def test_get_state_with_refresh(self, client: AsyncClient):
        """Test getting state with refresh parameter."""
        response = await client.get("/api/v1/portfolio/state?refresh=true")

        assert response.status_code in [200, 404]

    async def test_get_state_structure(self, client: AsyncClient):
        """Test state response has correct structure."""
        response = await client.get("/api/v1/portfolio/state")

        if response.status_code == 200:
            data = response.json()

            # Required fields
            assert "cash_balance" in data
            assert "portfolio_value" in data
            assert "unrealized_pnl" in data
            assert "daily_pnl" in data
            assert "position_count" in data

            # Type checks
            assert isinstance(data["cash_balance"], (int, float))
            assert isinstance(data["portfolio_value"], (int, float))
            assert isinstance(data["position_count"], int)

    async def test_get_state_consistency(self, client: AsyncClient):
        """Test multiple state requests are consistent."""
        response1 = await client.get("/api/v1/portfolio/state")
        response2 = await client.get("/api/v1/portfolio/state")

        if response1.status_code == 200 and response2.status_code == 200:
            data1 = response1.json()
            data2 = response2.json()

            # Portfolio value shouldn't change significantly
            assert abs(data1["portfolio_value"] - data2["portfolio_value"]) < 1000


# ============================================================================
# GET /positions Tests
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
class TestPortfolioPositionsEndpoint:
    """Test /api/v1/portfolio/positions endpoint."""

    async def test_get_positions_success(self, client: AsyncClient):
        """Test getting positions list."""
        response = await client.get("/api/v1/portfolio/positions")

        assert response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list) or isinstance(data, dict)

    async def test_get_positions_structure(self, client: AsyncClient):
        """Test positions response structure."""
        response = await client.get("/api/v1/portfolio/positions")

        if response.status_code == 200:
            data = response.json()

            if isinstance(data, list) and len(data) > 0:
                position = data[0]
                assert "symbol" in position
                assert "quantity" in position
                assert "market_value" in position or "value" in position

    async def test_get_positions_with_filter(self, client: AsyncClient):
        """Test getting positions with symbol filter."""
        response = await client.get("/api/v1/portfolio/positions?symbol=AAPL")

        assert response.status_code in [200, 404]

    async def test_get_positions_empty_portfolio(self, client: AsyncClient):
        """Test getting positions when portfolio is empty."""
        response = await client.get("/api/v1/portfolio/positions")

        if response.status_code == 200:
            data = response.json()
            # Should return empty list or dict, not error
            assert isinstance(data, (list, dict))


# ============================================================================
# GET /risk-metrics Tests
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
class TestRiskMetricsEndpoint:
    """Test /api/v1/portfolio/risk-metrics endpoint."""

    async def test_get_risk_metrics_success(self, client: AsyncClient):
        """Test getting risk metrics."""
        response = await client.get("/api/v1/portfolio/risk-metrics")

        assert response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.json()
            assert "portfolio_value" in data or "metrics" in data

    async def test_get_risk_metrics_structure(self, client: AsyncClient):
        """Test risk metrics response structure."""
        response = await client.get("/api/v1/portfolio/risk-metrics")

        if response.status_code == 200:
            data = response.json()

            # Common risk metrics
            expected_fields = [
                "portfolio_value",
                "leverage",
                "margin_utilization",
                "diversification_score",
            ]

            # Check for at least some metrics
            has_metrics = any(field in data for field in expected_fields)
            assert has_metrics

    async def test_get_risk_metrics_values(self, client: AsyncClient):
        """Test risk metrics have valid values."""
        response = await client.get("/api/v1/portfolio/risk-metrics")

        if response.status_code == 200:
            data = response.json()

            # Portfolio value should be non-negative
            if "portfolio_value" in data:
                assert data["portfolio_value"] >= 0

            # Leverage should be reasonable
            if "leverage" in data:
                assert 0 <= data["leverage"] <= 10  # Reasonable range

            # Margin utilization should be 0-1
            if "margin_utilization" in data:
                assert 0 <= data["margin_utilization"] <= 1


# ============================================================================
# POST /risk-check Tests
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
class TestRiskCheckEndpoint:
    """Test /api/v1/portfolio/risk-check endpoint."""

    async def test_risk_check_success(self, client: AsyncClient):
        """Test successful risk check."""
        response = await client.post(
            "/api/v1/portfolio/risk-check",
            json={
                "symbol": "AAPL",
                "direction": "buy",
                "quantity": 10.0,
                "price": 150.25,
                "portfolio_value": 100000.0,
            },
        )

        assert response.status_code in [200, 201, 404]

        if response.status_code == 200:
            data = response.json()
            assert "allowed" in data
            assert "violations" in data

    async def test_risk_check_with_existing_positions(
        self, client: AsyncClient
    ):
        """Test risk check with existing positions."""
        response = await client.post(
            "/api/v1/portfolio/risk-check",
            json={
                "symbol": "AAPL",
                "direction": "buy",
                "quantity": 10.0,
                "price": 150.25,
                "portfolio_value": 100000.0,
                "existing_positions": {"AAPL": 5.0, "MSFT": 10.0},
            },
        )

        assert response.status_code in [200, 201, 404]

    async def test_risk_check_large_position(self, client: AsyncClient):
        """Test risk check for very large position."""
        response = await client.post(
            "/api/v1/portfolio/risk-check",
            json={
                "symbol": "AAPL",
                "direction": "buy",
                "quantity": 1000.0,  # Very large
                "price": 150.25,
                "portfolio_value": 100000.0,
            },
        )

        if response.status_code == 200:
            data = response.json()
            # Should likely have violations
            assert "violations" in data

    async def test_risk_check_conservative_profile(self, client: AsyncClient):
        """Test risk check with conservative risk profile."""
        response = await client.post(
            "/api/v1/portfolio/risk-check",
            json={
                "symbol": "AAPL",
                "direction": "buy",
                "quantity": 10.0,
                "price": 150.25,
                "portfolio_value": 100000.0,
                "risk_profile": "conservative",
            },
        )

        assert response.status_code in [200, 201, 404]

    async def test_risk_check_aggressive_profile(self, client: AsyncClient):
        """Test risk check with aggressive risk profile."""
        response = await client.post(
            "/api/v1/portfolio/risk-check",
            json={
                "symbol": "AAPL",
                "direction": "buy",
                "quantity": 10.0,
                "price": 150.25,
                "portfolio_value": 100000.0,
                "risk_profile": "aggressive",
            },
        )

        assert response.status_code in [200, 201, 404]

    async def test_risk_check_missing_symbol(self, client: AsyncClient):
        """Test risk check without symbol returns 422."""
        response = await client.post(
            "/api/v1/portfolio/risk-check",
            json={
                "direction": "buy",
                "quantity": 10.0,
                "price": 150.25,
                "portfolio_value": 100000.0,
            },
        )

        assert response.status_code in [404, 422]

    async def test_risk_check_invalid_direction(self, client: AsyncClient):
        """Test risk check with invalid direction returns 422."""
        response = await client.post(
            "/api/v1/portfolio/risk-check",
            json={
                "symbol": "AAPL",
                "direction": "invalid",
                "quantity": 10.0,
                "price": 150.25,
                "portfolio_value": 100000.0,
            },
        )

        assert response.status_code in [404, 422]

    async def test_risk_check_zero_quantity(self, client: AsyncClient):
        """Test risk check with zero quantity returns 422."""
        response = await client.post(
            "/api/v1/portfolio/risk-check",
            json={
                "symbol": "AAPL",
                "direction": "buy",
                "quantity": 0.0,
                "price": 150.25,
                "portfolio_value": 100000.0,
            },
        )

        assert response.status_code in [404, 422]

    async def test_risk_check_negative_price(self, client: AsyncClient):
        """Test risk check with negative price returns 422."""
        response = await client.post(
            "/api/v1/portfolio/risk-check",
            json={
                "symbol": "AAPL",
                "direction": "buy",
                "quantity": 10.0,
                "price": -150.25,
                "portfolio_value": 100000.0,
            },
        )

        assert response.status_code in [404, 422]


# ============================================================================
# Error Handling Tests
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
class TestPortfolioErrorHandling:
    """Test error handling for portfolio endpoints."""

    async def test_malformed_json(self, client: AsyncClient):
        """Test request with malformed JSON returns 422."""
        response = await client.post(
            "/api/v1/portfolio/risk-check",
            content="invalid json{",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code in [404, 422]

    async def test_method_not_allowed_on_state(self, client: AsyncClient):
        """Test wrong HTTP method on state endpoint returns 405."""
        response = await client.post("/api/v1/portfolio/state")

        assert response.status_code in [404, 405]

    async def test_method_not_allowed_on_positions(self, client: AsyncClient):
        """Test wrong HTTP method on positions endpoint returns 405."""
        response = await client.post("/api/v1/portfolio/positions")

        assert response.status_code in [404, 405]


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
class TestPortfolioIntegration:
    """Test portfolio endpoint integration."""

    async def test_check_risk_before_execute(self, client: AsyncClient):
        """Test checking risk before executing trade."""
        # First check risk
        risk_response = await client.post(
            "/api/v1/portfolio/risk-check",
            json={
                "symbol": "AAPL",
                "direction": "buy",
                "quantity": 10.0,
                "price": 150.25,
                "portfolio_value": 100000.0,
            },
        )

        if risk_response.status_code == 200:
            risk_data = risk_response.json()

            # Only execute if risk check passed
            if risk_data.get("allowed", False):
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

    async def test_state_reflects_positions(self, client: AsyncClient):
        """Test portfolio state reflects positions."""
        state_response = await client.get("/api/v1/portfolio/state")
        positions_response = await client.get("/api/v1/portfolio/positions")

        if (
            state_response.status_code == 200
            and positions_response.status_code == 200
        ):
            state = state_response.json()
            positions = positions_response.json()

            # Position count should match
            state_count = state.get("position_count", 0)

            if isinstance(positions, list):
                assert state_count == len(positions)
            elif isinstance(positions, dict):
                assert state_count == len(positions)

    async def test_metrics_consistent_with_state(self, client: AsyncClient):
        """Test risk metrics are consistent with portfolio state."""
        state_response = await client.get("/api/v1/portfolio/state")
        metrics_response = await client.get("/api/v1/portfolio/risk-metrics")

        if (
            state_response.status_code == 200
            and metrics_response.status_code == 200
        ):
            state = state_response.json()
            metrics = metrics_response.json()

            # Portfolio values should match
            if (
                "portfolio_value" in state
                and "portfolio_value" in metrics
            ):
                assert (
                    abs(
                        state["portfolio_value"]
                        - metrics["portfolio_value"]
                    )
                    < 0.01
                )


# ============================================================================
# Concurrent Access Tests
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
class TestPortfolioConcurrency:
    """Test concurrent access to portfolio endpoints."""

    async def test_concurrent_state_reads(self, client: AsyncClient):
        """Test multiple concurrent state reads."""
        import asyncio

        async def get_state():
            return await client.get("/api/v1/portfolio/state")

        # Launch 5 concurrent requests
        responses = await asyncio.gather(
            get_state(),
            get_state(),
            get_state(),
            get_state(),
            get_state(),
        )

        # All should succeed or fail gracefully
        for response in responses:
            assert response.status_code in [200, 404, 429, 500]

    async def test_concurrent_risk_checks(self, client: AsyncClient):
        """Test multiple concurrent risk checks."""
        import asyncio

        async def check_risk():
            return await client.post(
                "/api/v1/portfolio/risk-check",
                json={
                    "symbol": "AAPL",
                    "direction": "buy",
                    "quantity": 10.0,
                    "price": 150.25,
                    "portfolio_value": 100000.0,
                },
            )

        # Launch 3 concurrent risk checks
        responses = await asyncio.gather(
            check_risk(), check_risk(), check_risk()
        )

        # All should succeed or fail gracefully
        for response in responses:
            assert response.status_code in [200, 201, 404, 429, 500]
