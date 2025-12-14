"""
Trading analysis and execution endpoints.

This module provides REST API endpoints for:
- Multi-agent analysis
- Trading decision making with MCTS
- Trade execution
- Analyst signals retrieval
- Trading state management
"""

from datetime import datetime
from typing import Any, Literal

import structlog
from fastapi import APIRouter, Depends, HTTPException, Path, status
from pydantic import BaseModel, ConfigDict, Field

from reasoning_trading.core.actions import TradingAction, TradingDirection
from reasoning_trading.core.state import AnalystSignals, TradingState
from reasoning_trading.langgraph.orchestrator import TradingOrchestrator
from reasoning_trading.mcts.tree import MCTSConfig, MCTSTree
from reasoning_trading.services.portfolio import PortfolioService

from enterprise_ui.backend.core.errors import handle_error

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/trading", tags=["trading"])


# Request/Response Models
class AnalyzeRequest(BaseModel):
    """Request for multi-agent analysis."""

    model_config = ConfigDict(extra='forbid', validate_default=True)

    symbol: str = Field(..., description="Trading symbol (e.g., AAPL, BTC)")
    current_price: float = Field(..., gt=0, description="Current market price")
    include_fundamentals: bool = Field(default=True, description="Include fundamental analysis")
    include_news: bool = Field(default=True, description="Include news analysis")
    include_social: bool = Field(default=True, description="Include social sentiment")


class AnalyzeResponse(BaseModel):
    """Response from multi-agent analysis."""

    model_config = ConfigDict(extra='forbid', validate_default=True)

    symbol: str
    analyst_signals: dict[str, Any]
    consensus_score: float = Field(..., ge=-1.0, le=1.0)
    confidence: float = Field(..., ge=0.0, le=1.0)
    timestamp: datetime


class DecideRequest(BaseModel):
    """Request for trading decision using MCTS."""

    model_config = ConfigDict(extra='forbid', validate_default=True)

    symbol: str
    current_price: float = Field(..., gt=0)
    max_simulations: int = Field(default=1000, ge=1, le=10000)
    time_budget_ms: int | None = Field(default=None, ge=50, le=60000)
    analyst_signals: dict[str, Any] | None = None


class DecideResponse(BaseModel):
    """Response from MCTS decision."""

    model_config = ConfigDict(extra='forbid', validate_default=True)

    symbol: str
    action: dict[str, Any]
    confidence: float
    value_estimate: float
    simulations_run: int
    computation_time_ms: float
    timestamp: datetime


class ExecuteRequest(BaseModel):
    """Request to execute a trade."""

    model_config = ConfigDict(extra='forbid', validate_default=True)

    symbol: str
    direction: Literal["buy", "sell", "hold", "short", "cover"] = Field(..., description="Trade direction: buy, sell, hold, short, cover")
    quantity: float = Field(..., gt=0)
    order_type: Literal["market", "limit", "stop"] = Field(default="market", description="Order type: market, limit, stop")
    limit_price: float | None = Field(default=None, gt=0)
    stop_loss_pct: float | None = Field(default=None, ge=0, le=0.5)
    take_profit_pct: float | None = Field(default=None, ge=0, le=1.0)


class ExecuteResponse(BaseModel):
    """Response from trade execution."""

    model_config = ConfigDict(extra='forbid', validate_default=True)

    symbol: str
    direction: str
    quantity: float
    price: float
    pnl: float
    fees: float
    timestamp: datetime
    success: bool
    message: str


class SignalsResponse(BaseModel):
    """Response with analyst signals for a symbol."""

    model_config = ConfigDict(extra='forbid', validate_default=True)

    symbol: str
    signals: dict[str, Any]
    timestamp: datetime


class StateResponse(BaseModel):
    """Response with trading state for a symbol."""

    model_config = ConfigDict(extra='forbid', validate_default=True)

    symbol: str
    current_price: float
    portfolio: dict[str, Any]
    technical_indicators: dict[str, Any]
    analyst_signals: dict[str, Any]
    market_regime: str
    timestamp: datetime


# Dependency injection
async def get_orchestrator() -> TradingOrchestrator:
    """Get trading orchestrator instance."""
    # In production, this would be a singleton or from dependency injection container
    return TradingOrchestrator()


async def get_mcts_tree() -> MCTSTree:
    """Get MCTS tree instance."""
    config = MCTSConfig()
    return MCTSTree(config=config)


async def get_portfolio_service() -> PortfolioService:
    """Get portfolio service instance."""
    # In production, this would be a singleton or from dependency injection container
    return PortfolioService()


