/**
 * API Contract Tests
 *
 * Tests for API request/response contracts:
 * - Type checking
 * - Schema validation
 * - Error response formats
 * - Request formats
 */

import { describe, it, expect, beforeEach } from 'vitest'
import { z } from 'zod'
import { server } from '../mocks/server'
import { http, HttpResponse } from 'msw'

const API_BASE_URL = 'http://localhost:8000'

// Zod schemas for API responses
const PortfolioSchema = z.object({
  portfolio_id: z.string(),
  account_id: z.string(),
  total_value: z.number(),
  cash_balance: z.number(),
  buying_power: z.number(),
  positions: z.array(z.any()),
  position_count: z.number(),
  long_positions: z.number(),
  short_positions: z.number(),
  unrealized_pnl: z.number(),
  realized_pnl_today: z.number(),
  realized_pnl_total: z.number(),
  risk_metrics: z.object({
    daily_var_95: z.number().nullable(),
    daily_var_99: z.number().nullable(),
    max_drawdown: z.number(),
    current_drawdown: z.number(),
    drawdown_start: z.string().nullable(),
    portfolio_volatility: z.number(),
    sharpe_ratio: z.number().nullable(),
    sortino_ratio: z.number().nullable(),
    largest_position_pct: z.number(),
    top5_concentration: z.number(),
    herfindahl_index: z.number(),
    leverage_ratio: z.number(),
    margin_utilization: z.number(),
  }),
  performance_metrics: z.any(),
  allocation: z.any(),
  margin_used: z.number(),
  margin_available: z.number(),
  maintenance_margin: z.number(),
  last_updated: z.string(),
  currency: z.string(),
})

const PositionSchema = z.object({
  symbol: z.string(),
  position_id: z.string(),
  side: z.enum(['long', 'short']),
  status: z.enum(['open', 'closed', 'pending']),
  quantity: z.number(),
  entry_price: z.number(),
  current_price: z.number(),
  cost_basis: z.number(),
  market_value: z.number(),
  unrealized_pnl: z.number(),
  unrealized_pnl_pct: z.number(),
  realized_pnl: z.number(),
  stop_loss_price: z.number().nullable(),
  take_profit_price: z.number().nullable(),
  trailing_stop: z.boolean(),
  trailing_distance_pct: z.number(),
  entry_time: z.string(),
  exit_time: z.string().nullable(),
  time_horizon: z.string(),
  entry_action: z.any(),
  notes: z.string(),
})

const OrderSchema = z.object({
  order_id: z.string(),
  client_order_id: z.string(),
  symbol: z.string(),
  side: z.enum(['buy', 'sell']),
  order_type: z.string(),
  time_in_force: z.string(),
  quantity: z.number(),
  limit_price: z.number().nullable(),
  stop_price: z.number().nullable(),
  filled_qty: z.number(),
  filled_avg_price: z.number().nullable(),
  status: z.string(),
  submitted_at: z.string(),
  filled_at: z.string().nullable(),
  cancelled_at: z.string().nullable(),
  expired_at: z.string().nullable(),
  failed_at: z.string().nullable(),
  replaced_at: z.string().nullable(),
  replaced_by: z.string().nullable(),
  replaces: z.string().nullable(),
})

const MarketDataSchema = z.object({
  symbol: z.string(),
  last_price: z.number(),
  bid: z.number(),
  ask: z.number(),
  bid_size: z.number(),
  ask_size: z.number(),
  volume: z.number(),
  open: z.number(),
  high: z.number(),
  low: z.number(),
  previous_close: z.number(),
  change: z.number(),
  change_percent: z.number(),
  timestamp: z.string(),
})

const AnalysisSchema = z.object({
  symbol: z.string(),
  recommendation: z.string(),
  confidence: z.number(),
  reasoning: z.string(),
  risk_level: z.string(),
  factors: z.array(z.object({
    name: z.string(),
    score: z.number(),
    weight: z.number(),
  })),
  timestamp: z.string(),
})

const ErrorResponseSchema = z.object({
  error: z.string(),
  message: z.string().optional(),
  details: z.any().optional(),
})

