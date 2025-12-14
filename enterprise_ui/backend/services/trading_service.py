"""
Trading service for executing trades and analyzing market data.

Integrates with TradingServiceAdapter and MarketDataService to provide
a unified interface for trading operations.
"""

from datetime import datetime
from typing import Any

import structlog

from reasoning_trading.config import Settings, TradingMode
from reasoning_trading.core.state import AnalystSignals, TradingState
from reasoning_trading.services.adapter import (
    OrderResult,
    TradingServiceAdapter,
    TradingSignal,
)
from reasoning_trading.services.market_data import MarketDataService, TimeFrame

from .cache_service import CacheService
from .exceptions import TradingServiceException, ValidationException

logger = structlog.get_logger(__name__)


class TradingService:
    """
    High-level trading service.

    Provides:
    - Symbol analysis with multi-agent system
    - Trading decision execution
    - Market data retrieval
    - Analyst signal aggregation
    - Risk metrics calculation
    """

    def __init__(
        self,
        trading_adapter: TradingServiceAdapter | None = None,
        market_data_service: MarketDataService | None = None,
        cache_service: CacheService | None = None,
        settings: Settings | None = None,
        trading_mode: TradingMode = TradingMode.PAPER,
    ):
        """
        Initialize trading service.

        Args:
            trading_adapter: Trading service adapter for execution
            market_data_service: Market data service
            cache_service: Cache service for results
            settings: Application settings
            trading_mode: Trading mode (paper or live)
        """
        self.settings = settings
        self.trading_mode = trading_mode
        self.cache = cache_service

        # Initialize adapter if not provided
        if trading_adapter is None:
            self.adapter = TradingServiceAdapter(
                trading_agent_url=None,
                mode=trading_mode,
                settings=settings,
            )
        else:
            self.adapter = trading_adapter

        # Initialize market data service
        self.market_data = market_data_service or MarketDataService(settings=settings)

        # Track initialization state
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the trading service and its dependencies."""
        if self._initialized:
            return

        try:
            await self.adapter._initialize()
            self._initialized = True
            logger.info("trading_service_initialized", mode=self.trading_mode.value)
        except Exception as e:
            logger.error("trading_service_initialization_failed", error=str(e))
            raise TradingServiceException(
                "Failed to initialize trading service",
                {"error": str(e)},
            )

    async def cleanup(self) -> None:
        """Cleanup resources."""
        if self._initialized:
            await self.adapter._cleanup()
            self._initialized = False
            logger.info("trading_service_cleaned_up")

    async def analyze_symbol(
        self,
        symbol: str,
        date: str | None = None,
        use_cache: bool = True,
    ) -> dict[str, Any]:
        """
        Analyze a symbol using multi-agent system.

        Args:
            symbol: Trading symbol (e.g., "AAPL", "BTC/USD")
            date: Analysis date in YYYY-MM-DD format (default: today)
            use_cache: Whether to use cached results

        Returns:
            Dictionary with analysis results including signal and market data

        Raises:
            ValidationException: On invalid inputs
            TradingServiceException: On analysis errors
        """
        # Validate symbol
        if not symbol or not symbol.strip():
            raise ValidationException("Symbol cannot be empty", field="symbol")

        # Use today's date if not provided
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        # Check cache
        cache_key = f"analysis:{symbol}:{date}"
        if use_cache and self.cache:
            cached = await self.cache.get(cache_key)
            if cached is not None:
                logger.debug("analysis_cache_hit", symbol=symbol, date=date)
                return cached

        try:
            # Get trading signal from adapter
            signal = await self.adapter.get_trading_signal(symbol, date)

            # Get current market data
            bars = await self.market_data.get_historical_bars(
                symbol=symbol,
                timeframe=TimeFrame.DAY_1,
                limit=200,
            )

            # Calculate technical indicators
            indicators = self.market_data.calculate_indicators(bars)

            # Detect market regime
            regime = self.market_data.detect_market_regime(bars)

            # Get current snapshot
            snapshot = await self.market_data.get_snapshot(symbol)

            result = {
                "symbol": symbol,
                "date": date,
                "signal": signal.model_dump(),
                "current_price": snapshot.last_price,
                "technical_indicators": indicators.model_dump(),
                "market_regime": regime.value,
                "bars_analyzed": len(bars),
                "timestamp": datetime.now().isoformat(),
            }

            # Cache result for 5 minutes
            if self.cache:
                await self.cache.set(cache_key, result, ttl=300)

            logger.info(
                "symbol_analyzed",
                symbol=symbol,
                direction=signal.direction,
                confidence=signal.confidence,
                regime=regime.value,
            )

            return result

        except Exception as e:
            logger.error("symbol_analysis_failed", symbol=symbol, error=str(e))
            raise TradingServiceException(
                f"Failed to analyze symbol '{symbol}'",
                {"symbol": symbol, "error": str(e)},
            )

    async def make_decision(
        self,
        symbol: str,
        analysis: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Make a trading decision based on analysis.

        Args:
            symbol: Trading symbol
            analysis: Pre-computed analysis (if None, will analyze)

        Returns:
            Dictionary with trading decision

        Raises:
            TradingServiceException: On decision errors
        """
        try:
            # Get analysis if not provided
            if analysis is None:
                analysis = await self.analyze_symbol(symbol)

            signal_data = analysis["signal"]
            direction = signal_data["direction"]
            confidence = signal_data["confidence"]

            # Determine if we should trade - get minimum confidence from settings or environment
            import os
            min_confidence = float(os.environ.get("MIN_TRADING_CONFIDENCE", "0.6"))
            if self.settings and hasattr(self.settings, "trading") and hasattr(self.settings.trading, "min_confidence"):
                min_confidence = self.settings.trading.min_confidence
            should_trade = confidence >= min_confidence and direction != "hold"

            decision = {
                "symbol": symbol,
                "should_trade": should_trade,
                "direction": direction,
                "confidence": confidence,
                "position_size_pct": signal_data["position_size_pct"],
                "stop_loss_pct": signal_data["stop_loss_pct"],
                "take_profit_pct": signal_data.get("take_profit_pct"),
                "reasoning": signal_data["reasoning"],
                "regime": analysis["market_regime"],
                "timestamp": datetime.now().isoformat(),
            }

            logger.info(
                "decision_made",
                symbol=symbol,
                should_trade=should_trade,
                direction=direction,
                confidence=confidence,
            )

            return decision

        except Exception as e:
            logger.error("decision_failed", symbol=symbol, error=str(e))
            raise TradingServiceException(
                f"Failed to make decision for '{symbol}'",
                {"symbol": symbol, "error": str(e)},
            )

    async def execute_trade(
        self,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str = "market",
    ) -> OrderResult:
        """
        Execute a trade.

        Args:
            symbol: Trading symbol
            side: "buy" or "sell"
            quantity: Number of shares/units
            order_type: "market" or "limit"

        Returns:
            OrderResult with execution details

        Raises:
            ValidationException: On invalid inputs
            TradingServiceException: On execution errors
        """
        # Validate inputs
        if not symbol or not symbol.strip():
            raise ValidationException("Symbol cannot be empty", field="symbol")

        if side.lower() not in ["buy", "sell"]:
            raise ValidationException(
                "Side must be 'buy' or 'sell'",
                field="side",
            )

        if quantity <= 0:
            raise ValidationException(
                "Quantity must be positive",
                field="quantity",
            )

        try:
            result = await self.adapter.execute_trade(
                symbol=symbol,
                side=side.lower(),
                quantity=quantity,
                order_type=order_type,
            )

            logger.info(
                "trade_executed",
                symbol=symbol,
                side=side,
                quantity=quantity,
                order_id=result.order_id,
                status=result.status,
            )

            return result

        except Exception as e:
            logger.error(
                "trade_execution_failed",
                symbol=symbol,
                side=side,
                quantity=quantity,
                error=str(e),
            )
            raise TradingServiceException(
                f"Failed to execute trade for '{symbol}'",
                {
                    "symbol": symbol,
                    "side": side,
                    "quantity": quantity,
                    "error": str(e),
                },
            )

    async def get_trading_state(self, symbol: str) -> TradingState:
        """
        Build complete TradingState for a symbol.

        Args:
            symbol: Trading symbol

        Returns:
            TradingState object for MCTS

        Raises:
            TradingServiceException: On state building errors
        """
        try:
            state = await self.adapter.build_trading_state(symbol)

            logger.debug(
                "trading_state_built",
                symbol=symbol,
                current_price=state.current_price,
                portfolio_value=state.portfolio.portfolio_value,
            )

            return state

        except Exception as e:
            logger.error("trading_state_build_failed", symbol=symbol, error=str(e))
            raise TradingServiceException(
                f"Failed to build trading state for '{symbol}'",
                {"symbol": symbol, "error": str(e)},
            )

    async def get_analyst_signals(
        self,
        symbol: str,
        date: str | None = None,
    ) -> AnalystSignals:
        """
        Get analyst signals for a symbol.

        Args:
            symbol: Trading symbol
            date: Analysis date (default: today)

        Returns:
            AnalystSignals object

        Raises:
            TradingServiceException: On signal retrieval errors
        """
        try:
            if date is None:
                date = datetime.now().strftime("%Y-%m-%d")

            signal = await self.adapter.get_trading_signal(symbol, date)

            analyst_signals = AnalystSignals(
                market_analyst_score=signal.analyst_signals.get("market", 0.0),
                news_analyst_score=signal.analyst_signals.get("news", 0.0),
                social_sentiment_score=signal.analyst_signals.get("social", 0.0),
                fundamental_analyst_score=signal.analyst_signals.get("fundamental", 0.0),
                macro_analyst_score=signal.analyst_signals.get("macro", 0.0),
                researcher_consensus=(
                    1.0
                    if signal.direction == "buy"
                    else -1.0 if signal.direction == "sell" else 0.0
                )
                * signal.confidence,
                debate_confidence=signal.confidence,
            )

            logger.debug(
                "analyst_signals_retrieved",
                symbol=symbol,
                consensus=analyst_signals.weighted_consensus(),
            )

            return analyst_signals

        except Exception as e:
            logger.error("analyst_signals_failed", symbol=symbol, error=str(e))
            raise TradingServiceException(
                f"Failed to get analyst signals for '{symbol}'",
                {"symbol": symbol, "error": str(e)},
            )

    async def get_risk_metrics(
        self,
        symbol: str,
        position_size_pct: float,
    ) -> dict[str, Any]:
        """
        Calculate risk metrics for a potential position.

        Args:
            symbol: Trading symbol
            position_size_pct: Proposed position size as % of portfolio

        Returns:
            Dictionary with risk metrics

        Raises:
            ValidationException: On invalid inputs
            TradingServiceException: On calculation errors
        """
        if position_size_pct <= 0 or position_size_pct > 1:
            raise ValidationException(
                "Position size must be between 0 and 1",
                field="position_size_pct",
            )

        try:
            metrics = await self.adapter.calculate_risk_metrics(symbol, position_size_pct)

            logger.debug(
                "risk_metrics_calculated",
                symbol=symbol,
                position_size_pct=position_size_pct,
                risk_rating=metrics.get("risk_rating"),
            )

            return metrics

        except Exception as e:
            logger.error("risk_metrics_failed", symbol=symbol, error=str(e))
            raise TradingServiceException(
                f"Failed to calculate risk metrics for '{symbol}'",
                {"symbol": symbol, "error": str(e)},
            )
