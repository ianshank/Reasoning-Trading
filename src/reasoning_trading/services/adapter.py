"""
Trading Service Adapter for LangGraph integration.

Exposes AlpacaTradingAgent functionality as LangGraph tools,
enabling MCTS to call trading operations during rollouts.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

import httpx
import structlog
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from tenacity import retry, stop_after_attempt, wait_exponential

from reasoning_trading.config import Settings, TradingMode, get_settings
from reasoning_trading.core.actions import TradingAction, TradingDirection
from reasoning_trading.core.state import AnalystSignals, PortfolioState, TradingState
from reasoning_trading.sentiment import SentimentService, AggregatedSentiment

logger = structlog.get_logger(__name__)


class TradingSignal(BaseModel):
    """Structured trading signal from analysis."""

    symbol: str
    direction: str  # buy, sell, hold
    confidence: float = Field(ge=0.0, le=1.0)
    position_size_pct: float = Field(ge=0.0, le=1.0)
    stop_loss_pct: float = Field(ge=0.0, le=0.5)
    take_profit_pct: float | None = Field(default=None, ge=0.0, le=1.0)
    reasoning: str = ""
    analyst_signals: dict[str, float] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)


class OrderResult(BaseModel):
    """Result of a trade execution."""

    order_id: str
    symbol: str
    side: str
    quantity: float
    filled_price: float | None = None
    status: str  # pending, filled, cancelled, rejected
    filled_at: datetime | None = None
    error_message: str | None = None


class TradingServiceAdapter:
    """
    Adapter that exposes AlpacaTradingAgent as LangGraph tools.

    Can operate in two modes:
    1. HTTP mode: Calls a running AlpacaTradingAgent REST API
    2. Direct mode: Uses alpaca-py directly (when no service URL provided)

    Usage:
        adapter = TradingServiceAdapter(mode=TradingMode.PAPER)
        tools = adapter.get_tools()

        # Use tools in LangGraph
        from langgraph.prebuilt import ToolNode
        tool_node = ToolNode(tools)
    """

    def __init__(
        self,
        trading_agent_url: str | None = None,
        mode: TradingMode = TradingMode.PAPER,
        settings: Settings | None = None,
    ):
        """
        Initialize trading service adapter.

        Args:
            trading_agent_url: URL of AlpacaTradingAgent REST API (optional)
            mode: Trading mode (paper or live)
            settings: Application settings (uses default if not provided)
        """
        self.settings = settings or get_settings()
        self.trading_agent_url = trading_agent_url
        self.mode = mode

        # HTTP client for service calls
        self._client: httpx.AsyncClient | None = None

        # Direct Alpaca client (when not using HTTP service)
        self._alpaca_trading: Any | None = None
        self._alpaca_data: Any | None = None

        # Sentiment service for news/social analysis
        self._sentiment_service: SentimentService | None = None

    async def __aenter__(self) -> TradingServiceAdapter:
        """Async context manager entry."""
        await self._initialize()
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        await self._cleanup()

    async def _initialize(self) -> None:
        """Initialize clients and connections."""
        if self.trading_agent_url:
            self._client = httpx.AsyncClient(
                base_url=self.trading_agent_url,
                timeout=httpx.Timeout(30.0, connect=10.0),
            )
        else:
            await self._initialize_alpaca_direct()

        # Initialize sentiment service
        self._sentiment_service = SentimentService(settings=self.settings)

    async def _initialize_alpaca_direct(self) -> None:
        """Initialize direct Alpaca connection."""
        try:
            from alpaca.trading.client import TradingClient
            from alpaca.data.historical import StockHistoricalDataClient

            api_key = self.settings.trading.api_key
            secret_key = self.settings.trading.secret_key

            if api_key is None or secret_key is None:
                logger.warning("Alpaca API keys not configured")
                return

            paper = self.mode == TradingMode.PAPER

            self._alpaca_trading = TradingClient(
                api_key=api_key.get_secret_value(),
                secret_key=secret_key.get_secret_value(),
                paper=paper,
            )

            self._alpaca_data = StockHistoricalDataClient(
                api_key=api_key.get_secret_value(),
                secret_key=secret_key.get_secret_value(),
            )

            logger.info("Alpaca clients initialized", paper_mode=paper)

        except ImportError:
            logger.warning("alpaca-py not installed, direct trading disabled")
        except Exception as e:
            logger.error("Failed to initialize Alpaca", error=str(e))

    async def _cleanup(self) -> None:
        """Cleanup connections."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
        if self._sentiment_service is not None:
            await self._sentiment_service.close()
            self._sentiment_service = None

    def get_tools(self) -> list[Any]:
        """
        Get LangGraph tools for trading operations.

        Returns:
            List of tool functions for use in ToolNode
        """
        # Create tool instances bound to this adapter
        return [
            self._create_get_trading_signal_tool(),
            self._create_execute_trade_tool(),
            self._create_get_portfolio_state_tool(),
            self._create_get_market_data_tool(),
            self._create_calculate_risk_metrics_tool(),
            self._create_get_sentiment_tool(),
        ]

    def _create_get_sentiment_tool(self) -> Any:
        """Create the get_sentiment tool."""
        adapter = self

        @tool
        async def get_sentiment(symbol: str) -> str:
            """
            Get news and social sentiment analysis for a symbol.

            Analyzes recent news articles and social media to determine
            market sentiment. Uses multiple models (FinBERT, VADER, LLM)
            combined in an ensemble for robust predictions.

            Args:
                symbol: Trading symbol (e.g., "AAPL" or "BTC")

            Returns:
                JSON string with sentiment scores, confidence, and
                top bullish/bearish headlines
            """
            try:
                sentiment = await adapter.get_sentiment(symbol)
                return sentiment.model_dump_json()
            except Exception as e:
                logger.error("get_sentiment failed", error=str(e))
                return f'{{"error": "{str(e)}"}}'

        return get_sentiment

    def _create_get_trading_signal_tool(self) -> Any:
        """Create the get_trading_signal tool."""
        adapter = self

        @tool
        async def get_trading_signal(symbol: str, date: str) -> str:
            """
            Get trading recommendation from multi-agent analysis.

            Analyzes the given symbol using multiple specialized analysts
            (Market, News, Social Sentiment, Fundamentals, Macro) and
            returns a structured trading signal.

            Args:
                symbol: Trading symbol (e.g., "NVDA" or "BTC/USD")
                date: Analysis date in YYYY-MM-DD format

            Returns:
                JSON string with trading signal including direction,
                confidence, position size, and reasoning
            """
            try:
                signal = await adapter.get_trading_signal(symbol, date)
                return signal.model_dump_json()
            except Exception as e:
                logger.error("get_trading_signal failed", error=str(e))
                return f'{{"error": "{str(e)}"}}'

        return get_trading_signal

    def _create_execute_trade_tool(self) -> Any:
        """Create the execute_trade tool."""
        adapter = self

        @tool
        async def execute_trade(
            symbol: str,
            side: str,
            quantity: float,
            order_type: str = "market",
        ) -> str:
            """
            Execute a trade via Alpaca API.

            Places an order for the specified symbol and quantity.
            In paper mode, orders are simulated without real money.

            Args:
                symbol: Trading symbol
                side: "buy" or "sell"
                quantity: Number of shares/units
                order_type: "market" or "limit"

            Returns:
                JSON string with order result including order_id and status
            """
            try:
                result = await adapter.execute_trade(symbol, side, quantity, order_type)
                return result.model_dump_json()
            except Exception as e:
                logger.error("execute_trade failed", error=str(e))
                return f'{{"error": "{str(e)}"}}'

        return execute_trade

    def _create_get_portfolio_state_tool(self) -> Any:
        """Create the get_portfolio_state tool."""
        adapter = self

        @tool
        async def get_portfolio_state() -> str:
            """
            Get current portfolio state including positions and P&L.

            Returns the current cash balance, positions, unrealized P&L,
            and other portfolio metrics.

            Returns:
                JSON string with portfolio state
            """
            try:
                state = await adapter.get_portfolio_state()
                return state.model_dump_json()
            except Exception as e:
                logger.error("get_portfolio_state failed", error=str(e))
                return f'{{"error": "{str(e)}"}}'

        return get_portfolio_state

    def _create_get_market_data_tool(self) -> Any:
        """Create the get_market_data tool."""
        adapter = self

        @tool
        async def get_market_data(symbol: str, timeframe: str = "1D", limit: int = 100) -> str:
            """
            Get historical market data for a symbol.

            Retrieves OHLCV data for technical analysis and
            state representation.

            Args:
                symbol: Trading symbol
                timeframe: Bar timeframe ("1Min", "5Min", "1H", "1D")
                limit: Number of bars to retrieve

            Returns:
                JSON string with OHLCV data and basic statistics
            """
            try:
                data = await adapter.get_market_data(symbol, timeframe, limit)
                return str(data)
            except Exception as e:
                logger.error("get_market_data failed", error=str(e))
                return f'{{"error": "{str(e)}"}}'

        return get_market_data

    def _create_calculate_risk_metrics_tool(self) -> Any:
        """Create the calculate_risk_metrics tool."""
        adapter = self

        @tool
        async def calculate_risk_metrics(symbol: str, position_size_pct: float) -> str:
            """
            Calculate risk metrics for a potential position.

            Computes Value at Risk, expected drawdown, and position
            sizing recommendations based on current volatility.

            Args:
                symbol: Trading symbol
                position_size_pct: Proposed position size as % of portfolio

            Returns:
                JSON string with risk metrics and recommendations
            """
            try:
                metrics = await adapter.calculate_risk_metrics(symbol, position_size_pct)
                return str(metrics)
            except Exception as e:
                logger.error("calculate_risk_metrics failed", error=str(e))
                return f'{{"error": "{str(e)}"}}'

        return calculate_risk_metrics

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def get_trading_signal(self, symbol: str, date: str) -> TradingSignal:
        """
        Get trading signal from analysis.

        If a trading agent URL is configured, calls the REST API.
        Otherwise, returns a mock signal for testing.
        """
        if self._client is not None:
            response = await self._client.post(
                "/analyze",
                json={"symbol": symbol, "date": date, "mode": self.mode.value},
            )
            response.raise_for_status()
            data = response.json()
            return TradingSignal(**data)

        # Mock signal for testing without service
        return TradingSignal(
            symbol=symbol,
            direction="hold",
            confidence=0.5,
            position_size_pct=0.0,
            stop_loss_pct=0.05,
            reasoning="Mock signal - no trading service configured",
            analyst_signals={
                "market": 0.0,
                "news": 0.0,
                "social": 0.0,
                "fundamental": 0.0,
                "macro": 0.0,
            },
        )

    async def get_sentiment(self, symbol: str) -> AggregatedSentiment:
        """
        Get news and social sentiment for a symbol.

        Uses the sentiment service to analyze recent news and
        optionally social media content.

        Args:
            symbol: Trading symbol

        Returns:
            AggregatedSentiment with combined scores
        """
        if self._sentiment_service is None:
            self._sentiment_service = SentimentService(settings=self.settings)

        return await self._sentiment_service.get_sentiment(symbol)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def execute_trade(
        self,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str = "market",
    ) -> OrderResult:
        """Execute a trade."""
        if self._client is not None:
            response = await self._client.post(
                "/trade",
                json={
                    "symbol": symbol,
                    "side": side,
                    "quantity": quantity,
                    "type": order_type,
                    "paper_mode": self.mode == TradingMode.PAPER,
                },
            )
            response.raise_for_status()
            data = response.json()
            return OrderResult(**data)

        if self._alpaca_trading is not None:
            return await self._execute_trade_direct(symbol, side, quantity, order_type)

        # Mock result for testing
        return OrderResult(
            order_id="mock_" + str(datetime.now().timestamp()),
            symbol=symbol,
            side=side,
            quantity=quantity,
            status="filled" if self.mode == TradingMode.PAPER else "pending",
        )

    async def _execute_trade_direct(
        self,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str,
    ) -> OrderResult:
        """Execute trade directly via Alpaca."""
        try:
            from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
            from alpaca.trading.enums import OrderSide, TimeInForce

            order_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL

            if order_type.lower() == "market":
                request = MarketOrderRequest(
                    symbol=symbol,
                    qty=quantity,
                    side=order_side,
                    time_in_force=TimeInForce.DAY,
                )
            else:
                # For limit orders, we'd need a price
                request = MarketOrderRequest(
                    symbol=symbol,
                    qty=quantity,
                    side=order_side,
                    time_in_force=TimeInForce.DAY,
                )

            order = self._alpaca_trading.submit_order(request)

            return OrderResult(
                order_id=str(order.id),
                symbol=order.symbol,
                side=order.side.value,
                quantity=float(order.qty),
                status=order.status.value,
                filled_price=float(order.filled_avg_price) if order.filled_avg_price else None,
                filled_at=order.filled_at,
            )

        except Exception as e:
            logger.error("Direct trade execution failed", error=str(e))
            return OrderResult(
                order_id="error",
                symbol=symbol,
                side=side,
                quantity=quantity,
                status="rejected",
                error_message=str(e),
            )

    async def get_portfolio_state(self) -> PortfolioState:
        """Get current portfolio state."""
        if self._client is not None:
            response = await self._client.get("/portfolio")
            response.raise_for_status()
            data = response.json()
            return PortfolioState(**data)

        if self._alpaca_trading is not None:
            return await self._get_portfolio_direct()

        # Mock state for testing
        return PortfolioState(
            cash_balance=100000.0,
            portfolio_value=100000.0,
        )

    async def _get_portfolio_direct(self) -> PortfolioState:
        """Get portfolio state directly from Alpaca."""
        try:
            account = self._alpaca_trading.get_account()
            positions = self._alpaca_trading.get_all_positions()

            position_dict = {}
            position_values = {}
            position_costs = {}

            for pos in positions:
                position_dict[pos.symbol] = float(pos.qty)
                position_values[pos.symbol] = float(pos.market_value)
                position_costs[pos.symbol] = float(pos.cost_basis)

            return PortfolioState(
                cash_balance=float(account.cash),
                portfolio_value=float(account.portfolio_value),
                positions=position_dict,
                position_values=position_values,
                position_costs=position_costs,
                unrealized_pnl=float(account.unrealized_pl) if account.unrealized_pl else 0.0,
                margin_used=float(account.initial_margin) if account.initial_margin else 0.0,
            )

        except Exception as e:
            logger.error("Failed to get portfolio from Alpaca", error=str(e))
            return PortfolioState()

    async def get_market_data(
        self,
        symbol: str,
        timeframe: str = "1D",
        limit: int = 100,
    ) -> dict[str, Any]:
        """Get historical market data."""
        if self._client is not None:
            response = await self._client.get(
                f"/market-data/{symbol}",
                params={"timeframe": timeframe, "limit": limit},
            )
            response.raise_for_status()
            return response.json()

        if self._alpaca_data is not None:
            return await self._get_market_data_direct(symbol, timeframe, limit)

        # Mock data
        return {
            "symbol": symbol,
            "bars": [],
            "message": "No data source configured",
        }

    async def _get_market_data_direct(
        self,
        symbol: str,
        timeframe: str,
        limit: int,
    ) -> dict[str, Any]:
        """Get market data directly from Alpaca."""
        try:
            from alpaca.data.requests import StockBarsRequest
            from alpaca.data.timeframe import TimeFrame
            from datetime import timedelta

            # Map timeframe string to TimeFrame enum
            tf_map = {
                "1Min": TimeFrame.Minute,
                "5Min": TimeFrame(5, "Min"),
                "1H": TimeFrame.Hour,
                "1D": TimeFrame.Day,
            }
            tf = tf_map.get(timeframe, TimeFrame.Day)

            end = datetime.now()
            start = end - timedelta(days=limit * 2)  # Rough approximation

            request = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=tf,
                start=start,
                end=end,
                limit=limit,
            )

            bars = self._alpaca_data.get_stock_bars(request)

            if symbol not in bars:
                return {"symbol": symbol, "bars": []}

            bar_list = []
            for bar in bars[symbol]:
                bar_list.append({
                    "timestamp": bar.timestamp.isoformat(),
                    "open": float(bar.open),
                    "high": float(bar.high),
                    "low": float(bar.low),
                    "close": float(bar.close),
                    "volume": int(bar.volume),
                })

            return {"symbol": symbol, "bars": bar_list}

        except Exception as e:
            logger.error("Failed to get market data", error=str(e))
            return {"symbol": symbol, "bars": [], "error": str(e)}

    async def calculate_risk_metrics(
        self,
        symbol: str,
        position_size_pct: float,
    ) -> dict[str, Any]:
        """Calculate risk metrics for a potential position."""
        # Get recent market data for volatility calculation
        market_data = await self.get_market_data(symbol, "1D", 30)

        if not market_data.get("bars"):
            return {
                "symbol": symbol,
                "error": "Insufficient market data",
            }

        import numpy as np

        bars = market_data["bars"]
        closes = [b["close"] for b in bars]

        if len(closes) < 2:
            return {"symbol": symbol, "error": "Not enough data points"}

        # Calculate returns
        returns = np.diff(closes) / closes[:-1]

        # Daily volatility
        daily_vol = np.std(returns)

        # Annualized volatility
        annual_vol = daily_vol * np.sqrt(252)

        # Value at Risk (95%)
        var_95 = np.percentile(returns, 5) * position_size_pct

        # Expected shortfall (CVaR)
        cvar_95 = np.mean(returns[returns <= np.percentile(returns, 5)]) * position_size_pct

        # Max drawdown from history
        cumulative = np.cumprod(1 + returns)
        running_max = np.maximum.accumulate(cumulative)
        drawdowns = (running_max - cumulative) / running_max
        max_drawdown = np.max(drawdowns)

        # Position size recommendation based on risk
        recommended_size = min(
            position_size_pct,
            0.02 / daily_vol,  # Target 2% daily risk
            self.settings.risk.max_position_size_fraction,
        )

        return {
            "symbol": symbol,
            "proposed_size_pct": position_size_pct,
            "daily_volatility": float(daily_vol),
            "annual_volatility": float(annual_vol),
            "var_95_pct": float(var_95),
            "cvar_95_pct": float(cvar_95),
            "historical_max_drawdown": float(max_drawdown),
            "recommended_size_pct": float(recommended_size),
            "risk_rating": "high" if daily_vol > 0.03 else "medium" if daily_vol > 0.015 else "low",
        }

    async def build_trading_state(
        self,
        symbol: str,
        include_sentiment: bool = True,
    ) -> TradingState:
        """
        Build complete TradingState for MCTS.

        Combines portfolio state, market data, analyst signals, and
        sentiment analysis into a TradingState object for tree search.

        Args:
            symbol: Trading symbol
            include_sentiment: Whether to fetch and include sentiment analysis

        Returns:
            Complete TradingState for MCTS
        """
        import numpy as np
        from reasoning_trading.core.state import TechnicalIndicators

        # Get current data in parallel
        portfolio_task = self.get_portfolio_state()
        market_task = self.get_market_data(symbol, "1D", 200)
        signal_task = self.get_trading_signal(symbol, datetime.now().strftime("%Y-%m-%d"))

        # Optionally include sentiment analysis
        tasks = [portfolio_task, market_task, signal_task]
        if include_sentiment:
            sentiment_task = self._get_sentiment_safe(symbol)
            tasks.append(sentiment_task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        portfolio = results[0] if not isinstance(results[0], Exception) else PortfolioState()
        market_data = results[1] if not isinstance(results[1], Exception) else {"bars": []}
        signal = results[2] if not isinstance(results[2], Exception) else TradingSignal(
            symbol=symbol, direction="hold", confidence=0.5, position_size_pct=0.0, stop_loss_pct=0.05
        )
        sentiment = results[3] if len(results) > 3 and not isinstance(results[3], Exception) else None

        # Build OHLCV array
        bars = market_data.get("bars", []) if isinstance(market_data, dict) else []
        ohlcv = None
        current_price = 0.0

        if bars:
            ohlcv = np.array([
                [b["open"], b["high"], b["low"], b["close"], b["volume"]]
                for b in bars
            ], dtype=np.float64)
            current_price = bars[-1]["close"]

        # Build analyst signals with sentiment integration
        news_score = signal.analyst_signals.get("news", 0.0)
        news_confidence = 0.5
        social_score = signal.analyst_signals.get("social", 0.0)
        social_confidence = 0.5

        # Override with actual sentiment if available
        if sentiment is not None and sentiment.is_reliable:
            news_score = sentiment.news_score
            news_confidence = sentiment.news_confidence
            social_score = sentiment.social_score
            social_confidence = sentiment.social_confidence
            logger.info(
                "Integrated sentiment into trading state",
                symbol=symbol,
                news_score=news_score,
                social_score=social_score,
            )

        analyst_signals = AnalystSignals(
            market_analyst_score=signal.analyst_signals.get("market", 0.0),
            news_analyst_score=news_score,
            news_analyst_confidence=news_confidence,
            social_sentiment_score=social_score,
            social_sentiment_confidence=social_confidence,
            fundamental_analyst_score=signal.analyst_signals.get("fundamental", 0.0),
            macro_analyst_score=signal.analyst_signals.get("macro", 0.0),
            researcher_consensus=(
                1.0 if signal.direction == "buy"
                else -1.0 if signal.direction == "sell"
                else 0.0
            ) * signal.confidence,
            debate_confidence=signal.confidence,
        )

        # Add sentiment evidence to analyst signals
        if sentiment is not None:
            analyst_signals.evidence_packets["sentiment"] = {
                "news_score": sentiment.news_score,
                "social_score": sentiment.social_score,
                "combined_score": sentiment.combined_score,
                "article_count": sentiment.article_count,
                "top_bullish": sentiment.top_bullish_headlines[:2],
                "top_bearish": sentiment.top_bearish_headlines[:2],
            }

        return TradingState(
            symbol=symbol,
            timestamp=datetime.now(),
            current_price=current_price,
            ohlcv_history=ohlcv,
            portfolio=portfolio,
            analyst_signals=analyst_signals,
            risk_profile=self.settings.risk.default_risk_profile.value,
        )

    async def _get_sentiment_safe(self, symbol: str) -> AggregatedSentiment | None:
        """Safely get sentiment, returning None on failure."""
        try:
            return await self.get_sentiment(symbol)
        except Exception as e:
            logger.warning(
                "Failed to get sentiment for trading state",
                symbol=symbol,
                error=str(e),
            )
            return None