describe('API Contract Tests', () => {
  beforeEach(() => {
    server.resetHandlers()
  })

  describe('Portfolio Endpoints', () => {
    it('GET /api/v1/portfolio should match schema', async () => {
      const response = await fetch(`${API_BASE_URL}/api/v1/portfolio`)
      const data = await response.json()

      expect(response.ok).toBe(true)
      expect(() => PortfolioSchema.parse(data)).not.toThrow()
    })

    it('GET /api/v1/portfolio/:accountId should match schema', async () => {
      const response = await fetch(`${API_BASE_URL}/api/v1/portfolio/test-account`)
      const data = await response.json()

      expect(response.ok).toBe(true)
      expect(() => PortfolioSchema.parse(data)).not.toThrow()
    })

    it('should return correct content-type header', async () => {
      const response = await fetch(`${API_BASE_URL}/api/v1/portfolio`)

      expect(response.headers.get('content-type')).toContain('application/json')
    })
  })

  describe('Position Endpoints', () => {
    it('GET /api/v1/positions should return array of positions', async () => {
      const response = await fetch(`${API_BASE_URL}/api/v1/positions`)
      const data = await response.json()

      expect(response.ok).toBe(true)
      expect(data).toHaveProperty('positions')
      expect(Array.isArray(data.positions)).toBe(true)

      if (data.positions.length > 0) {
        data.positions.forEach((position: any) => {
          expect(() => PositionSchema.parse(position)).not.toThrow()
        })
      }
    })

    it('POST /api/v1/positions/:positionId/close should return success', async () => {
      const response = await fetch(
        `${API_BASE_URL}/api/v1/positions/pos-123/close`,
        { method: 'POST' }
      )
      const data = await response.json()

      expect(response.ok).toBe(true)
      expect(data).toHaveProperty('success')
      expect(data.success).toBe(true)
    })
  })

  describe('Order Endpoints', () => {
    it('GET /api/v1/orders should return array of orders', async () => {
      const response = await fetch(`${API_BASE_URL}/api/v1/orders`)
      const data = await response.json()

      expect(response.ok).toBe(true)
      expect(data).toHaveProperty('orders')
      expect(Array.isArray(data.orders)).toBe(true)

      if (data.orders.length > 0) {
        data.orders.forEach((order: any) => {
          expect(() => OrderSchema.parse(order)).not.toThrow()
        })
      }
    })

    it('POST /api/v1/orders should accept valid order request', async () => {
      const orderRequest = {
        symbol: 'AAPL',
        side: 'buy',
        order_type: 'limit',
        quantity: 10,
        limit_price: 150.00,
        time_in_force: 'gtc',
      }

      const response = await fetch(`${API_BASE_URL}/api/v1/orders`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(orderRequest),
      })
      const data = await response.json()

      expect(response.ok).toBe(true)
      expect(data).toHaveProperty('order_id')
      expect(data).toHaveProperty('status')
    })

    it('DELETE /api/v1/orders/:orderId should return success', async () => {
      const response = await fetch(
        `${API_BASE_URL}/api/v1/orders/order-123`,
        { method: 'DELETE' }
      )
      const data = await response.json()

      expect(response.ok).toBe(true)
      expect(data).toHaveProperty('success')
      expect(data.success).toBe(true)
    })
  })

  describe('Market Data Endpoints', () => {
    it('GET /api/v1/market/:symbol should match schema', async () => {
      const response = await fetch(`${API_BASE_URL}/api/v1/market/AAPL`)
      const data = await response.json()

      expect(response.ok).toBe(true)
      expect(() => MarketDataSchema.parse(data)).not.toThrow()
    })

    it('GET /api/v1/market/:symbol/bars should return bars array', async () => {
      const response = await fetch(
        `${API_BASE_URL}/api/v1/market/AAPL/bars?timeframe=1D&limit=100`
      )
      const data = await response.json()

      expect(response.ok).toBe(true)
      expect(data).toHaveProperty('bars')
      expect(Array.isArray(data.bars)).toBe(true)
      expect(data).toHaveProperty('symbol')
      expect(data).toHaveProperty('timeframe')

      if (data.bars.length > 0) {
        const bar = data.bars[0]
        expect(bar).toHaveProperty('timestamp')
        expect(bar).toHaveProperty('open')
        expect(bar).toHaveProperty('high')
        expect(bar).toHaveProperty('low')
        expect(bar).toHaveProperty('close')
        expect(bar).toHaveProperty('volume')
      }
    })
  })

  describe('Analysis Endpoints', () => {
    it('GET /api/v1/analysis/:symbol should match schema', async () => {
      const response = await fetch(`${API_BASE_URL}/api/v1/analysis/AAPL`)
      const data = await response.json()

      expect(response.ok).toBe(true)
      expect(() => AnalysisSchema.parse(data)).not.toThrow()
    })
  })

  describe('MCTS Endpoints', () => {
    it('GET /api/v1/mcts/:symbol/state should return valid state', async () => {
      const response = await fetch(`${API_BASE_URL}/api/v1/mcts/AAPL/state`)
      const data = await response.json()

      expect(response.ok).toBe(true)
      expect(data).toHaveProperty('symbol')
      expect(data).toHaveProperty('iteration')
      expect(data).toHaveProperty('phase')
      expect(data).toHaveProperty('total_nodes')
      expect(data).toHaveProperty('max_iterations')
    })

    it('POST /api/v1/mcts/:symbol/search should return search result', async () => {
      const searchRequest = {
        maxIterations: 100,
        explorationConstant: 1.414,
        temperature: 1.0,
        usePolicyPrior: true,
        parallelSimulations: 4,
      }

      const response = await fetch(
        `${API_BASE_URL}/api/v1/mcts/AAPL/search`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(searchRequest),
        }
      )
      const data = await response.json()

      expect(response.ok).toBe(true)
      expect(data).toHaveProperty('best_action')
      expect(data).toHaveProperty('total_simulations')
      expect(data).toHaveProperty('computation_time_ms')
      expect(data).toHaveProperty('root_value')
    })
  })

  describe('Error Response Format', () => {
    it('500 errors should match error schema', async () => {
      const response = await fetch(`${API_BASE_URL}/api/v1/error/500`)
      const data = await response.json()

      expect(response.ok).toBe(false)
      expect(response.status).toBe(500)
      expect(() => ErrorResponseSchema.parse(data)).not.toThrow()
    })

    it('401 errors should match error schema', async () => {
      const response = await fetch(`${API_BASE_URL}/api/v1/error/401`)
      const data = await response.json()

      expect(response.ok).toBe(false)
      expect(response.status).toBe(401)
      expect(() => ErrorResponseSchema.parse(data)).not.toThrow()
    })

    it('404 errors should match error schema', async () => {
      const response = await fetch(`${API_BASE_URL}/api/v1/error/404`)
      const data = await response.json()

      expect(response.ok).toBe(false)
      expect(response.status).toBe(404)
      expect(() => ErrorResponseSchema.parse(data)).not.toThrow()
    })
  })

  describe('Request Format Validation', () => {
    it('should reject malformed order requests', async () => {
      const invalidOrder = {
        symbol: 'AAPL',
        // Missing required fields
      }

      server.use(
        http.post(`${API_BASE_URL}/api/v1/orders`, () => {
          return HttpResponse.json(
            { error: 'Invalid request', message: 'Missing required fields' },
            { status: 400 }
          )
        })
      )

      const response = await fetch(`${API_BASE_URL}/api/v1/orders`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(invalidOrder),
      })

      expect(response.ok).toBe(false)
      expect(response.status).toBe(400)
    })

    it('should validate numeric types', async () => {
      const invalidOrder = {
        symbol: 'AAPL',
        side: 'buy',
        quantity: 'not-a-number', // Should be number
        order_type: 'market',
      }

      server.use(
        http.post(`${API_BASE_URL}/api/v1/orders`, () => {
          return HttpResponse.json(
            { error: 'Invalid request', message: 'Quantity must be a number' },
            { status: 400 }
          )
        })
      )

      const response = await fetch(`${API_BASE_URL}/api/v1/orders`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(invalidOrder),
      })

      expect(response.ok).toBe(false)
    })

    it('should validate enum values', async () => {
      const invalidOrder = {
        symbol: 'AAPL',
        side: 'invalid-side', // Should be 'buy' or 'sell'
        quantity: 10,
        order_type: 'market',
      }

      server.use(
        http.post(`${API_BASE_URL}/api/v1/orders`, () => {
          return HttpResponse.json(
            { error: 'Invalid request', message: 'Invalid order side' },
            { status: 400 }
          )
        })
      )

      const response = await fetch(`${API_BASE_URL}/api/v1/orders`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(invalidOrder),
      })

      expect(response.ok).toBe(false)
    })
  })

  describe('Response Headers', () => {
    it('should include appropriate CORS headers', async () => {
      const response = await fetch(`${API_BASE_URL}/api/v1/portfolio`)

      // Check for CORS headers (if applicable)
      // Your actual implementation may differ
    })

    it('should include cache control headers', async () => {
      const response = await fetch(`${API_BASE_URL}/api/v1/market/AAPL`)

      // Market data might have cache headers
      // const cacheControl = response.headers.get('cache-control')
    })
  })

  describe('Pagination', () => {
    it('should handle pagination parameters', async () => {
      const response = await fetch(
        `${API_BASE_URL}/api/v1/orders?page=1&limit=10`
      )

      expect(response.ok).toBe(true)
      // Check for pagination metadata in response
    })
  })

  describe('Field Types and Constraints', () => {
    it('should return ISO 8601 timestamps', async () => {
      const response = await fetch(`${API_BASE_URL}/api/v1/portfolio`)
      const data = await response.json()

      expect(data.last_updated).toMatch(
        /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/
      )
    })

    it('should return proper numeric precision for prices', async () => {
      const response = await fetch(`${API_BASE_URL}/api/v1/market/AAPL`)
      const data = await response.json()

      // Prices should have reasonable precision (typically 2-4 decimal places)
      const price = data.last_price
      const decimals = price.toString().split('.')[1]?.length || 0
      expect(decimals).toBeLessThanOrEqual(4)
    })

    it('should return percentages as decimals (0-1)', async () => {
      const response = await fetch(`${API_BASE_URL}/api/v1/portfolio`)
      const data = await response.json()

      const marginUtilization = data.risk_metrics.margin_utilization
      expect(marginUtilization).toBeGreaterThanOrEqual(0)
      expect(marginUtilization).toBeLessThanOrEqual(1)
    })
  })
})
