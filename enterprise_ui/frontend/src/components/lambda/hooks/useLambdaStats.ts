import { useState, useEffect, useCallback } from 'react';

export interface BatchStats {
  isRunning: boolean;
  pendingJobs: number;
  runningJobs: number;
  completedJobs: number;
  totalResults: number;
  lastBatchTime: string | null;
  lastRunDuration: number | null;
  nextScheduledRun: string | null;
  symbolsProcessed: number;
  successRate: number;
  avgConfidence: number;
}

export interface SpeedMetrics {
  avgLatencyMs: number;
  p50LatencyMs: number;
  p95LatencyMs: number;
  p99LatencyMs: number;
  maxLatencyMs: number;
  policyNetworkPct: number;
  cacheHitPct: number;
  heuristicPct: number;
  mctsLitePct: number;
  totalDecisions: number;
  decisionsPerSecond: number;
  avgConfidence: number;
  errorRate: number;
}

export interface CacheStats {
  backend: string;
  totalEntries: number;
  activeEntries: number;
  expiredEntries: number;
  semanticIndexSize: number;
  totalAccesses: number;
  maxEntries: number;
  hitRate: number;
  avgTtl: number;
  popularKeys: Array<{ key: string; accessCount: number }>;
}

export interface RegimeTrigger {
  previousRegime: string;
  newRegime: string;
  confidence: number;
  action: 'trigger_batch' | 'invalidate_cache' | 'update_policies' | 'alert_only';
  triggeredAt: string;
  batchJobId: string | null;
  completed: boolean;
}

export interface LambdaStats {
  currentRegime: string;
  regimeConfidence: number;
  regimeSince: string;
  totalTriggers: number;
  recentTriggers: RegimeTrigger[];
  batchLayer: BatchStats;
  speedLayer: SpeedMetrics;
  servingLayer: CacheStats;
}

interface UseLambdaStatsResult {
  stats: LambdaStats | null;
  batchStats: BatchStats | null;
  speedStats: SpeedMetrics | null;
  cacheStats: CacheStats | null;
  triggers: RegimeTrigger[];
  isLoading: boolean;
  error: Error | null;
  refresh: () => Promise<void>;
}

const DEFAULT_POLLING_INTERVAL = 5000; // 5 seconds

export function useLambdaStats(
  pollingInterval: number = DEFAULT_POLLING_INTERVAL,
  autoRefresh: boolean = true
): UseLambdaStatsResult {
  const [stats, setStats] = useState<LambdaStats | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchStats = useCallback(async () => {
    try {
      setError(null);
      const response = await fetch('/api/lambda/stats');

      if (!response.ok) {
        throw new Error(`Failed to fetch Lambda stats: ${response.statusText}`);
      }

      const data: LambdaStats = await response.json();
      setStats(data);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Unknown error'));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStats();

    if (autoRefresh && pollingInterval > 0) {
      const intervalId = setInterval(fetchStats, pollingInterval);
      return () => clearInterval(intervalId);
    }
  }, [fetchStats, autoRefresh, pollingInterval]);

  return {
    stats,
    batchStats: stats?.batchLayer ?? null,
    speedStats: stats?.speedLayer ?? null,
    cacheStats: stats?.servingLayer ?? null,
    triggers: stats?.recentTriggers ?? [],
    isLoading,
    error,
    refresh: fetchStats,
  };
}
