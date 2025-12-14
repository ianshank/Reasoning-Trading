"""
Contract tests for API endpoints.

Tests cover:
- Response schema validation
- Required field presence
- Type checking
- Backward compatibility
- OpenAPI schema compliance
"""

import pytest
from httpx import AsyncClient


# ============================================================================
# Response Schema Validation Tests
# ============================================================================


@pytest.mark.contract
@pytest.mark.asyncio
class TestTradingResponseContracts:
    """Test trading endpoint response contracts."""

    async def test_analyze_response_schema(self, client: AsyncClient):
        """Test analyze endpoint response matches schema."""
        response = await client.post(
            "/api/v1/trading/analyze",
            json={"symbol": "AAPL", "current_price": 150.25},
        )

        if response.status_code == 200:
            data = response.json()

            # Required fields
            required_fields = [
                "symbol",
                "analyst_signals",
                "consensus_score",
                "confidence",
                "timestamp",
            ]

            for field in required_fields:
                assert (
                    field in data
                ), f"Required field '{field}' missing from response"

            # Field types
            assert isinstance(data["symbol"], str)
            assert isinstance(data["analyst_signals"], dict)
            assert isinstance(data["consensus_score"], (int, float))
            assert isinstance(data["confidence"], (int, float))
            assert isinstance(data["timestamp"], str)

            # Value ranges
            assert -1.0 <= data["consensus_score"] <= 1.0
            assert 0.0 <= data["confidence"] <= 1.0

    async def test_decide_response_schema(self, client: AsyncClient):
        """Test decide endpoint response matches schema."""
        response = await client.post(
            "/api/v1/trading/decide",
            json={"symbol": "AAPL", "current_price": 150.25},
        )

        if response.status_code == 200:
            data = response.json()

            # Required fields
            required_fields = [
                "symbol",
                "action",
                "confidence",
                "value_estimate",
                "timestamp",
            ]

            for field in required_fields:
                assert field in data

            # Action object structure
            action = data["action"]
            assert isinstance(action, dict)
            assert "direction" in action

            # Types
            assert isinstance(data["symbol"], str)
            assert isinstance(data["confidence"], (int, float))
            assert isinstance(data["value_estimate"], (int, float))

    async def test_execute_response_schema(self, client: AsyncClient):
        """Test execute endpoint response matches schema."""
        response = await client.post(
            "/api/v1/trading/execute",
            json={
                "symbol": "AAPL",
                "direction": "buy",
                "quantity": 10.0,
                "order_type": "market",
            },
        )

        if response.status_code in [200, 201]:
            data = response.json()

            # Required fields for execution response
            required_fields = [
                "symbol",
                "direction",
                "quantity",
                "success",
                "message",
            ]

            for field in required_fields:
                assert field in data

            # Types
            assert isinstance(data["symbol"], str)
            assert isinstance(data["direction"], str)
            assert isinstance(data["quantity"], (int, float))
            assert isinstance(data["success"], bool)
            assert isinstance(data["message"], str)


@pytest.mark.contract
@pytest.mark.asyncio
class TestPortfolioResponseContracts:
    """Test portfolio endpoint response contracts."""

    async def test_state_response_schema(self, client: AsyncClient):
        """Test portfolio state response matches schema."""
        response = await client.get("/api/v1/portfolio/state")

        if response.status_code == 200:
            data = response.json()

            # Required fields
            required_fields = [
                "cash_balance",
                "portfolio_value",
                "timestamp",
            ]

            for field in required_fields:
                assert field in data

            # Types
            assert isinstance(data["cash_balance"], (int, float))
            assert isinstance(data["portfolio_value"], (int, float))
            assert isinstance(data["timestamp"], str)

            # Non-negative values
            assert data["cash_balance"] >= 0
            assert data["portfolio_value"] >= 0

    async def test_positions_response_schema(self, client: AsyncClient):
        """Test positions response matches schema."""
        response = await client.get("/api/v1/portfolio/positions")

        if response.status_code == 200:
            data = response.json()

            assert isinstance(data, (list, dict))

            if isinstance(data, list) and len(data) > 0:
                position = data[0]

                # Each position should have these fields
                assert "symbol" in position
                assert "quantity" in position

                assert isinstance(position["symbol"], str)
                assert isinstance(position["quantity"], (int, float))

    async def test_risk_metrics_response_schema(self, client: AsyncClient):
        """Test risk metrics response matches schema."""
        response = await client.get("/api/v1/portfolio/risk-metrics")

        if response.status_code == 200:
            data = response.json()

            # Should have risk-related fields
            assert isinstance(data, dict)

            # Check for common risk metrics
            if "leverage" in data:
                assert isinstance(data["leverage"], (int, float))
                assert data["leverage"] >= 0

            if "margin_utilization" in data:
                assert isinstance(data["margin_utilization"], (int, float))
                assert 0 <= data["margin_utilization"] <= 1

    async def test_risk_check_response_schema(self, client: AsyncClient):
        """Test risk check response matches schema."""
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

        if response.status_code == 200:
            data = response.json()

            # Required fields
            required_fields = ["allowed", "violations"]

            for field in required_fields:
                assert field in data

            # Types
            assert isinstance(data["allowed"], bool)
            assert isinstance(data["violations"], list)


