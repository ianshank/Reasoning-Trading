"""
Unit tests for Pydantic models.

Tests cover:
- Request model validation
- Response model serialization
- WebSocket message models
- Field validators
- Edge cases and error handling
- Type coercion
- Default values
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from enterprise_ui.backend.models.requests import (
    BatchTriggerRequest,
    HierarchicalSearchRequest,
    MCTSSearchRequest,
    PortfolioQueryRequest,
    RiskCheckRequest,
    TradeExecutionRequest,
    TradingAnalysisRequest,
    TradingDecisionRequest,
)
from enterprise_ui.backend.models.responses import (
    AnalystSignalResponse,
    ErrorResponse,
    HealthCheckResponse,
    PortfolioStateResponse,
    PositionResponse,
    RegimeResponse,
    RiskCheckResponse,
    TradingAnalysisResponse,
    TradingDecisionResponse,
)
from enterprise_ui.backend.models.websocket import (
    MCTSProgressPayload,
    PortfolioUpdatePayload,
    PriceUpdatePayload,
    SubscribeMessage,
    UnsubscribeMessage,
    WSMessage,
    WSMessageType,
    create_error,
    create_heartbeat,
    create_portfolio_update,
    create_price_update,
)
from reasoning_trading.config import RiskProfile
from reasoning_trading.core.state import MarketRegime


# ============================================================================
# Request Model Tests
# ============================================================================


@pytest.mark.unit
class TestTradingAnalysisRequest:
    """Test TradingAnalysisRequest model."""

    def test_valid_request(self):
        """Test valid trading analysis request."""
        request = TradingAnalysisRequest(
            symbol="AAPL",
            include_news=True,
            include_social=True,
            include_fundamentals=True,
            include_macro=True,
            enable_debate=True,
            max_debate_rounds=4,
        )
        assert request.symbol == "AAPL"
        assert request.include_news is True
        assert request.max_debate_rounds == 4

    def test_symbol_normalization(self):
        """Test symbol is normalized to uppercase."""
        request = TradingAnalysisRequest(symbol="aapl")
        assert request.symbol == "AAPL"

    def test_symbol_stripped(self):
        """Test symbol whitespace is stripped."""
        request = TradingAnalysisRequest(symbol="  aapl  ")
        assert request.symbol == "AAPL"

    def test_default_values(self):
        """Test default values are applied correctly."""
        request = TradingAnalysisRequest(symbol="AAPL")
        assert request.include_news is True
        assert request.include_social is True
        assert request.include_fundamentals is True
        assert request.include_macro is True
        assert request.enable_debate is True
        assert request.max_debate_rounds == 4

    def test_invalid_symbol_empty(self):
        """Test empty symbol is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            TradingAnalysisRequest(symbol="")
        errors = exc_info.value.errors()
        assert any("symbol" in str(e.get("loc")) for e in errors)

    def test_invalid_max_debate_rounds_too_low(self):
        """Test max_debate_rounds below minimum is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            TradingAnalysisRequest(symbol="AAPL", max_debate_rounds=0)
        errors = exc_info.value.errors()
        assert any("max_debate_rounds" in str(e.get("loc")) for e in errors)

    def test_invalid_max_debate_rounds_too_high(self):
        """Test max_debate_rounds above maximum is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            TradingAnalysisRequest(symbol="AAPL", max_debate_rounds=11)
        errors = exc_info.value.errors()
        assert any("max_debate_rounds" in str(e.get("loc")) for e in errors)


