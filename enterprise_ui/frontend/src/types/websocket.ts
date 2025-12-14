/**
 * WebSocket message types
 *
 * TypeScript definitions for real-time WebSocket communication
 */

import type { TradingState, MarketRegime } from './trading';
import type { TradingAction } from './actions';
import type { MCTSPhase, MCTSNode } from './mcts';
import type { Position, Portfolio } from './portfolio';

/**
 * WebSocket message types
 */
export enum WSMessageType {
  // Connection
  CONNECT = 'connect',
  DISCONNECT = 'disconnect',
  PING = 'ping',
  PONG = 'pong',

  // Subscriptions
  SUBSCRIBE = 'subscribe',
  UNSUBSCRIBE = 'unsubscribe',

  // Market data
  MARKET_DATA = 'market_data',
  PRICE_UPDATE = 'price_update',
  REGIME_CHANGE = 'regime_change',

  // Portfolio
  PORTFOLIO_UPDATE = 'portfolio_update',
  POSITION_UPDATE = 'position_update',
  ORDER_UPDATE = 'order_update',

  // MCTS
  MCTS_STARTED = 'mcts_started',
  MCTS_PHASE_UPDATE = 'mcts_phase_update',
  MCTS_NODE_UPDATE = 'mcts_node_update',
  MCTS_COMPLETED = 'mcts_completed',
  MCTS_ERROR = 'mcts_error',

  // Trading
  TRADE_SIGNAL = 'trade_signal',
  TRADE_EXECUTED = 'trade_executed',

  // Alerts
  RISK_ALERT = 'risk_alert',
  SYSTEM_ALERT = 'system_alert',

  // Error
  ERROR = 'error',
}

/**
 * Base WebSocket message
 */
export interface WSMessage<T = unknown> {
  type: WSMessageType;
  data: T;
  timestamp: string;
  message_id: string;
}

/**
 * Subscription channels
 */
export enum WSChannel {
  MARKET_DATA = 'market_data',
  PORTFOLIO = 'portfolio',
  MCTS = 'mcts',
  TRADES = 'trades',
  ALERTS = 'alerts',
  ALL = 'all',
}

/**
 * Subscribe message
 */
export interface SubscribeMessage {
  channels: WSChannel[];
  symbols?: string[];
}

/**
 * Unsubscribe message
 */
export interface UnsubscribeMessage {
  channels: WSChannel[];
  symbols?: string[];
}

// ==================== Market Data Messages ====================

/**
 * Market data update
 */
export interface MarketDataUpdate {
  symbol: string;
  state: TradingState;
  timestamp: string;
}

/**
 * Price update (lightweight)
 */
export interface PriceUpdate {
  symbol: string;
  price: number;
  change: number;
  change_pct: number;
  volume: number;
  timestamp: string;
}

/**
 * Regime change notification
 */
export interface RegimeChangeUpdate {
  symbol: string;
  old_regime: MarketRegime;
  new_regime: MarketRegime;
  confidence: number;
  timestamp: string;
}

// ==================== Portfolio Messages ====================

/**
 * Portfolio update
 */
export interface PortfolioUpdate {
  portfolio: Portfolio;
  changes: {
    total_value_change: number;
    pnl_change: number;
    new_positions: string[];
    closed_positions: string[];
  };
  timestamp: string;
}

/**
 * Position update
 */
export interface PositionUpdate {
  position: Position;
  change_type: 'opened' | 'updated' | 'closed';
  timestamp: string;
}

/**
 * Order update
 */
export interface OrderUpdate {
  order_id: string;
  symbol: string;
  status: 'pending' | 'filled' | 'partially_filled' | 'rejected' | 'cancelled';
  filled_quantity: number;
  remaining_quantity: number;
  average_price: number;
  timestamp: string;
}

// ==================== MCTS Messages ====================

/**
 * MCTS search started
 */
export interface MCTSStartedUpdate {
  search_id: string;
  symbol: string;
  max_iterations: number;
  timestamp: string;
}

