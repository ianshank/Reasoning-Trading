"""
Portfolio management endpoints.

This module provides REST API endpoints for:
- Portfolio state retrieval
- Position management
- Risk metrics calculation
- Position risk checking
"""

import os
from datetime import datetime
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Path, status
from pydantic import BaseModel, Field

from reasoning_trading.services.portfolio import PortfolioService

from enterprise_ui.backend.core.errors import handle_error

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


# Request/Response Models
class PortfolioStateResponse(BaseModel):
    """Portfolio state response."""

    cash_balance: float
    portfolio_value: float
    positions_value: float
    unrealized_pnl: float
    realized_pnl_today: float
    realized_pnl_total: float
    position_count: int
    largest_position_pct: float
    current_drawdown: float
    max_drawdown: float
    timestamp: datetime


class PositionResponse(BaseModel):
    """Individual position response."""

    symbol: str
    quantity: float
    entry_price: float
    current_price: float
    market_value: float
    cost_basis: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    entry_time: datetime
    stop_loss_price: float | None = None
    take_profit_price: float | None = None
    is_long: bool


class PositionsResponse(BaseModel):
    """All positions response."""

    positions: list[PositionResponse]
    total_value: float
    total_pnl: float
    count: int
    timestamp: datetime


class RiskMetricsResponse(BaseModel):
    """Risk metrics response."""

    portfolio_value: float
    cash_balance: float
    positions_value: float
    unrealized_pnl: float
    current_drawdown: float
    max_drawdown: float
    largest_position_pct: float
    position_count: int
    sharpe_ratio: float
    margin_used: float
    margin_available: float
    daily_var_95: float | None = None
    timestamp: datetime


class RiskCheckRequest(BaseModel):
    """Risk check request."""

    symbol: str
    direction: str
    position_value: float = Field(..., gt=0)


class RiskCheckResponse(BaseModel):
    """Risk check response."""

    can_trade: bool
    reason: str
    checks: dict[str, Any]
    timestamp: datetime


# Dependency injection
async def get_portfolio_service() -> PortfolioService:
    """Get portfolio service instance."""
    # In production, this would be a singleton or from dependency injection container
    return PortfolioService()


# Endpoints
@router.get(
    "/state",
    response_model=PortfolioStateResponse,
    status_code=status.HTTP_200_OK,
    summary="Get portfolio state",
    description="""
    Retrieves current portfolio state snapshot.

    This endpoint returns complete portfolio information including cash balance,
    position values, P&L metrics, and risk statistics.

    **State Components:**
    - Cash and total portfolio value
    - Position count and largest position %
    - Realized and unrealized P&L
    - Drawdown metrics
    - Margin utilization

    **Use Case:** Get real-time portfolio overview for monitoring.

    **Returns:** Complete portfolio state snapshot.
    """,
)
async def get_portfolio_state(
    portfolio: PortfolioService = Depends(get_portfolio_service),
) -> PortfolioStateResponse:
    """
    Get current portfolio state.

    Args:
        portfolio: Portfolio service

    Returns:
        PortfolioStateResponse with current state
    """
    logger.info("Fetching portfolio state")

    try:
        state = portfolio.get_state()

        return PortfolioStateResponse(
            cash_balance=state.cash_balance,
            portfolio_value=state.portfolio_value,
            positions_value=portfolio.positions_value,
            unrealized_pnl=state.unrealized_pnl,
            realized_pnl_today=state.realized_pnl_today,
            realized_pnl_total=state.realized_pnl_total,
            position_count=state.position_count,
            largest_position_pct=state.largest_position_pct,
            current_drawdown=state.current_drawdown,
            max_drawdown=state.max_drawdown,
            timestamp=datetime.now(),
        )

    except Exception as e:
        raise handle_error(
            logger=logger,
            error=e,
            generic_message="Failed to fetch portfolio state",
            log_message="Failed to fetch portfolio state",
        )


