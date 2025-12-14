/**
 * Trading action types and enums
 *
 * TypeScript definitions mirroring Python models from:
 * - src/reasoning_trading/core/actions.py
 */

/**
 * Trading direction enum
 */
export enum TradingDirection {
  BUY = 'buy',
  SELL = 'sell',
  HOLD = 'hold',
  SHORT = 'short',
  /** Cover short position */
  COVER = 'cover',
}

/**
 * Trading time horizon for position management
 */
export enum TimeHorizon {
  /** 1 hour */
  SCALP = '1H',
  /** 4 hours */
  INTRADAY = '4H',
  /** 1 day */
  SWING = '1D',
  /** 1 week */
  POSITION = '1W',
  /** 1 month */
  INVESTMENT = '1M',
}

/**
 * Order type for execution
 */
export enum OrderType {
  MARKET = 'market',
  LIMIT = 'limit',
  STOP = 'stop',
  STOP_LIMIT = 'stop_limit',
}

/**
 * Continuous position size action with Kelly Criterion reference
 */
export interface PositionSizeAction {
  /** Position size as fraction of portfolio (0 to 1) */
  size_fraction: number;
  /** Fraction of Kelly optimal size (0 to 2) */
  kelly_fraction: number;
}

/**
 * Stop-loss configuration for risk management
 */
export interface StopLossAction {
  /** Stop-loss percentage (0 to 0.5) */
  stop_loss_pct: number;
  /** Take-profit percentage (0 to 1.0) */
  take_profit_pct: number | null;
  /** Enable trailing stop */
  trailing_stop: boolean;
  /** Trailing stop distance (0 to 0.2) */
  trailing_distance_pct: number;
}

/**
 * Complete trading action representation
 *
 * Combines direction, sizing, stop-loss, and timing into a single
 * action that can be executed or used in MCTS tree expansion.
 */
export interface TradingAction {
  direction: TradingDirection;
  position_size: PositionSizeAction;
  stop_loss: StopLossAction;
  time_horizon: TimeHorizon;

  // Execution parameters
  order_type: OrderType;
  limit_price: number | null;

  // Confidence and reasoning
  /** Confidence in this action (0-1) */
  confidence: number;
  /** LLM-generated reasoning */
  reasoning: string;

  // MCTS metadata (optional)
  visit_count?: number;
  value_sum?: number;
}

/**
 * Action space configuration
 */
export interface ActionSpaceConfig {
  /** Whether short selling is allowed */
  allow_shorts: boolean;
  /** Maximum position size as fraction of portfolio */
  max_position_size: number;
  /** Minimum position size */
  min_position_size: number;
  /** Stop-loss range [min, max] */
  stop_loss_range: [number, number];
  /** Alpha parameter for progressive widening */
  progressive_widening_alpha: number;
}

/**
 * Helper functions for TradingDirection
 */
export const TradingDirectionUtils = {
  /**
   * Check if this is an entry action
   */
  isEntry(direction: TradingDirection): boolean {
    return direction === TradingDirection.BUY || direction === TradingDirection.SHORT;
  },

  /**
   * Check if this is an exit action
   */
  isExit(direction: TradingDirection): boolean {
    return direction === TradingDirection.SELL || direction === TradingDirection.COVER;
  },

  /**
   * Get the opposite direction for closing positions
   */
  opposite(direction: TradingDirection): TradingDirection {
    const opposites: Record<TradingDirection, TradingDirection> = {
      [TradingDirection.BUY]: TradingDirection.SELL,
      [TradingDirection.SELL]: TradingDirection.BUY,
      [TradingDirection.SHORT]: TradingDirection.COVER,
      [TradingDirection.COVER]: TradingDirection.SHORT,
      [TradingDirection.HOLD]: TradingDirection.HOLD,
    };
    return opposites[direction];
  },
};

/**
 * Helper functions for TimeHorizon
 */
export const TimeHorizonUtils = {
  /**
   * Convert horizon to hours
   */
  toHours(horizon: TimeHorizon): number {
    const mapping: Record<TimeHorizon, number> = {
      [TimeHorizon.SCALP]: 1,
      [TimeHorizon.INTRADAY]: 4,
      [TimeHorizon.SWING]: 24,
      [TimeHorizon.POSITION]: 168,
      [TimeHorizon.INVESTMENT]: 720,
    };
    return mapping[horizon];
  },

  /**
   * Convert horizon to trading days (6.5 hours per day)
   */
  toTradingDays(horizon: TimeHorizon): number {
    return this.toHours(horizon) / 6.5;
  },
};

/**
 * Type guard to check if a value is a valid TradingDirection
 */
export function isTradingDirection(value: string): value is TradingDirection {
  return (
    value === TradingDirection.BUY ||
    value === TradingDirection.SELL ||
    value === TradingDirection.HOLD ||
    value === TradingDirection.SHORT ||
    value === TradingDirection.COVER
  );
}

/**
 * Type guard to check if a value is a valid TimeHorizon
 */
export function isTimeHorizon(value: string): value is TimeHorizon {
  return (
    value === TimeHorizon.SCALP ||
    value === TimeHorizon.INTRADAY ||
    value === TimeHorizon.SWING ||
    value === TimeHorizon.POSITION ||
    value === TimeHorizon.INVESTMENT
  );
}

/**
 * Type guard to check if a PositionSizeAction is valid
 */
export function isValidPositionSize(
  size: Partial<PositionSizeAction>
): size is PositionSizeAction {
  if (
    size.size_fraction !== undefined &&
    (size.size_fraction < 0 || size.size_fraction > 1)
  ) {
    return false;
  }

  if (
    size.kelly_fraction !== undefined &&
    (size.kelly_fraction < 0 || size.kelly_fraction > 2)
  ) {
    return false;
  }

  return true;
}

/**
 * Type guard to check if a StopLossAction is valid
 */
export function isValidStopLoss(
  stopLoss: Partial<StopLossAction>
): stopLoss is StopLossAction {
  if (
    stopLoss.stop_loss_pct !== undefined &&
    (stopLoss.stop_loss_pct < 0 || stopLoss.stop_loss_pct > 0.5)
  ) {
    return false;
  }

  if (
    stopLoss.take_profit_pct !== undefined &&
    stopLoss.take_profit_pct !== null &&
    (stopLoss.take_profit_pct < 0 || stopLoss.take_profit_pct > 1.0)
  ) {
    return false;
  }

  if (
    stopLoss.trailing_distance_pct !== undefined &&
    (stopLoss.trailing_distance_pct < 0 || stopLoss.trailing_distance_pct > 0.2)
  ) {
    return false;
  }

  return true;
}

/**
 * Calculate risk/reward ratio from stop-loss action
 */
export function calculateRiskRewardRatio(stopLoss: StopLossAction): number | null {
  if (stopLoss.take_profit_pct === null || stopLoss.stop_loss_pct === 0) {
    return null;
  }
  return stopLoss.take_profit_pct / stopLoss.stop_loss_pct;
}

/**
 * Create a default HOLD action
 */
export function createHoldAction(): TradingAction {
  return {
    direction: TradingDirection.HOLD,
    position_size: {
      size_fraction: 0.0,
      kelly_fraction: 0.0,
    },
    stop_loss: {
      stop_loss_pct: 0.05,
      take_profit_pct: null,
      trailing_stop: false,
      trailing_distance_pct: 0.03,
    },
    time_horizon: TimeHorizon.INTRADAY,
    order_type: OrderType.MARKET,
    limit_price: null,
    confidence: 1.0,
    reasoning: 'No action taken',
  };
}
