/**
 * WebSocket hook for MCTS real-time updates
 *
 * Connects to the MCTS WebSocket endpoint and manages tree state,
 * statistics, and search control for real-time visualization.
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import type { MCTSTree, MCTSNode, MCTSState, MCTSPhase } from '../../../types/mcts';

/**
 * MCTS search statistics
 */
export interface MCTSSearchStats {
  totalSimulations: number;
  timeElapsed: number;
  simulationsPerSecond: number;
  maxDepth: number;
  totalNodes: number;
  bestAction: string | null;
  rootValue: number;
  currentPhase: MCTSPhase;
  iteration: number;
}

/**
 * WebSocket message types
 */
type WSMessageType =
  | 'tree_update'
  | 'node_update'
  | 'stats_update'
  | 'iteration_complete'
  | 'search_complete'
  | 'search_started'
  | 'error'
  | 'connection_ack';

/**
 * WebSocket message structure
 */
interface WSMessage {
  type: WSMessageType;
  data: any;
  timestamp: string;
}

/**
 * Search configuration
 */
export interface MCTSSearchConfig {
  maxIterations: number;
  explorationConstant: number;
  temperature: number;
  usePolicyPrior: boolean;
  parallelSimulations: number;
  timeBudgetMs?: number;
}

/**
 * Hook return type
 */
export interface UseMCTSWebSocketReturn {
  treeData: MCTSTree | null;
  stats: MCTSSearchStats | null;
  isConnected: boolean;
  isSearching: boolean;
  error: string | null;
  startSearch: (config: MCTSSearchConfig) => void;
  stopSearch: () => void;
  resetSearch: () => void;
}

const DEFAULT_STATS: MCTSSearchStats = {
  totalSimulations: 0,
  timeElapsed: 0,
  simulationsPerSecond: 0,
  maxDepth: 0,
  totalNodes: 0,
  bestAction: null,
  rootValue: 0,
  currentPhase: 'selection' as MCTSPhase,
  iteration: 0,
};

/**
 * WebSocket hook for MCTS updates
 *
 * @param symbol - Trading symbol for the MCTS search
 * @param autoConnect - Whether to connect automatically on mount
 * @returns MCTS tree data, stats, and control functions
 *
 * @example
 * ```tsx
 * const { treeData, stats, isConnected, startSearch, stopSearch } =
 *   useMCTSWebSocket('AAPL');
 *
 * // Start search with configuration
 * startSearch({
 *   maxIterations: 100,
 *   explorationConstant: 1.414,
 *   temperature: 1.0,
 *   usePolicyPrior: true,
 *   parallelSimulations: 4,
 * });
 * ```
 */
export function useMCTSWebSocket(
  symbol: string,
  autoConnect: boolean = true
): UseMCTSWebSocketReturn {
  const [treeData, setTreeData] = useState<MCTSTree | null>(null);
  const [stats, setStats] = useState<MCTSSearchStats | null>(DEFAULT_STATS);
  const [isConnected, setIsConnected] = useState(false);
  const [isSearching, setIsSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttempts = 5;
  const reconnectDelayMs = 2000;

  /**
   * Handle incoming WebSocket messages
   */
  const handleMessage = useCallback((event: MessageEvent) => {
    try {
      const message: WSMessage = JSON.parse(event.data);

      switch (message.type) {
        case 'connection_ack':
          setIsConnected(true);
          setError(null);
          reconnectAttemptsRef.current = 0;
          break;

        case 'tree_update':
          setTreeData(message.data as MCTSTree);
          break;

        case 'node_update':
          // Update specific node in tree
          setTreeData((prev) => {
            if (!prev) return null;
            const node = message.data as MCTSNode;
            return {
              ...prev,
              nodes: {
                ...prev.nodes,
                [node.id]: node,
              },
            };
          });
          break;

        case 'stats_update':
          setStats(message.data as MCTSSearchStats);
          break;

        case 'iteration_complete':
          setStats((prev) => ({
            ...(prev || DEFAULT_STATS),
            iteration: message.data.iteration,
            totalSimulations: message.data.totalSimulations,
          }));
          break;

        case 'search_started':
          setIsSearching(true);
          setError(null);
          break;

        case 'search_complete':
          setIsSearching(false);
          setStats((prev) => ({
            ...(prev || DEFAULT_STATS),
            ...message.data,
          }));
          break;

        case 'error':
          setError(message.data.message || 'Unknown error occurred');
          setIsSearching(false);
          break;

        default:
          console.warn('Unknown message type:', message.type);
      }
    } catch (err) {
      console.error('Error parsing WebSocket message:', err);
      setError('Failed to parse WebSocket message');
    }
  }, []);

  /**
   * Connect to WebSocket
   */
  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    try {
      // Determine WebSocket URL
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = window.location.host;
      const wsUrl = `${protocol}//${host}/ws/mcts/${symbol}`;

      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        console.log(`WebSocket connected to ${wsUrl}`);
      };

      ws.onmessage = handleMessage;

      ws.onerror = (event) => {
        console.error('WebSocket error:', event);
        setError('WebSocket connection error');
      };

      ws.onclose = (event) => {
        console.log('WebSocket closed:', event.code, event.reason);
        setIsConnected(false);

        // Attempt reconnection
        if (
          !event.wasClean &&
          reconnectAttemptsRef.current < maxReconnectAttempts
        ) {
          reconnectAttemptsRef.current += 1;
          console.log(
            `Reconnecting... Attempt ${reconnectAttemptsRef.current}/${maxReconnectAttempts}`
          );

          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, reconnectDelayMs * reconnectAttemptsRef.current);
        } else if (reconnectAttemptsRef.current >= maxReconnectAttempts) {
          setError('Failed to reconnect after maximum attempts');
        }
      };

      wsRef.current = ws;
    } catch (err) {
      console.error('Error creating WebSocket:', err);
      setError('Failed to create WebSocket connection');
    }
  }, [symbol, handleMessage]);

  /**
   * Disconnect from WebSocket
   */
  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    setIsConnected(false);
  }, []);

  /**
   * Send message to WebSocket
   */
  const sendMessage = useCallback((type: string, data: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          type,
          data,
          timestamp: new Date().toISOString(),
        })
      );
    } else {
      console.error('WebSocket is not connected');
      setError('WebSocket is not connected');
    }
  }, []);

  /**
   * Start MCTS search
   */
  const startSearch = useCallback(
    (config: MCTSSearchConfig) => {
      sendMessage('start_search', config);
      setIsSearching(true);
    },
    [sendMessage]
  );

  /**
   * Stop MCTS search
   */
  const stopSearch = useCallback(() => {
    sendMessage('stop_search', {});
    setIsSearching(false);
  }, [sendMessage]);

  /**
   * Reset search state
   */
  const resetSearch = useCallback(() => {
    sendMessage('reset_search', {});
    setTreeData(null);
    setStats(DEFAULT_STATS);
    setIsSearching(false);
  }, [sendMessage]);

  /**
   * Connect on mount, disconnect on unmount
   */
  useEffect(() => {
    if (autoConnect) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [autoConnect, connect, disconnect]);

  return {
    treeData,
    stats,
    isConnected,
    isSearching,
    error,
    startSearch,
    stopSearch,
    resetSearch,
  };
}
