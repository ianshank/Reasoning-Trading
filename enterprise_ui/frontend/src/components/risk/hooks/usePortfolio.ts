/**
 * Portfolio Data Hook
 *
 * Fetches and manages portfolio state with real-time updates
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import type { Portfolio, Position } from '../../../types/portfolio';

interface UsePortfolioResult {
  portfolio: Portfolio | null;
  positions: Position[];
  isLoading: boolean;
  error: Error | null;
  refresh: () => Promise<void>;
}

interface WebSocketMessage {
  type: 'portfolio_update' | 'position_update' | 'position_closed';
  data: Portfolio | Position;
}

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
const WS_BASE_URL = process.env.REACT_APP_WS_URL || 'ws://localhost:8000';

export const usePortfolio = (accountId?: string): UsePortfolioResult => {
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [positions, setPositions] = useState<Position[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<Error | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptsRef = useRef<number>(0);

  const MAX_RECONNECT_ATTEMPTS = 5;
  const RECONNECT_DELAY = 3000;

  const fetchPortfolio = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);

      const endpoint = accountId
        ? `${API_BASE_URL}/api/v1/portfolio/${accountId}`
        : `${API_BASE_URL}/api/v1/portfolio`;

      const response = await fetch(endpoint, {
        headers: {
          'Content-Type': 'application/json',
          // Add authentication headers as needed
          // 'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch portfolio: ${response.statusText}`);
      }

      const data: Portfolio = await response.json();
      setPortfolio(data);
      setPositions(data.positions || []);
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Unknown error');
      setError(error);
      console.error('Error fetching portfolio:', error);
    } finally {
      setIsLoading(false);
    }
  }, [accountId]);

  const connectWebSocket = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    try {
      const wsUrl = accountId
        ? `${WS_BASE_URL}/ws/portfolio/${accountId}`
        : `${WS_BASE_URL}/ws/portfolio`;

      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        console.log('WebSocket connected');
        reconnectAttemptsRef.current = 0;
      };

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);

          switch (message.type) {
            case 'portfolio_update':
              const portfolioData = message.data as Portfolio;
              setPortfolio(portfolioData);
              setPositions(portfolioData.positions || []);
              break;

            case 'position_update':
              const updatedPosition = message.data as Position;
              setPositions((prev) =>
                prev.map((pos) =>
                  pos.position_id === updatedPosition.position_id
                    ? updatedPosition
                    : pos
                )
              );
              break;

            case 'position_closed':
              const closedPosition = message.data as Position;
              setPositions((prev) =>
                prev.filter((pos) => pos.position_id !== closedPosition.position_id)
              );
              break;

            default:
              console.warn('Unknown WebSocket message type:', message.type);
          }
        } catch (err) {
          console.error('Error parsing WebSocket message:', err);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
      };

      ws.onclose = () => {
        console.log('WebSocket disconnected');
        wsRef.current = null;

        // Attempt to reconnect
        if (reconnectAttemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
          reconnectAttemptsRef.current += 1;
          console.log(
            `Reconnecting... (attempt ${reconnectAttemptsRef.current}/${MAX_RECONNECT_ATTEMPTS})`
          );

          reconnectTimeoutRef.current = setTimeout(() => {
            connectWebSocket();
          }, RECONNECT_DELAY);
        } else {
          console.error('Max reconnection attempts reached');
          setError(
            new Error('WebSocket connection lost. Please refresh the page.')
          );
        }
      };

      wsRef.current = ws;
    } catch (err) {
      console.error('Error creating WebSocket connection:', err);
    }
  }, [accountId]);

  const refresh = useCallback(async () => {
    await fetchPortfolio();
  }, [fetchPortfolio]);

  useEffect(() => {
    // Initial fetch
    fetchPortfolio();

    // Connect WebSocket for real-time updates
    connectWebSocket();

    // Cleanup
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [fetchPortfolio, connectWebSocket]);

  return {
    portfolio,
    positions,
    isLoading,
    error,
    refresh,
  };
};
