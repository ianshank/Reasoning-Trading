import React from 'react';
import { DecisionSourceChart } from './DecisionSourceChart';
import { LatencyChart, type LatencyDataPoint } from './LatencyChart';
import type { SpeedMetrics } from './hooks/useLambdaStats';

export interface SpeedLayerPanelProps {
  speedMetrics: SpeedMetrics;
  latencyHistory?: LatencyDataPoint[];
  latencyThreshold?: number;
  className?: string;
}

export function SpeedLayerPanel({
  speedMetrics,
  latencyHistory = [],
  latencyThreshold = 100,
  className = '',
}: SpeedLayerPanelProps): React.ReactElement {
  const getLatencyColor = (latency: number, threshold: number) => {
    if (latency < threshold * 0.5) return 'text-green-600 dark:text-green-400';
    if (latency < threshold) return 'text-yellow-600 dark:text-yellow-400';
    return 'text-red-600 dark:text-red-400';
  };

  const getErrorRateColor = (errorRate: number) => {
    if (errorRate < 0.01) return 'text-green-600 dark:text-green-400';
    if (errorRate < 0.05) return 'text-yellow-600 dark:text-yellow-400';
    return 'text-red-600 dark:text-red-400';
  };

  return (
    <div
      className={`bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 ${className}`}
      role="region"
      aria-label="Speed layer panel"
    >
      <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100 mb-6">
        Speed Layer
      </h2>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="p-3 rounded-lg bg-gray-50 dark:bg-gray-900">
          <div className="text-xs text-gray-600 dark:text-gray-400 mb-1">Avg Latency</div>
          <div
            className={`text-lg font-semibold ${getLatencyColor(
              speedMetrics.avgLatencyMs,
              latencyThreshold
            )}`}
          >
            {speedMetrics.avgLatencyMs.toFixed(2)}ms
          </div>
        </div>

        <div className="p-3 rounded-lg bg-gray-50 dark:bg-gray-900">
          <div className="text-xs text-gray-600 dark:text-gray-400 mb-1">P95 Latency</div>
          <div
            className={`text-lg font-semibold ${getLatencyColor(
              speedMetrics.p95LatencyMs,
              latencyThreshold
            )}`}
          >
            {speedMetrics.p95LatencyMs.toFixed(2)}ms
          </div>
        </div>

        <div className="p-3 rounded-lg bg-gray-50 dark:bg-gray-900">
          <div className="text-xs text-gray-600 dark:text-gray-400 mb-1">Throughput</div>
          <div className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            {speedMetrics.decisionsPerSecond.toFixed(1)}/s
          </div>
        </div>

        <div className="p-3 rounded-lg bg-gray-50 dark:bg-gray-900">
          <div className="text-xs text-gray-600 dark:text-gray-400 mb-1">Error Rate</div>
          <div className={`text-lg font-semibold ${getErrorRateColor(speedMetrics.errorRate)}`}>
            {(speedMetrics.errorRate * 100).toFixed(2)}%
          </div>
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-6 mb-6">
        <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-4">
            Latency Distribution
          </h3>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-600 dark:text-gray-400">P50 (Median)</span>
              <span
                className={`text-sm font-medium ${getLatencyColor(
                  speedMetrics.p50LatencyMs,
                  latencyThreshold
                )}`}
              >
                {speedMetrics.p50LatencyMs.toFixed(2)}ms
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-600 dark:text-gray-400">P95</span>
              <span
                className={`text-sm font-medium ${getLatencyColor(
                  speedMetrics.p95LatencyMs,
                  latencyThreshold
                )}`}
              >
                {speedMetrics.p95LatencyMs.toFixed(2)}ms
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-600 dark:text-gray-400">P99</span>
              <span
                className={`text-sm font-medium ${getLatencyColor(
                  speedMetrics.p99LatencyMs,
                  latencyThreshold
                )}`}
              >
                {speedMetrics.p99LatencyMs.toFixed(2)}ms
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-600 dark:text-gray-400">Max</span>
              <span
                className={`text-sm font-medium ${getLatencyColor(
                  speedMetrics.maxLatencyMs,
                  latencyThreshold
                )}`}
              >
                {speedMetrics.maxLatencyMs.toFixed(2)}ms
              </span>
            </div>
          </div>
        </div>

        <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-4">
            Decision Sources
          </h3>
          <DecisionSourceChart
            sourceStats={{
              policyNetworkPct: speedMetrics.policyNetworkPct,
              cacheHitPct: speedMetrics.cacheHitPct,
              heuristicPct: speedMetrics.heuristicPct,
              mctsLitePct: speedMetrics.mctsLitePct,
            }}
          />
        </div>
      </div>

      {latencyHistory.length > 0 && (
        <div className="border-t border-gray-200 dark:border-gray-700 pt-6">
          <LatencyChart latencyHistory={latencyHistory} threshold={latencyThreshold} />
        </div>
      )}

      <div className="border-t border-gray-200 dark:border-gray-700 pt-4 mt-6">
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          <div>
            <div className="text-xs text-gray-600 dark:text-gray-400">Total Decisions</div>
            <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
              {speedMetrics.totalDecisions.toLocaleString()}
            </div>
          </div>
          <div>
            <div className="text-xs text-gray-600 dark:text-gray-400">Avg Confidence</div>
            <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
              {(speedMetrics.avgConfidence * 100).toFixed(1)}%
            </div>
          </div>
          <div>
            <div className="text-xs text-gray-600 dark:text-gray-400">Decisions/sec</div>
            <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
              {speedMetrics.decisionsPerSecond.toFixed(2)}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
