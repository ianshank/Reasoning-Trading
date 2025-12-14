/**
 * MSW Server for Node.js tests
 *
 * Sets up the Mock Service Worker server for intercepting
 * HTTP requests during tests.
 */

import { setupServer } from 'msw/node'
import { handlers } from './handlers'

// Setup the MSW server with default handlers
export const server = setupServer(...handlers)
