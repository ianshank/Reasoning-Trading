/**
 * Portfolio and position management types
 *
 * TypeScript definitions for portfolio state, positions, and risk metrics
 */

import type { TradingAction } from './actions';

/**
 * Position status
 */
export enum PositionStatus {
  OPEN = 'open',
  CLOSED = 'closed',
  PENDING = 'pending',
}

/**
 * Position side (long or short)
 */
export enum PositionSide {
  LONG = 'long',
  SHORT = 'short',
}

/**
 * Individual position details
 */
export interface Position {
  // Identity
  symbol: string;
  position_id: string;

  // Position details
  side: PositionSide;
  status: PositionStatus;
  quantity: number;
  entry_price: number;
  current_price: number;

  // Costs
  cost_basis: number;
  market_value: number;

  // P&L
  unrealized_pnl: number;
  unrealized_pnl_pct: number;
  realized_pnl: number;

  // Risk management
  stop_loss_price: number | null;
  take_profit_price: number | null;
  trailing_stop: boolean;
  trailing_distance_pct: number;

  // Timing
  entry_time: string;
  exit_time: string | null;
  time_horizon: string;

  // Metadata
  entry_action: TradingAction;
  notes: string;
}

/**
 * Risk metrics for portfolio
 */
export interface RiskMetrics {
  // Value at Risk
  /** 95% daily Value at Risk */
  daily_var_95: number | null;
  /** 99% daily Value at Risk */
  daily_var_99: number | null;

  // Drawdown
  /** Maximum drawdown (0 to 1) */
  max_drawdown: number;
  /** Current drawdown (0 to 1) */
  current_drawdown: number;
  /** Drawdown start date */
  drawdown_start: string | null;

  // Volatility
  /** Portfolio volatility (annualized) */
  portfolio_volatility: number;
  /** Sharpe ratio */
  sharpe_ratio: number | null;
  /** Sortino ratio */
  sortino_ratio: number | null;

  // Concentration
  /** Largest position as % of portfolio (0 to 1) */
  largest_position_pct: number;
  /** Top 5 positions concentration */
  top5_concentration: number;
  /** Herfindahl index (diversification measure) */
  herfindahl_index: number;

  // Leverage
  /** Total leverage ratio */
  leverage_ratio: number;
  /** Margin utilization (0 to 1) */
  margin_utilization: number;
}

/**
 * Portfolio performance metrics
 */
export interface PerformanceMetrics {
  // Returns
  total_return: number;
  total_return_pct: number;
  today_return: number;
  today_return_pct: number;

  // Period returns
  day_return_pct: number;
  week_return_pct: number;
  month_return_pct: number;
  year_return_pct: number;

  // Win/Loss
  win_rate: number;
  profit_factor: number;
  avg_win: number;
  avg_loss: number;
  largest_win: number;
  largest_loss: number;

  // Trade statistics
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  avg_trade_duration_hours: number;
}

/**
 * Portfolio allocation by asset type
 */
export interface PortfolioAllocation {
  cash: number;
  stocks: number;
  crypto: number;
  options: number;
  other: number;
}

/**
 * Complete portfolio state
 */
export interface Portfolio {
  // Identity
  portfolio_id: string;
  account_id: string;

  // Value
  total_value: number;
  cash_balance: number;
  buying_power: number;

  // Positions
  positions: Position[];
  position_count: number;
  long_positions: number;
  short_positions: number;

  // P&L
  unrealized_pnl: number;
  realized_pnl_today: number;
  realized_pnl_total: number;

  // Risk
  risk_metrics: RiskMetrics;
  performance_metrics: PerformanceMetrics;
  allocation: PortfolioAllocation;

  // Margin
  margin_used: number;
  margin_available: number;
  maintenance_margin: number;

  // Metadata
  last_updated: string;
  currency: string;
}

/**
 * Portfolio summary for dashboard
 */
export interface PortfolioSummary {
  total_value: number;
  cash_balance: number;
  total_pnl: number;
  total_pnl_pct: number;
  today_pnl: number;
  today_pnl_pct: number;
  position_count: number;
  buying_power: number;
  margin_used_pct: number;
}

/**
 * Historical portfolio value point
 */
export interface PortfolioValuePoint {
  timestamp: string;
  total_value: number;
  cash: number;
  positions_value: number;
  pnl: number;
}

/**
 * Portfolio history time series
 */
export interface PortfolioHistory {
  values: PortfolioValuePoint[];
  start_date: string;
  end_date: string;
  initial_value: number;
  final_value: number;
  total_return_pct: number;
}

/**
 * Type guard to check if a position is open
 */
export function isOpenPosition(position: Position): boolean {
  return position.status === PositionStatus.OPEN;
}

/**
 * Type guard to check if a position is long
 */
export function isLongPosition(position: Position): boolean {
  return position.side === PositionSide.LONG;
}

/**
 * Type guard to check if a position is short
 */
export function isShortPosition(position: Position): boolean {
  return position.side === PositionSide.SHORT;
}

/**
 * Calculate position P&L percentage
 */
export function calculatePositionPnlPct(position: Position): number {
  if (position.cost_basis === 0) return 0;
  return (position.unrealized_pnl / position.cost_basis) * 100;
}

/**
 * Calculate portfolio allocation percentage
 */
export function calculateAllocationPct(
  allocation: PortfolioAllocation,
  totalValue: number
): Record<keyof PortfolioAllocation, number> {
  if (totalValue === 0) {
    return {
      cash: 0,
      stocks: 0,
      crypto: 0,
      options: 0,
      other: 0,
    };
  }

  return {
    cash: (allocation.cash / totalValue) * 100,
    stocks: (allocation.stocks / totalValue) * 100,
    crypto: (allocation.crypto / totalValue) * 100,
    options: (allocation.options / totalValue) * 100,
    other: (allocation.other / totalValue) * 100,
  };
}

/**
 * Get risk level based on metrics
 */
export function getRiskLevel(metrics: RiskMetrics): 'low' | 'medium' | 'high' | 'critical' {
  if (metrics.margin_utilization > 0.9 || metrics.current_drawdown > 0.2) {
    return 'critical';
  }
  if (metrics.margin_utilization > 0.7 || metrics.current_drawdown > 0.15) {
    return 'high';
  }
  if (metrics.margin_utilization > 0.5 || metrics.current_drawdown > 0.1) {
    return 'medium';
  }
  return 'low';
}
