"""
Pytest configuration and fixtures for backend tests.

This module provides:
- Test client setup with proper lifespan handling
- Mock services and dependencies
- Test database/Redis fixtures
- Authentication fixtures
- Sample data factories
- Shared test utilities
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest
import pytest_asyncio
from fakeredis.aioredis import FakeRedis
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from enterprise_ui.backend.config import BackendSettings
from enterprise_ui.backend.dependencies import get_redis_client
from enterprise_ui.backend.main import create_application
from enterprise_ui.backend.models.requests import (
    MCTSSearchRequest,
    RiskCheckRequest,
    TradingAnalysisRequest,
    TradingDecisionRequest,
    TradeExecutionRequest,
)
from enterprise_ui.backend.models.responses import (
    AnalystSignalResponse,
    PortfolioStateResponse,
    PositionResponse,
    TradingAnalysisResponse,
)
from enterprise_ui.backend.services.cache_service import CacheService
from enterprise_ui.backend.services.mcts_service import MCTSService
from enterprise_ui.backend.services.portfolio_service import PortfolioService
from enterprise_ui.backend.services.trading_service import TradingService
from reasoning_trading.config import RiskProfile, Settings as CoreSettings
from reasoning_trading.core.state import MarketRegime, PortfolioState, TradingState
from reasoning_trading.mcts.tree import MCTSConfig, MCTSResult
from reasoning_trading.services.adapter import OrderResult, TradingSignal


# ============================================================================
# Pytest Configuration
# ============================================================================


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "contract: Contract tests")
    config.addinivalue_line("markers", "slow: Slow-running tests")
    config.addinivalue_line("markers", "websocket: WebSocket tests")


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Application & Client Fixtures
# ============================================================================


@pytest.fixture
def test_settings() -> BackendSettings:
    """Create test settings with safe defaults."""
    settings = BackendSettings(
        environment="test",
        host="127.0.0.1",
        port=8888,
        reload=False,
        workers=1,
        openapi_url="/api/openapi.json",
        docs_url="/docs",
    )
    settings.core = CoreSettings(
        alpaca_api_key="test_alpaca_key",
        alpaca_secret_key="test_alpaca_secret",
        openai_api_key="test_openai_key",
        anthropic_api_key="test_anthropic_key",
        trading_mode="paper",
    )
    return settings


@pytest.fixture
def app(test_settings: BackendSettings, mock_redis: FakeRedis) -> FastAPI:
    """Create FastAPI app instance for testing."""
    application = create_application()

    # Override dependencies
    async def override_redis():
        return mock_redis

    application.dependency_overrides[get_redis_client] = override_redis

    return application


@pytest_asyncio.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Create async HTTP client for testing."""
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
        headers={"Content-Type": "application/json"},
    ) as ac:
        yield ac


# ============================================================================
# Mock Service Fixtures
# ============================================================================


@pytest.fixture
def mock_redis() -> FakeRedis:
    """Create fake Redis client for testing."""
    return FakeRedis()


@pytest_asyncio.fixture
async def cache_service(mock_redis: FakeRedis) -> CacheService:
    """Create cache service with fake Redis."""
    return CacheService(
        redis_client=mock_redis,
        default_ttl=3600,
        key_prefix="test",
    )


@pytest.fixture
def mock_trading_adapter() -> Mock:
    """Create mock trading adapter."""
    adapter = Mock()
    adapter._initialize = AsyncMock()
    adapter._cleanup = AsyncMock()
    adapter.get_trading_signal = AsyncMock(
        return_value=TradingSignal(
            direction="buy",
            confidence=0.75,
            position_size_pct=0.15,
            stop_loss_pct=0.05,
            take_profit_pct=0.15,
            reasoning="Strong bullish signals",
            analyst_signals={
                "market": 0.7,
                "news": 0.6,
                "social": 0.5,
                "fundamental": 0.8,
                "macro": 0.6,
            },
        )
    )
    adapter.execute_trade = AsyncMock(
        return_value=OrderResult(
            order_id="test_order_123",
            symbol="AAPL",
            status="filled",
            filled_qty=10.0,
            filled_price=150.25,
            timestamp=datetime.now(),
        )
    )
    adapter.build_trading_state = AsyncMock(
        return_value=TradingState(
            symbol="AAPL",
            current_price=150.0,
            portfolio=PortfolioState(
                cash_balance=50000.0,
                portfolio_value=100000.0,
            ),
        )
    )
    adapter.calculate_risk_metrics = AsyncMock(
        return_value={
            "risk_rating": "moderate",
            "var_95": 0.05,
            "expected_drawdown": 0.03,
        }
    )
    return adapter