@pytest.mark.unit
class TestTradingDecisionRequest:
    """Test TradingDecisionRequest model."""

    def test_valid_request(self):
        """Test valid trading decision request."""
        request = TradingDecisionRequest(
            symbol="AAPL",
            current_price=150.25,
            portfolio_value=100000.0,
            cash_balance=50000.0,
            risk_profile=RiskProfile.MODERATE,
            max_simulations=1000,
            time_budget_ms=500,
        )
        assert request.symbol == "AAPL"
        assert request.current_price == 150.25
        assert request.risk_profile == RiskProfile.MODERATE

    def test_invalid_current_price_zero(self):
        """Test current_price of zero is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            TradingDecisionRequest(symbol="AAPL", current_price=0.0)
        errors = exc_info.value.errors()
        assert any("current_price" in str(e.get("loc")) for e in errors)

    def test_invalid_current_price_negative(self):
        """Test negative current_price is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            TradingDecisionRequest(symbol="AAPL", current_price=-10.0)
        errors = exc_info.value.errors()
        assert any("current_price" in str(e.get("loc")) for e in errors)

    def test_invalid_simulations_too_low(self):
        """Test max_simulations below minimum is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            TradingDecisionRequest(
                symbol="AAPL", current_price=150.0, max_simulations=5
            )
        errors = exc_info.value.errors()
        assert any("max_simulations" in str(e.get("loc")) for e in errors)

    def test_invalid_simulations_too_high(self):
        """Test max_simulations above maximum is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            TradingDecisionRequest(
                symbol="AAPL", current_price=150.0, max_simulations=200000
            )
        errors = exc_info.value.errors()
        assert any("max_simulations" in str(e.get("loc")) for e in errors)


@pytest.mark.unit
class TestTradeExecutionRequest:
    """Test TradeExecutionRequest model."""

    def test_valid_request(self):
        """Test valid trade execution request."""
        request = TradeExecutionRequest(
            symbol="AAPL",
            direction="buy",
            quantity=10.0,
            order_type="market",
            time_in_force="day",
            dry_run=True,
        )
        assert request.symbol == "AAPL"
        assert request.direction == "buy"
        assert request.dry_run is True

    def test_valid_limit_order(self):
        """Test valid limit order with limit_price."""
        request = TradeExecutionRequest(
            symbol="AAPL",
            direction="buy",
            quantity=10.0,
            order_type="limit",
            limit_price=149.50,
        )
        assert request.order_type == "limit"
        assert request.limit_price == 149.50

    def test_valid_stop_order(self):
        """Test valid stop order with stop_price."""
        request = TradeExecutionRequest(
            symbol="AAPL",
            direction="sell",
            quantity=10.0,
            order_type="stop",
            stop_price=145.00,
        )
        assert request.order_type == "stop"
        assert request.stop_price == 145.00

    def test_invalid_direction(self):
        """Test invalid trade direction is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            TradeExecutionRequest(
                symbol="AAPL", direction="invalid", quantity=10.0
            )
        errors = exc_info.value.errors()
        assert any("direction" in str(e.get("loc")) for e in errors)

    def test_invalid_quantity_zero(self):
        """Test quantity of zero is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            TradeExecutionRequest(symbol="AAPL", direction="buy", quantity=0.0)
        errors = exc_info.value.errors()
        assert any("quantity" in str(e.get("loc")) for e in errors)

    def test_invalid_quantity_negative(self):
        """Test negative quantity is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            TradeExecutionRequest(symbol="AAPL", direction="buy", quantity=-5.0)
        errors = exc_info.value.errors()
        assert any("quantity" in str(e.get("loc")) for e in errors)


@pytest.mark.unit
class TestMCTSSearchRequest:
    """Test MCTSSearchRequest model."""

    def test_valid_request(self):
        """Test valid MCTS search request."""
        request = MCTSSearchRequest(
            symbol="AAPL",
            current_price=150.25,
            max_simulations=1000,
            exploration_weight=1.414,
            return_tree=False,
        )
        assert request.symbol == "AAPL"
        assert request.exploration_weight == 1.414

    def test_default_exploration_weight(self):
        """Test default exploration weight (sqrt(2))."""
        request = MCTSSearchRequest(symbol="AAPL", current_price=150.0)
        assert request.exploration_weight == 1.414

    def test_invalid_exploration_weight_negative(self):
        """Test negative exploration weight is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            MCTSSearchRequest(
                symbol="AAPL", current_price=150.0, exploration_weight=-1.0
            )
        errors = exc_info.value.errors()
        assert any("exploration_weight" in str(e.get("loc")) for e in errors)


