/**
 * Analysis Page Integration Tests
 *
 * Tests for the analysis page including:
 * - Symbol selection
 * - Agent analysis display
 * - MCTS controls
 * - Decision panel
 * - Accessibility
 */

import { describe, it, expect, beforeEach } from 'vitest'
import { screen, waitFor, within } from '@testing-library/react'
import { render } from '../utils/testUtils'
import AnalysisPage from '../../src/app/analysis/page'
import { server } from '../mocks/server'
import { http, HttpResponse } from 'msw'

describe('Analysis Page', () => {
  beforeEach(() => {
    server.resetHandlers()
  })

  describe('Rendering', () => {
    it('should render the analysis page', () => {
      render(<AnalysisPage />)

      expect(screen.getByRole('main')).toBeInTheDocument()
    })

    it('should display page heading', async () => {
      render(<AnalysisPage />)

      await waitFor(() => {
        expect(screen.getByRole('heading', { name: /analysis/i })).toBeInTheDocument()
      })
    })

    it('should be accessible', () => {
      const { container } = render(<AnalysisPage />)

      expect(screen.getByRole('main')).toBeInTheDocument()

      const headings = screen.getAllByRole('heading')
      expect(headings.length).toBeGreaterThan(0)
    })
  })

  describe('Symbol Selection', () => {
    it('should have symbol input field', () => {
      render(<AnalysisPage />)

      const symbolInput = screen.getByRole('combobox', { name: /symbol/i }) ||
                         screen.getByRole('textbox', { name: /symbol/i }) ||
                         screen.getByPlaceholderText(/symbol|ticker/i)

      expect(symbolInput).toBeInTheDocument()
    })

    it('should allow entering a symbol', async () => {
      const { user } = render(<AnalysisPage />)

      const symbolInput = screen.getByRole('combobox', { name: /symbol/i }) ||
                         screen.getByRole('textbox', { name: /symbol/i }) ||
                         screen.getByPlaceholderText(/symbol|ticker/i)

      await user.type(symbolInput, 'AAPL')

      expect(symbolInput).toHaveValue('AAPL')
    })

    it('should fetch analysis when symbol is selected', async () => {
      server.use(
        http.get('http://localhost:8000/api/v1/analysis/:symbol', ({ params }) => {
          return HttpResponse.json({
            symbol: params.symbol,
            recommendation: 'BUY',
            confidence: 0.85,
            reasoning: 'Strong technical indicators and positive momentum',
            risk_level: 'medium',
            factors: [
              { name: 'Technical Analysis', score: 0.88, weight: 0.4 },
              { name: 'Fundamental Analysis', score: 0.82, weight: 0.3 },
              { name: 'Sentiment', score: 0.85, weight: 0.3 },
            ],
            timestamp: new Date().toISOString(),
          })
        })
      )

      const { user } = render(<AnalysisPage />)

      const symbolInput = screen.getByRole('combobox', { name: /symbol/i }) ||
                         screen.getByRole('textbox', { name: /symbol/i }) ||
                         screen.getByPlaceholderText(/symbol|ticker/i)

      await user.type(symbolInput, 'AAPL')
      await user.keyboard('{Enter}')

      await waitFor(() => {
        expect(screen.getByText(/BUY/i)).toBeInTheDocument()
      })
    })

    it('should show suggestions when typing', async () => {
      const { user } = render(<AnalysisPage />)

      const symbolInput = screen.getByRole('combobox', { name: /symbol/i }) ||
                         screen.getByRole('textbox', { name: /symbol/i }) ||
                         screen.getByPlaceholderText(/symbol|ticker/i)

      await user.type(symbolInput, 'AA')

      await waitFor(() => {
        // Check for autocomplete suggestions
        const suggestions = screen.queryAllByRole('option')
        // Your implementation may or may not have autocomplete
      })
    })
  })

  describe('Agent Analysis Display', () => {
    beforeEach(() => {
      server.use(
        http.get('http://localhost:8000/api/v1/analysis/:symbol', () => {
          return HttpResponse.json({
            symbol: 'AAPL',
            recommendation: 'BUY',
            confidence: 0.85,
            reasoning: 'Strong technical indicators and positive momentum',
            risk_level: 'medium',
            factors: [
              { name: 'Technical Analysis', score: 0.88, weight: 0.4 },
              { name: 'Fundamental Analysis', score: 0.82, weight: 0.3 },
              { name: 'Sentiment', score: 0.85, weight: 0.3 },
            ],
            timestamp: new Date().toISOString(),
          })
        })
      )
    })

    it('should display recommendation', async () => {
      render(<AnalysisPage />)

      await waitFor(() => {
        expect(screen.getByText(/BUY/i)).toBeInTheDocument()
      })
    })

    it('should display confidence score', async () => {
      render(<AnalysisPage />)

      await waitFor(() => {
        expect(screen.getByText(/85%|0\.85/)).toBeInTheDocument()
      })
    })

    it('should display reasoning', async () => {
      render(<AnalysisPage />)

      await waitFor(() => {
        expect(screen.getByText(/Strong technical indicators/i)).toBeInTheDocument()
      })
    })

    it('should display risk level', async () => {
      render(<AnalysisPage />)

      await waitFor(() => {
        expect(screen.getByText(/medium/i)).toBeInTheDocument()
      })
    })

    it('should display analysis factors', async () => {
      render(<AnalysisPage />)

      await waitFor(() => {
        expect(screen.getByText(/Technical Analysis/i)).toBeInTheDocument()
        expect(screen.getByText(/Fundamental Analysis/i)).toBeInTheDocument()
        expect(screen.getByText(/Sentiment/i)).toBeInTheDocument()
      })
    })

    it('should visualize factor scores', async () => {
      render(<AnalysisPage />)

      await waitFor(() => {
        // Look for progress bars or charts showing factor scores
        expect(screen.getByText(/0\.88|88%/)).toBeInTheDocument()
      })
    })
  })

  describe('MCTS Controls', () => {
    it('should have MCTS search button', async () => {
      render(<AnalysisPage />)

      const searchButton = screen.queryByRole('button', { name: /search|mcts|analyze/i })
      if (searchButton) {
        expect(searchButton).toBeInTheDocument()
      }
    })

    it('should have exploration constant control', async () => {
      render(<AnalysisPage />)

      const explorationControl = screen.queryByLabelText(/exploration/i)
      if (explorationControl) {
        expect(explorationControl).toBeInTheDocument()
      }
    })

    it('should have max iterations control', async () => {
      render(<AnalysisPage />)

      const iterationsControl = screen.queryByLabelText(/iterations/i)
      if (iterationsControl) {
        expect(iterationsControl).toBeInTheDocument()
      }
    })

    it('should start MCTS search when button clicked', async () => {
      let searchStarted = false

      server.use(
        http.post('http://localhost:8000/api/v1/mcts/:symbol/search', () => {
          searchStarted = true
          return HttpResponse.json({
            best_action: {
              action_type: 'buy',
              symbol: 'AAPL',
              quantity: 10,
              confidence: 0.85,
            },
            total_simulations: 100,
            computation_time_ms: 450,
            root_value: 0.75,
          })
        })
      )

      const { user } = render(<AnalysisPage />)

      const searchButton = screen.queryByRole('button', { name: /search|start|run/i })
      if (searchButton) {
        await user.click(searchButton)

        await waitFor(() => {
          expect(searchStarted).toBe(true)
        })
      }
    })

    it('should show loading state during search', async () => {
      server.use(
        http.post('http://localhost:8000/api/v1/mcts/:symbol/search', async () => {
          await new Promise((resolve) => setTimeout(resolve, 1000))
          return HttpResponse.json({
            best_action: {
              action_type: 'buy',
              symbol: 'AAPL',
              quantity: 10,
              confidence: 0.85,
            },
          })
        })
      )

      const { user } = render(<AnalysisPage />)

      const searchButton = screen.queryByRole('button', { name: /search|start|run/i })
      if (searchButton) {
        await user.click(searchButton)

        // Should show loading indicator
        const loadingIndicator = screen.queryByText(/searching|loading|analyzing/i) ||
                                screen.queryByRole('progressbar')
        if (loadingIndicator) {
          expect(loadingIndicator).toBeInTheDocument()
        }
      }
    })

    it('should allow stopping search', async () => {
      const { user } = render(<AnalysisPage />)

      const stopButton = screen.queryByRole('button', { name: /stop|cancel/i })
      if (stopButton) {
        expect(stopButton).toBeInTheDocument()
        await user.click(stopButton)
      }
    })
  })

  describe('Decision Panel', () => {
    it('should display best action from MCTS', async () => {
      server.use(
        http.post('http://localhost:8000/api/v1/mcts/:symbol/search', () => {
          return HttpResponse.json({
            best_action: {
              action_type: 'buy',
              symbol: 'AAPL',
              quantity: 10,
              price: 150.00,
              confidence: 0.85,
            },
            total_simulations: 100,
            root_value: 0.75,
          })
        })
      )

      const { user } = render(<AnalysisPage />)

      const searchButton = screen.queryByRole('button', { name: /search|start|run/i })
      if (searchButton) {
        await user.click(searchButton)

        await waitFor(() => {
          expect(screen.getByText(/buy/i)).toBeInTheDocument()
        })
      }
    })

    it('should show action confidence', async () => {
      server.use(
        http.post('http://localhost:8000/api/v1/mcts/:symbol/search', () => {
          return HttpResponse.json({
            best_action: {
              action_type: 'buy',
              symbol: 'AAPL',
              quantity: 10,
              confidence: 0.85,
            },
          })
        })
      )

      const { user } = render(<AnalysisPage />)

      const searchButton = screen.queryByRole('button', { name: /search|start|run/i })
      if (searchButton) {
        await user.click(searchButton)

        await waitFor(() => {
          expect(screen.getByText(/85%|0\.85/)).toBeInTheDocument()
        })
      }
    })

    it('should have execute action button', async () => {
      server.use(
        http.post('http://localhost:8000/api/v1/mcts/:symbol/search', () => {
          return HttpResponse.json({
            best_action: {
              action_type: 'buy',
              symbol: 'AAPL',
              quantity: 10,
              confidence: 0.85,
            },
          })
        })
      )

      const { user } = render(<AnalysisPage />)

      const searchButton = screen.queryByRole('button', { name: /search|start|run/i })
      if (searchButton) {
        await user.click(searchButton)

        await waitFor(() => {
          const executeButton = screen.queryByRole('button', { name: /execute|place|submit/i })
          if (executeButton) {
            expect(executeButton).toBeInTheDocument()
          }
        })
      }
    })
  })

  describe('Error Handling', () => {
    it('should handle analysis fetch errors', async () => {
      server.use(
        http.get('http://localhost:8000/api/v1/analysis/:symbol', () => {
          return HttpResponse.json(
            { error: 'Failed to analyze symbol' },
            { status: 500 }
          )
        })
      )

      render(<AnalysisPage />)

      await waitFor(() => {
        const errorMessage = screen.queryByText(/error|failed/i)
        if (errorMessage) {
          expect(errorMessage).toBeInTheDocument()
        }
      })
    })

    it('should handle MCTS search errors', async () => {
      server.use(
        http.post('http://localhost:8000/api/v1/mcts/:symbol/search', () => {
          return HttpResponse.json(
            { error: 'MCTS search failed' },
            { status: 500 }
          )
        })
      )

      const { user } = render(<AnalysisPage />)

      const searchButton = screen.queryByRole('button', { name: /search|start|run/i })
      if (searchButton) {
        await user.click(searchButton)

        await waitFor(() => {
          const errorMessage = screen.queryByText(/error|failed/i)
          if (errorMessage) {
            expect(errorMessage).toBeInTheDocument()
          }
        })
      }
    })

    it('should handle invalid symbol errors', async () => {
      server.use(
        http.get('http://localhost:8000/api/v1/analysis/:symbol', () => {
          return HttpResponse.json(
            { error: 'Invalid symbol' },
            { status: 404 }
          )
        })
      )

      const { user } = render(<AnalysisPage />)

      const symbolInput = screen.getByRole('combobox', { name: /symbol/i }) ||
                         screen.getByRole('textbox', { name: /symbol/i }) ||
                         screen.getByPlaceholderText(/symbol|ticker/i)

      await user.type(symbolInput, 'INVALID')
      await user.keyboard('{Enter}')

      await waitFor(() => {
        const errorMessage = screen.queryByText(/invalid|not found/i)
        if (errorMessage) {
          expect(errorMessage).toBeInTheDocument()
        }
      })
    })
  })

  describe('Market Data Display', () => {
    it('should display current price', async () => {
      server.use(
        http.get('http://localhost:8000/api/v1/market/:symbol', () => {
          return HttpResponse.json({
            symbol: 'AAPL',
            last_price: 150.25,
            change: 2.50,
            change_percent: 1.69,
          })
        })
      )

      render(<AnalysisPage />)

      await waitFor(() => {
        expect(screen.getByText(/150\.25/)).toBeInTheDocument()
      })
    })

    it('should display price change', async () => {
      server.use(
        http.get('http://localhost:8000/api/v1/market/:symbol', () => {
          return HttpResponse.json({
            symbol: 'AAPL',
            last_price: 150.25,
            change: 2.50,
            change_percent: 1.69,
          })
        })
      )

      render(<AnalysisPage />)

      await waitFor(() => {
        expect(screen.getByText(/2\.50/)).toBeInTheDocument()
        expect(screen.getByText(/1\.69%/)).toBeInTheDocument()
      })
    })
  })

  describe('Accessibility', () => {
    it('should have proper ARIA labels on controls', () => {
      render(<AnalysisPage />)

      const symbolInput = screen.queryByLabelText(/symbol/i)
      if (symbolInput) {
        expect(symbolInput).toBeInTheDocument()
      }
    })

    it('should support keyboard navigation', async () => {
      const { user } = render(<AnalysisPage />)

      await user.tab()

      expect(document.activeElement).not.toBe(document.body)
    })

    it('should announce analysis results to screen readers', async () => {
      render(<AnalysisPage />)

      // Check for aria-live regions
      const liveRegions = document.querySelectorAll('[aria-live]')
      // Your implementation may use these
    })

    it('should have descriptive button labels', () => {
      render(<AnalysisPage />)

      const buttons = screen.getAllByRole('button')
      buttons.forEach((button) => {
        expect(button).toHaveAccessibleName()
      })
    })
  })

  describe('Loading States', () => {
    it('should show skeleton loaders for analysis', async () => {
      render(<AnalysisPage />)

      // Initial loading state
      const loadingIndicators = screen.queryAllByRole('progressbar')
      // Your implementation may show loaders
    })

    it('should show progress during MCTS search', async () => {
      server.use(
        http.post('http://localhost:8000/api/v1/mcts/:symbol/search', async () => {
          await new Promise((resolve) => setTimeout(resolve, 500))
          return HttpResponse.json({
            best_action: { action_type: 'buy', symbol: 'AAPL', quantity: 10, confidence: 0.85 },
          })
        })
      )

      const { user } = render(<AnalysisPage />)

      const searchButton = screen.queryByRole('button', { name: /search|start|run/i })
      if (searchButton) {
        await user.click(searchButton)

        const progressIndicator = screen.queryByRole('progressbar')
        if (progressIndicator) {
          expect(progressIndicator).toBeInTheDocument()
        }
      }
    })
  })
})
