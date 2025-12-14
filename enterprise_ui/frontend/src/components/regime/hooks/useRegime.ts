/**
 * Regime Data Hook
 *
 * Custom hook for fetching and managing regime detection data
 * Provides real-time regime classification, historical data, and notifications
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import type {
  RegimeClassification,
  RegimeHistory,
  RegimeStatistics,
  RegimeAlert,
} from '../../../types/regime';

interface UseRegimeOptions {
  symbol?: string;
  autoRefresh?: boolean;
  refreshInterval?: number;
  enableWebSocket?: boolean;
}

interface UseRegimeReturn {
  current: RegimeClassification | null;
  history: RegimeHistory | null;
  statistics: RegimeStatistics | null;
  alerts: RegimeAlert[];
  isLoading: boolean;
  error: Error | null;
  refresh: () => Promise<void>;
  acknowledgeAlert: (alertId: string) => void;
}

/**
 * Hook for regime detection data
 *
 * @param options - Configuration options
 * @returns Regime data and control functions
 *
 * @example
 * ```tsx
 * const { current, history, isLoading } = useRegime({
 *   symbol: 'AAPL',
 *   autoRefresh: true,
 *   refreshInterval: 30000,
 * });
 * ```
 */
export function useRegime(options: UseRegimeOptions = {}): UseRegimeReturn {
  const {
    symbol = 'SPY',
    autoRefresh = true,
    refreshInterval = 30000,
    enableWebSocket = true,
  } = options;

  const [current, setCurrent] = useState<RegimeClassification | null>(null);
  const [history, setHistory] = useState<RegimeHistory | null>(null);
  const [statistics, setStatistics] = useState<RegimeStatistics | null>(null);
  const [alerts, setAlerts] = useState<RegimeAlert[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<Error | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const refreshTimerRef = useRef<NodeJS.Timeout | null>(null);

  /**
   * Fetch current regime classification
   */
  const fetchCurrent = useCallback(async (): Promise<void> => {
    try {
      const response = await fetch(`/api/v1/regime/current?symbol=${symbol}`);
      if (!response.ok) {
        throw new Error(`Failed to fetch regime: ${response.statusText}`);
      }
      const data = await response.json();
      setCurrent(data);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Unknown error'));
      throw err;
    }
  }, [symbol]);

  /**
   * Fetch regime history
   */
  const fetchHistory = useCallback(async (): Promise<void> => {
    try {
      const response = await fetch(`/api/v1/regime/history?symbol=${symbol}&limit=100`);
      if (!response.ok) {
        throw new Error(`Failed to fetch history: ${response.statusText}`);
      }
      const data = await response.json();
      setHistory(data);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Unknown error'));
      throw err;
    }
  }, [symbol]);

  /**
   * Fetch regime statistics
   */
  const fetchStatistics = useCallback(async (): Promise<void> => {
    try {
      const response = await fetch(`/api/v1/regime/statistics?symbol=${symbol}`);
      if (!response.ok) {
        throw new Error(`Failed to fetch statistics: ${response.statusText}`);
      }
      const data = await response.json();
      setStatistics(data);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Unknown error'));
      throw err;
    }
  }, [symbol]);

  /**
   * Fetch all regime data
   */
  const refresh = useCallback(async (): Promise<void> => {
    setIsLoading(true);
    setError(null);

    try {
      await Promise.all([fetchCurrent(), fetchHistory(), fetchStatistics()]);
    } catch (err) {
      // Error already set in individual fetch functions
      console.error('Failed to refresh regime data:', err);
    } finally {
      setIsLoading(false);
    }
  }, [fetchCurrent, fetchHistory, fetchStatistics]);

  /**
   * Handle WebSocket messages
   */
  const handleWebSocketMessage = useCallback((event: MessageEvent) => {
    try {
      const data = JSON.parse(event.data);

      if (data.type === 'regime_update') {
        setCurrent(data.classification);
      } else if (data.type === 'regime_change') {
        // Add alert for regime change
        const alert: RegimeAlert = {
          id: `alert-${Date.now()}`,
          timestamp: new Date().toISOString(),
          from_regime: data.from_regime,
          to_regime: data.to_regime,
          confidence: data.confidence,
          severity: data.confidence > 0.8 ? 'high' : data.confidence > 0.6 ? 'medium' : 'low',
          message: `Regime changed from ${data.from_regime} to ${data.to_regime}`,
          acknowledged: false,
        };
        setAlerts((prev) => [alert, ...prev].slice(0, 50));

        // Refresh data
        refresh();
      }
    } catch (err) {
      console.error('Failed to parse WebSocket message:', err);
    }
  }, [refresh]);

  /**
   * Setup WebSocket connection
   */
  const setupWebSocket = useCallback(() => {
    if (!enableWebSocket) return;

    try {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/api/v1/ws/regime?symbol=${symbol}`;

      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        console.log('Regime WebSocket connected');
      };

      ws.onmessage = handleWebSocketMessage;

      ws.onerror = (event) => {
        console.error('Regime WebSocket error:', event);
      };

      ws.onclose = () => {
        console.log('Regime WebSocket disconnected');
        // Attempt to reconnect after 5 seconds
        setTimeout(() => {
          if (wsRef.current === ws) {
            setupWebSocket();
          }
        }, 5000);
      };

      wsRef.current = ws;
    } catch (err) {
      console.error('Failed to setup WebSocket:', err);
    }
  }, [symbol, enableWebSocket, handleWebSocketMessage]);

  /**
   * Acknowledge an alert
   */
  const acknowledgeAlert = useCallback((alertId: string) => {
    setAlerts((prev) =>
      prev.map((alert) =>
        alert.id === alertId ? { ...alert, acknowledged: true } : alert
      )
    );
  }, []);

  /**
   * Initial data fetch
   */
  useEffect(() => {
    refresh();
  }, [refresh]);

  /**
   * Setup auto-refresh
   */
  useEffect(() => {
    if (!autoRefresh) return;

    refreshTimerRef.current = setInterval(() => {
      refresh();
    }, refreshInterval);

    return () => {
      if (refreshTimerRef.current) {
        clearInterval(refreshTimerRef.current);
      }
    };
  }, [autoRefresh, refreshInterval, refresh]);

  /**
   * Setup WebSocket
   */
  useEffect(() => {
    setupWebSocket();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [setupWebSocket]);

  return {
    current,
    history,
    statistics,
    alerts,
    isLoading,
    error,
    refresh,
    acknowledgeAlert,
  };
}
