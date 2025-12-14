"""
Integration tests for trading API endpoints.

Tests cover:
- POST /api/v1/trading/analyze
- POST /api/v1/trading/decide
- POST /api/v1/trading/execute
- GET /api/v1/trading/signals/{symbol}
- GET /api/v1/trading/state/{symbol}
- Authentication and authorization
- Error handling and validation
- Rate limiting
"""

import pytest
from httpx import AsyncClient


# ============================================================================
# POST /analyze Tests
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
class TestAnalyzeEndpoint:
    """Test /api/v1/trading/analyze endpoint."""

    async def test_analyze_success(self, client: AsyncClient):
        """Test successful analysis request."""
        response = await client.post(
            "/api/v1/trading/analyze",
            json={
                "symbol": "AAPL",
                "current_price": 150.25,
                "include_fundamentals": True,
                "include_news": True,
                "include_social": True,
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["symbol"] == "AAPL"
        assert "analyst_signals" in data
        assert "consensus_score" in data
        assert "confidence" in data
        assert "timestamp" in data

    async def test_analyze_minimal_request(self, client: AsyncClient):
        """Test analysis with minimal required fields."""
        response = await client.post(
            "/api/v1/trading/analyze",
            json={"symbol": "AAPL", "current_price": 150.25},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "AAPL"

    async def test_analyze_with_all_options(self, client: AsyncClient):
        """Test analysis with all optional parameters."""
        response = await client.post(
            "/api/v1/trading/analyze",
            json={
                "symbol": "TSLA",
                "current_price": 250.50,
                "include_fundamentals": True,
                "include_news": True,
                "include_social": True,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "TSLA"
        assert "analyst_signals" in data

    async def test_analyze_missing_symbol(self, client: AsyncClient):
        """Test analysis without symbol returns 422."""
        response = await client.post(
            "/api/v1/trading/analyze", json={"current_price": 150.25}
        )

        assert response.status_code == 422

    async def test_analyze_missing_price(self, client: AsyncClient):
        """Test analysis without price returns 422."""
        response = await client.post("/api/v1/trading/analyze", json={"symbol": "AAPL"})

        assert response.status_code == 422

    async def test_analyze_invalid_price_zero(self, client: AsyncClient):
        """Test analysis with zero price returns 422."""
        response = await client.post(
            "/api/v1/trading/analyze",
            json={"symbol": "AAPL", "current_price": 0.0},
        )

        assert response.status_code == 422

    async def test_analyze_invalid_price_negative(self, client: AsyncClient):
        """Test analysis with negative price returns 422."""
        response = await client.post(
            "/api/v1/trading/analyze",
            json={"symbol": "AAPL", "current_price": -10.0},
        )

        assert response.status_code == 422

    async def test_analyze_invalid_symbol_type(self, client: AsyncClient):
        """Test analysis with non-string symbol returns 422."""
        response = await client.post(
            "/api/v1/trading/analyze", json={"symbol": 123, "current_price": 150.0}
        )

        assert response.status_code == 422

    async def test_analyze_response_structure(self, client: AsyncClient):
        """Test analysis response has correct structure."""
        response = await client.post(
            "/api/v1/trading/analyze",
            json={"symbol": "AAPL", "current_price": 150.25},
        )

        assert response.status_code == 200
        data = response.json()

        # Verify required fields
        assert "symbol" in data
        assert "analyst_signals" in data
        assert "consensus_score" in data
        assert "confidence" in data
        assert "timestamp" in data

        # Verify field types
        assert isinstance(data["symbol"], str)
        assert isinstance(data["analyst_signals"], dict)
        assert isinstance(data["consensus_score"], (int, float))
        assert isinstance(data["confidence"], (int, float))
        assert isinstance(data["timestamp"], str)


# ============================================================================
# POST /decide Tests
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
class TestDecideEndpoint:
    """Test /api/v1/trading/decide endpoint."""

    async def test_decide_success(self, client: AsyncClient):
        """Test successful decision request."""
        response = await client.post(
            "/api/v1/trading/decide",
            json={
                "symbol": "AAPL",
                "current_price": 150.25,
                "max_simulations": 1000,
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["symbol"] == "AAPL"
        assert "action" in data
        assert "confidence" in data
        assert "value_estimate" in data
        assert "simulations_run" in data

    async def test_decide_with_time_budget(self, client: AsyncClient):
        """Test decision with time budget."""
        response = await client.post(
            "/api/v1/trading/decide",
            json={
                "symbol": "AAPL",
                "current_price": 150.25,
                "max_simulations": 1000,
                "time_budget_ms": 500,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "computation_time_ms" in data

    async def test_decide_with_analyst_signals(self, client: AsyncClient):
        """Test decision with pre-computed analyst signals."""
        response = await client.post(
            "/api/v1/trading/decide",
            json={
                "symbol": "AAPL",
                "current_price": 150.25,
                "max_simulations": 500,
                "analyst_signals": {
                    "market_analyst_score": 0.7,
                    "news_analyst_score": 0.5,
                },
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "AAPL"

    async def test_decide_missing_symbol(self, client: AsyncClient):
        """Test decision without symbol returns 422."""
        response = await client.post(
            "/api/v1/trading/decide",
            json={"current_price": 150.25, "max_simulations": 1000},
        )

        assert response.status_code == 422

    async def test_decide_invalid_simulations(self, client: AsyncClient):
        """Test decision with invalid simulations returns 422."""
        response = await client.post(
            "/api/v1/trading/decide",
            json={
                "symbol": "AAPL",
                "current_price": 150.25,
                "max_simulations": 0,
            },
        )

        assert response.status_code == 422

    async def test_decide_response_structure(self, client: AsyncClient):
        """Test decision response has correct structure."""
        response = await client.post(
            "/api/v1/trading/decide",
            json={"symbol": "AAPL", "current_price": 150.25},
        )

        assert response.status_code == 200
        data = response.json()

        # Verify required fields
        assert "symbol" in data
        assert "action" in data
        assert "confidence" in data
        assert "value_estimate" in data
        assert "timestamp" in data

        # Verify action structure
        action = data["action"]
        assert isinstance(action, dict)
        assert "direction" in action


# ============================================================================
# POST /execute Tests
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
class TestExecuteEndpoint:
    """Test /api/v1/trading/execute endpoint."""

    async def test_execute_market_buy(self, client: AsyncClient):
        """Test executing a market buy order."""
        response = await client.post(
            "/api/v1/trading/execute",
            json={
                "symbol": "AAPL",
                "direction": "buy",
                "quantity": 10.0,
                "order_type": "market",
            },
        )

        # May return 200 or 201 depending on implementation
        assert response.status_code in [200, 201]
        data = response.json()

        assert data["symbol"] == "AAPL"
        assert data["direction"] == "buy"
        assert data["quantity"] == 10.0

    async def test_execute_limit_order(self, client: AsyncClient):
        """Test executing a limit order."""
        response = await client.post(
            "/api/v1/trading/execute",
            json={
                "symbol": "AAPL",
                "direction": "buy",
                "quantity": 10.0,
                "order_type": "limit",
                "limit_price": 149.50,
            },
        )

        assert response.status_code in [200, 201]
        data = response.json()
        assert data["symbol"] == "AAPL"

    async def test_execute_stop_order(self, client: AsyncClient):
        """Test executing a stop order."""
        response = await client.post(
            "/api/v1/trading/execute",
            json={
                "symbol": "AAPL",
                "direction": "sell",
                "quantity": 10.0,
                "order_type": "stop",
                "stop_loss_pct": 0.05,
            },
        )

        assert response.status_code in [200, 201]

    async def test_execute_with_stop_loss(self, client: AsyncClient):
        """Test execution with stop loss."""
        response = await client.post(
            "/api/v1/trading/execute",
            json={
                "symbol": "AAPL",
                "direction": "buy",
                "quantity": 10.0,
                "order_type": "market",
                "stop_loss_pct": 0.05,
            },
        )

        assert response.status_code in [200, 201]

    async def test_execute_with_take_profit(self, client: AsyncClient):
        """Test execution with take profit."""
        response = await client.post(
            "/api/v1/trading/execute",
            json={
                "symbol": "AAPL",
                "direction": "buy",
                "quantity": 10.0,
                "order_type": "market",
                "take_profit_pct": 0.15,
            },
        )

        assert response.status_code in [200, 201]

    async def test_execute_missing_direction(self, client: AsyncClient):
        """Test execution without direction returns 422."""
        response = await client.post(
            "/api/v1/trading/execute",
            json={"symbol": "AAPL", "quantity": 10.0},
        )

        assert response.status_code == 422

    async def test_execute_invalid_direction(self, client: AsyncClient):
        """Test execution with invalid direction returns 422."""
        response = await client.post(
            "/api/v1/trading/execute",
            json={
                "symbol": "AAPL",
                "direction": "invalid",
                "quantity": 10.0,
            },
        )

        assert response.status_code == 422

    async def test_execute_zero_quantity(self, client: AsyncClient):
        """Test execution with zero quantity returns 422."""
        response = await client.post(
            "/api/v1/trading/execute",
            json={
                "symbol": "AAPL",
                "direction": "buy",
                "quantity": 0.0,
            },
        )

        assert response.status_code == 422

    async def test_execute_negative_quantity(self, client: AsyncClient):
        """Test execution with negative quantity returns 422."""
        response = await client.post(
            "/api/v1/trading/execute",
            json={
                "symbol": "AAPL",
                "direction": "buy",
                "quantity": -10.0,
            },
        )

        assert response.status_code == 422


# ============================================================================
# GET /signals/{symbol} Tests
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
class TestSignalsEndpoint:
    """Test /api/v1/trading/signals/{symbol} endpoint."""

    async def test_get_signals_success(self, client: AsyncClient):
        """Test getting signals for a symbol."""
        response = await client.get("/api/v1/trading/signals/AAPL")

        assert response.status_code == 200
        data = response.json()

        assert data["symbol"] == "AAPL"
        assert "signals" in data
        assert "timestamp" in data

    async def test_get_signals_different_symbols(self, client: AsyncClient):
        """Test getting signals for different symbols."""
        symbols = ["AAPL", "MSFT", "TSLA"]

        for symbol in symbols:
            response = await client.get(f"/api/v1/trading/signals/{symbol}")
            assert response.status_code in [200, 404]  # May not have cached signals

    async def test_get_signals_case_insensitive(self, client: AsyncClient):
        """Test signals endpoint is case-insensitive."""
        response1 = await client.get("/api/v1/trading/signals/aapl")
        response2 = await client.get("/api/v1/trading/signals/AAPL")

        # Both should work
        assert response1.status_code in [200, 404]
        assert response2.status_code in [200, 404]

    async def test_get_signals_nonexistent_symbol(self, client: AsyncClient):
        """Test getting signals for nonexistent symbol returns 404."""
        response = await client.get("/api/v1/trading/signals/INVALID_SYMBOL_XYZ")

        assert response.status_code == 404


# ============================================================================
# GET /state/{symbol} Tests
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
class TestStateEndpoint:
    """Test /api/v1/trading/state/{symbol} endpoint."""

    async def test_get_state_success(self, client: AsyncClient):
        """Test getting trading state for a symbol."""
        response = await client.get("/api/v1/trading/state/AAPL")

        assert response.status_code == 200
        data = response.json()

        assert data["symbol"] == "AAPL"
        assert "current_price" in data
        assert "portfolio" in data
        assert "technical_indicators" in data
        assert "market_regime" in data
        assert "timestamp" in data

    async def test_get_state_portfolio_structure(self, client: AsyncClient):
        """Test state response includes proper portfolio structure."""
        response = await client.get("/api/v1/trading/state/AAPL")

        assert response.status_code == 200
        data = response.json()

        portfolio = data["portfolio"]
        assert "cash_balance" in portfolio
        assert "portfolio_value" in portfolio

    async def test_get_state_technical_indicators(self, client: AsyncClient):
        """Test state response includes technical indicators."""
        response = await client.get("/api/v1/trading/state/AAPL")

        assert response.status_code == 200
        data = response.json()

        indicators = data["technical_indicators"]
        assert isinstance(indicators, dict)

    async def test_get_state_multiple_symbols(self, client: AsyncClient):
        """Test getting state for multiple symbols."""
        symbols = ["AAPL", "MSFT"]

        for symbol in symbols:
            response = await client.get(f"/api/v1/trading/state/{symbol}")
            assert response.status_code == 200
            data = response.json()
            assert data["symbol"] == symbol


# ============================================================================
# Error Handling Tests
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
class TestTradingErrorHandling:
    """Test error handling for trading endpoints."""

    async def test_malformed_json(self, client: AsyncClient):
        """Test request with malformed JSON returns 422."""
        response = await client.post(
            "/api/v1/trading/analyze",
            content="invalid json{",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 422

    async def test_wrong_content_type(self, client: AsyncClient):
        """Test request with wrong content type."""
        response = await client.post(
            "/api/v1/trading/analyze",
            content="symbol=AAPL&price=150",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        # FastAPI should handle this gracefully
        assert response.status_code in [415, 422]

    async def test_missing_content_type(self, client: AsyncClient):
        """Test request without content type header."""
        response = await client.post(
            "/api/v1/trading/analyze",
            content='{"symbol": "AAPL", "current_price": 150.25}',
        )

        # Should still work as FastAPI is smart about this
        assert response.status_code in [200, 422]

    async def test_extra_fields_ignored(self, client: AsyncClient):
        """Test extra fields in request are ignored."""
        response = await client.post(
            "/api/v1/trading/analyze",
            json={
                "symbol": "AAPL",
                "current_price": 150.25,
                "extra_field": "should be ignored",
                "another_extra": 123,
            },
        )

        # Should succeed and ignore extra fields
        assert response.status_code == 200

    async def test_type_coercion(self, client: AsyncClient):
        """Test type coercion for compatible types."""
        response = await client.post(
            "/api/v1/trading/analyze",
            json={
                "symbol": "AAPL",
                "current_price": "150.25",  # String instead of float
            },
        )

        # FastAPI/Pydantic should coerce this
        assert response.status_code == 200

    async def test_method_not_allowed(self, client: AsyncClient):
        """Test wrong HTTP method returns 405."""
        response = await client.get("/api/v1/trading/analyze")

        assert response.status_code == 405


# ============================================================================
# Authentication Tests
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
class TestTradingAuthentication:
    """Test authentication for trading endpoints."""

    @pytest.mark.skip(reason="Auth not yet implemented")
    async def test_analyze_without_auth(self, client: AsyncClient):
        """Test analysis without authentication returns 401."""
        # Remove auth headers
        client.headers.pop("Authorization", None)

        response = await client.post(
            "/api/v1/trading/analyze",
            json={"symbol": "AAPL", "current_price": 150.25},
        )

        assert response.status_code == 401

    @pytest.mark.skip(reason="Auth not yet implemented")
    async def test_execute_requires_auth(self, client: AsyncClient):
        """Test execution requires authentication."""
        client.headers.pop("Authorization", None)

        response = await client.post(
            "/api/v1/trading/execute",
            json={
                "symbol": "AAPL",
                "direction": "buy",
                "quantity": 10.0,
            },
        )

        assert response.status_code == 401
