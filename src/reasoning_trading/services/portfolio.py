"""
Portfolio management service.

Provides portfolio state tracking, position management, and
risk calculations for the trading system.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

import numpy as np
import structlog

from reasoning_trading.config import RiskProfile, Settings, get_settings
from reasoning_trading.core.actions import TradingAction, TradingDirection
from reasoning_trading.core.state import PortfolioState

logger = structlog.get_logger(__name__)


@dataclass
class Position:
    """Individual position tracking."""

    symbol: str
    quantity: float
    entry_price: float
    entry_time: datetime
    current_price: float = 0.0
    stop_loss_price: float | None = None
    take_profit_price: float | None = None

    @property
    def market_value(self) -> float:
        """Current market value of position."""
        return self.quantity * self.current_price

    @property
    def cost_basis(self) -> float:
        """Total cost of position."""
        return self.quantity * self.entry_price

    @property
    def unrealized_pnl(self) -> float:
        """Unrealized profit/loss."""
        return self.market_value - self.cost_basis

    @property
    def unrealized_pnl_pct(self) -> float:
        """Unrealized P&L as percentage."""
        if self.cost_basis == 0:
            return 0.0
        return self.unrealized_pnl / self.cost_basis

    @property
    def is_long(self) -> bool:
        """Check if this is a long position."""
        return self.quantity > 0

    @property
    def is_short(self) -> bool:
        """Check if this is a short position."""
        return self.quantity < 0

    def should_stop_loss(self) -> bool:
        """Check if stop-loss should trigger."""
        if self.stop_loss_price is None:
            return False
        if self.is_long:
            return self.current_price <= self.stop_loss_price
        else:
            return self.current_price >= self.stop_loss_price

    def should_take_profit(self) -> bool:
        """Check if take-profit should trigger."""
        if self.take_profit_price is None:
            return False
        if self.is_long:
            return self.current_price >= self.take_profit_price
        else:
            return self.current_price <= self.take_profit_price


@dataclass
class TradeRecord:
    """Record of an executed trade."""

    symbol: str
    side: str
    quantity: float
    price: float
    timestamp: datetime
    pnl: float = 0.0
    fees: float = 0.0


class PortfolioService:
    """
    Portfolio management and risk monitoring service.

    Provides:
    - Position tracking and management
    - P&L calculation
    - Risk metric computation
    - Portfolio state snapshots
    """

    def __init__(
        self,
        initial_cash: float = 100000.0,
        settings: Settings | None = None,
    ):
        """
        Initialize portfolio service.

        Args:
            initial_cash: Starting cash balance
            settings: Application settings
        """
        self.settings = settings or get_settings()
        self._cash = initial_cash
        self._initial_cash = initial_cash
        self._positions: dict[str, Position] = {}
        self._trade_history: list[TradeRecord] = []
        self._daily_pnl_history: list[tuple[datetime, float]] = []
        self._peak_value = initial_cash

    @property
    def cash_balance(self) -> float:
        """Current cash balance."""
        return self._cash

    @property
    def positions_value(self) -> float:
        """Total value of all positions."""
        return sum(p.market_value for p in self._positions.values())

    @property
    def portfolio_value(self) -> float:
        """Total portfolio value (cash + positions)."""
        return self._cash + self.positions_value

    @property
    def unrealized_pnl(self) -> float:
        """Total unrealized P&L across positions."""
        return sum(p.unrealized_pnl for p in self._positions.values())

    @property
    def total_pnl(self) -> float:
        """Total P&L (realized + unrealized)."""
        realized = sum(t.pnl for t in self._trade_history)
        return realized + self.unrealized_pnl

    @property
    def current_drawdown(self) -> float:
        """Current drawdown from peak."""
        if self._peak_value == 0:
            return 0.0
        return (self._peak_value - self.portfolio_value) / self._peak_value

    def get_state(self) -> PortfolioState:
        """Get current portfolio state snapshot."""
        positions = {s: p.quantity for s, p in self._positions.items()}
        position_values = {s: p.market_value for s, p in self._positions.items()}
        position_costs = {s: p.cost_basis for s, p in self._positions.items()}

        # Calculate largest position
        largest_pct = 0.0
        if self._positions and self.portfolio_value > 0:
            largest_value = max(abs(p.market_value) for p in self._positions.values())
            largest_pct = largest_value / self.portfolio_value

        # Calculate realized P&L
        today = datetime.now().date()
        today_pnl = sum(
            t.pnl
            for t in self._trade_history
            if t.timestamp.date() == today
        )

        return PortfolioState(
            cash_balance=self._cash,
            portfolio_value=self.portfolio_value,
            positions=positions,
            position_values=position_values,
            position_costs=position_costs,
            unrealized_pnl=self.unrealized_pnl,
            realized_pnl_today=today_pnl,
            realized_pnl_total=sum(t.pnl for t in self._trade_history),
            current_drawdown=self.current_drawdown,
            max_drawdown=self._calculate_max_drawdown(),
            largest_position_pct=largest_pct,
            position_count=len(self._positions),
        )

    def update_prices(self, prices: dict[str, float]) -> None:
        """
        Update position prices.

        Args:
            prices: Map of symbol to current price
        """
        for symbol, price in prices.items():
            if symbol in self._positions:
                self._positions[symbol].current_price = price

        # Update peak value
        self._peak_value = max(self._peak_value, self.portfolio_value)

    def can_open_position(
        self,
        symbol: str,
        direction: TradingDirection,
        value: float,
    ) -> tuple[bool, str]:
        """
        Check if a position can be opened.

        Args:
            symbol: Trading symbol
            direction: Trade direction
            value: Position value

        Returns:
            Tuple of (can_trade, reason)
        """
        # Check cash availability
        if value > self._cash:
            return False, f"Insufficient cash: need {value}, have {self._cash}"

        # Check position size limits
        max_position = self.portfolio_value * self.settings.risk.max_position_size_fraction
        if value > max_position:
            return False, f"Position too large: {value} > max {max_position}"

        # Check if we already have a position
        if symbol in self._positions:
            existing = self._positions[symbol]
            # Can't go opposite direction without closing first
            if (
                (direction == TradingDirection.BUY and existing.is_short)
                or (direction == TradingDirection.SHORT and existing.is_long)
            ):
                return False, f"Must close existing position first"

        # Check daily loss limit
        daily_loss = self._get_daily_loss()
        max_daily_loss = self.portfolio_value * self.settings.risk.max_daily_loss_percent
        if daily_loss >= max_daily_loss:
            return False, f"Daily loss limit reached: {daily_loss}"

        return True, "OK"

    def execute_trade(
        self,
        symbol: str,
        direction: TradingDirection,
        quantity: float,
        price: float,
        stop_loss_pct: float | None = None,
        take_profit_pct: float | None = None,
        commission_rate: float = 0.001,
    ) -> TradeRecord:
        """
        Execute a trade and update portfolio.

        Args:
            symbol: Trading symbol
            direction: Trade direction
            quantity: Number of units
            price: Execution price
            stop_loss_pct: Stop-loss percentage (optional)
            take_profit_pct: Take-profit percentage (optional)
            commission_rate: Commission rate

        Returns:
            TradeRecord of the executed trade
        """
        trade_value = quantity * price
        commission = trade_value * commission_rate

        pnl = 0.0

        if direction in (TradingDirection.BUY, TradingDirection.SHORT):
            # Opening position
            sign = 1 if direction == TradingDirection.BUY else -1
            actual_quantity = sign * quantity

            if symbol in self._positions:
                # Adding to existing position
                existing = self._positions[symbol]
                new_quantity = existing.quantity + actual_quantity
                new_cost = (existing.cost_basis + trade_value) / new_quantity if new_quantity != 0 else 0
                existing.quantity = new_quantity
                existing.entry_price = new_cost
            else:
                # New position
                stop_loss_price = None
                take_profit_price = None

                if stop_loss_pct is not None:
                    if direction == TradingDirection.BUY:
                        stop_loss_price = price * (1 - stop_loss_pct)
                    else:
                        stop_loss_price = price * (1 + stop_loss_pct)

                if take_profit_pct is not None:
                    if direction == TradingDirection.BUY:
                        take_profit_price = price * (1 + take_profit_pct)
                    else:
                        take_profit_price = price * (1 - take_profit_pct)

                self._positions[symbol] = Position(
                    symbol=symbol,
                    quantity=actual_quantity,
                    entry_price=price,
                    entry_time=datetime.now(),
                    current_price=price,
                    stop_loss_price=stop_loss_price,
                    take_profit_price=take_profit_price,
                )

            self._cash -= trade_value + commission

        elif direction in (TradingDirection.SELL, TradingDirection.COVER):
            # Closing position
            if symbol in self._positions:
                position = self._positions[symbol]
                pnl = position.unrealized_pnl - commission
                self._cash += trade_value - commission
                del self._positions[symbol]
            else:
                logger.warning("No position to close", symbol=symbol)

        elif direction == TradingDirection.HOLD:
            pass  # No action

        trade = TradeRecord(
            symbol=symbol,
            side=direction.value,
            quantity=quantity,
            price=price,
            timestamp=datetime.now(),
            pnl=pnl,
            fees=commission,
        )

        self._trade_history.append(trade)

        logger.info(
            "Trade executed",
            symbol=symbol,
            direction=direction.value,
            quantity=quantity,
            price=price,
            pnl=pnl,
        )

        return trade

    def apply_action(
        self,
        symbol: str,
        action: TradingAction,
        current_price: float,
    ) -> TradeRecord | None:
        """
        Apply a TradingAction to the portfolio.

        Args:
            symbol: Trading symbol
            action: TradingAction to execute
            current_price: Current market price

        Returns:
            TradeRecord if trade executed, None otherwise
        """
        if action.direction == TradingDirection.HOLD:
            return None

        # Calculate quantity from position size
        position_value = action.position_size.size_fraction * self.portfolio_value
        quantity = position_value / current_price

        if quantity <= 0:
            return None

        can_trade, reason = self.can_open_position(
            symbol, action.direction, position_value
        )

        if not can_trade:
            logger.warning("Cannot execute trade", reason=reason)
            return None

        return self.execute_trade(
            symbol=symbol,
            direction=action.direction,
            quantity=quantity,
            price=current_price,
            stop_loss_pct=action.stop_loss.stop_loss_pct,
            take_profit_pct=action.stop_loss.take_profit_pct,
        )

    def check_stop_losses(self) -> list[str]:
        """
        Check all positions for stop-loss triggers.

        Returns:
            List of symbols that triggered stop-loss
        """
        triggered = []
        for symbol, position in list(self._positions.items()):
            if position.should_stop_loss():
                triggered.append(symbol)
                logger.info(
                    "Stop-loss triggered",
                    symbol=symbol,
                    price=position.current_price,
                    stop_price=position.stop_loss_price,
                )
        return triggered

    def check_take_profits(self) -> list[str]:
        """
        Check all positions for take-profit triggers.

        Returns:
            List of symbols that triggered take-profit
        """
        triggered = []
        for symbol, position in list(self._positions.items()):
            if position.should_take_profit():
                triggered.append(symbol)
                logger.info(
                    "Take-profit triggered",
                    symbol=symbol,
                    price=position.current_price,
                    target_price=position.take_profit_price,
                )
        return triggered

    def get_position(self, symbol: str) -> Position | None:
        """Get position for a symbol."""
        return self._positions.get(symbol)

    def get_all_positions(self) -> list[Position]:
        """Get all open positions."""
        return list(self._positions.values())

    def get_trade_history(
        self,
        symbol: str | None = None,
        since: datetime | None = None,
    ) -> list[TradeRecord]:
        """
        Get trade history with optional filters.

        Args:
            symbol: Filter by symbol (optional)
            since: Filter by timestamp (optional)

        Returns:
            List of matching TradeRecords
        """
        trades = self._trade_history

        if symbol is not None:
            trades = [t for t in trades if t.symbol == symbol]

        if since is not None:
            trades = [t for t in trades if t.timestamp >= since]

        return trades

    def calculate_sharpe_ratio(self, risk_free_rate: float = 0.0) -> float:
        """
        Calculate Sharpe ratio from trade history.

        Args:
            risk_free_rate: Annual risk-free rate

        Returns:
            Annualized Sharpe ratio
        """
        if len(self._trade_history) < 2:
            return 0.0

        returns = [t.pnl / max(self._initial_cash, 1) for t in self._trade_history]
        mean_return = np.mean(returns)
        std_return = np.std(returns)

        if std_return == 0:
            return 0.0

        # Annualize (assuming daily returns)
        sharpe = (mean_return - risk_free_rate / 252) / std_return
        return float(sharpe * np.sqrt(252))

    def _calculate_max_drawdown(self) -> float:
        """Calculate maximum drawdown from portfolio history."""
        if not self._daily_pnl_history:
            return self.current_drawdown

        values = [self._initial_cash]
        for _, pnl in self._daily_pnl_history:
            values.append(values[-1] + pnl)

        peak = values[0]
        max_dd = 0.0

        for value in values:
            if value > peak:
                peak = value
            dd = (peak - value) / peak if peak > 0 else 0
            max_dd = max(max_dd, dd)

        return max_dd

    def _get_daily_loss(self) -> float:
        """Get total loss for today."""
        today = datetime.now().date()
        daily_loss = 0.0

        for trade in self._trade_history:
            if trade.timestamp.date() == today and trade.pnl < 0:
                daily_loss -= trade.pnl

        return daily_loss

    def reset(self, initial_cash: float | None = None) -> None:
        """
        Reset portfolio to initial state.

        Args:
            initial_cash: New initial cash (uses original if not provided)
        """
        if initial_cash is not None:
            self._initial_cash = initial_cash

        self._cash = self._initial_cash
        self._positions.clear()
        self._trade_history.clear()
        self._daily_pnl_history.clear()
        self._peak_value = self._initial_cash

        logger.info("Portfolio reset", initial_cash=self._initial_cash)
