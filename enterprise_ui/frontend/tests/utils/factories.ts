/**
 * Mock Data Factories
 *
 * Factories for generating realistic test data using faker
 */

import { faker } from '@faker-js/faker'
import type { Portfolio, Position, PositionStatus, PositionSide } from '../../src/types/portfolio'
import type { Order } from '../../src/types/orders'

/**
 * Create a mock position
 */
export function createMockPosition(overrides?: Partial<Position>): Position {
  const symbol = overrides?.symbol || faker.string.alpha({ length: 4, casing: 'upper' })
  const quantity = overrides?.quantity || faker.number.int({ min: 1, max: 100 })
  const entryPrice = faker.number.float({ min: 50, max: 500, fractionDigits: 2 })
  const currentPrice = faker.number.float({ min: 50, max: 500, fractionDigits: 2 })
  const costBasis = entryPrice * quantity
  const marketValue = currentPrice * quantity
  const unrealizedPnl = marketValue - costBasis

  return {
    symbol,
    position_id: faker.string.uuid(),
    side: 'long' as PositionSide,
    status: 'open' as PositionStatus,
    quantity,
    entry_price: entryPrice,
    current_price: currentPrice,
    cost_basis: costBasis,
    market_value: marketValue,
    unrealized_pnl: unrealizedPnl,
    unrealized_pnl_pct: (unrealizedPnl / costBasis) * 100,
    realized_pnl: 0,
    stop_loss_price: null,
    take_profit_price: null,
    trailing_stop: false,
    trailing_distance_pct: 0,
    entry_time: faker.date.recent({ days: 30 }).toISOString(),
    exit_time: null,
    time_horizon: 'medium',
    entry_action: {
      action_type: 'buy',
      symbol,
      quantity,
      price: entryPrice,
      reasoning: 'Test position',
      confidence: 0.8,
    },
    notes: '',
    ...overrides,
  }
}

/**
 * Create a mock portfolio
 */
export function createMockPortfolio(overrides?: Partial<Portfolio>): Portfolio {
  const positions = overrides?.positions || [
    createMockPosition({ symbol: 'AAPL' }),
    createMockPosition({ symbol: 'GOOGL' }),
    createMockPosition({ symbol: 'MSFT' }),
  ]

  const totalValue = faker.number.float({ min: 50000, max: 500000, fractionDigits: 2 })
  const cashBalance = faker.number.float({ min: 10000, max: 100000, fractionDigits: 2 })
  const unrealizedPnl = positions.reduce((sum, pos) => sum + pos.unrealized_pnl, 0)

  return {
    portfolio_id: faker.string.uuid(),
    account_id: 'test-account',
    total_value: totalValue,
    cash_balance: cashBalance,
    buying_power: cashBalance * 2,
    positions,
    position_count: positions.length,
    long_positions: positions.filter((p) => p.side === 'long').length,
    short_positions: positions.filter((p) => p.side === 'short').length,
    unrealized_pnl: unrealizedPnl,
    realized_pnl_today: faker.number.float({ min: -1000, max: 1000, fractionDigits: 2 }),
    realized_pnl_total: faker.number.float({ min: -5000, max: 5000, fractionDigits: 2 }),
    risk_metrics: {
      daily_var_95: faker.number.float({ min: -5000, max: -1000, fractionDigits: 2 }),
      daily_var_99: faker.number.float({ min: -8000, max: -2000, fractionDigits: 2 }),
      max_drawdown: faker.number.float({ min: 0.05, max: 0.20, fractionDigits: 4 }),
      current_drawdown: faker.number.float({ min: 0, max: 0.10, fractionDigits: 4 }),
      drawdown_start: faker.date.recent({ days: 10 }).toISOString(),
      portfolio_volatility: faker.number.float({ min: 0.10, max: 0.30, fractionDigits: 4 }),
      sharpe_ratio: faker.number.float({ min: 0.5, max: 2.5, fractionDigits: 2 }),
      sortino_ratio: faker.number.float({ min: 0.8, max: 3.0, fractionDigits: 2 }),
      largest_position_pct: faker.number.float({ min: 0.10, max: 0.25, fractionDigits: 4 }),
      top5_concentration: faker.number.float({ min: 0.40, max: 0.80, fractionDigits: 4 }),
      herfindahl_index: faker.number.float({ min: 0.10, max: 0.30, fractionDigits: 4 }),
      leverage_ratio: faker.number.float({ min: 1.0, max: 2.0, fractionDigits: 2 }),
      margin_utilization: faker.number.float({ min: 0.20, max: 0.60, fractionDigits: 4 }),
    },
    performance_metrics: {
      total_return: faker.number.float({ min: -10000, max: 20000, fractionDigits: 2 }),
      total_return_pct: faker.number.float({ min: -20, max: 40, fractionDigits: 2 }),
      today_return: faker.number.float({ min: -2000, max: 2000, fractionDigits: 2 }),
      today_return_pct: faker.number.float({ min: -5, max: 5, fractionDigits: 2 }),
      day_return_pct: faker.number.float({ min: -5, max: 5, fractionDigits: 2 }),
      week_return_pct: faker.number.float({ min: -10, max: 10, fractionDigits: 2 }),
      month_return_pct: faker.number.float({ min: -15, max: 15, fractionDigits: 2 }),
      year_return_pct: faker.number.float({ min: -30, max: 50, fractionDigits: 2 }),
      win_rate: faker.number.float({ min: 0.40, max: 0.70, fractionDigits: 2 }),
      profit_factor: faker.number.float({ min: 1.0, max: 3.0, fractionDigits: 2 }),
      avg_win: faker.number.float({ min: 500, max: 2000, fractionDigits: 2 }),
      avg_loss: faker.number.float({ min: -1000, max: -300, fractionDigits: 2 }),
      largest_win: faker.number.float({ min: 2000, max: 5000, fractionDigits: 2 }),
      largest_loss: faker.number.float({ min: -3000, max: -1000, fractionDigits: 2 }),
      total_trades: faker.number.int({ min: 50, max: 200 }),
      winning_trades: faker.number.int({ min: 25, max: 120 }),
      losing_trades: faker.number.int({ min: 20, max: 80 }),
      avg_trade_duration_hours: faker.number.float({ min: 12, max: 168, fractionDigits: 1 }),
    },
    allocation: {
      cash: cashBalance,
      stocks: totalValue - cashBalance,
      crypto: 0,
      options: 0,
      other: 0,
    },
    margin_used: faker.number.float({ min: 5000, max: 30000, fractionDigits: 2 }),
    margin_available: faker.number.float({ min: 20000, max: 70000, fractionDigits: 2 }),
    maintenance_margin: faker.number.float({ min: 3000, max: 15000, fractionDigits: 2 }),
    last_updated: new Date().toISOString(),
    currency: 'USD',
    ...overrides,
  }
}