# Endpoints
@router.post(
    "/analyze",
    response_model=AnalyzeResponse,
    status_code=status.HTTP_200_OK,
    summary="Run multi-agent analysis",
    description="""
    Executes comprehensive multi-agent analysis on a trading symbol.

    This endpoint coordinates multiple AI analysts (market, news, social sentiment,
    fundamental, macro) to provide a consensus view on the asset. The analysts
    engage in structured debate to arrive at a confidence-weighted recommendation.

    **Analysis Components:**
    - Market Analyst: Technical indicators and price action
    - News Analyst: Recent news sentiment and impact
    - Social Sentiment: Twitter/Reddit sentiment analysis
    - Fundamental Analyst: Company metrics and valuation
    - Macro Analyst: Economic context and sector trends

    **Returns:** Aggregated analyst signals with consensus score and confidence.
    """,
)
async def analyze_symbol(
    request: AnalyzeRequest,
    orchestrator: TradingOrchestrator = Depends(get_orchestrator),
) -> AnalyzeResponse:
    """
    Run multi-agent analysis on a symbol.

    Args:
        request: Analysis request parameters
        orchestrator: Trading orchestrator service

    Returns:
        AnalyzeResponse with analyst signals and consensus
    """
    logger.info(
        "Starting multi-agent analysis",
        symbol=request.symbol,
        price=request.current_price,
    )

    try:
        # TODO: Implement actual orchestrator call
        # For now, return mock response
        analyst_signals = {
            "market_analyst_score": 0.5,
            "news_analyst_score": 0.3,
            "social_sentiment_score": 0.2,
            "fundamental_analyst_score": 0.4,
            "macro_analyst_score": 0.1,
        }

        consensus = sum(analyst_signals.values()) / len(analyst_signals)

        logger.info(
            "Multi-agent analysis completed",
            symbol=request.symbol,
            consensus=consensus,
        )

        return AnalyzeResponse(
            symbol=request.symbol,
            analyst_signals=analyst_signals,
            consensus_score=consensus,
            confidence=0.75,
            timestamp=datetime.now(),
        )

    except Exception as e:
        raise handle_error(
            logger=logger,
            error=e,
            generic_message="Analysis failed",
            log_message="Analysis failed",
            symbol=request.symbol,
        )


@router.post(
    "/decide",
    response_model=DecideResponse,
    status_code=status.HTTP_200_OK,
    summary="Make trading decision using MCTS",
    description="""
    Uses Monte Carlo Tree Search to make an optimal trading decision.

    This endpoint runs MCTS simulations to explore the action space and find
    the highest-value trading action. It considers position sizing, stop-loss
    levels, time horizons, and risk/reward ratios.

    **MCTS Process:**
    1. Selection: Traverse tree using UCB to find promising nodes
    2. Expansion: Generate new action candidates
    3. Simulation: Rollout to estimate future value
    4. Backpropagation: Update node statistics

    **Parameters:**
    - max_simulations: Number of MCTS iterations (more = better but slower)
    - time_budget_ms: Maximum computation time in milliseconds
    - analyst_signals: Optional pre-computed analyst signals

    **Returns:** Best action with confidence and value estimate.
    """,
)
async def make_decision(
    request: DecideRequest,
    mcts_tree: MCTSTree = Depends(get_mcts_tree),
) -> DecideResponse:
    """
    Make a trading decision using MCTS.

    Args:
        request: Decision request parameters
        mcts_tree: MCTS tree instance

    Returns:
        DecideResponse with best action and statistics
    """
    logger.info(
        "Starting MCTS decision",
        symbol=request.symbol,
        max_simulations=request.max_simulations,
    )

    try:
        # TODO: Implement actual MCTS search
        # For now, return mock response
        action = {
            "direction": "buy",
            "position_size": 0.1,
            "stop_loss_pct": 0.05,
            "take_profit_pct": 0.15,
            "time_horizon": "1D",
        }

        logger.info(
            "MCTS decision completed",
            symbol=request.symbol,
            action=action["direction"],
        )

        return DecideResponse(
            symbol=request.symbol,
            action=action,
            confidence=0.82,
            value_estimate=1.25,
            simulations_run=request.max_simulations,
            computation_time_ms=450.0,
            timestamp=datetime.now(),
        )

    except Exception as e:
        raise handle_error(
            logger=logger,
            error=e,
            generic_message="Decision failed",
            log_message="Decision failed",
            symbol=request.symbol,
        )


