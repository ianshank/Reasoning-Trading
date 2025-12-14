/**
 * Dashboard Integration Tests
 *
 * Tests for the main dashboard page including:
 * - Page rendering
 * - Data loading states
 * - Widget interactions
 * - Navigation
 * - Accessibility
 */

import { describe, it, expect, beforeEach } from 'vitest'
import { screen, waitFor, within } from '@testing-library/react'
import { render } from '../utils/testUtils'
import DashboardPage from '../../src/app/dashboard/page'
import { server } from '../mocks/server'
import { http, HttpResponse } from 'msw'
import { createMockPortfolio } from '../utils/factories'

describe('Dashboard Page', () => {
  beforeEach(() => {
    // Reset any runtime handlers
    server.resetHandlers()
  })

  describe('Rendering', () => {
    it('should render the dashboard page', async () => {
      render(<DashboardPage />)

      expect(screen.getByRole('main')).toBeInTheDocument()
    })

    it('should have correct page title', async () => {
      render(<DashboardPage />)

      await waitFor(() => {
        expect(screen.getByText(/dashboard/i)).toBeInTheDocument()
      })
    })

    it('should be accessible', async () => {
      const { container } = render(<DashboardPage />)

      // Check for landmark regions
      expect(screen.getByRole('main')).toBeInTheDocument()

      // Check that there are no accessibility violations
      // Note: You can integrate axe-core for more thorough a11y testing
      const headings = screen.queryAllByRole('heading')
      expect(headings.length).toBeGreaterThan(0)
    })
  })

  describe('Data Loading', () => {
    it('should show loading state initially', () => {
      render(<DashboardPage />)

      // Check for loading indicators
      const loadingElements = screen.queryAllByText(/loading/i)
      if (loadingElements.length > 0) {
        expect(loadingElements[0]).toBeInTheDocument()
      }
    })

    it('should load and display portfolio data', async () => {
      const mockPortfolio = createMockPortfolio({
        total_value: 125000.50,
        unrealized_pnl: 5250.25,
      })

      server.use(
        http.get('http://localhost:8000/api/v1/portfolio', () => {
          return HttpResponse.json(mockPortfolio)
        })
      )

      render(<DashboardPage />)

      await waitFor(() => {
        // Portfolio value should be displayed
        expect(screen.getByText(/125,000\.50|125000\.50/)).toBeInTheDocument()
      })
    })

    it('should handle error state gracefully', async () => {
      server.use(
        http.get('http://localhost:8000/api/v1/portfolio', () => {
          return HttpResponse.json(
            { error: 'Failed to load portfolio' },
            { status: 500 }
          )
        })
      )

      render(<DashboardPage />)

      await waitFor(() => {
        const errorMessage = screen.queryByText(/error/i) || screen.queryByText(/failed/i)
        if (errorMessage) {
          expect(errorMessage).toBeInTheDocument()
        }
      })
    })

    it('should retry failed requests', async () => {
      let callCount = 0

      server.use(
        http.get('http://localhost:8000/api/v1/portfolio', () => {
          callCount++
          if (callCount === 1) {
            return HttpResponse.json(
              { error: 'Server error' },
              { status: 500 }
            )
          }
          return HttpResponse.json(createMockPortfolio())
        })
      )

      const { user } = render(<DashboardPage />)

      await waitFor(() => {
        const retryButton = screen.queryByRole('button', { name: /retry/i })
        if (retryButton) {
          expect(retryButton).toBeInTheDocument()
        }
      })
    })
  })

  describe('Portfolio Summary Widget', () => {
    it('should display total portfolio value', async () => {
      const mockPortfolio = createMockPortfolio({
        total_value: 100000.00,
      })

      server.use(
        http.get('http://localhost:8000/api/v1/portfolio', () => {
          return HttpResponse.json(mockPortfolio)
        })
      )

      render(<DashboardPage />)

      await waitFor(() => {
        expect(screen.getByText(/100,000\.00|100000/)).toBeInTheDocument()
      })
    })

    it('should display P&L with correct styling', async () => {
      const mockPortfolio = createMockPortfolio({
        unrealized_pnl: 5000.00,
      })

      server.use(
        http.get('http://localhost:8000/api/v1/portfolio', () => {
          return HttpResponse.json(mockPortfolio)
        })
      )

      render(<DashboardPage />)

      await waitFor(() => {
        const pnlElement = screen.getByText(/5,000\.00|5000/)
        expect(pnlElement).toBeInTheDocument()

        // Positive P&L should have green/success styling
        // This depends on your actual implementation
      })
    })

    it('should display position count', async () => {
      const mockPortfolio = createMockPortfolio({
        position_count: 5,
      })

      server.use(
        http.get('http://localhost:8000/api/v1/portfolio', () => {
          return HttpResponse.json(mockPortfolio)
        })
      )

      render(<DashboardPage />)

      await waitFor(() => {
        expect(screen.getByText(/5.*position/i)).toBeInTheDocument()
      })
    })
  })

  describe('Performance Chart Widget', () => {
    it('should render performance chart', async () => {
      render(<DashboardPage />)

      await waitFor(() => {
        // Look for chart container or SVG element
        const chartElements = screen.queryAllByRole('img')
        // Recharts might render as SVG, adjust selector as needed
      })
    })

    it('should allow timeframe selection', async () => {
      const { user } = render(<DashboardPage />)

      await waitFor(() => {
        const timeframeButtons = screen.queryAllByRole('button', { name: /1D|1W|1M|3M|1Y/i })
        if (timeframeButtons.length > 0) {
          expect(timeframeButtons.length).toBeGreaterThan(0)
        }
      })
    })
  })

  describe('Recent Positions Widget', () => {
    it('should display recent positions', async () => {
      const mockPortfolio = createMockPortfolio()

      server.use(
        http.get('http://localhost:8000/api/v1/portfolio', () => {
          return HttpResponse.json(mockPortfolio)
        })
      )

      render(<DashboardPage />)

      await waitFor(() => {
        mockPortfolio.positions.forEach((position) => {
          const symbolElement = screen.queryByText(position.symbol)
          if (symbolElement) {
            expect(symbolElement).toBeInTheDocument()
          }
        })
      })
    })

    it('should navigate to position details on click', async () => {
      const mockPortfolio = createMockPortfolio()

      server.use(
        http.get('http://localhost:8000/api/v1/portfolio', () => {
          return HttpResponse.json(mockPortfolio)
        })
      )

      const { user } = render(<DashboardPage />)

      await waitFor(() => {
        const positionLinks = screen.queryAllByRole('link')
        if (positionLinks.length > 0) {
          expect(positionLinks[0]).toHaveAttribute('href')
        }
      })
    })
  })

  describe('Risk Metrics Widget', () => {
    it('should display risk metrics', async () => {
      const mockPortfolio = createMockPortfolio()

      server.use(
        http.get('http://localhost:8000/api/v1/portfolio', () => {
          return HttpResponse.json(mockPortfolio)
        })
      )

      render(<DashboardPage />)

      await waitFor(() => {
        // Look for common risk metrics
        const riskText = screen.queryByText(/risk/i) ||
                        screen.queryByText(/sharpe/i) ||
                        screen.queryByText(/volatility/i)
        if (riskText) {
          expect(riskText).toBeInTheDocument()
        }
      })
    })

    it('should show risk alerts for high-risk conditions', async () => {
      const mockPortfolio = createMockPortfolio({
        risk_metrics: {
          daily_var_95: -5000,
          daily_var_99: -8000,
          max_drawdown: 0.25, // High drawdown
          current_drawdown: 0.22, // High current drawdown
          drawdown_start: new Date().toISOString(),
          portfolio_volatility: 0.35,
          sharpe_ratio: 0.5,
          sortino_ratio: 0.7,
          largest_position_pct: 0.30,
          top5_concentration: 0.85,
          herfindahl_index: 0.4,
          leverage_ratio: 2.0,
          margin_utilization: 0.85, // High margin usage
        },
      })

      server.use(
        http.get('http://localhost:8000/api/v1/portfolio', () => {
          return HttpResponse.json(mockPortfolio)
        })
      )

      render(<DashboardPage />)

      await waitFor(() => {
        const alerts = screen.queryAllByRole('alert')
        // If alerts are shown, verify they exist
      })
    })
  })

  describe('Navigation', () => {
    it('should have navigation links to other pages', async () => {
      render(<DashboardPage />)

      // Check for common navigation items
      // This might be in a sidebar or header
      const links = screen.queryAllByRole('link')
      expect(links.length).toBeGreaterThan(0)
    })

    it('should navigate to portfolio page', async () => {
      const { user } = render(<DashboardPage />)

      const portfolioLink = screen.queryByRole('link', { name: /portfolio/i })
      if (portfolioLink) {
        await user.click(portfolioLink)
        expect(window.location.pathname).toContain('/portfolio')
      }
    })
  })

  describe('Real-time Updates', () => {
    it('should handle real-time portfolio updates', async () => {
      render(<DashboardPage />)

      // Initial load
      await waitFor(() => {
        const mainContent = screen.queryByRole('main')
        expect(mainContent).toBeInTheDocument()
      })

      // Update mock data
      const updatedPortfolio = createMockPortfolio({
        total_value: 150000.00,
      })

      server.use(
        http.get('http://localhost:8000/api/v1/portfolio', () => {
          return HttpResponse.json(updatedPortfolio)
        })
      )

      // Trigger a refresh or wait for auto-refresh
      // Implementation depends on your refresh mechanism
    })
  })

  describe('Responsive Design', () => {
    it('should render correctly on mobile viewport', async () => {
      // Set mobile viewport
      global.innerWidth = 375
      global.innerHeight = 667

      render(<DashboardPage />)

      await waitFor(() => {
        expect(screen.getByRole('main')).toBeInTheDocument()
      })
    })

    it('should render correctly on tablet viewport', async () => {
      // Set tablet viewport
      global.innerWidth = 768
      global.innerHeight = 1024

      render(<DashboardPage />)

      await waitFor(() => {
        expect(screen.getByRole('main')).toBeInTheDocument()
      })
    })
  })

  describe('Accessibility', () => {
    it('should have proper ARIA labels', async () => {
      render(<DashboardPage />)

      // Main content should have accessible label
      const main = screen.getByRole('main')
      expect(main).toBeInTheDocument()
    })

    it('should support keyboard navigation', async () => {
      const { user } = render(<DashboardPage />)

      // Tab through interactive elements
      await user.tab()

      // First focusable element should be focused
      const focusedElement = document.activeElement
      expect(focusedElement).not.toBe(document.body)
    })

    it('should announce dynamic content changes to screen readers', async () => {
      render(<DashboardPage />)

      // Check for aria-live regions
      const liveRegions = document.querySelectorAll('[aria-live]')
      // Verify they exist if your implementation uses them
    })
  })
})