@pytest.mark.unit
class TestRiskCheckRequest:
    """Test RiskCheckRequest model."""

    def test_valid_request(self):
        """Test valid risk check request."""
        request = RiskCheckRequest(
            symbol="AAPL",
            direction="buy",
            quantity=10.0,
            price=150.25,
            portfolio_value=100000.0,
            existing_positions={"AAPL": 5.0},
            risk_profile=RiskProfile.MODERATE,
        )
        assert request.symbol == "AAPL"
        assert request.existing_positions == {"AAPL": 5.0}

    def test_empty_existing_positions(self):
        """Test empty existing_positions defaults correctly."""
        request = RiskCheckRequest(
            symbol="AAPL",
            direction="buy",
            quantity=10.0,
            price=150.0,
            portfolio_value=100000.0,
        )
        assert request.existing_positions == {}


@pytest.mark.unit
class TestBatchTriggerRequest:
    """Test BatchTriggerRequest model."""

    def test_valid_request(self):
        """Test valid batch trigger request."""
        request = BatchTriggerRequest(
            symbols=["AAPL", "MSFT", "TSLA"],
            analysis_type="quick",
            priority="normal",
        )
        assert len(request.symbols) == 3
        assert "AAPL" in request.symbols

    def test_symbols_normalized(self):
        """Test symbols are normalized to uppercase."""
        request = BatchTriggerRequest(symbols=["aapl", "msft"])
        assert request.symbols == ["AAPL", "MSFT"]

    def test_invalid_empty_symbols(self):
        """Test empty symbols list is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            BatchTriggerRequest(symbols=[])
        errors = exc_info.value.errors()
        assert any("symbols" in str(e.get("loc")) for e in errors)

    def test_invalid_too_many_symbols(self):
        """Test too many symbols is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            BatchTriggerRequest(symbols=["SYM" + str(i) for i in range(51)])
        errors = exc_info.value.errors()
        assert any("symbols" in str(e.get("loc")) for e in errors)


# ============================================================================
# Response Model Tests
# ============================================================================


@pytest.mark.unit
class TestAnalystSignalResponse:
    """Test AnalystSignalResponse model."""

    def test_valid_response(self):
        """Test valid analyst signal response."""
        response = AnalystSignalResponse(
            analyst_type="market",
            score=0.65,
            confidence=0.85,
            reasoning="Strong upward momentum",
        )
        assert response.analyst_type == "market"
        assert response.score == 0.65

    def test_serialization(self):
        """Test response serializes correctly."""
        response = AnalystSignalResponse(
            analyst_type="market", score=0.5, confidence=0.8
        )
        data = response.model_dump()
        assert "analyst_type" in data
        assert "score" in data
        assert "confidence" in data


@pytest.mark.unit
class TestTradingAnalysisResponse:
    """Test TradingAnalysisResponse model."""

    def test_valid_response(self, sample_analyst_signals):
        """Test valid trading analysis response."""
        response = TradingAnalysisResponse(
            symbol="AAPL",
            timestamp=datetime.now(),
            current_price=150.25,
            market_regime=MarketRegime.TRENDING_UP,
            analyst_signals=sample_analyst_signals,
            consensus_score=0.55,
            consensus_confidence=0.77,
            recommendation="MODERATE BUY",
            analysis_time_ms=1234.56,
        )
        assert response.symbol == "AAPL"
        assert len(response.analyst_signals) == 3

    def test_serialization(self, sample_analyst_signals):
        """Test response serializes correctly with nested models."""
        response = TradingAnalysisResponse(
            symbol="AAPL",
            timestamp=datetime.now(),
            current_price=150.0,
            market_regime=MarketRegime.NEUTRAL,
            analyst_signals=sample_analyst_signals,
            consensus_score=0.5,
            consensus_confidence=0.7,
            recommendation="HOLD",
            analysis_time_ms=1000.0,
        )
        data = response.model_dump()
        assert "analyst_signals" in data
        assert isinstance(data["analyst_signals"], list)