/**
 * MCTS phase update
 */
export interface MCTSPhaseUpdate {
  search_id: string;
  phase: MCTSPhase;
  iteration: number;
  max_iterations: number;
  progress: number;
  phase_time_ms: number;
  timestamp: string;
}

/**
 * MCTS node update
 */
export interface MCTSNodeUpdate {
  search_id: string;
  node: MCTSNode;
  update_type: 'created' | 'expanded' | 'backpropagated';
  timestamp: string;
}

/**
 * MCTS search completed
 */
export interface MCTSCompletedUpdate {
  search_id: string;
  best_action: TradingAction;
  total_simulations: number;
  computation_time_ms: number;
  confidence: number;
  timestamp: string;
}

/**
 * MCTS error
 */
export interface MCTSErrorUpdate {
  search_id: string;
  error: string;
  phase: MCTSPhase;
  iteration: number;
  timestamp: string;
}

// ==================== Trading Messages ====================

/**
 * Trade signal
 */
export interface TradeSignalUpdate {
  symbol: string;
  action: TradingAction;
  confidence: number;
  reasoning: string;
  source: 'mcts' | 'analyst' | 'manual';
  timestamp: string;
}

/**
 * Trade executed
 */
export interface TradeExecutedUpdate {
  order_id: string;
  symbol: string;
  action: TradingAction;
  filled_quantity: number;
  average_price: number;
  total_cost: number;
  commission: number;
  timestamp: string;
}

// ==================== Alert Messages ====================

/**
 * Risk alert severity
 */
export enum AlertSeverity {
  INFO = 'info',
  WARNING = 'warning',
  CRITICAL = 'critical',
}

/**
 * Risk alert
 */
export interface RiskAlertUpdate {
  severity: AlertSeverity;
  alert_type:
    | 'stop_loss_hit'
    | 'margin_call'
    | 'max_drawdown'
    | 'position_limit'
    | 'daily_loss_limit';
  message: string;
  symbol: string | null;
  action_required: boolean;
  details: Record<string, unknown>;
  timestamp: string;
}

/**
 * System alert
 */
export interface SystemAlertUpdate {
  severity: AlertSeverity;
  alert_type: 'api_error' | 'connection_lost' | 'service_degraded' | 'maintenance';
  message: string;
  action_required: boolean;
  timestamp: string;
}

// ==================== Connection State ====================

/**
 * WebSocket connection state
 */
export enum WSConnectionState {
  CONNECTING = 'connecting',
  CONNECTED = 'connected',
  RECONNECTING = 'reconnecting',
  DISCONNECTED = 'disconnected',
  ERROR = 'error',
}

/**
 * Connection status
 */
export interface WSConnectionStatus {
  state: WSConnectionState;
  connected_at: string | null;
  last_ping: string | null;
  latency_ms: number | null;
  subscribed_channels: WSChannel[];
  error: string | null;
}

// ==================== Type Guards ====================

/**
 * Type guard for WebSocket message
 */
export function isWSMessage<T>(
  message: unknown,
  type: WSMessageType
): message is WSMessage<T> {
  return (
    typeof message === 'object' &&
    message !== null &&
    'type' in message &&
    message.type === type &&
    'data' in message
  );
}

/**
 * Parse WebSocket message
 */
export function parseWSMessage(data: string): WSMessage | null {
  try {
    const parsed = JSON.parse(data);
    if (
      parsed &&
      typeof parsed === 'object' &&
      'type' in parsed &&
      'data' in parsed &&
      'timestamp' in parsed
    ) {
      return parsed as WSMessage;
    }
    return null;
  } catch {
    return null;
  }
}

/**
 * Create WebSocket message
 */
export function createWSMessage<T>(
  type: WSMessageType,
  data: T,
  messageId?: string
): WSMessage<T> {
  return {
    type,
    data,
    timestamp: new Date().toISOString(),
    message_id: messageId || crypto.randomUUID(),
  };
}
