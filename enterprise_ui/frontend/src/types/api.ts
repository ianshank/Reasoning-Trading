/**
 * API request and response types
 *
 * TypeScript definitions for REST API interactions
 */

import type { TradingAction, TimeHorizon } from './actions';
import type { TradingState, MarketRegime, RegimeClassification } from './trading';
import type { MCTSResult, MCTSPhase } from './mcts';
import type { Portfolio, Position } from './portfolio';

/**
 * Standard API response wrapper
 */
export interface APIResponse<T = unknown> {
  success: boolean;
  data: T | null;
  error: string | null;
  timestamp: string;
  request_id: string;
}

/**
 * Paginated API response
 */
export interface PaginatedResponse<T = unknown> {
  success: boolean;
  data: T[];
  pagination: {
    page: number;
    page_size: number;
    total_items: number;
    total_pages: number;
    has_next: boolean;
    has_prev: boolean;
  };
  error: string | null;
  timestamp: string;
}

/**
 * API error details
 */
export interface APIError {
  code: string;
  message: string;
  details: Record<string, unknown>;
  timestamp: string;
}

// ==================== Trading Endpoints ====================

/**
 * Request to get trading decision
 */
export interface GetTradingDecisionRequest {
  symbol: string;
  /** Use MCTS for decision making */
  use_mcts?: boolean;
  /** Maximum MCTS simulations */
  max_simulations?: number;
  /** Risk profile */
  risk_profile?: 'conservative' | 'moderate' | 'aggressive';
  /** Time horizon filter */
  time_horizon?: TimeHorizon;
}

/**
 * Trading decision response
 */
export interface TradingDecisionResponse {
  action: TradingAction;
  mcts_result: MCTSResult | null;
  reasoning: string;
  confidence: number;
  timestamp: string;
}

/**
 * Execute trade request
 */
export interface ExecuteTradeRequest {
  symbol: string;
  action: TradingAction;
  /** Dry run mode (don't execute) */
  dry_run?: boolean;
  /** Force execution even if risk checks fail */
  force?: boolean;
}

/**
 * Trade execution response
 */
export interface ExecuteTradeResponse {
  order_id: string;
  symbol: string;
  action: TradingAction;
  status: 'pending' | 'filled' | 'partially_filled' | 'rejected' | 'cancelled';
  filled_quantity: number;
  average_price: number;
  commission: number;
  timestamp: string;
  rejection_reason: string | null;
}

// ==================== Portfolio Endpoints ====================

/**
 * Get portfolio request
 */
export interface GetPortfolioRequest {
  /** Include historical data */
  include_history?: boolean;
  /** History days */
  history_days?: number;
}

/**
 * Portfolio response
 */
export interface PortfolioResponse {
  portfolio: Portfolio;
  timestamp: string;
}

/**
 * Get position request
 */
export interface GetPositionRequest {
  symbol: string;
}

/**
 * Position response
 */
export interface PositionResponse {
  position: Position | null;
  timestamp: string;
}

// ==================== Market Data Endpoints ====================

/**
 * Get market data request
 */
export interface GetMarketDataRequest {
  symbol: string;
  /** Time period */
  period?: '1d' | '5d' | '1mo' | '3mo' | '6mo' | '1y' | 'ytd' | 'max';
  /** Interval */
  interval?: '1m' | '5m' | '15m' | '30m' | '1h' | '1d' | '1wk' | '1mo';
  /** Include technical indicators */
  include_indicators?: boolean;
}

/**
 * Market data response
 */
export interface MarketDataResponse {
  symbol: string;
  current_price: number;
  state: TradingState;
  timestamp: string;
}

/**
 * Get regime classification request
 */
export interface GetRegimeRequest {
  symbol: string;
}

/**
 * Regime classification response
 */
export interface RegimeResponse {
  classification: RegimeClassification;
  history: Array<{
    regime: MarketRegime;
    confidence: number;
    timestamp: string;
  }>;
  timestamp: string;
}

// ==================== MCTS Endpoints ====================

/**
 * Start MCTS search request
 */
export interface StartMCTSRequest {
  symbol: string;
  initial_state: TradingState;
  max_iterations?: number;
  exploration_constant?: number;
  parallel_simulations?: number;
  use_policy_prior?: boolean;
}

/**
 * MCTS search started response
 */
export interface MCTSStartedResponse {
  search_id: string;
  status: 'started';
  timestamp: string;
}

/**
 * Get MCTS status request
 */
export interface GetMCTSStatusRequest {
  search_id: string;
}

/**
 * MCTS status response
 */
export interface MCTSStatusResponse {
  search_id: string;
  status: 'running' | 'completed' | 'failed';
  phase: MCTSPhase;
  iteration: number;
  max_iterations: number;
  progress: number;
  result: MCTSResult | null;
  error: string | null;
  timestamp: string;
}

// ==================== Analytics Endpoints ====================

/**
 * Get analytics request
 */
export interface GetAnalyticsRequest {
  /** Start date (ISO string) */
  start_date?: string;
  /** End date (ISO string) */
  end_date?: string;
  /** Metrics to include */
  metrics?: Array<
    | 'returns'
    | 'sharpe'
    | 'drawdown'
    | 'win_rate'
    | 'profit_factor'
    | 'volatility'
  >;
}

/**
 * Analytics response
 */
export interface AnalyticsResponse {
  portfolio_id: string;
  period: {
    start_date: string;
    end_date: string;
  };
  metrics: Record<string, number | null>;
  charts: {
    equity_curve: Array<{ timestamp: string; value: number }>;
    drawdown_curve: Array<{ timestamp: string; drawdown: number }>;
    returns_distribution: Array<{ bin: number; count: number }>;
  };
  timestamp: string;
}

// ==================== System Endpoints ====================

/**
 * Health check response
 */
export interface HealthResponse {
  status: 'healthy' | 'degraded' | 'unhealthy';
  version: string;
  uptime_seconds: number;
  services: {
    database: boolean;
    redis: boolean;
    alpaca: boolean;
    llm: boolean;
  };
  timestamp: string;
}

/**
 * System configuration response
 */
export interface ConfigResponse {
  trading_mode: 'paper' | 'live';
  features: {
    allow_shorts: boolean;
    enable_margin_trading: boolean;
    enable_crypto_trading: boolean;
    auto_execute_trades: boolean;
  };
  mcts: {
    max_simulations: number;
    exploration_weight: number;
    progressive_widening_alpha: number;
  };
  risk: {
    max_position_size_fraction: number;
    default_stop_loss_percent: number;
    max_daily_loss_percent: number;
  };
  timestamp: string;
}

/**
 * API rate limit info
 */
export interface RateLimitInfo {
  limit: number;
  remaining: number;
  reset_at: string;
}

// ==================== Type Guards ====================

/**
 * Type guard for successful API response
 */
export function isSuccessResponse<T>(
  response: APIResponse<T>
): response is APIResponse<T> & { success: true; data: T } {
  return response.success && response.data !== null;
}

/**
 * Type guard for error response
 */
export function isErrorResponse<T>(
  response: APIResponse<T>
): response is APIResponse<T> & { success: false; error: string } {
  return !response.success && response.error !== null;
}