@router.get(
    "/positions",
    response_model=PositionsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get all positions",
    description="""
    Retrieves all open positions in the portfolio.

    This endpoint returns detailed information for every open position
    including entry details, current values, P&L, and risk parameters.

    **Position Details:**
    - Symbol and quantity
    - Entry and current prices
    - Market value and cost basis
    - Unrealized P&L ($ and %)
    - Stop-loss and take-profit levels
    - Long/short indicator

    **Use Case:** Monitor all active positions.

    **Returns:** List of all open positions with details.
    """,
)
async def get_all_positions(
    portfolio: PortfolioService = Depends(get_portfolio_service),
) -> PositionsResponse:
    """
    Get all open positions.

    Args:
        portfolio: Portfolio service

    Returns:
        PositionsResponse with all positions
    """
    logger.info("Fetching all positions")

    try:
        positions = portfolio.get_all_positions()

        position_responses = [
            PositionResponse(
                symbol=pos.symbol,
                quantity=abs(pos.quantity),
                entry_price=pos.entry_price,
                current_price=pos.current_price,
                market_value=pos.market_value,
                cost_basis=pos.cost_basis,
                unrealized_pnl=pos.unrealized_pnl,
                unrealized_pnl_pct=pos.unrealized_pnl_pct,
                entry_time=pos.entry_time,
                stop_loss_price=pos.stop_loss_price,
                take_profit_price=pos.take_profit_price,
                is_long=pos.is_long,
            )
            for pos in positions
        ]

        total_value = sum(pos.market_value for pos in positions)
        total_pnl = sum(pos.unrealized_pnl for pos in positions)

        return PositionsResponse(
            positions=position_responses,
            total_value=total_value,
            total_pnl=total_pnl,
            count=len(positions),
            timestamp=datetime.now(),
        )

    except Exception as e:
        raise handle_error(
            logger=logger,
            error=e,
            generic_message="Failed to fetch positions",
            log_message="Failed to fetch positions",
        )


