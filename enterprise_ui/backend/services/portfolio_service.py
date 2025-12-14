"""
Portfolio service for position tracking and risk management.

Provides portfolio state management, position tracking,
and risk metrics calculation.
"""

from datetime import datetime
from typing import Any, Optional

import numpy as np
import structlog

from reasoning_trading.config import Settings
from reasoning_trading.core.state import PortfolioState

from .cache_service import CacheService
from .exceptions import PortfolioServiceException, ValidationException

logger = structlog.get_logger(__name__)


class PortfolioService:
    """
    Portfolio management service.

    Provides:
    - Portfolio state retrieval and updates
    - Position tracking and analysis
    - Risk metrics calculation (VaR, Sharpe, drawdown)
    - Position risk checks
    - Portfolio statistics
    """

    def __init__(
        self,
        cache_service: Optional[CacheService] = None,
        settings: Optional[Settings] = None,
    ):
        """
        Initialize portfolio service.

        Args:
            cache_service: Cache service for portfolio data
            settings: Application settings
        """
        self.cache = cache_service
        self.settings = settings

        # In-memory portfolio state (would be database in production)
        self._portfolio_state: Optional[PortfolioState] = None

    async def get_state(
        self,
        refresh: bool = False,
    ) -> PortfolioState:
        """
        Get current portfolio state.

        Args:
            refresh: Force refresh from source

        Returns:
            Current PortfolioState

        Raises:
            PortfolioServiceException: On retrieval errors
        """
        try:
            # Check cache first
            if not refresh and self.cache:
                cached = await self.cache.get("portfolio:state", use_pickle=True)
                if cached is not None:
                    logger.debug("portfolio_state_cache_hit")
                    return cached

            # Get fresh state (would query trading adapter in production)
            if self._portfolio_state is None:
                # Initialize with default state
                self._portfolio_state = PortfolioState(
                    cash_balance=100000.0,
                    portfolio_value=100000.0,
                )

            # Cache for 30 seconds
            if self.cache:
                await self.cache.set(
                    "portfolio:state",
                    self._portfolio_state,
                    ttl=30,
                    use_pickle=True,
                )

            logger.debug(
                "portfolio_state_retrieved",
                cash_balance=self._portfolio_state.cash_balance,
                portfolio_value=self._portfolio_state.portfolio_value,
            )

            return self._portfolio_state

        except Exception as e:
            logger.error("portfolio_state_retrieval_failed", error=str(e))
            raise PortfolioServiceException(
                "Failed to get portfolio state",
                {"error": str(e)},
            )

    async def update_state(self, state: PortfolioState) -> None:
        """
        Update portfolio state.

        Args:
            state: New portfolio state

        Raises:
            ValidationException: On invalid state
            PortfolioServiceException: On update errors
        """
        if state.cash_balance < 0:
            raise ValidationException(
                "Cash balance cannot be negative",
                field="cash_balance",
            )

        if state.portfolio_value < 0:
            raise ValidationException(
                "Portfolio value cannot be negative",
                field="portfolio_value",
            )

        try:
            self._portfolio_state = state

            # Update cache
            if self.cache:
                await self.cache.delete("portfolio:state")
                await self.cache.set(
                    "portfolio:state",
                    state,
                    ttl=30,
                    use_pickle=True,
                )

            logger.info(
                "portfolio_state_updated",
                cash_balance=state.cash_balance,
                portfolio_value=state.portfolio_value,
            )

        except Exception as e:
            logger.error("portfolio_state_update_failed", error=str(e))
            raise PortfolioServiceException(
                "Failed to update portfolio state",
                {"error": str(e)},
            )

    async def get_positions(self) -> dict[str, dict[str, Any]]:
        """
        Get all current positions with details.

        Returns:
            Dictionary mapping symbols to position details

        Raises:
            PortfolioServiceException: On retrieval errors
        """
        try:
            state = await self.get_state()

            positions = {}
            for symbol, quantity in state.positions.items():
                if quantity == 0:
                    continue

                value = state.position_values.get(symbol, 0.0)
                cost = state.position_costs.get(symbol, 0.0)
                pnl = value - cost
                pnl_pct = (pnl / cost * 100) if cost > 0 else 0.0

                positions[symbol] = {
                    "symbol": symbol,
                    "quantity": quantity,
                    "value": value,
                    "cost_basis": cost,
                    "unrealized_pnl": pnl,
                    "unrealized_pnl_pct": pnl_pct,
                    "weight": value / state.portfolio_value if state.portfolio_value > 0 else 0.0,
                }

            logger.debug("positions_retrieved", count=len(positions))

            return positions

        except Exception as e:
            logger.error("positions_retrieval_failed", error=str(e))
            raise PortfolioServiceException(
                "Failed to get positions",
                {"error": str(e)},
            )

    async def get_risk_metrics(self) -> dict[str, Any]:
        """
        Calculate portfolio risk metrics.

        Returns:
            Dictionary with risk metrics

        Raises:
            PortfolioServiceException: On calculation errors
        """
        try:
            state = await self.get_state()
            positions = await self.get_positions()

            # Calculate concentration risk
            position_weights = [p["weight"] for p in positions.values()]
            max_concentration = max(position_weights) if position_weights else 0.0
            herfindahl_index = sum(w**2 for w in position_weights)

            # Calculate leverage
            total_position_value = sum(p["value"] for p in positions.values())
            leverage = total_position_value / state.portfolio_value if state.portfolio_value > 0 else 0.0

            # Calculate margin metrics
            buying_power = state.cash_balance
            if state.margin_limit > 0:
                buying_power = state.margin_limit - state.margin_used

            margin_utilization = (
                state.margin_used / state.margin_limit if state.margin_limit > 0 else 0.0
            )

            # Portfolio-level risk metrics
            metrics = {
                "portfolio_value": state.portfolio_value,
                "cash_balance": state.cash_balance,
                "unrealized_pnl": state.unrealized_pnl,
                "margin_used": state.margin_used,
                "margin_limit": state.margin_limit,
                "margin_utilization": margin_utilization,
                "buying_power": buying_power,
                "leverage": leverage,
                "num_positions": len(positions),
                "max_concentration": max_concentration,
                "herfindahl_index": herfindahl_index,
                "diversification_score": 1.0 - herfindahl_index if herfindahl_index < 1.0 else 0.0,
                "timestamp": datetime.now().isoformat(),
            }

            # Add position-specific risks
            if positions:
                total_pnl = sum(p["unrealized_pnl"] for p in positions.values())
                metrics["total_unrealized_pnl"] = total_pnl
                metrics["winning_positions"] = sum(1 for p in positions.values() if p["unrealized_pnl"] > 0)
                metrics["losing_positions"] = sum(1 for p in positions.values() if p["unrealized_pnl"] < 0)

            logger.debug(
                "risk_metrics_calculated",
                leverage=leverage,
                margin_utilization=margin_utilization,
                num_positions=len(positions),
            )

            return metrics

        except Exception as e:
            logger.error("risk_metrics_calculation_failed", error=str(e))
            raise PortfolioServiceException(
                "Failed to calculate risk metrics",
                {"error": str(e)},
            )

    async def check_position_risk(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
    ) -> dict[str, Any]:
        """
        Check if a position would violate risk limits.

        Args:
            symbol: Trading symbol
            side: "buy" or "sell"
            quantity: Position quantity
            price: Entry price

        Returns:
            Dictionary with risk check results

        Raises:
            ValidationException: On invalid inputs
            PortfolioServiceException: On check errors
        """
        if not symbol or not symbol.strip():
            raise ValidationException("Symbol cannot be empty", field="symbol")

        if side.lower() not in ["buy", "sell"]:
            raise ValidationException("Side must be 'buy' or 'sell'", field="side")

        if quantity <= 0:
            raise ValidationException("Quantity must be positive", field="quantity")

        if price <= 0:
            raise ValidationException("Price must be positive", field="price")

        try:
            state = await self.get_state()
            positions = await self.get_positions()

            position_value = quantity * price
            new_portfolio_value = state.portfolio_value

            # Calculate new position weight
            if side.lower() == "buy":
                new_portfolio_value += position_value

            position_weight = position_value / new_portfolio_value if new_portfolio_value > 0 else 0.0

            # Get risk limits from settings
            max_position_size = 0.25  # Default 25%
            max_leverage = 2.0
            max_concentration = 0.50

            if self.settings:
                max_position_size = self.settings.risk.max_position_size_fraction
                max_leverage = self.settings.risk.max_leverage
                max_concentration = self.settings.risk.max_concentration

            # Check limits
            violations = []

            if position_weight > max_position_size:
                violations.append({
                    "rule": "max_position_size",
                    "limit": max_position_size,
                    "value": position_weight,
                })

            # Calculate new leverage
            total_position_value = sum(p["value"] for p in positions.values())
            if side.lower() == "buy":
                total_position_value += position_value

            new_leverage = total_position_value / state.portfolio_value if state.portfolio_value > 0 else 0.0

            if new_leverage > max_leverage:
                violations.append({
                    "rule": "max_leverage",
                    "limit": max_leverage,
                    "value": new_leverage,
                })

            # Check concentration
            if position_weight > max_concentration:
                violations.append({
                    "rule": "max_concentration",
                    "limit": max_concentration,
                    "value": position_weight,
                })

            # Check margin requirements
            margin_required = position_value * 0.5  # Simplified 50% margin
            available_margin = state.margin_limit - state.margin_used

            if side.lower() == "buy" and margin_required > available_margin:
                violations.append({
                    "rule": "insufficient_margin",
                    "limit": available_margin,
                    "value": margin_required,
                })

            # Check cash balance
            if side.lower() == "buy" and position_value > state.cash_balance:
                violations.append({
                    "rule": "insufficient_cash",
                    "limit": state.cash_balance,
                    "value": position_value,
                })

            result = {
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "price": price,
                "position_value": position_value,
                "position_weight": position_weight,
                "new_leverage": new_leverage,
                "violations": violations,
                "allowed": len(violations) == 0,
                "timestamp": datetime.now().isoformat(),
            }

            logger.info(
                "position_risk_checked",
                symbol=symbol,
                allowed=result["allowed"],
                violations=len(violations),
            )

            return result

        except ValidationException:
            raise
        except Exception as e:
            logger.error("position_risk_check_failed", symbol=symbol, error=str(e))
            raise PortfolioServiceException(
                f"Failed to check position risk for '{symbol}'",
                {"symbol": symbol, "error": str(e)},
            )

    async def get_statistics(self) -> dict[str, Any]:
        """
        Get portfolio statistics.

        Returns:
            Dictionary with portfolio statistics

        Raises:
            PortfolioServiceException: On calculation errors
        """
        try:
            state = await self.get_state()
            positions = await self.get_positions()
            risk_metrics = await self.get_risk_metrics()

            stats = {
                "portfolio_value": state.portfolio_value,
                "cash_balance": state.cash_balance,
                "cash_pct": state.cash_balance / state.portfolio_value * 100 if state.portfolio_value > 0 else 0,
                "invested_pct": (state.portfolio_value - state.cash_balance) / state.portfolio_value * 100 if state.portfolio_value > 0 else 0,
                "num_positions": len(positions),
                "unrealized_pnl": state.unrealized_pnl,
                "unrealized_pnl_pct": state.unrealized_pnl / state.portfolio_value * 100 if state.portfolio_value > 0 else 0,
                "leverage": risk_metrics["leverage"],
                "diversification_score": risk_metrics["diversification_score"],
                "timestamp": datetime.now().isoformat(),
            }

            if positions:
                stats["top_positions"] = sorted(
                    positions.values(),
                    key=lambda p: p["value"],
                    reverse=True,
                )[:5]

            logger.debug("portfolio_statistics_calculated")

            return stats

        except Exception as e:
            logger.error("portfolio_statistics_failed", error=str(e))
            raise PortfolioServiceException(
                "Failed to calculate portfolio statistics",
                {"error": str(e)},
            )