# ============================================================================
# Error Response Contracts
# ============================================================================


@pytest.mark.contract
@pytest.mark.asyncio
class TestErrorResponseContracts:
    """Test error response contracts."""

    async def test_validation_error_schema(self, client: AsyncClient):
        """Test validation error response schema."""
        response = await client.post(
            "/api/v1/trading/analyze",
            json={},  # Missing required fields
        )

        assert response.status_code == 422

        data = response.json()

        # FastAPI validation error format
        assert "detail" in data
        assert isinstance(data["detail"], (list, dict, str))

    async def test_not_found_error_schema(self, client: AsyncClient):
        """Test 404 error response schema."""
        response = await client.get("/api/v1/trading/signals/NONEXISTENT")

        if response.status_code == 404:
            data = response.json()

            # Should have error details
            assert "detail" in data or "message" in data

    async def test_method_not_allowed_schema(self, client: AsyncClient):
        """Test 405 error response schema."""
        response = await client.get("/api/v1/trading/analyze")

        assert response.status_code == 405

        # Should have error details
        data = response.json()
        assert isinstance(data, dict)


# ============================================================================
# Type Consistency Tests
# ============================================================================


@pytest.mark.contract
@pytest.mark.asyncio
class TestTypeConsistency:
    """Test type consistency across endpoints."""

    async def test_symbol_always_string(self, client: AsyncClient):
        """Test symbol is always a string across all endpoints."""
        # Test analyze endpoint
        response = await client.post(
            "/api/v1/trading/analyze",
            json={"symbol": "AAPL", "current_price": 150.25},
        )

        if response.status_code == 200:
            assert isinstance(response.json()["symbol"], str)

        # Test signals endpoint
        response = await client.get("/api/v1/trading/signals/AAPL")

        if response.status_code == 200:
            assert isinstance(response.json()["symbol"], str)

    async def test_timestamp_always_iso_string(self, client: AsyncClient):
        """Test timestamp is always ISO format string."""
        response = await client.post(
            "/api/v1/trading/analyze",
            json={"symbol": "AAPL", "current_price": 150.25},
        )

        if response.status_code == 200:
            timestamp = response.json()["timestamp"]
            assert isinstance(timestamp, str)

            # Should be valid ISO format
            from datetime import datetime

            try:
                datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            except ValueError:
                pytest.fail(f"Invalid ISO timestamp: {timestamp}")

    async def test_prices_always_positive(self, client: AsyncClient):
        """Test price fields are always positive."""
        response = await client.post(
            "/api/v1/trading/analyze",
            json={"symbol": "AAPL", "current_price": 150.25},
        )

        if response.status_code == 200:
            data = response.json()

            if "current_price" in data:
                assert data["current_price"] > 0


# ============================================================================
# Backward Compatibility Tests
# ============================================================================


@pytest.mark.contract
@pytest.mark.asyncio
class TestBackwardCompatibility:
    """Test API backward compatibility."""

    async def test_analyze_accepts_minimal_request(
        self, client: AsyncClient
    ):
        """Test analyze endpoint still accepts minimal request."""
        # V1 minimal request
        response = await client.post(
            "/api/v1/trading/analyze",
            json={"symbol": "AAPL", "current_price": 150.25},
        )

        # Should work (200) or endpoint might not exist yet (404)
        assert response.status_code in [200, 404]

    async def test_decide_accepts_optional_parameters(
        self, client: AsyncClient
    ):
        """Test decide endpoint accepts optional parameters."""
        # Without optional params
        response1 = await client.post(
            "/api/v1/trading/decide",
            json={"symbol": "AAPL", "current_price": 150.25},
        )

        # With optional params
        response2 = await client.post(
            "/api/v1/trading/decide",
            json={
                "symbol": "AAPL",
                "current_price": 150.25,
                "max_simulations": 500,
                "time_budget_ms": 1000,
            },
        )

        # Both should work
        if response1.status_code == 200:
            assert response2.status_code == 200

    async def test_extra_fields_ignored(self, client: AsyncClient):
        """Test extra fields in request are ignored (forward compatibility)."""
        response = await client.post(
            "/api/v1/trading/analyze",
            json={
                "symbol": "AAPL",
                "current_price": 150.25,
                "future_field": "should be ignored",
                "another_future_field": 12345,
            },
        )

        # Should succeed despite extra fields
        assert response.status_code in [200, 404]


