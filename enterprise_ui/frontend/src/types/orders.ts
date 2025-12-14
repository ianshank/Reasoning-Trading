/**
 * Order management types
 *
 * TypeScript definitions for order entry, tracking, and execution
 */

import type { TradingDirection, OrderType, TimeHorizon } from './actions';

/**
 * Order status enumeration
 */
export enum OrderStatus {
  PENDING = 'pending',
  SUBMITTED = 'submitted',
  FILLED = 'filled',
  PARTIALLY_FILLED = 'partially_filled',
  REJECTED = 'rejected',
  CANCELLED = 'cancelled',
  EXPIRED = 'expired',
}

/**
 * Time in force options
 */
export enum TimeInForce {
  DAY = 'day',
  GTC = 'gtc',
  IOC = 'ioc',
  FOK = 'fok',
  GTD = 'gtd',
}

/**
 * Order book side
 */
export enum OrderBookSide {
  BID = 'bid',
  ASK = 'ask',
}

/**
 * Order book price level
 */
export interface OrderBookLevel {
  price: number;
  quantity: number;
  orders: number;
}

/**
 * Order book data
 */
export interface OrderBook {
  symbol: string;
  bids: OrderBookLevel[];
  asks: OrderBookLevel[];
  spread: number;
  spread_pct: number;
  mid_price: number;
  timestamp: string;
}

/**
 * Order entry form data
 */
export interface OrderFormData {
  symbol: string;
  direction: TradingDirection;
  order_type: OrderType;
  quantity: number;
  limit_price: number | null;
  stop_price: number | null;
  stop_loss_price: number | null;
  take_profit_price: number | null;
  time_in_force: TimeInForce;
  time_horizon: TimeHorizon;
  trailing_stop: boolean;
  trailing_distance_pct: number;
  notes: string;
}

/**
 * Order submission request
 */
export interface OrderSubmitRequest {
  symbol: string;
  direction: TradingDirection;
  order_type: OrderType;
  quantity: number;
  limit_price?: number | null;
  stop_price?: number | null;
  stop_loss_price?: number | null;
  take_profit_price?: number | null;
  time_in_force: TimeInForce;
  time_horizon?: TimeHorizon;
  trailing_stop?: boolean;
  trailing_distance_pct?: number;
  notes?: string;
}

/**
 * Complete order record
 */
export interface Order {
  order_id: string;
  account_id: string;
  symbol: string;
  direction: TradingDirection;
  order_type: OrderType;
  status: OrderStatus;

  // Quantities
  quantity: number;
  filled_quantity: number;
  remaining_quantity: number;

  // Prices
  limit_price: number | null;
  stop_price: number | null;
  average_fill_price: number | null;

  // Risk management
  stop_loss_price: number | null;
  take_profit_price: number | null;
  trailing_stop: boolean;
  trailing_distance_pct: number;

  // Execution details
  time_in_force: TimeInForce;
  time_horizon: TimeHorizon;

  // Costs
  commission: number;
  fees: number;
  total_cost: number;

  // Timing
  created_at: string;
  submitted_at: string | null;
  filled_at: string | null;
  cancelled_at: string | null;
  expires_at: string | null;

  // Metadata
  notes: string;
  rejection_reason: string | null;
  parent_order_id: string | null;
  child_order_ids: string[];
}

/**
 * Order execution details
 */
export interface OrderExecution {
  execution_id: string;
  order_id: string;
  symbol: string;
  quantity: number;
  price: number;
  commission: number;
  fees: number;
  liquidity_flag: 'added' | 'removed';
  executed_at: string;
  venue: string;
}

/**
 * Order with executions
 */
export interface OrderWithExecutions extends Order {
  executions: OrderExecution[];
  total_executions: number;
  average_execution_price: number;
  slippage: number;
  slippage_pct: number;
}

/**
 * Order filters for history queries
 */
export interface OrderFilters {
  symbols?: string[];
  statuses?: OrderStatus[];
  directions?: TradingDirection[];
  order_types?: OrderType[];
  start_date?: string;
  end_date?: string;
  min_quantity?: number;
  max_quantity?: number;
  limit?: number;
  offset?: number;
}

/**
 * Order history response
 */
export interface OrderHistory {
  orders: OrderWithExecutions[];
  total_count: number;
  page: number;
  page_size: number;
  has_more: boolean;
}

/**
 * Order preview/estimate
 */
