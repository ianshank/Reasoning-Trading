/**
 * MSW Mock Handlers
 *
 * Defines mock API responses for all backend endpoints.
 * Uses faker for generating realistic test data.
 */

import { http, HttpResponse, delay } from 'msw'
import { createMockPortfolio, createMockPosition, createMockOrder, createMockMarketData } from '../utils/factories'

const API_BASE_URL = 'http://localhost:8000'

export const handlers = [
  // Portfolio endpoints
  http.get(`${API_BASE_URL}/api/v1/portfolio`, async () => {
    await delay(100) // Simulate network delay
    return HttpResponse.json(createMockPortfolio())
  }),

  http.get(`${API_BASE_URL}/api/v1/portfolio/:accountId`, async ({ params }) => {
    await delay(100)
    return HttpResponse.json(createMockPortfolio({ account_id: params.accountId as string }))
  }),

  // Positions endpoints
  http.get(`${API_BASE_URL}/api/v1/positions`, async () => {
    await delay(100)
    return HttpResponse.json({
      positions: [
        createMockPosition({ symbol: 'AAPL' }),
        createMockPosition({ symbol: 'GOOGL' }),
        createMockPosition({ symbol: 'MSFT' }),
      ],
    })
  }),

  http.post(`${API_BASE_URL}/api/v1/positions/:positionId/close`, async ({ params }) => {
    await delay(100)
    return HttpResponse.json({
      success: true,
      position_id: params.positionId,
      message: 'Position closed successfully',
    })
  }),

  // Orders endpoints
  http.get(`${API_BASE_URL}/api/v1/orders`, async ({ request }) => {
    const url = new URL(request.url)
    const status = url.searchParams.get('status')

    await delay(100)
    return HttpResponse.json({
      orders: [
        createMockOrder({ status: status || 'pending' }),
        createMockOrder({ status: status || 'pending' }),
      ],
    })
  }),

  http.post(`${API_BASE_URL}/api/v1/orders`, async ({ request }) => {
    const body = await request.json()
    await delay(100)

    return HttpResponse.json({
      order_id: `order-${Date.now()}`,
      ...body,
      status: 'pending',
      created_at: new Date().toISOString(),
    })
  }),

  http.delete(`${API_BASE_URL}/api/v1/orders/:orderId`, async ({ params }) => {
    await delay(100)
    return HttpResponse.json({
      success: true,
      order_id: params.orderId,
      message: 'Order cancelled successfully',
    })
  }),

  // Market data endpoints
  http.get(`${API_BASE_URL}/api/v1/market/:symbol`, async ({ params }) => {
    await delay(100)
    return HttpResponse.json(createMockMarketData(params.symbol as string))
  }),

  http.get(`${API_BASE_URL}/api/v1/market/:symbol/bars`, async ({ params, request }) => {
    const url = new URL(request.url)
    const timeframe = url.searchParams.get('timeframe') || '1D'
    const limit = parseInt(url.searchParams.get('limit') || '100')

    await delay(100)
    const bars = Array.from({ length: limit }, (_, i) => ({
      timestamp: new Date(Date.now() - i * 24 * 60 * 60 * 1000).toISOString(),
      open: 150 + Math.random() * 10,
      high: 155 + Math.random() * 10,
      low: 145 + Math.random() * 10,
      close: 150 + Math.random() * 10,
      volume: Math.floor(1000000 + Math.random() * 500000),
    }))

    return HttpResponse.json({
      symbol: params.symbol,
      timeframe,
      bars: bars.reverse(),
    })
  }),

  // MCTS endpoints
  http.get(`${API_BASE_URL}/api/v1/mcts/:symbol/state`, async ({ params }) => {
    await delay(100)
    return HttpResponse.json({
      symbol: params.symbol,
      iteration: 0,
      phase: 'selection',
      total_nodes: 1,
      max_iterations: 100,
      exploration_constant: 1.414,
    })
  }),

  http.post(`${API_BASE_URL}/api/v1/mcts/:symbol/search`, async ({ request, params }) => {
    const body = await request.json()
    await delay(500) // Longer delay for search operations

    return HttpResponse.json({
      best_action: {
        action_type: 'buy',
        symbol: params.symbol,
        quantity: 10,
        confidence: 0.85,
      },
      total_simulations: body.maxIterations || 100,
      computation_time_ms: 450,
      root_value: 0.75,
    })
  }),

  // Analysis endpoints
  http.get(`${API_BASE_URL}/api/v1/analysis/:symbol`, async ({ params }) => {
    await delay(200)
    return HttpResponse.json({
      symbol: params.symbol,
      recommendation: 'BUY',
      confidence: 0.82,
      reasoning: 'Strong technical indicators and positive sentiment',
      risk_level: 'medium',
      factors: [
        { name: 'Technical Analysis', score: 0.85, weight: 0.4 },
        { name: 'Fundamental Analysis', score: 0.78, weight: 0.3 },
        { name: 'Sentiment Analysis', score: 0.83, weight: 0.3 },
      ],
      timestamp: new Date().toISOString(),
    })
  }),

  // Regime detection endpoints
  http.get(`${API_BASE_URL}/api/v1/regime/current`, async () => {
    await delay(100)
    return HttpResponse.json({
      regime: 'bull_normal',
      confidence: 0.87,
      indicators: {
        trend: 'bullish',
        volatility: 'normal',
        volume: 'high',
      },
      transition_probability: {
        bull_normal: 0.70,
        bull_volatile: 0.15,
        bear_normal: 0.10,
        bear_volatile: 0.05,
      },
      timestamp: new Date().toISOString(),
    })
  }),

  // Risk metrics endpoints
  http.get(`${API_BASE_URL}/api/v1/risk/metrics`, async () => {
    await delay(100)
    return HttpResponse.json({
      daily_var_95: -2500.00,
      daily_var_99: -4200.00,
      max_drawdown: 0.12,
      current_drawdown: 0.03,
      portfolio_volatility: 0.18,
      sharpe_ratio: 1.45,
      sortino_ratio: 1.82,
      largest_position_pct: 0.15,
      top5_concentration: 0.52,
      leverage_ratio: 1.2,
      margin_utilization: 0.35,
    })
  }),

  // Account endpoints
  http.get(`${API_BASE_URL}/api/v1/account`, async () => {
    await delay(100)
    return HttpResponse.json({
      account_id: 'test-account',
      account_number: 'ACC123456',
      status: 'active',
      buying_power: 50000.00,
      cash: 25000.00,
      portfolio_value: 100000.00,
      equity: 100000.00,
      currency: 'USD',
      pattern_day_trader: false,
    })
  }),

  // Health check
  http.get(`${API_BASE_URL}/health`, async () => {
    return HttpResponse.json({
      status: 'healthy',
      timestamp: new Date().toISOString(),
    })
  }),

  // Error scenarios - can be used in specific tests
  http.get(`${API_BASE_URL}/api/v1/error/500`, async () => {
    return HttpResponse.json(
      { error: 'Internal Server Error', message: 'Something went wrong' },
      { status: 500 }
    )
  }),

  http.get(`${API_BASE_URL}/api/v1/error/401`, async () => {
    return HttpResponse.json(
      { error: 'Unauthorized', message: 'Invalid credentials' },
      { status: 401 }
    )
  }),

  http.get(`${API_BASE_URL}/api/v1/error/404`, async () => {
    return HttpResponse.json(
      { error: 'Not Found', message: 'Resource not found' },
      { status: 404 }
    )
  }),
]

// Helper to create custom handlers for specific tests
export const createErrorHandler = (endpoint: string, status: number, message: string) => {
  return http.get(endpoint, async () => {
    return HttpResponse.json(
      { error: 'Error', message },
      { status }
    )
  })
}

export const createSuccessHandler = (endpoint: string, data: any) => {
  return http.get(endpoint, async () => {
    await delay(100)
    return HttpResponse.json(data)
  })
}

export const createDelayedHandler = (endpoint: string, data: any, delayMs: number) => {
  return http.get(endpoint, async () => {
    await delay(delayMs)
    return HttpResponse.json(data)
  })
}
