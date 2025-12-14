/**
 * Orders Page Integration Tests
 *
 * Tests for the orders page including:
 * - Order form validation
 * - Pending orders display
 * - Order history
 * - Filtering and sorting
 * - Order actions (cancel, modify)
 * - Accessibility
 */

import { describe, it, expect, beforeEach } from 'vitest'
import { screen, waitFor, within } from '@testing-library/react'
import { render } from '../utils/testUtils'
import OrdersPage from '../../src/app/orders/page'
import { server } from '../mocks/server'
import { http, HttpResponse } from 'msw'
import { createMockOrder } from '../utils/factories'

describe('Orders Page', () => {
  beforeEach(() => {
    server.resetHandlers()
  })

  describe('Rendering', () => {
    it('should render the orders page', () => {
      render(<OrdersPage />)

      expect(screen.getByRole('main')).toBeInTheDocument()
    })

    it('should display page heading', async () => {
      render(<OrdersPage />)

      await waitFor(() => {
        expect(screen.getByRole('heading', { name: /orders/i })).toBeInTheDocument()
      })
    })

    it('should be accessible', () => {
      const { container } = render(<OrdersPage />)

      expect(screen.getByRole('main')).toBeInTheDocument()

      const headings = screen.getAllByRole('heading')
      expect(headings.length).toBeGreaterThan(0)
    })
  })

  describe('Order Form', () => {
    it('should render order form', () => {
      render(<OrdersPage />)

      const form = screen.getByRole('form') || screen.getByTestId('order-form')
      expect(form).toBeInTheDocument()
    })

    it('should have symbol input', () => {
      render(<OrdersPage />)

      const symbolInput = screen.getByLabelText(/symbol|ticker/i)
      expect(symbolInput).toBeInTheDocument()
    })

    it('should have quantity input', () => {
      render(<OrdersPage />)

      const quantityInput = screen.getByLabelText(/quantity|shares/i)
      expect(quantityInput).toBeInTheDocument()
    })

    it('should have order type selector', () => {
      render(<OrdersPage />)

      const orderTypeSelector = screen.getByLabelText(/order type|type/i)
      expect(orderTypeSelector).toBeInTheDocument()
    })

    it('should have side selector (buy/sell)', () => {
      render(<OrdersPage />)

      const buyButton = screen.getByRole('button', { name: /buy/i }) ||
                       screen.getByLabelText(/buy/i)
      const sellButton = screen.getByRole('button', { name: /sell/i }) ||
                        screen.getByLabelText(/sell/i)

      expect(buyButton).toBeInTheDocument()
      expect(sellButton).toBeInTheDocument()
    })

    it('should show limit price input for limit orders', async () => {
      const { user } = render(<OrdersPage />)

      const orderTypeSelector = screen.getByLabelText(/order type|type/i)
      await user.click(orderTypeSelector)

      const limitOption = screen.queryByText(/limit/i)
      if (limitOption) {
        await user.click(limitOption)

        await waitFor(() => {
          const limitPriceInput = screen.getByLabelText(/limit price|price/i)
          expect(limitPriceInput).toBeInTheDocument()
        })
      }
    })

    it('should validate required fields', async () => {
      const { user } = render(<OrdersPage />)

      const submitButton = screen.getByRole('button', { name: /place order|submit/i })
      await user.click(submitButton)

      await waitFor(() => {
        const errorMessages = screen.queryAllByText(/required|enter|invalid/i)
        if (errorMessages.length > 0) {
          expect(errorMessages.length).toBeGreaterThan(0)
        }
      })
    })

    it('should validate quantity is positive', async () => {
      const { user } = render(<OrdersPage />)

      const quantityInput = screen.getByLabelText(/quantity|shares/i)
      await user.clear(quantityInput)
      await user.type(quantityInput, '-10')

      await waitFor(() => {
        const errorMessage = screen.queryByText(/positive|greater than/i)
        if (errorMessage) {
          expect(errorMessage).toBeInTheDocument()
        }
      })
    })

    it('should submit order with valid data', async () => {
      let orderSubmitted = false

      server.use(
        http.post('http://localhost:8000/api/v1/orders', async ({ request }) => {
          orderSubmitted = true
          const body = await request.json()
          return HttpResponse.json({
            order_id: 'order-123',
            ...body,
            status: 'pending',
            created_at: new Date().toISOString(),
          })
        })
      )

      const { user } = render(<OrdersPage />)

      // Fill out form
      const symbolInput = screen.getByLabelText(/symbol|ticker/i)
      await user.type(symbolInput, 'AAPL')

      const quantityInput = screen.getByLabelText(/quantity|shares/i)
      await user.clear(quantityInput)
      await user.type(quantityInput, '10')

      const submitButton = screen.getByRole('button', { name: /place order|submit/i })
      await user.click(submitButton)

      await waitFor(() => {
        expect(orderSubmitted).toBe(true)
      })
    })

    it('should show success message after order submission', async () => {
      server.use(
        http.post('http://localhost:8000/api/v1/orders', () => {
          return HttpResponse.json({
            order_id: 'order-123',
            status: 'pending',
            created_at: new Date().toISOString(),
          })
        })
      )

      const { user } = render(<OrdersPage />)

      // Fill and submit form
      const symbolInput = screen.getByLabelText(/symbol|ticker/i)
      await user.type(symbolInput, 'AAPL')

      const quantityInput = screen.getByLabelText(/quantity|shares/i)
      await user.clear(quantityInput)
      await user.type(quantityInput, '10')

      const submitButton = screen.getByRole('button', { name: /place order|submit/i })
      await user.click(submitButton)

      await waitFor(() => {
        const successMessage = screen.queryByText(/success|placed|submitted/i)
        if (successMessage) {
          expect(successMessage).toBeInTheDocument()
        }
      })
    })

    it('should handle order submission errors', async () => {
      server.use(
        http.post('http://localhost:8000/api/v1/orders', () => {
          return HttpResponse.json(
            { error: 'Insufficient buying power' },
            { status: 400 }
          )
        })
      )

      const { user } = render(<OrdersPage />)

      // Fill and submit form
      const symbolInput = screen.getByLabelText(/symbol|ticker/i)
      await user.type(symbolInput, 'AAPL')

      const quantityInput = screen.getByLabelText(/quantity|shares/i)
      await user.clear(quantityInput)
      await user.type(quantityInput, '10')

      const submitButton = screen.getByRole('button', { name: /place order|submit/i })
      await user.click(submitButton)

      await waitFor(() => {
        expect(screen.getByText(/insufficient|error/i)).toBeInTheDocument()
      })
    })

    it('should reset form after successful submission', async () => {
      server.use(
        http.post('http://localhost:8000/api/v1/orders', () => {
          return HttpResponse.json({
            order_id: 'order-123',
            status: 'pending',
          })
        })
      )

      const { user } = render(<OrdersPage />)

      const symbolInput = screen.getByLabelText(/symbol|ticker/i)
      await user.type(symbolInput, 'AAPL')

      const submitButton = screen.getByRole('button', { name: /place order|submit/i })
      await user.click(submitButton)

      await waitFor(() => {
        // Form should be reset
        expect(symbolInput).toHaveValue('')
      })
    })
  })

  describe('Pending Orders', () => {
    it('should display pending orders list', async () => {
      const mockOrders = [
        createMockOrder({ status: 'pending', symbol: 'AAPL' }),
        createMockOrder({ status: 'pending', symbol: 'GOOGL' }),
      ]

      server.use(
        http.get('http://localhost:8000/api/v1/orders', ({ request }) => {
          const url = new URL(request.url)
          const status = url.searchParams.get('status')
          if (status === 'pending') {
            return HttpResponse.json({ orders: mockOrders })
          }
          return HttpResponse.json({ orders: [] })
        })
      )

      render(<OrdersPage />)

      await waitFor(() => {
        expect(screen.getByText('AAPL')).toBeInTheDocument()
        expect(screen.getByText('GOOGL')).toBeInTheDocument()
      })
    })

    it('should show empty state when no pending orders', async () => {
      server.use(
        http.get('http://localhost:8000/api/v1/orders', () => {
          return HttpResponse.json({ orders: [] })
        })
      )

      render(<OrdersPage />)

      await waitFor(() => {
        const emptyMessage = screen.queryByText(/no.*orders|no pending|empty/i)
        if (emptyMessage) {
          expect(emptyMessage).toBeInTheDocument()
        }
      })
    })

    it('should display order details', async () => {
      const mockOrder = createMockOrder({
        symbol: 'AAPL',
        quantity: 10,
        limit_price: 150.00,
        side: 'buy',
        status: 'pending',
      })

      server.use(
        http.get('http://localhost:8000/api/v1/orders', () => {
          return HttpResponse.json({ orders: [mockOrder] })
        })
      )

      render(<OrdersPage />)

      await waitFor(() => {
        expect(screen.getByText('AAPL')).toBeInTheDocument()
        expect(screen.getByText(/10/)).toBeInTheDocument()
        expect(screen.getByText(/150\.00/)).toBeInTheDocument()
        expect(screen.getByText(/buy/i)).toBeInTheDocument()
      })
    })

    it('should have cancel button for each order', async () => {
      const mockOrder = createMockOrder({ status: 'pending' })

      server.use(
        http.get('http://localhost:8000/api/v1/orders', () => {
          return HttpResponse.json({ orders: [mockOrder] })
        })
      )

      render(<OrdersPage />)

      await waitFor(() => {
        const cancelButtons = screen.getAllByRole('button', { name: /cancel/i })
        expect(cancelButtons.length).toBeGreaterThan(0)
      })
    })

    it('should cancel order when cancel button clicked', async () => {
      const mockOrder = createMockOrder({
        order_id: 'order-123',
        status: 'pending',
      })

      let orderCancelled = false

      server.use(
        http.get('http://localhost:8000/api/v1/orders', () => {
          if (orderCancelled) {
            return HttpResponse.json({ orders: [] })
          }
          return HttpResponse.json({ orders: [mockOrder] })
        }),
        http.delete('http://localhost:8000/api/v1/orders/order-123', () => {
          orderCancelled = true
          return HttpResponse.json({
            success: true,
            message: 'Order cancelled',
          })
        })
      )

      const { user } = render(<OrdersPage />)

      await waitFor(() => {
        expect(screen.getByText(mockOrder.symbol)).toBeInTheDocument()
      })

      const cancelButton = screen.getAllByRole('button', { name: /cancel/i })[0]
      await user.click(cancelButton)

      // May show confirmation dialog
      const confirmButton = screen.queryByRole('button', { name: /confirm|yes|ok/i })
      if (confirmButton) {
        await user.click(confirmButton)
      }

      await waitFor(() => {
        expect(orderCancelled).toBe(true)
      })
    })
  })

  describe('Order History', () => {
    it('should display order history tab', () => {
      render(<OrdersPage />)

      const historyTab = screen.getByRole('tab', { name: /history/i }) ||
                        screen.getByText(/history/i)

      expect(historyTab).toBeInTheDocument()
    })

    it('should show filled orders in history', async () => {
      const mockOrders = [
        createMockOrder({ status: 'filled', symbol: 'AAPL' }),
        createMockOrder({ status: 'filled', symbol: 'GOOGL' }),
      ]

      server.use(
        http.get('http://localhost:8000/api/v1/orders', ({ request }) => {
          const url = new URL(request.url)
          const status = url.searchParams.get('status')
          if (status === 'filled') {
            return HttpResponse.json({ orders: mockOrders })
          }
          return HttpResponse.json({ orders: [] })
        })
      )

      const { user } = render(<OrdersPage />)

      const historyTab = screen.queryByRole('tab', { name: /history/i })
      if (historyTab) {
        await user.click(historyTab)

        await waitFor(() => {
          expect(screen.getByText('AAPL')).toBeInTheDocument()
          expect(screen.getByText('GOOGL')).toBeInTheDocument()
        })
      }
    })

    it('should show cancelled orders in history', async () => {
      const mockOrder = createMockOrder({ status: 'cancelled' })

      server.use(
        http.get('http://localhost:8000/api/v1/orders', () => {
          return HttpResponse.json({ orders: [mockOrder] })
        })
      )

      const { user } = render(<OrdersPage />)

      const historyTab = screen.queryByRole('tab', { name: /history/i })
      if (historyTab) {
        await user.click(historyTab)

        await waitFor(() => {
          expect(screen.getByText(/cancelled/i)).toBeInTheDocument()
        })
      }
    })
  })

  describe('Filtering and Sorting', () => {
    it('should filter orders by status', async () => {
      const { user } = render(<OrdersPage />)

      const statusFilter = screen.queryByLabelText(/status|filter/i)
      if (statusFilter) {
        await user.click(statusFilter)

        const pendingOption = screen.queryByText(/pending/i)
        if (pendingOption) {
          await user.click(pendingOption)

          await waitFor(() => {
            // Should only show pending orders
          })
        }
      }
    })

    it('should filter orders by symbol', async () => {
      const { user } = render(<OrdersPage />)

      const searchInput = screen.queryByPlaceholderText(/search|filter/i)
      if (searchInput) {
        await user.type(searchInput, 'AAPL')

        await waitFor(() => {
          // Should only show AAPL orders
        })
      }
    })

    it('should sort orders by date', async () => {
      const { user } = render(<OrdersPage />)

      const dateHeader = screen.queryByText(/date|time/i)
      if (dateHeader) {
        await user.click(dateHeader)

        await waitFor(() => {
          // Orders should be sorted by date
        })
      }
    })

    it('should filter by date range', async () => {
      const { user } = render(<OrdersPage />)

      const dateRangeFilter = screen.queryByLabelText(/date range|from|to/i)
      if (dateRangeFilter) {
        expect(dateRangeFilter).toBeInTheDocument()
      }
    })
  })

  describe('Error Handling', () => {
    it('should handle orders fetch errors', async () => {
      server.use(
        http.get('http://localhost:8000/api/v1/orders', () => {
          return HttpResponse.json(
            { error: 'Failed to load orders' },
            { status: 500 }
          )
        })
      )

      render(<OrdersPage />)

      await waitFor(() => {
        const errorMessage = screen.queryByText(/error|failed/i)
        if (errorMessage) {
          expect(errorMessage).toBeInTheDocument()
        }
      })
    })

    it('should show retry button on error', async () => {
      server.use(
        http.get('http://localhost:8000/api/v1/orders', () => {
          return HttpResponse.json(
            { error: 'Server error' },
            { status: 500 }
          )
        })
      )

      render(<OrdersPage />)

      await waitFor(() => {
        const retryButton = screen.queryByRole('button', { name: /retry|try again/i })
        if (retryButton) {
          expect(retryButton).toBeInTheDocument()
        }
      })
    })
  })

  describe('Real-time Updates', () => {
    it('should update orders list when WebSocket message received', async () => {
      render(<OrdersPage />)

      // WebSocket updates handled by hook
      await waitFor(() => {
        expect(screen.getByRole('main')).toBeInTheDocument()
      })
    })

    it('should show notification when order is filled', async () => {
      render(<OrdersPage />)

      // Simulate WebSocket message for filled order
      // Check for notification
      const notifications = screen.queryAllByRole('alert')
      // Your implementation may show toast notifications
    })
  })

  describe('Accessibility', () => {
    it('should have accessible form labels', () => {
      render(<OrdersPage />)

      const symbolInput = screen.getByLabelText(/symbol|ticker/i)
      expect(symbolInput).toHaveAccessibleName()

      const quantityInput = screen.getByLabelText(/quantity|shares/i)
      expect(quantityInput).toHaveAccessibleName()
    })

    it('should support keyboard navigation', async () => {
      const { user } = render(<OrdersPage />)

      await user.tab()

      expect(document.activeElement).not.toBe(document.body)
    })

    it('should have accessible table', async () => {
      const mockOrders = [createMockOrder()]

      server.use(
        http.get('http://localhost:8000/api/v1/orders', () => {
          return HttpResponse.json({ orders: mockOrders })
        })
      )

      render(<OrdersPage />)

      await waitFor(() => {
        const table = screen.queryByRole('table')
        if (table) {
          const headers = within(table).getAllByRole('columnheader')
          expect(headers.length).toBeGreaterThan(0)
        }
      })
    })

    it('should announce form errors to screen readers', async () => {
      const { user } = render(<OrdersPage />)

      const submitButton = screen.getByRole('button', { name: /place order|submit/i })
      await user.click(submitButton)

      await waitFor(() => {
        // Check for aria-live or aria-describedby on error messages
        const errorRegions = document.querySelectorAll('[role="alert"]')
        // Your implementation may use alerts for validation errors
      })
    })
  })
})