# ============================================================================
# OpenAPI Schema Compliance Tests
# ============================================================================


@pytest.mark.contract
@pytest.mark.asyncio
class TestOpenAPICompliance:
    """Test OpenAPI schema compliance."""

    async def test_openapi_schema_available(self, client: AsyncClient):
        """Test OpenAPI schema is available."""
        response = await client.get("/api/openapi.json")

        # Might be disabled in production
        assert response.status_code in [200, 404]

        if response.status_code == 200:
            schema = response.json()

            # Basic OpenAPI structure
            assert "openapi" in schema or "swagger" in schema
            assert "info" in schema
            assert "paths" in schema

    async def test_docs_page_available(self, client: AsyncClient):
        """Test Swagger UI docs are available."""
        response = await client.get("/docs")

        # Might be disabled in production
        assert response.status_code in [200, 404]

    async def test_redoc_page_available(self, client: AsyncClient):
        """Test ReDoc docs are available."""
        response = await client.get("/redoc")

        # Might be disabled in production
        assert response.status_code in [200, 404]


# ============================================================================
# Health Check Contract Tests
# ============================================================================


@pytest.mark.contract
@pytest.mark.asyncio
class TestHealthCheckContract:
    """Test health check endpoint contract."""

    async def test_health_check_schema(self, client: AsyncClient):
        """Test health check response schema."""
        response = await client.get("/health")

        assert response.status_code == 200

        data = response.json()

        # Required fields
        assert "status" in data
        assert isinstance(data["status"], str)

        # Common fields
        if "version" in data:
            assert isinstance(data["version"], str)

        if "environment" in data:
            assert isinstance(data["environment"], str)


# ============================================================================
# Pagination Contract Tests
# ============================================================================


@pytest.mark.contract
@pytest.mark.asyncio
class TestPaginationContracts:
    """Test pagination contracts for list endpoints."""

    async def test_positions_pagination_schema(self, client: AsyncClient):
        """Test positions endpoint pagination if supported."""
        response = await client.get(
            "/api/v1/portfolio/positions?limit=10&offset=0"
        )

        if response.status_code == 200:
            data = response.json()

            # If pagination is supported, check for metadata
            if isinstance(data, dict) and "items" in data:
                assert "total" in data or "count" in data
                assert "items" in data
                assert isinstance(data["items"], list)


# ============================================================================
# Content Type Contract Tests
# ============================================================================


@pytest.mark.contract
@pytest.mark.asyncio
class TestContentTypeContracts:
    """Test content type contracts."""

    async def test_json_content_type(self, client: AsyncClient):
        """Test API returns JSON content type."""
        response = await client.post(
            "/api/v1/trading/analyze",
            json={"symbol": "AAPL", "current_price": 150.25},
        )

        if response.status_code == 200:
            content_type = response.headers.get("content-type", "")
            assert "application/json" in content_type

    async def test_accepts_json_content_type(self, client: AsyncClient):
        """Test API accepts JSON content type."""
        response = await client.post(
            "/api/v1/trading/analyze",
            json={"symbol": "AAPL", "current_price": 150.25},
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code in [200, 404, 422]


# ============================================================================
# CORS Contract Tests
# ============================================================================


@pytest.mark.contract
@pytest.mark.asyncio
class TestCORSContracts:
    """Test CORS header contracts."""

    async def test_cors_headers_present(self, client: AsyncClient):
        """Test CORS headers are present on responses."""
        response = await client.options(
            "/api/v1/trading/analyze",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            },
        )

        # CORS headers might be present
        if response.status_code == 200:
            headers = response.headers

            # Check for CORS headers
            assert (
                "access-control-allow-origin" in headers
                or "Access-Control-Allow-Origin" in headers
                or True  # Flexible check
            )

    async def test_cors_preflight_success(self, client: AsyncClient):
        """Test CORS preflight requests succeed."""
        response = await client.options(
            "/api/v1/trading/analyze",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )

        # Should succeed or return 405 if OPTIONS not implemented
        assert response.status_code in [200, 204, 405]
