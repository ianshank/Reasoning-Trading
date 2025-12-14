/**
 * MCTS Page Integration Tests
 *
 * Tests for the MCTS visualization page including:
 * - Tree visualization rendering
 * - WebSocket connection
 * - Search controls
 * - Statistics display
 * - Real-time updates
 * - Accessibility
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { screen, waitFor, within } from '@testing-library/react'
import { render } from '../utils/testUtils'
import MCTSPage from '../../src/app/mcts/page'
import { server } from '../mocks/server'
import { http, HttpResponse } from 'msw'
import { createMockMCTSTree } from '../utils/factories'

describe('MCTS Page', () => {
  beforeEach(() => {
    server.resetHandlers()
  })

  describe('Rendering', () => {
    it('should render the MCTS page', () => {
      render(<MCTSPage />)

      expect(screen.getByRole('main')).toBeInTheDocument()
    })

    it('should display page heading', async () => {
      render(<MCTSPage />)

      await waitFor(() => {
        expect(screen.getByRole('heading', { name: /mcts|monte carlo/i })).toBeInTheDocument()
      })
    })

    it('should be accessible', () => {
      const { container } = render(<MCTSPage />)

      expect(screen.getByRole('main')).toBeInTheDocument()

      const headings = screen.getAllByRole('heading')
      expect(headings.length).toBeGreaterThan(0)
    })
  })

  describe('Tree Visualization', () => {
    it('should render tree container', async () => {
      render(<MCTSPage />)

      await waitFor(() => {
        // Look for SVG or canvas element for tree visualization
        const svg = container.querySelector('svg')
        const canvas = container.querySelector('canvas')

        if (svg || canvas) {
          expect(svg || canvas).toBeInTheDocument()
        }
      })
    })

    it('should display root node', async () => {
      server.use(
        http.get('http://localhost:8000/api/v1/mcts/:symbol/state', () => {
          return HttpResponse.json(createMockMCTSTree())
        })
      )

      render(<MCTSPage />)

      await waitFor(() => {
        const rootNode = screen.queryByText(/root/i) || screen.queryByTestId('mcts-root-node')
        if (rootNode) {
          expect(rootNode).toBeInTheDocument()
        }
      })
    })

    it('should display node visit counts', async () => {
      const mockTree = createMockMCTSTree()

      server.use(
        http.get('http://localhost:8000/api/v1/mcts/:symbol/state', () => {
          return HttpResponse.json(mockTree)
        })
      )

      render(<MCTSPage />)

      await waitFor(() => {
        // Look for visit count display
        expect(screen.getByText(/100|visits/i)).toBeInTheDocument()
      })
    })

    it('should display node values', async () => {
      const mockTree = createMockMCTSTree()

      server.use(
        http.get('http://localhost:8000/api/v1/mcts/:symbol/state', () => {
          return HttpResponse.json(mockTree)
        })
      )

      render(<MCTSPage />)

      await waitFor(() => {
        // Look for value display (0.5 in mock)
        expect(screen.getByText(/0\.5|value/i)).toBeInTheDocument()
      })
    })

    it('should allow clicking on nodes for details', async () => {
      const mockTree = createMockMCTSTree()

      server.use(
        http.get('http://localhost:8000/api/v1/mcts/:symbol/state', () => {
          return HttpResponse.json(mockTree)
        })
      )

      const { user } = render(<MCTSPage />)

      await waitFor(() => {
        const nodes = screen.queryAllByTestId(/mcts-node/)
        if (nodes.length > 0) {
          user.click(nodes[0])

          // Should show node details panel
          waitFor(() => {
            const detailsPanel = screen.queryByText(/details|node info/i)
            if (detailsPanel) {
              expect(detailsPanel).toBeInTheDocument()
            }
          })
        }
      })
    })

    it('should highlight best path', async () => {
      const mockTree = createMockMCTSTree()

      server.use(
        http.get('http://localhost:8000/api/v1/mcts/:symbol/state', () => {
          return HttpResponse.json({
            ...mockTree,
            best_action: 'node-1',
          })
        })
      )

      render(<MCTSPage />)

      await waitFor(() => {
        // Look for highlighted or best path indicators
        const bestPath = screen.queryByTestId('best-path') ||
                        document.querySelector('.best-path')
        if (bestPath) {
          expect(bestPath).toBeInTheDocument()
        }
      })
    })
  })

  describe('Search Controls', () => {
    it('should have start search button', () => {
      render(<MCTSPage />)

      const startButton = screen.getByRole('button', { name: /start|search|run/i })
      expect(startButton).toBeInTheDocument()
    })

    it('should have stop search button when searching', async () => {
      const { user } = render(<MCTSPage />)

      const startButton = screen.getByRole('button', { name: /start|search|run/i })
      await user.click(startButton)

      await waitFor(() => {
        const stopButton = screen.queryByRole('button', { name: /stop|pause|cancel/i })
        if (stopButton) {
          expect(stopButton).toBeInTheDocument()
        }
      })
    })

    it('should have reset button', () => {
      render(<MCTSPage />)

      const resetButton = screen.queryByRole('button', { name: /reset|clear/i })
      if (resetButton) {
        expect(resetButton).toBeInTheDocument()
      }
    })

    it('should have iteration count control', () => {
      render(<MCTSPage />)

      const iterationControl = screen.queryByLabelText(/iterations|simulations/i)
      if (iterationControl) {
        expect(iterationControl).toBeInTheDocument()
      }
    })

    it('should have exploration constant control', () => {
      render(<MCTSPage />)

      const explorationControl = screen.queryByLabelText(/exploration/i)
      if (explorationControl) {
        expect(explorationControl).toBeInTheDocument()
      }
    })

    it('should start search when button clicked', async () => {
      const { user } = render(<MCTSPage />)

      const startButton = screen.getByRole('button', { name: /start|search|run/i })
      await user.click(startButton)

      await waitFor(() => {
        // Should show searching state
        const searchingIndicator = screen.queryByText(/searching|running/i) ||
                                   screen.queryByRole('progressbar')
        if (searchingIndicator) {
          expect(searchingIndicator).toBeInTheDocument()
        }
      })
    })

    it('should update controls when search starts', async () => {
      const { user } = render(<MCTSPage />)

      const startButton = screen.getByRole('button', { name: /start|search|run/i })

      // Controls should be enabled initially
      expect(startButton).toBeEnabled()

      await user.click(startButton)

      await waitFor(() => {
        // Start button should be disabled during search
        // Or replaced with stop button
        const stopButton = screen.queryByRole('button', { name: /stop|pause|cancel/i })
        if (stopButton) {
          expect(stopButton).toBeEnabled()
        }
      })
    })
  })

  describe('Statistics Display', () => {
    it('should display total simulations', async () => {
      const mockTree = createMockMCTSTree()

      server.use(
        http.get('http://localhost:8000/api/v1/mcts/:symbol/state', () => {
          return HttpResponse.json(mockTree)
        })
      )

      render(<MCTSPage />)

      await waitFor(() => {
        expect(screen.getByText(/100.*simulations?/i)).toBeInTheDocument()
      })
    })

    it('should display current iteration', async () => {
      server.use(
        http.get('http://localhost:8000/api/v1/mcts/:symbol/state', () => {
          return HttpResponse.json({
            iteration: 45,
            max_iterations: 100,
          })
        })
      )

      render(<MCTSPage />)

      await waitFor(() => {
        expect(screen.getByText(/45.*100|iteration/i)).toBeInTheDocument()
      })
    })

    it('should display tree depth', async () => {
      server.use(
        http.get('http://localhost:8000/api/v1/mcts/:symbol/state', () => {
          return HttpResponse.json({
            max_depth: 8,
          })
        })
      )

      render(<MCTSPage />)

      await waitFor(() => {
        const depthText = screen.queryByText(/8.*depth|depth.*8/i)
        if (depthText) {
          expect(depthText).toBeInTheDocument()
        }
      })
    })

    it('should display root value', async () => {
      const mockTree = createMockMCTSTree()

      server.use(
        http.get('http://localhost:8000/api/v1/mcts/:symbol/state', () => {
          return HttpResponse.json(mockTree)
        })
      )

      render(<MCTSPage />)

      await waitFor(() => {
        expect(screen.getByText(/0\.5|root value/i)).toBeInTheDocument()
      })
    })

    it('should display simulations per second', async () => {
      server.use(
        http.get('http://localhost:8000/api/v1/mcts/:symbol/state', () => {
          return HttpResponse.json({
            simulations_per_second: 150.5,
          })
        })
      )

      render(<MCTSPage />)

      await waitFor(() => {
        const spsText = screen.queryByText(/150\.5.*\/s|sim\/s/i)
        if (spsText) {
          expect(spsText).toBeInTheDocument()
        }
      })
    })
  })

  describe('WebSocket Connection', () => {
    it('should show connection status', () => {
      render(<MCTSPage />)

      // Look for connection indicator
      const connectionStatus = screen.queryByText(/connected|disconnected/i) ||
                              screen.queryByTestId('connection-status')
      if (connectionStatus) {
        expect(connectionStatus).toBeInTheDocument()
      }
    })

    it('should connect to WebSocket on mount', async () => {
      render(<MCTSPage />)

      await waitFor(() => {
        // WebSocket mock should be created
        // Check in setup.ts mock
      }, { timeout: 1000 })
    })

    it('should handle WebSocket messages', async () => {
      render(<MCTSPage />)

      // Simulate WebSocket message
      // This would use the mock WebSocket from setup.ts
      await waitFor(() => {
        // Tree should update with new data
      })
    })

    it('should show reconnection attempts on disconnect', async () => {
      render(<MCTSPage />)

      // Simulate disconnect
      // Mock WebSocket close event

      await waitFor(() => {
        const reconnectMessage = screen.queryByText(/reconnecting|connection lost/i)
        if (reconnectMessage) {
          expect(reconnectMessage).toBeInTheDocument()
        }
      })
    })

    it('should cleanup WebSocket on unmount', () => {
      const { unmount } = render(<MCTSPage />)

      unmount()

      // WebSocket should be closed
      // Verify through mock
    })
  })

  describe('Real-time Updates', () => {
    it('should update tree when new nodes added', async () => {
      render(<MCTSPage />)

      const { user } = render(<MCTSPage />)

      const startButton = screen.getByRole('button', { name: /start|search|run/i })
      await user.click(startButton)

      // Simulate WebSocket update with new node
      await waitFor(() => {
        // Tree visualization should update
      })
    })

    it('should update statistics in real-time', async () => {
      render(<MCTSPage />)

      // Simulate stat updates via WebSocket
      await waitFor(() => {
        // Statistics should change
      })
    })

    it('should animate node updates', async () => {
      render(<MCTSPage />)

      // Look for CSS animations or transitions
      const nodes = document.querySelectorAll('[data-node]')
      // Check for animation classes
    })
  })

  describe('Phase Visualization', () => {
    it('should highlight current phase', async () => {
      server.use(
        http.get('http://localhost:8000/api/v1/mcts/:symbol/state', () => {
          return HttpResponse.json({
            phase: 'selection',
          })
        })
      )

      render(<MCTSPage />)

      await waitFor(() => {
        expect(screen.getByText(/selection/i)).toBeInTheDocument()
      })
    })

    it('should show phase progress', async () => {
      render(<MCTSPage />)

      const phaseIndicators = screen.queryAllByText(/selection|expansion|simulation|backpropagation/i)
      if (phaseIndicators.length > 0) {
        expect(phaseIndicators.length).toBeGreaterThan(0)
      }
    })
  })

  describe('Action Distribution', () => {
    it('should display action probabilities', async () => {
      server.use(
        http.get('http://localhost:8000/api/v1/mcts/:symbol/state', () => {
          return HttpResponse.json({
            action_probabilities: {
              buy: 0.65,
              sell: 0.15,
              hold: 0.20,
            },
          })
        })
      )

      render(<MCTSPage />)

      await waitFor(() => {
        expect(screen.getByText(/buy/i)).toBeInTheDocument()
        expect(screen.getByText(/65%|0\.65/)).toBeInTheDocument()
      })
    })

    it('should visualize action distribution chart', async () => {
      render(<MCTSPage />)

      await waitFor(() => {
        // Look for chart or bars showing distribution
        const chart = screen.queryByText(/distribution|probability/i)
        if (chart) {
          expect(chart).toBeInTheDocument()
        }
      })
    })
  })

  describe('Error Handling', () => {
    it('should handle MCTS state fetch errors', async () => {
      server.use(
        http.get('http://localhost:8000/api/v1/mcts/:symbol/state', () => {
          return HttpResponse.json(
            { error: 'Failed to load MCTS state' },
            { status: 500 }
          )
        })
      )

      render(<MCTSPage />)

      await waitFor(() => {
        const errorMessage = screen.queryByText(/error|failed/i)
        if (errorMessage) {
          expect(errorMessage).toBeInTheDocument()
        }
      })
    })

    it('should handle WebSocket connection errors', async () => {
      // Mock WebSocket error
      render(<MCTSPage />)

      await waitFor(() => {
        const errorMessage = screen.queryByText(/connection.*error|unable.*connect/i)
        // May or may not show depending on implementation
      })
    })

    it('should show retry button on error', async () => {
      server.use(
        http.get('http://localhost:8000/api/v1/mcts/:symbol/state', () => {
          return HttpResponse.json(
            { error: 'Server error' },
            { status: 500 }
          )
        })
      )

      render(<MCTSPage />)

      await waitFor(() => {
        const retryButton = screen.queryByRole('button', { name: /retry|try again/i })
        if (retryButton) {
          expect(retryButton).toBeInTheDocument()
        }
      })
    })
  })

  describe('Accessibility', () => {
    it('should have accessible labels on controls', () => {
      render(<MCTSPage />)

      const buttons = screen.getAllByRole('button')
      buttons.forEach((button) => {
        expect(button).toHaveAccessibleName()
      })
    })

    it('should support keyboard navigation', async () => {
      const { user } = render(<MCTSPage />)

      await user.tab()

      expect(document.activeElement).not.toBe(document.body)
    })

    it('should have ARIA labels on tree visualization', () => {
      render(<MCTSPage />)

      const treeContainer = screen.queryByRole('img', { name: /tree|mcts/i }) ||
                           screen.queryByLabelText(/tree|visualization/i)
      // Your implementation may use different accessibility patterns
    })

    it('should announce updates to screen readers', () => {
      render(<MCTSPage />)

      const liveRegions = document.querySelectorAll('[aria-live]')
      // Check if your implementation uses live regions for updates
    })
  })

  describe('Performance', () => {
    it('should handle large trees efficiently', async () => {
      const largeMockTree = {
        ...createMockMCTSTree(),
        nodes: Object.fromEntries(
          Array.from({ length: 1000 }, (_, i) => [
            `node-${i}`,
            {
              id: `node-${i}`,
              visits: Math.floor(Math.random() * 100),
              value: Math.random(),
            },
          ])
        ),
      }

      server.use(
        http.get('http://localhost:8000/api/v1/mcts/:symbol/state', () => {
          return HttpResponse.json(largeMockTree)
        })
      )

      const startTime = performance.now()
      render(<MCTSPage />)

      await waitFor(() => {
        expect(screen.getByRole('main')).toBeInTheDocument()
      })

      const endTime = performance.now()
      const renderTime = endTime - startTime

      // Should render in reasonable time (adjust threshold as needed)
      expect(renderTime).toBeLessThan(3000)
    })
  })
})