@pytest.fixture
def mock_market_data() -> Mock:
    """Create mock market data service."""
    market_data = Mock()
    market_data.get_historical_bars = AsyncMock(return_value=[])
    market_data.calculate_indicators = Mock(
        return_value=Mock(
            rsi_14=55.0,
            macd=0.5,
            adx_14=25.0,
            model_dump=lambda: {"rsi_14": 55.0, "macd": 0.5, "adx_14": 25.0},
        )
    )
    market_data.detect_market_regime = Mock(return_value=MarketRegime.NEUTRAL)
    market_data.get_snapshot = AsyncMock(
        return_value=Mock(last_price=150.25, bid=150.20, ask=150.30)
    )
    return market_data


@pytest_asyncio.fixture
async def trading_service(
    mock_trading_adapter: Mock,
    mock_market_data: Mock,
    cache_service: CacheService,
) -> TradingService:
    """Create trading service with mocks."""
    service = TradingService(
        trading_adapter=mock_trading_adapter,
        market_data_service=mock_market_data,
        cache_service=cache_service,
    )
    await service.initialize()
    return service


@pytest_asyncio.fixture
async def mcts_service(cache_service: CacheService) -> MCTSService:
    """Create MCTS service."""
    config = MCTSConfig(max_simulations=100, time_budget_ms=1000)
    return MCTSService(cache_service=cache_service, mcts_config=config)


@pytest_asyncio.fixture
async def portfolio_service(cache_service: CacheService) -> PortfolioService:
    """Create portfolio service."""
    return PortfolioService(cache_service=cache_service)


# ============================================================================
# Sample Data Factories
# ============================================================================


@pytest.fixture
def sample_trading_analysis_request() -> TradingAnalysisRequest:
    """Create sample trading analysis request."""
    return TradingAnalysisRequest(
        symbol="AAPL",
        include_news=True,
        include_social=True,
        include_fundamentals=True,
        include_macro=True,
        enable_debate=True,
        max_debate_rounds=4,
    )


@pytest.fixture
def sample_trading_decision_request() -> TradingDecisionRequest:
    """Create sample trading decision request."""
    return TradingDecisionRequest(
        symbol="AAPL",
        current_price=150.25,
        portfolio_value=100000.0,
        cash_balance=50000.0,
        risk_profile=RiskProfile.MODERATE,
        max_simulations=1000,
        time_budget_ms=500,
    )


@pytest.fixture
def sample_trade_execution_request() -> TradeExecutionRequest:
    """Create sample trade execution request."""
    return TradeExecutionRequest(
        symbol="AAPL",
        direction="buy",
        quantity=10.0,
        order_type="market",
        time_in_force="day",
        dry_run=True,
    )


@pytest.fixture
def sample_mcts_search_request() -> MCTSSearchRequest:
    """Create sample MCTS search request."""
    return MCTSSearchRequest(
        symbol="AAPL",
        current_price=150.25,
        max_simulations=1000,
        exploration_weight=1.414,
        return_tree=False,
    )


@pytest.fixture
def sample_risk_check_request() -> RiskCheckRequest:
    """Create sample risk check request."""
    return RiskCheckRequest(
        symbol="AAPL",
        direction="buy",
        quantity=10.0,
        price=150.25,
        portfolio_value=100000.0,
        existing_positions={"AAPL": 5.0},
        risk_profile=RiskProfile.MODERATE,
    )


@pytest.fixture
def sample_analyst_signals() -> list[AnalystSignalResponse]:
    """Create sample analyst signals."""
    return [
        AnalystSignalResponse(
            analyst_type="market",
            score=0.65,
            confidence=0.85,
            reasoning="Strong upward momentum",
        ),
        AnalystSignalResponse(
            analyst_type="news",
            score=0.45,
            confidence=0.75,
            reasoning="Positive news sentiment",
        ),
        AnalystSignalResponse(
            analyst_type="social",
            score=0.55,
            confidence=0.70,
            reasoning="Bullish social sentiment",
        ),
    ]


@pytest.fixture
def sample_trading_analysis_response(
    sample_analyst_signals: list[AnalystSignalResponse],
) -> TradingAnalysisResponse:
    """Create sample trading analysis response."""
    return TradingAnalysisResponse(
        symbol="AAPL",
        timestamp=datetime.now(),
        current_price=150.25,
        market_regime=MarketRegime.TRENDING_UP,
        analyst_signals=sample_analyst_signals,
        consensus_score=0.55,
        consensus_confidence=0.77,
        recommendation="MODERATE BUY - Multiple analysts show bullish signals",
        analysis_time_ms=1234.56,
    )