@router.post(
    "/execute",
    response_model=ExecuteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Execute a trade",
    description="""
    Executes a trade order through the trading platform.

    This endpoint validates the trade request, checks risk limits, and submits
    the order for execution. It supports various order types and risk management
    parameters.

    **Order Types:**
    - market: Execute immediately at current market price
    - limit: Execute only at specified price or better
    - stop: Execute when price reaches stop level

    **Risk Management:**
    - stop_loss_pct: Automatic stop-loss as percentage
    - take_profit_pct: Automatic profit target as percentage

    **Validations:**
    - Portfolio balance check
    - Position size limits
    - Daily loss limits
    - Margin requirements

    **Returns:** Trade execution details including P&L and fees.
    """,
)
async def execute_trade(
    request: ExecuteRequest,
    portfolio: PortfolioService = Depends(get_portfolio_service),
) -> ExecuteResponse:
    """
    Execute a trade.

    Args:
        request: Trade execution request
        portfolio: Portfolio service

    Returns:
        ExecuteResponse with execution details
    """
    logger.info(
        "Executing trade",
        symbol=request.symbol,
        direction=request.direction,
        quantity=request.quantity,
    )

    try:
        # Validate direction
        try:
            direction = TradingDirection(request.direction.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid direction: {request.direction}",
            )

        # TODO: Get current price from market data service
        current_price = request.limit_price or 100.0

        # Execute trade
        trade_record = portfolio.execute_trade(
            symbol=request.symbol,
            direction=direction,
            quantity=request.quantity,
            price=current_price,
            stop_loss_pct=request.stop_loss_pct,
            take_profit_pct=request.take_profit_pct,
        )

        logger.info(
            "Trade executed successfully",
            symbol=request.symbol,
            pnl=trade_record.pnl,
        )

        return ExecuteResponse(
            symbol=request.symbol,
            direction=request.direction,
            quantity=request.quantity,
            price=trade_record.price,
            pnl=trade_record.pnl,
            fees=trade_record.fees,
            timestamp=trade_record.timestamp,
            success=True,
            message="Trade executed successfully",
        )

    except HTTPException:
        raise
    except Exception as e:
        raise handle_error(
            logger=logger,
            error=e,
            generic_message="Trade execution failed",
            log_message="Trade execution failed",
            symbol=request.symbol,
        )


@router.get(
    "/signals/{symbol}",
    response_model=SignalsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get analyst signals",
    description="""
    Retrieves the latest analyst signals for a symbol.

    This endpoint returns cached analyst signals from the most recent analysis.
    Signals include individual analyst scores, confidence levels, and consensus.

    **Signal Components:**
    - Individual analyst scores (-1 to 1 scale)
    - Confidence levels per analyst (0 to 1)
    - Weighted consensus score
    - Bull/Bear debate outcome

    **Use Case:** Check current analyst sentiment before making a decision.

    **Returns:** Latest analyst signals if available.
    """,
)
async def get_signals(
    symbol: str = Path(..., pattern="^[A-Z0-9/]{1,10}$", description="Trading symbol")
) -> SignalsResponse:
    """
    Get analyst signals for a symbol.

    Args:
        symbol: Trading symbol

    Returns:
        SignalsResponse with analyst signals
    """
    logger.info("Fetching analyst signals", symbol=symbol)

    try:
        # TODO: Implement signal retrieval from cache/database
        signals = {
            "market_analyst_score": 0.5,
            "news_analyst_score": 0.3,
            "consensus": 0.4,
            "confidence": 0.75,
        }

        return SignalsResponse(
            symbol=symbol,
            signals=signals,
            timestamp=datetime.now(),
        )

    except Exception as e:
        logger.error("Failed to fetch signals", symbol=symbol, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Signals not found for {symbol}",
        )


@router.get(
    "/state/{symbol}",
    response_model=StateResponse,
    status_code=status.HTTP_200_OK,
    summary="Get trading state",
    description="""
    Retrieves complete trading state for a symbol.

    This endpoint returns the full trading state including market data,
    portfolio positions, technical indicators, analyst signals, and
    market regime classification.

    **State Components:**
    - Current price and OHLCV history
    - Portfolio position and P&L
    - Technical indicators (RSI, MACD, Bollinger Bands, etc.)
    - Analyst signals and consensus
    - Market regime (trending, volatile, mean-reverting, etc.)

    **Use Case:** Get complete context before analysis or decision-making.

    **Returns:** Complete trading state snapshot.
    """,
)
async def get_trading_state(
    symbol: str = Path(..., pattern="^[A-Z0-9/]{1,10}$", description="Trading symbol"),
    portfolio: PortfolioService = Depends(get_portfolio_service),
) -> StateResponse:
    """
    Get trading state for a symbol.

    Args:
        symbol: Trading symbol
        portfolio: Portfolio service

    Returns:
        StateResponse with complete trading state
    """
    logger.info("Fetching trading state", symbol=symbol)

    try:
        # TODO: Build complete trading state from services
        portfolio_state = portfolio.get_state()

        state = {
            "symbol": symbol,
            "current_price": 100.0,
            "portfolio": {
                "cash_balance": portfolio_state.cash_balance,
                "portfolio_value": portfolio_state.portfolio_value,
                "positions": portfolio_state.positions,
                "unrealized_pnl": portfolio_state.unrealized_pnl,
            },
            "technical_indicators": {
                "rsi_14": 55.0,
                "macd": 0.5,
                "adx_14": 25.0,
            },
            "analyst_signals": {
                "consensus": 0.4,
                "confidence": 0.75,
            },
            "market_regime": "neutral",
            "timestamp": datetime.now(),
        }

        return StateResponse(**state)

    except Exception as e:
        raise handle_error(
            logger=logger,
            error=e,
            generic_message="Failed to fetch state",
            log_message="Failed to fetch state",
            symbol=symbol,
        )
