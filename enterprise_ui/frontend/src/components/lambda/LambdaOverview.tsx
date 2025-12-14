import React from 'react';
import { LayerHealthIndicator, type LayerStatus } from './LayerHealthIndicator';
import type { LambdaStats } from './hooks/useLambdaStats';

export interface LambdaOverviewProps {
  stats: LambdaStats;
  currentRegime?: string;
  className?: string;
}

const REGIME_COLORS: Record<string, string> = {
  volatile: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-200',
  high_volatility: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-200',
  trending_up: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-200',
  trending_down: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-200',
  mean_reverting: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-200',
  unknown: 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-200',
};

export function LambdaOverview({
  stats,
  currentRegime,
  className = '',
}: LambdaOverviewProps): React.ReactElement {
  const regime = currentRegime || stats.currentRegime;

  const getLayerStatus = (layer: 'batch' | 'speed' | 'serving'): LayerStatus => {
    if (layer === 'batch') {
      if (stats.batchLayer.isRunning) return 'healthy';
      if (stats.batchLayer.successRate < 0.8) return 'unhealthy';
      if (stats.batchLayer.successRate < 0.95) return 'degraded';
      return 'healthy';
    }

    if (layer === 'speed') {
      if (stats.speedLayer.errorRate > 0.05) return 'unhealthy';
      if (stats.speedLayer.errorRate > 0.01 || stats.speedLayer.p95LatencyMs > 100)
        return 'degraded';
      return 'healthy';
    }

    if (layer === 'serving') {
      if (stats.servingLayer.hitRate < 0.5) return 'unhealthy';
      if (stats.servingLayer.hitRate < 0.7) return 'degraded';
      return 'healthy';
    }

    return 'unknown';
  };

  const formatTimeSince = (dateString: string): string => {
    try {
      const date = new Date(dateString);
      const now = new Date();
      const diffMs = now.getTime() - date.getTime();
      const diffMins = Math.floor(diffMs / 60000);
      const diffHours = Math.floor(diffMins / 60);
      const diffDays = Math.floor(diffHours / 24);

      if (diffDays > 0) return `${diffDays}d ago`;
      if (diffHours > 0) return `${diffHours}h ago`;
      if (diffMins > 0) return `${diffMins}m ago`;
      return 'just now';
    } catch {
      return 'unknown';
    }
  };

  const regimeColorClass =
    REGIME_COLORS[regime.toLowerCase()] || REGIME_COLORS.unknown;

  return (
    <div
      className={`bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 ${className}`}
      role="region"
      aria-label="Lambda architecture overview"
    >
      <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-6">
        Lambda Architecture Overview
      </h2>

      {/* Architecture Diagram */}
      <div className="mb-8 p-6 bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
          Data Flow Architecture
        </h3>

        <div className="flex flex-col md:flex-row items-center justify-around gap-6">
          {/* Batch Layer */}
          <div className="flex flex-col items-center">
            <div className="w-32 h-32 rounded-lg bg-blue-500 dark:bg-blue-600 flex items-center justify-center shadow-lg">
              <div className="text-center text-white">
                <div className="text-2xl font-bold mb-1">Batch</div>
                <div className="text-xs opacity-90">Strategic</div>
              </div>
            </div>
            <div className="mt-2 text-xs text-gray-600 dark:text-gray-400 text-center">
              Deep MCTS
              <br />
              Overnight Planning
            </div>
          </div>

          {/* Flow Arrow */}
          <div className="hidden md:block text-gray-400 dark:text-gray-600 text-4xl" aria-hidden="true">
            →
          </div>
          <div className="md:hidden text-gray-400 dark:text-gray-600 text-4xl rotate-90" aria-hidden="true">
            →
          </div>

          {/* Serving Layer */}
          <div className="flex flex-col items-center">
            <div className="w-32 h-32 rounded-lg bg-green-500 dark:bg-green-600 flex items-center justify-center shadow-lg">
              <div className="text-center text-white">
                <div className="text-2xl font-bold mb-1">Serving</div>
                <div className="text-xs opacity-90">Cache</div>
              </div>
            </div>
            <div className="mt-2 text-xs text-gray-600 dark:text-gray-400 text-center">
              Policy Cache
              <br />
              Semantic Lookup
            </div>
          </div>

          {/* Flow Arrow */}
          <div className="hidden md:block text-gray-400 dark:text-gray-600 text-4xl" aria-hidden="true">
            ⇄
          </div>
          <div className="md:hidden text-gray-400 dark:text-gray-600 text-4xl rotate-90" aria-hidden="true">
            ⇄
          </div>

          {/* Speed Layer */}
          <div className="flex flex-col items-center">
            <div className="w-32 h-32 rounded-lg bg-purple-500 dark:bg-purple-600 flex items-center justify-center shadow-lg">
              <div className="text-center text-white">
                <div className="text-2xl font-bold mb-1">Speed</div>
                <div className="text-xs opacity-90">Realtime</div>
              </div>
            </div>
            <div className="mt-2 text-xs text-gray-600 dark:text-gray-400 text-center">
              Policy Network
              <br />
              Sub-100ms
            </div>
          </div>
        </div>
      </div>

      {/* Current Regime */}
      <div className="mb-6 p-4 rounded-lg border border-gray-200 dark:border-gray-700">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-3">
          Current Market Regime
        </h3>
        <div className="flex items-center justify-between">
          <div>
            <span className={`inline-flex items-center px-3 py-1 rounded-full text-lg font-medium ${regimeColorClass}`}>
              {regime}
            </span>
            <div className="mt-2 text-sm text-gray-600 dark:text-gray-400">
              Confidence: {(stats.regimeConfidence * 100).toFixed(1)}%
            </div>
          </div>
          <div className="text-right">
            <div className="text-xs text-gray-600 dark:text-gray-400">Active Since</div>
            <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
              {formatTimeSince(stats.regimeSince)}
            </div>
          </div>
        </div>
      </div>

      {/* Layer Status Indicators */}
      <div className="grid md:grid-cols-3 gap-4 mb-6">
        <LayerHealthIndicator
          layer="batch"
          status={getLayerStatus('batch')}
          metrics={{
            pendingJobs: stats.batchLayer.pendingJobs,
            successRate: `${(stats.batchLayer.successRate * 100).toFixed(1)}%`,
          }}
        />
        <LayerHealthIndicator
          layer="speed"
          status={getLayerStatus('speed')}
          metrics={{
            avgLatency: `${stats.speedLayer.avgLatencyMs.toFixed(1)}ms`,
            throughput: `${stats.speedLayer.decisionsPerSecond.toFixed(1)}/s`,
          }}
        />
        <LayerHealthIndicator
          layer="serving"
          status={getLayerStatus('serving')}
          metrics={{
            hitRate: `${(stats.servingLayer.hitRate * 100).toFixed(1)}%`,
            entries: stats.servingLayer.activeEntries,
          }}
        />
      </div>

      {/* Regime Triggers Summary */}
      <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
            Regime Changes
          </h3>
          <span className="text-2xl font-bold text-gray-900 dark:text-gray-100">
            {stats.totalTriggers}
          </span>
        </div>
        {stats.recentTriggers.length > 0 && (
          <div className="mt-2 text-xs text-gray-600 dark:text-gray-400">
            Last change: {formatTimeSince(stats.recentTriggers[0].triggeredAt)} (
            {stats.recentTriggers[0].previousRegime} → {stats.recentTriggers[0].newRegime})
          </div>
        )}
      </div>
    </div>
  );
}
