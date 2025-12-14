/**
 * Hook for fetching and managing agent signals
 *
 * Provides real-time access to multi-agent analyst signals via REST API
 * and WebSocket connections for live updates.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import type { AnalystSignals } from '../../../types/trading';

/**
 * Debate argument from Bull or Bear analyst
 */
export interface DebateArgument {
  timestamp: string;
  speaker: 'bull' | 'bear';
  argument: string;
  evidence_references: string[];
  confidence: number;
}

/**
 * Complete debate transcript
 */
export interface Debate {
  symbol: string;
  timestamp: string;
  arguments: DebateArgument[];
  duration_seconds: number;
  total_exchanges: number;
}

/**
 * Verdict from debate outcome
 */
export interface DebateVerdict {
  recommendation: 'BUY' | 'SELL' | 'HOLD';
  strength: number;
  reasoning: string[];
  timestamp: string;
}

/**
 * Consensus calculation result
 */
export interface Consensus {
  recommendation: 'BUY' | 'SELL' | 'HOLD';
  weighted_score: number;
  confidence_interval: [number, number];
  contributing_factors: {
    name: string;
    weight: number;
    score: number;
    confidence: number;
  }[];
  timestamp: string;
}

/**
 * Evidence item from analyst
 */
export interface EvidenceItem {
  id: string;
  source: string;
  timestamp: string;
  data: Record<string, unknown>;
  relevance_score: number;
}

/**
 * Historical signal data point
 */
export interface SignalHistoryPoint {
  timestamp: string;
  market_analyst_score: number;
  news_analyst_score: number;
  social_sentiment_score: number;
  fundamental_analyst_score: number;
  macro_analyst_score: number;
  consensus: number;
}

/**
 * Signal history data
 */
export interface SignalHistory {
  symbol: string;
  timeframe: string;
  data_points: SignalHistoryPoint[];
  significant_events: {
    timestamp: string;
    event_type: string;
    description: string;
    impact: number;
  }[];
}

/**
 * Hook options
 */
export interface UseAgentSignalsOptions {
  symbol: string;
  enableWebSocket?: boolean;
  refreshInterval?: number;
}

/**
 * Hook return value
 */
export interface UseAgentSignalsResult {
  signals: AnalystSignals | null;
  debate: Debate | null;
  verdict: DebateVerdict | null;
  consensus: Consensus | null;
  evidence: EvidenceItem[];
  history: SignalHistory | null;
  isLoading: boolean;
  error: Error | null;
  refresh: () => Promise<void>;
}

const API_BASE_URL = '/api/v1';

/**
 * Custom hook for fetching agent signals with real-time updates
 */
export const useAgentSignals = ({
  symbol,
  enableWebSocket = true,
  refreshInterval = 30000,
}: UseAgentSignalsOptions): UseAgentSignalsResult => {
  const [signals, setSignals] = useState<AnalystSignals | null>(null);
  const [debate, setDebate] = useState<Debate | null>(null);
  const [verdict, setVerdict] = useState<DebateVerdict | null>(null);
  const [consensus, setConsensus] = useState<Consensus | null>(null);
  const [evidence, setEvidence] = useState<EvidenceItem[]>([]);
  const [history, setHistory] = useState<SignalHistory | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<Error | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const refreshTimerRef = useRef<NodeJS.Timeout | null>(null);

  /**
   * Fetch signals from REST API
   */
  const fetchSignals = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);

      const response = await fetch(`${API_BASE_URL}/agents/signals/${symbol}`);
      if (!response.ok) {
        throw new Error(`Failed to fetch signals: ${response.statusText}`);
      }

      const data = await response.json();
      setSignals(data.signals);
      setDebate(data.debate || null);
      setVerdict(data.verdict || null);
      setConsensus(data.consensus || null);
      setEvidence(data.evidence || []);
      setHistory(data.history || null);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Unknown error'));
    } finally {
      setIsLoading(false);
    }
  }, [symbol]);

  /**
   * Connect to WebSocket for real-time updates
   */
  const connectWebSocket = useCallback(() => {
    if (!enableWebSocket) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/v1/agents/signals/${symbol}/ws`;

    try {
      wsRef.current = new WebSocket(wsUrl);

      wsRef.current.onopen = () => {
        console.log('WebSocket connected for agent signals');
      };

      wsRef.current.onmessage = (event) => {
        try {
          const update = JSON.parse(event.data);

          if (update.type === 'signals') {
            setSignals(update.data);
          } else if (update.type === 'debate') {
            setDebate(update.data);
          } else if (update.type === 'verdict') {
            setVerdict(update.data);
          } else if (update.type === 'consensus') {
            setConsensus(update.data);
          } else if (update.type === 'evidence') {
            setEvidence((prev) => [...prev, update.data]);
          } else if (update.type === 'history') {
            setHistory(update.data);
          }
        } catch (err) {
          console.error('Failed to parse WebSocket message:', err);
        }
      };

      wsRef.current.onerror = (event) => {
        console.error('WebSocket error:', event);
        setError(new Error('WebSocket connection error'));
      };

      wsRef.current.onclose = () => {
        console.log('WebSocket disconnected');
        // Attempt to reconnect after 5 seconds
        setTimeout(() => {
          if (enableWebSocket) {
            connectWebSocket();
          }
        }, 5000);
      };
    } catch (err) {
      console.error('Failed to create WebSocket:', err);
      setError(err instanceof Error ? err : new Error('WebSocket error'));
    }
  }, [symbol, enableWebSocket]);

  /**
   * Disconnect WebSocket
   */
  const disconnectWebSocket = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  /**
   * Refresh data manually
   */
  const refresh = useCallback(async () => {
    await fetchSignals();
  }, [fetchSignals]);

  // Initial fetch
  useEffect(() => {
    fetchSignals();
  }, [fetchSignals]);

  // Setup WebSocket connection
  useEffect(() => {
    if (enableWebSocket) {
      connectWebSocket();
    }

    return () => {
      disconnectWebSocket();
    };
  }, [enableWebSocket, connectWebSocket, disconnectWebSocket]);

  // Setup polling interval
  useEffect(() => {
    if (refreshInterval > 0 && !enableWebSocket) {
      refreshTimerRef.current = setInterval(() => {
        fetchSignals();
      }, refreshInterval);
    }

    return () => {
      if (refreshTimerRef.current) {
        clearInterval(refreshTimerRef.current);
      }
    };
  }, [refreshInterval, enableWebSocket, fetchSignals]);

  return {
    signals,
    debate,
    verdict,
    consensus,
    evidence,
    history,
    isLoading,
    error,
    refresh,
  };
};