/**
 * Create a mock order
 */
export function createMockOrder(overrides?: Partial<Order>): Order {
  const symbol = overrides?.symbol || faker.string.alpha({ length: 4, casing: 'upper' })
  const quantity = overrides?.quantity || faker.number.int({ min: 1, max: 100 })
  const limitPrice = faker.number.float({ min: 50, max: 500, fractionDigits: 2 })

  return {
    order_id: faker.string.uuid(),
    client_order_id: `client-${faker.string.alphanumeric(10)}`,
    symbol,
    side: faker.helpers.arrayElement(['buy', 'sell']),
    order_type: 'limit',
    time_in_force: 'gtc',
    quantity,
    limit_price: limitPrice,
    stop_price: null,
    filled_qty: 0,
    filled_avg_price: null,
    status: 'pending',
    submitted_at: faker.date.recent({ days: 1 }).toISOString(),
    filled_at: null,
    cancelled_at: null,
    expired_at: null,
    failed_at: null,
    replaced_at: null,
    replaced_by: null,
    replaces: null,
    ...overrides,
  }
}

/**
 * Create mock market data
 */
export function createMockMarketData(symbol: string) {
  const lastPrice = faker.number.float({ min: 50, max: 500, fractionDigits: 2 })
  const change = faker.number.float({ min: -10, max: 10, fractionDigits: 2 })

  return {
    symbol,
    last_price: lastPrice,
    bid: lastPrice - 0.05,
    ask: lastPrice + 0.05,
    bid_size: faker.number.int({ min: 100, max: 1000 }),
    ask_size: faker.number.int({ min: 100, max: 1000 }),
    volume: faker.number.int({ min: 1000000, max: 50000000 }),
    open: lastPrice - change,
    high: lastPrice + Math.abs(change),
    low: lastPrice - Math.abs(change),
    previous_close: lastPrice - change,
    change,
    change_percent: (change / (lastPrice - change)) * 100,
    timestamp: new Date().toISOString(),
  }
}

/**
 * Create mock MCTS tree data
 */
export function createMockMCTSTree() {
  return {
    root: {
      id: 'root',
      state: null,
      action: null,
      parent_id: null,
      children_ids: ['node-1', 'node-2'],
      messages: [],
      reflection: '',
      value: 0.5,
      visits: 100,
      value_sum: 50,
      q_value: 0.5,
      prior: 1.0,
      is_solved: false,
      is_terminal: false,
      depth: 0,
      created_at: new Date().toISOString(),
    },
    nodes: {
      root: {
        id: 'root',
        state: null,
        action: null,
        parent_id: null,
        children_ids: ['node-1', 'node-2'],
        messages: [],
        reflection: '',
        value: 0.5,
        visits: 100,
        value_sum: 50,
        q_value: 0.5,
        prior: 1.0,
        is_solved: false,
        is_terminal: false,
        depth: 0,
        created_at: new Date().toISOString(),
      },
    },
    total_simulations: 100,
    start_time: new Date().toISOString(),
    end_time: null,
  }
}