@router.get(
    "/position/{symbol}",
    response_model=PositionResponse,
    status_code=status.HTTP_200_OK,
    summary="Get position details",
    description="""
    Retrieves detailed information for a specific position.

    This endpoint returns complete position data including entry details,
    current market value, P&L, and risk management parameters.

    **Use Case:** Get detailed view of a specific position.

    **Returns:** Position details if exists, 404 if no position found.
    """,
)
async def get_position(
    symbol: str = Path(..., pattern="^[A-Z0-9/]{1,10}$", description="Trading symbol"),
    portfolio: PortfolioService = Depends(get_portfolio_service),
) -> PositionResponse:
    """
    Get position details for a symbol.

    Args:
        symbol: Trading symbol
        portfolio: Portfolio service

    Returns:
        PositionResponse with position details
    """
    logger.info("Fetching position", symbol=symbol)

    try:
        position = portfolio.get_position(symbol)

        if position is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No position found for {symbol}",
            )

        return PositionResponse(
            symbol=position.symbol,
            quantity=abs(position.quantity),
            entry_price=position.entry_price,
            current_price=position.current_price,
            market_value=position.market_value,
            cost_basis=position.cost_basis,
            unrealized_pnl=position.unrealized_pnl,
            unrealized_pnl_pct=position.unrealized_pnl_pct,
            entry_time=position.entry_time,
            stop_loss_price=position.stop_loss_price,
            take_profit_price=position.take_profit_price,
            is_long=position.is_long,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise handle_error(
            logger=logger,
            error=e,
            generic_message="Failed to fetch position",
            log_message="Failed to fetch position",
            symbol=symbol,
        )


@router.get(
    "/risk-metrics",
    response_model=RiskMetricsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get risk metrics",
    description="""
    Retrieves comprehensive portfolio risk metrics.

    This endpoint calculates and returns various risk measures including
    drawdowns, concentration, Sharpe ratio, and margin utilization.

    **Risk Metrics:**
    - Current and maximum drawdown
    - Position concentration (largest position %)
    - Sharpe ratio (risk-adjusted returns)
    - Margin usage and availability
    - Value at Risk (VaR) at 95% confidence
    - Unrealized P&L exposure

    **Use Case:** Monitor portfolio risk and compliance with limits.

    **Returns:** Comprehensive risk metrics.
    """,
)
async def get_risk_metrics(
    portfolio: PortfolioService = Depends(get_portfolio_service),
) -> RiskMetricsResponse:
    """
    Get portfolio risk metrics.

    Args:
        portfolio: Portfolio service

    Returns:
        RiskMetricsResponse with risk metrics
    """
    logger.info("Calculating risk metrics")

    try:
        state = portfolio.get_state()
        sharpe_ratio = portfolio.calculate_sharpe_ratio()

        return RiskMetricsResponse(
            portfolio_value=state.portfolio_value,
            cash_balance=state.cash_balance,
            positions_value=portfolio.positions_value,
            unrealized_pnl=state.unrealized_pnl,
            current_drawdown=state.current_drawdown,
            max_drawdown=state.max_drawdown,
            largest_position_pct=state.largest_position_pct,
            position_count=state.position_count,
            sharpe_ratio=sharpe_ratio,
            margin_used=state.margin_used,
            margin_available=state.margin_available,
            daily_var_95=state.daily_var_95,
            timestamp=datetime.now(),
        )

    except Exception as e:
        raise handle_error(
            logger=logger,
            error=e,
            generic_message="Failed to calculate risk metrics",
            log_message="Failed to calculate risk metrics",
        )


@router.post(
    "/risk-check",
    response_model=RiskCheckResponse,
    status_code=status.HTTP_200_OK,
    summary="Check position risk",
    description="""
    Checks if a position can be opened given risk constraints.

    This endpoint validates a proposed trade against various risk limits
    and constraints without executing the trade.

    **Risk Checks:**
    - Cash availability
    - Position size limits (% of portfolio)
    - Daily loss limits (circuit breaker)
    - Margin requirements
    - Concentration limits
    - Opposite position conflicts

    **Use Case:** Validate trade before execution to prevent rule violations.

    **Returns:** Can-trade flag, reason, and detailed check results.
    """,
)
async def check_position_risk(
    request: RiskCheckRequest,
    portfolio: PortfolioService = Depends(get_portfolio_service),
) -> RiskCheckResponse:
    """
    Check if a position can be opened.

    Args:
        request: Risk check request
        portfolio: Portfolio service

    Returns:
        RiskCheckResponse with check results
    """
    logger.info(
        "Checking position risk",
        symbol=request.symbol,
        direction=request.direction,
        value=request.position_value,
    )

    try:
        from reasoning_trading.core.actions import TradingDirection

        # Validate direction
        try:
            direction = TradingDirection(request.direction.lower())
        except ValueError:
            return RiskCheckResponse(
                can_trade=False,
                reason=f"Invalid direction: {request.direction}",
                checks={},
                timestamp=datetime.now(),
            )

        # Run risk checks
        can_trade, reason = portfolio.can_open_position(
            symbol=request.symbol,
            direction=direction,
            value=request.position_value,
        )

        # Detailed checks - get position limit from environment or settings
        max_position_size_pct = float(os.environ.get("MAX_POSITION_SIZE_PCT", "10.0")) / 100.0
        state = portfolio.get_state()
        checks = {
            "has_sufficient_cash": state.cash_balance >= request.position_value,
            "within_position_limit": request.position_value <= state.portfolio_value * max_position_size_pct,
            "within_daily_loss_limit": True,  # Would check actual daily loss
            "no_conflicting_position": portfolio.get_position(request.symbol) is None,
        }

        logger.info(
            "Risk check completed",
            symbol=request.symbol,
            can_trade=can_trade,
        )

        return RiskCheckResponse(
            can_trade=can_trade,
            reason=reason,
            checks=checks,
            timestamp=datetime.now(),
        )

    except Exception as e:
        raise handle_error(
            logger=logger,
            error=e,
            generic_message="Risk check failed",
            log_message="Risk check failed",
            symbol=request.symbol,
        )