@pytest.fixture
def sample_portfolio_state() -> PortfolioState:
    """Create sample portfolio state."""
    return PortfolioState(
        cash_balance=50000.0,
        portfolio_value=100000.0,
        positions={"AAPL": 100.0, "MSFT": 50.0},
        position_values={"AAPL": 15000.0, "MSFT": 20000.0},
        position_costs={"AAPL": 14000.0, "MSFT": 19000.0},
        unrealized_pnl=2000.0,
        margin_used=0.0,
        margin_limit=50000.0,
    )


@pytest.fixture
def sample_positions() -> list[PositionResponse]:
    """Create sample positions."""
    return [
        PositionResponse(
            symbol="AAPL",
            quantity=100.0,
            average_cost=140.0,
            current_price=150.25,
            market_value=15025.0,
            unrealized_pnl=1025.0,
            unrealized_pnl_pct=0.073,
        ),
        PositionResponse(
            symbol="MSFT",
            quantity=50.0,
            average_cost=380.0,
            current_price=400.0,
            market_value=20000.0,
            unrealized_pnl=1000.0,
            unrealized_pnl_pct=0.053,
        ),
    ]


@pytest.fixture
def sample_portfolio_state_response(
    sample_positions: list[PositionResponse],
) -> PortfolioStateResponse:
    """Create sample portfolio state response."""
    return PortfolioStateResponse(
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


@pytest.fixture
def sample_trading_state(sample_portfolio_state: PortfolioState) -> TradingState:
    """Create sample trading state."""
    return TradingState(
        symbol="AAPL",
        current_price=150.25,
        portfolio=sample_portfolio_state,
        technical_indicators=Mock(
            rsi_14=55.0,
            macd=0.5,
            adx_14=25.0,
        ),
        market_regime=MarketRegime.NEUTRAL,
    )


@pytest.fixture
def sample_mcts_result() -> MCTSResult:
    """Create sample MCTS result."""
    return MCTSResult(
        best_action=Mock(
            direction="buy",
            position_size=0.15,
            stop_loss_pct=0.05,
            to_dict=lambda: {
                "direction": "buy",
                "position_size": 0.15,
                "stop_loss_pct": 0.05,
            },
        ),
        best_value=1.25,
        total_simulations=1000,
        nodes_created=450,
        total_time_ms=487.23,
        root=None,
    )


# ============================================================================
# Authentication Fixtures
# ============================================================================


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Create authentication headers for testing."""
    return {
        "Authorization": "Bearer test_token",
        "X-API-Key": "test_api_key",
    }


@pytest.fixture
def mock_auth_dependency():
    """Create mock authentication dependency."""

    async def mock_auth():
        return {"user_id": "test_user", "role": "admin"}

    return mock_auth


# ============================================================================
# WebSocket Fixtures
# ============================================================================


@pytest.fixture
def websocket_url() -> str:
    """Get WebSocket URL for testing."""
    return "ws://testserver/api/v1/ws"


# ============================================================================
# Database Fixtures
# ============================================================================


@pytest_asyncio.fixture
async def clean_database():
    """Clean database before and after tests."""
    # Setup: Clean database
    yield
    # Teardown: Clean database


# ============================================================================
# Utility Fixtures
# ============================================================================


@pytest.fixture
def freeze_time():
    """Freeze time for predictable timestamps."""
    frozen_time = datetime(2024, 1, 15, 10, 30, 0)

    def _frozen_now():
        return frozen_time

    return _frozen_now


@pytest.fixture
def assert_valid_timestamp():
    """Utility to assert timestamp is recent and valid."""

    def _assert(timestamp: datetime, max_age_seconds: int = 5):
        now = datetime.now()
        if timestamp.tzinfo is None:
            # Make both naive for comparison
            age = (now - timestamp).total_seconds()
        else:
            # Make both aware for comparison
            from datetime import timezone

            now = now.replace(tzinfo=timezone.utc)
            age = (now - timestamp).total_seconds()

        assert age >= 0, f"Timestamp is in the future: {timestamp}"
        assert age <= max_age_seconds, f"Timestamp is too old: {timestamp} ({age}s)"

    return _assert


@pytest.fixture
def assert_dict_contains():
    """Utility to assert dictionary contains expected keys/values."""

    def _assert(actual: dict[str, Any], expected: dict[str, Any]):
        for key, value in expected.items():
            assert key in actual, f"Missing key: {key}"
            if value is not None:
                assert (
                    actual[key] == value
                ), f"Mismatch for {key}: {actual[key]} != {value}"

    return _assert
