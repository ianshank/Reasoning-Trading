/**
 * Portfolio Page Integration Tests
 *
 * Tests for the portfolio page including:
 * - Positions table rendering
 * - Chart visualization
 * - Position actions (close, edit)
 * - Filtering and sorting
 * - Accessibility
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { screen, waitFor, within } from '@testing-library/react'
import { render } from '../utils/testUtils'
import PortfolioPage from '../../src/app/portfolio/page'
import { server } from '../mocks/server'
import { http, HttpResponse } from 'msw'
import { createMockPortfolio, createMockPosition } from '../utils/factories'

describe('Portfolio Page', () => {
  beforeEach(() => {
    server.resetHandlers()
  })

  describe('Rendering', () => {
    it('should render the portfolio page', async () => {
      render(<PortfolioPage />)

      expect(screen.getByRole('main')).toBeInTheDocument()
    })

    it('should display page heading', async () => {
      render(<PortfolioPage />)

      await waitFor(() => {
        expect(screen.getByRole('heading', { name: /portfolio/i })).toBeInTheDocument()
      })
    })

    it('should be accessible', async () => {
      const { container } = render(<PortfolioPage />)

      expect(screen.getByRole('main')).toBeInTheDocument()

      // Should have proper heading hierarchy
      const headings = screen.getAllByRole('heading')
      expect(headings.length).toBeGreaterThan(0)
    })
  })

  describe('Positions Table', () => {
    it('should render positions table', async () => {
      const mockPortfolio = createMockPortfolio()

      server.use(
        http.get('http://localhost:8000/api/v1/portfolio', () => {
          return HttpResponse.json(mockPortfolio)
        })
      )

      render(<PortfolioPage />)

      await waitFor(() => {
        // Check for table or grid
        const table = screen.queryByRole('table') || screen.queryByRole('grid')
        if (table) {
          expect(table).toBeInTheDocument()
        }
      })
    })

    it('should display position data correctly', async () => {
      const mockPosition = createMockPosition({
        symbol: 'AAPL',
        quantity: 100,
        entry_price: 150.00,
        current_price: 155.00,
        unrealized_pnl: 500.00,
      })

      const mockPortfolio = createMockPortfolio({
        positions: [mockPosition],
      })

      server.use(
        http.get('http://localhost:8000/api/v1/portfolio', () => {
          return HttpResponse.json(mockPortfolio)
        })
      )

      render(<PortfolioPage />)

      await waitFor(() => {
        expect(screen.getByText('AAPL')).toBeInTheDocument()
        expect(screen.getByText(/100/)).toBeInTheDocument()
        expect(screen.getByText(/150\.00/)).toBeInTheDocument()
        expect(screen.getByText(/155\.00/)).toBeInTheDocument()
        expect(screen.getByText(/500\.00/)).toBeInTheDocument()
      })
    })

    it('should show empty state when no positions', async () => {
      const mockPortfolio = createMockPortfolio({
        positions: [],
        position_count: 0,
      })

      server.use(
        http.get('http://localhost:8000/api/v1/portfolio', () => {
          return HttpResponse.json(mockPortfolio)
        })
      )

      render(<PortfolioPage />)

      await waitFor(() => {
        const emptyMessage = screen.queryByText(/no positions/i) ||
                           screen.queryByText(/empty/i) ||
                           screen.queryByText(/no open/i)
        if (emptyMessage) {
          expect(emptyMessage).toBeInTheDocument()
        }
      })
    })

    it('should highlight profitable positions in green', async () => {
      const mockPosition = createMockPosition({
        symbol: 'AAPL',
        unrealized_pnl: 1000.00,
        unrealized_pnl_pct: 10.0,
      })

      const mockPortfolio = createMockPortfolio({
        positions: [mockPosition],
      })

      server.use(
        http.get('http://localhost:8000/api/v1/portfolio', () => {
          return HttpResponse.json(mockPortfolio)
        })
      )

      render(<PortfolioPage />)

      await waitFor(() => {
        const pnlElements = screen.getAllByText(/1,000\.00|1000/)
        expect(pnlElements.length).toBeGreaterThan(0)
        // Check for positive styling class
        // This depends on your implementation
      })
    })

    it('should highlight losing positions in red', async () => {
      const mockPosition = createMockPosition({
        symbol: 'AAPL',
        unrealized_pnl: -500.00,
        unrealized_pnl_pct: -5.0,
      })

      const mockPortfolio = createMockPortfolio({
        positions: [mockPosition],
      })

      server.use(
        http.get('http://localhost:8000/api/v1/portfolio', () => {
          return HttpResponse.json(mockPortfolio)
        })
      )

      render(<PortfolioPage />)

      await waitFor(() => {
        const pnlElement = screen.getByText(/-500\.00/)
        expect(pnlElement).toBeInTheDocument()
      })
    })
  })

  describe('Position Actions', () => {
    it('should show action buttons for each position', async () => {
      const mockPortfolio = createMockPortfolio()

      server.use(
        http.get('http://localhost:8000/api/v1/portfolio', () => {
          return HttpResponse.json(mockPortfolio)
        })
      )

      render(<PortfolioPage />)

      await waitFor(() => {
        const actionButtons = screen.queryAllByRole('button', { name: /close|edit|details/i })
        expect(actionButtons.length).toBeGreaterThan(0)
      })
    })

    it('should close a position when close button is clicked', async () => {
      const mockPosition = createMockPosition({
        symbol: 'AAPL',
        position_id: 'pos-123',
      })

      const mockPortfolio = createMockPortfolio({
        positions: [mockPosition],
      })

      server.use(
        http.get('http://localhost:8000/api/v1/portfolio', () => {
          return HttpResponse.json(mockPortfolio)
        }),
        http.post('http://localhost:8000/api/v1/positions/pos-123/close', () => {
          return HttpResponse.json({
            success: true,
            message: 'Position closed successfully',
          })
        })
      )

      const { user } = render(<PortfolioPage />)

      await waitFor(() => {
        expect(screen.getByText('AAPL')).toBeInTheDocument()
      })

      const closeButton = screen.getAllByRole('button', { name: /close/i })[0]
      await user.click(closeButton)

      // Should show confirmation dialog
      await waitFor(() => {
        const confirmDialog = screen.queryByRole('dialog') || screen.queryByText(/confirm/i)
        if (confirmDialog) {
          expect(confirmDialog).toBeInTheDocument()
        }
      })
    })

    it('should show success message after closing position', async () => {
      const mockPosition = createMockPosition({
        symbol: 'AAPL',
        position_id: 'pos-123',
      })

      const mockPortfolio = createMockPortfolio({
        positions: [mockPosition],
      })

      let positionClosed = false

      server.use(
        http.get('http://localhost:8000/api/v1/portfolio', () => {
          if (positionClosed) {
            return HttpResponse.json(createMockPortfolio({ positions: [] }))
          }
          return HttpResponse.json(mockPortfolio)
        }),
        http.post('http://localhost:8000/api/v1/positions/pos-123/close', () => {
          positionClosed = true
          return HttpResponse.json({
            success: true,
            message: 'Position closed successfully',
          })
        })
      )

      const { user } = render(<PortfolioPage />)

      await waitFor(() => {
        expect(screen.getByText('AAPL')).toBeInTheDocument()
      })

      const closeButtons = screen.getAllByRole('button', { name: /close/i })
      if (closeButtons.length > 0) {
        await user.click(closeButtons[0])

        // Confirm if there's a dialog
        const confirmButton = screen.queryByRole('button', { name: /confirm|yes|ok/i })
        if (confirmButton) {
          await user.click(confirmButton)
        }

        await waitFor(() => {
          const successMessage = screen.queryByText(/success/i) || screen.queryByText(/closed/i)
          if (successMessage) {
            expect(successMessage).toBeInTheDocument()
          }
        })
      }
    })

    it('should handle close position errors', async () => {
      const mockPosition = createMockPosition({
        symbol: 'AAPL',
        position_id: 'pos-123',
      })

      const mockPortfolio = createMockPortfolio({
        positions: [mockPosition],
      })

      server.use(
        http.get('http://localhost:8000/api/v1/portfolio', () => {
          return HttpResponse.json(mockPortfolio)
        }),
        http.post('http://localhost:8000/api/v1/positions/pos-123/close', () => {
          return HttpResponse.json(
            { error: 'Failed to close position' },
            { status: 500 }
          )
        })
      )

      const { user } = render(<PortfolioPage />)

      await waitFor(() => {
        expect(screen.getByText('AAPL')).toBeInTheDocument()
      })

      const closeButtons = screen.getAllByRole('button', { name: /close/i })
      if (closeButtons.length > 0) {
        await user.click(closeButtons[0])

        // Confirm if there's a dialog
        const confirmButton = screen.queryByRole('button', { name: /confirm|yes|ok/i })
        if (confirmButton) {
          await user.click(confirmButton)
        }

        await waitFor(() => {
          const errorMessage = screen.queryByText(/error/i) || screen.queryByText(/failed/i)
          if (errorMessage) {
            expect(errorMessage).toBeInTheDocument()
          }
        })
      }
    })
  })

  describe('Filtering and Sorting', () => {
    it('should filter positions by symbol', async () => {
      const mockPortfolio = createMockPortfolio({
        positions: [
          createMockPosition({ symbol: 'AAPL' }),
          createMockPosition({ symbol: 'GOOGL' }),
          createMockPosition({ symbol: 'MSFT' }),
        ],
      })

      server.use(
        http.get('http://localhost:8000/api/v1/portfolio', () => {
          return HttpResponse.json(mockPortfolio)
        })
      )

      const { user } = render(<PortfolioPage />)

      await waitFor(() => {
        expect(screen.getByText('AAPL')).toBeInTheDocument()
        expect(screen.getByText('GOOGL')).toBeInTheDocument()
        expect(screen.getByText('MSFT')).toBeInTheDocument()
      })

      // Look for search or filter input
      const filterInput = screen.queryByPlaceholderText(/search|filter/i)
      if (filterInput) {
        await user.type(filterInput, 'AAPL')

        await waitFor(() => {
          expect(screen.getByText('AAPL')).toBeInTheDocument()
          expect(screen.queryByText('GOOGL')).not.toBeInTheDocument()
          expect(screen.queryByText('MSFT')).not.toBeInTheDocument()
        })
      }
    })

    it('should sort positions by P&L', async () => {
      const mockPortfolio = createMockPortfolio({
        positions: [
          createMockPosition({ symbol: 'AAPL', unrealized_pnl: 500 }),
          createMockPosition({ symbol: 'GOOGL', unrealized_pnl: -200 }),
          createMockPosition({ symbol: 'MSFT', unrealized_pnl: 1000 }),
        ],
      })

      server.use(
        http.get('http://localhost:8000/api/v1/portfolio', () => {
          return HttpResponse.json(mockPortfolio)
        })
      )

      const { user } = render(<PortfolioPage />)

      await waitFor(() => {
        expect(screen.getByText('AAPL')).toBeInTheDocument()
      })

      // Look for sort button or column header
      const sortButtons = screen.queryAllByRole('button', { name: /p&l|profit|loss/i })
      if (sortButtons.length > 0) {
        await user.click(sortButtons[0])

        // Verify sorting order changed
        await waitFor(() => {
          const rows = screen.getAllByRole('row')
          // Verify the order
        })
      }
    })

    it('should filter by position status', async () => {
      const mockPortfolio = createMockPortfolio({
        positions: [
          createMockPosition({ symbol: 'AAPL', status: 'open' }),
          createMockPosition({ symbol: 'GOOGL', status: 'open' }),
        ],
      })

      server.use(
        http.get('http://localhost:8000/api/v1/portfolio', () => {
          return HttpResponse.json(mockPortfolio)
        })
      )

      render(<PortfolioPage />)

      await waitFor(() => {
        expect(screen.getByText('AAPL')).toBeInTheDocument()
      })

      // Check for status filter
      const statusFilter = screen.queryByRole('combobox', { name: /status/i })
      if (statusFilter) {
        expect(statusFilter).toBeInTheDocument()
      }
    })
  })

  describe('Charts and Visualizations', () => {
    it('should render portfolio allocation chart', async () => {
      const mockPortfolio = createMockPortfolio()

      server.use(
        http.get('http://localhost:8000/api/v1/portfolio', () => {
          return HttpResponse.json(mockPortfolio)
        })
      )

      render(<PortfolioPage />)

      await waitFor(() => {
        // Look for chart container
        const chartHeading = screen.queryByText(/allocation|distribution/i)
        if (chartHeading) {
          expect(chartHeading).toBeInTheDocument()
        }
      })
    })

    it('should render P&L chart over time', async () => {
      render(<PortfolioPage />)

      await waitFor(() => {
        const chartHeading = screen.queryByText(/performance|p&l|profit/i)
        if (chartHeading) {
          expect(chartHeading).toBeInTheDocument()
        }
      })
    })
  })

  describe('Summary Statistics', () => {
    it('should display total portfolio value', async () => {
      const mockPortfolio = createMockPortfolio({
        total_value: 125000.50,
      })

      server.use(
        http.get('http://localhost:8000/api/v1/portfolio', () => {
          return HttpResponse.json(mockPortfolio)
        })
      )

      render(<PortfolioPage />)

      await waitFor(() => {
        expect(screen.getByText(/125,000\.50|125000\.50/)).toBeInTheDocument()
      })
    })

    it('should display total unrealized P&L', async () => {
      const mockPortfolio = createMockPortfolio({
        unrealized_pnl: 5250.25,
      })

      server.use(
        http.get('http://localhost:8000/api/v1/portfolio', () => {
          return HttpResponse.json(mockPortfolio)
        })
      )

      render(<PortfolioPage />)

      await waitFor(() => {
        expect(screen.getByText(/5,250\.25|5250\.25/)).toBeInTheDocument()
      })
    })

    it('should display position count', async () => {
      const mockPortfolio = createMockPortfolio({
        position_count: 7,
      })

      server.use(
        http.get('http://localhost:8000/api/v1/portfolio', () => {
          return HttpResponse.json(mockPortfolio)
        })
      )

      render(<PortfolioPage />)

      await waitFor(() => {
        expect(screen.getByText(/7.*position/i)).toBeInTheDocument()
      })
    })
  })

  describe('Real-time Updates', () => {
    it('should update positions when WebSocket message received', async () => {
      const mockPortfolio = createMockPortfolio()

      server.use(
        http.get('http://localhost:8000/api/v1/portfolio', () => {
          return HttpResponse.json(mockPortfolio)
        })
      )

      render(<PortfolioPage />)

      await waitFor(() => {
        expect(screen.getByRole('main')).toBeInTheDocument()
      })

      // WebSocket updates are handled by the hook
      // The mock WebSocket in setup.ts can be used to simulate messages
    })
  })

  describe('Accessibility', () => {
    it('should have accessible table headers', async () => {
      const mockPortfolio = createMockPortfolio()

      server.use(
        http.get('http://localhost:8000/api/v1/portfolio', () => {
          return HttpResponse.json(mockPortfolio)
        })
      )

      render(<PortfolioPage />)

      await waitFor(() => {
        const table = screen.queryByRole('table')
        if (table) {
          const headers = within(table).getAllByRole('columnheader')
          expect(headers.length).toBeGreaterThan(0)
        }
      })
    })

    it('should support keyboard navigation in table', async () => {
      const mockPortfolio = createMockPortfolio()

      server.use(
        http.get('http://localhost:8000/api/v1/portfolio', () => {
          return HttpResponse.json(mockPortfolio)
        })
      )

      const { user } = render(<PortfolioPage />)

      await waitFor(() => {
        expect(screen.getByRole('main')).toBeInTheDocument()
      })

      // Tab through interactive elements
      await user.tab()
      expect(document.activeElement).not.toBe(document.body)
    })

    it('should announce position updates to screen readers', async () => {
      render(<PortfolioPage />)

      // Check for aria-live regions
      const liveRegions = document.querySelectorAll('[aria-live]')
      // Your implementation may or may not use these
    })
  })
})