export interface OrderPreview {
  symbol: string;
  direction: TradingDirection;
  quantity: number;
  estimated_price: number;
  estimated_total: number;
  estimated_commission: number;
  estimated_fees: number;
  buying_power_effect: number;
  margin_requirement: number;
  position_effect: 'open' | 'close' | 'increase' | 'decrease';
  warnings: string[];
}

/**
 * Trade with slippage analysis
 */
export interface TradeWithSlippage {
  execution_id: string;
  order_id: string;
  symbol: string;
  quantity: number;
  expected_price: number;
  actual_price: number;
  slippage: number;
  slippage_pct: number;
  slippage_cost: number;
  executed_at: string;
  order_type: OrderType;
}

/**
 * Slippage statistics
 */
export interface SlippageStats {
  symbol: string;
  timeframe: string;
  trades: TradeWithSlippage[];
  avg_slippage: number;
  avg_slippage_pct: number;
  total_slippage_cost: number;
  positive_slippage_count: number;
  negative_slippage_count: number;
  max_slippage: number;
  min_slippage: number;
}

/**
 * Type guard to check if order is pending
 */
export function isPendingOrder(order: Order): boolean {
  return order.status === OrderStatus.PENDING || order.status === OrderStatus.SUBMITTED;
}

/**
 * Type guard to check if order is filled
 */
export function isFilledOrder(order: Order): boolean {
  return order.status === OrderStatus.FILLED;
}

/**
 * Type guard to check if order is active
 */
export function isActiveOrder(order: Order): boolean {
  return (
    order.status === OrderStatus.PENDING ||
    order.status === OrderStatus.SUBMITTED ||
    order.status === OrderStatus.PARTIALLY_FILLED
  );
}

/**
 * Calculate order fill percentage
 */
export function getOrderFillPercentage(order: Order): number {
  if (order.quantity === 0) return 0;
  return (order.filled_quantity / order.quantity) * 100;
}

/**
 * Get order status display color
 */
export function getOrderStatusColor(status: OrderStatus): 'success' | 'warning' | 'danger' | 'info' {
  switch (status) {
    case OrderStatus.FILLED:
      return 'success';
    case OrderStatus.PARTIALLY_FILLED:
    case OrderStatus.PENDING:
    case OrderStatus.SUBMITTED:
      return 'warning';
    case OrderStatus.REJECTED:
    case OrderStatus.CANCELLED:
      return 'danger';
    case OrderStatus.EXPIRED:
      return 'info';
    default:
      return 'info';
  }
}

/**
 * Format time in force for display
 */
export function formatTimeInForce(tif: TimeInForce): string {
  const labels: Record<TimeInForce, string> = {
    [TimeInForce.DAY]: 'Day',
    [TimeInForce.GTC]: 'Good Till Cancelled',
    [TimeInForce.IOC]: 'Immediate or Cancel',
    [TimeInForce.FOK]: 'Fill or Kill',
    [TimeInForce.GTD]: 'Good Till Date',
  };
  return labels[tif];
}

/**
 * Validate order form data
 */
export function validateOrderForm(data: Partial<OrderFormData>): string[] {
  const errors: string[] = [];

  if (!data.symbol || data.symbol.trim() === '') {
    errors.push('Symbol is required');
  }

  if (!data.direction) {
    errors.push('Direction is required');
  }

  if (!data.order_type) {
    errors.push('Order type is required');
  }

  if (!data.quantity || data.quantity <= 0) {
    errors.push('Quantity must be greater than 0');
  }

  if (data.order_type === OrderType.LIMIT && (!data.limit_price || data.limit_price <= 0)) {
    errors.push('Limit price is required for limit orders');
  }

  if (data.order_type === OrderType.STOP && (!data.stop_price || data.stop_price <= 0)) {
    errors.push('Stop price is required for stop orders');
  }

  if (data.order_type === OrderType.STOP_LIMIT) {
    if (!data.limit_price || data.limit_price <= 0) {
      errors.push('Limit price is required for stop-limit orders');
    }
    if (!data.stop_price || data.stop_price <= 0) {
      errors.push('Stop price is required for stop-limit orders');
    }
  }

  if (data.stop_loss_price !== null && data.stop_loss_price !== undefined && data.stop_loss_price < 0) {
    errors.push('Stop-loss price must be positive');
  }

  if (data.take_profit_price !== null && data.take_profit_price !== undefined && data.take_profit_price < 0) {
    errors.push('Take-profit price must be positive');
  }

  if (data.trailing_stop && (!data.trailing_distance_pct || data.trailing_distance_pct <= 0 || data.trailing_distance_pct > 100)) {
    errors.push('Trailing distance must be between 0 and 100%');
  }

  return errors;
}