@pytest.mark.unit
class TestPortfolioStateResponse:
    """Test PortfolioStateResponse model."""

    def test_valid_response(self, sample_positions):
        """Test valid portfolio state response."""
        response = PortfolioStateResponse(
            timestamp=datetime.now(),
            cash_balance=50000.0,
            portfolio_value=100000.0,
            positions=sample_positions,
            unrealized_pnl=2025.0,
            realized_pnl_today=500.0,
            realized_pnl_total=5000.0,
            daily_pnl=2525.0,
            daily_pnl_pct=0.0258,
            max_drawdown=0.05,
            current_drawdown=0.02,
            position_count=2,
        )
        assert response.portfolio_value == 100000.0
        assert len(response.positions) == 2


@pytest.mark.unit
class TestErrorResponse:
    """Test ErrorResponse model."""

    def test_valid_error(self):
        """Test valid error response."""
        response = ErrorResponse(
            error="ValidationError",
            message="Invalid input parameters",
            details={"field": "symbol", "issue": "required"},
        )
        assert response.error == "ValidationError"
        assert "field" in response.details

    def test_error_without_details(self):
        """Test error response without details."""
        response = ErrorResponse(error="InternalError", message="Server error")
        assert response.details is None


# ============================================================================
# WebSocket Model Tests
# ============================================================================


@pytest.mark.unit
class TestWSMessage:
    """Test WSMessage model."""

    def test_valid_message(self):
        """Test valid WebSocket message."""
        message = WSMessage(
            type=WSMessageType.PRICE_UPDATE,
            payload={"symbol": "AAPL", "price": 150.25},
        )
        assert message.type == WSMessageType.PRICE_UPDATE
        assert message.payload["symbol"] == "AAPL"

    def test_timestamp_auto_generated(self):
        """Test timestamp is auto-generated if not provided."""
        message = WSMessage(
            type=WSMessageType.PING,
            payload={},
        )
        assert message.timestamp is not None
        assert isinstance(message.timestamp, datetime)


@pytest.mark.unit
class TestSubscribeMessage:
    """Test SubscribeMessage model."""

    def test_valid_subscription(self):
        """Test valid subscription message."""
        message = SubscribeMessage(
            channels=["prices", "portfolio"],
            symbols=["AAPL", "MSFT"],
        )
        assert "prices" in message.channels
        assert "AAPL" in message.symbols

    def test_subscription_without_symbols(self):
        """Test subscription without specific symbols."""
        message = SubscribeMessage(channels=["portfolio"])
        assert message.symbols is None


@pytest.mark.unit
class TestPriceUpdatePayload:
    """Test PriceUpdatePayload model."""

    def test_valid_payload(self):
        """Test valid price update payload."""
        payload = PriceUpdatePayload(
            symbol="AAPL",
            price=150.25,
            bid=150.20,
            ask=150.30,
            volume=1000000.0,
            change_pct=0.015,
            timestamp=datetime.now(),
        )
        assert payload.symbol == "AAPL"
        assert payload.price == 150.25

    def test_invalid_price_zero(self):
        """Test price of zero is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            PriceUpdatePayload(
                symbol="AAPL",
                price=0.0,
                change_pct=0.0,
                timestamp=datetime.now(),
            )
        errors = exc_info.value.errors()
        assert any("price" in str(e.get("loc")) for e in errors)


@pytest.mark.unit
class TestPortfolioUpdatePayload:
    """Test PortfolioUpdatePayload model."""

    def test_valid_payload(self):
        """Test valid portfolio update payload."""
        payload = PortfolioUpdatePayload(
            portfolio_value=100000.0,
            cash_balance=50000.0,
            unrealized_pnl=2000.0,
            realized_pnl_today=500.0,
            daily_pnl_pct=0.025,
            position_count=5,
            timestamp=datetime.now(),
        )
        assert payload.portfolio_value == 100000.0
        assert payload.position_count == 5


@pytest.mark.unit
class TestMCTSProgressPayload:
    """Test MCTSProgressPayload model."""

    def test_valid_payload(self):
        """Test valid MCTS progress payload."""
        payload = MCTSProgressPayload(
            symbol="AAPL",
            simulations_completed=500,
            total_simulations=1000,
            progress_pct=0.5,
            best_action_so_far="buy",
            expected_value=1.25,
        )
        assert payload.progress_pct == 0.5
        assert payload.simulations_completed == 500

    def test_invalid_progress_pct_too_high(self):
        """Test progress_pct above 1.0 is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            MCTSProgressPayload(
                symbol="AAPL",
                simulations_completed=1500,
                total_simulations=1000,
                progress_pct=1.5,
                best_action_so_far="buy",
                expected_value=1.0,
            )
        errors = exc_info.value.errors()
        assert any("progress_pct" in str(e.get("loc")) for e in errors)


# ============================================================================
# WebSocket Helper Functions Tests
# ============================================================================


@pytest.mark.unit
class TestWebSocketHelpers:
    """Test WebSocket helper functions."""

    def test_create_price_update(self):
        """Test create_price_update helper."""
        message = create_price_update(
            symbol="AAPL", price=150.25, change_pct=0.015
        )
        assert message.type == WSMessageType.PRICE_UPDATE
        assert message.payload["symbol"] == "AAPL"
        assert message.payload["price"] == 150.25

    def test_create_portfolio_update(self):
        """Test create_portfolio_update helper."""
        message = create_portfolio_update(
            portfolio_value=100000.0,
            cash_balance=50000.0,
            unrealized_pnl=2000.0,
            realized_pnl_today=500.0,
            daily_pnl_pct=0.025,
            position_count=5,
        )
        assert message.type == WSMessageType.PORTFOLIO_UPDATE
        assert message.payload["portfolio_value"] == 100000.0

    def test_create_error(self):
        """Test create_error helper."""
        message = create_error(
            error_code="INVALID_SYMBOL",
            error_message="Symbol not found",
            details={"symbol": "INVALID"},
        )
        assert message.type == WSMessageType.ERROR
        assert message.payload["error_code"] == "INVALID_SYMBOL"

    def test_create_heartbeat(self):
        """Test create_heartbeat helper."""
        message = create_heartbeat(connection_id="conn_123", uptime_seconds=300.0)
        assert message.type == WSMessageType.HEARTBEAT
        assert message.payload["connection_id"] == "conn_123"


# ============================================================================
# Edge Cases and Type Coercion Tests
# ============================================================================


@pytest.mark.unit
class TestEdgeCases:
    """Test edge cases and type coercion."""

    def test_string_to_float_coercion(self):
        """Test string is coerced to float where appropriate."""
        request = TradingDecisionRequest(
            symbol="AAPL",
            current_price="150.25",  # String that can be coerced
        )
        assert isinstance(request.current_price, float)
        assert request.current_price == 150.25

    def test_string_to_int_coercion(self):
        """Test string is coerced to int where appropriate."""
        request = TradingDecisionRequest(
            symbol="AAPL", current_price=150.0, max_simulations="1000"
        )
        assert isinstance(request.max_simulations, int)
        assert request.max_simulations == 1000

    def test_very_long_symbol(self):
        """Test very long symbol is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            TradingAnalysisRequest(symbol="A" * 20)
        errors = exc_info.value.errors()
        assert any("symbol" in str(e.get("loc")) for e in errors)

    def test_unicode_in_reasoning(self):
        """Test unicode characters in reasoning field."""
        signal = AnalystSignalResponse(
            analyst_type="market",
            score=0.5,
            confidence=0.7,
            reasoning="Strong momentum 📈 with positive sentiment 😊",
        )
        assert "📈" in signal.reasoning
        assert "😊" in signal.reasoning

    def test_extreme_values(self):
        """Test extreme but valid values."""
        request = TradingDecisionRequest(
            symbol="AAPL",
            current_price=999999.99,  # Very high price
            portfolio_value=1000000000.0,  # $1B portfolio
            max_simulations=100000,  # Maximum simulations
        )
        assert request.current_price == 999999.99
        assert request.portfolio_value == 1000000000.0
