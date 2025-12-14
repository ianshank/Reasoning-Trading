import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';

export interface LatencyDataPoint {
  timestamp: string;
  p50: number;
  p95: number;
  p99: number;
}

export interface LatencyChartProps {
  latencyHistory: LatencyDataPoint[];
  threshold?: number;
  className?: string;
}

const PERCENTILE_COLORS = {
  p50: '#3b82f6', // blue-500
  p95: '#f59e0b', // amber-500
  p99: '#ef4444', // red-500
};

const PERCENTILE_LABELS: Record<string, string> = {
  p50: 'P50 (Median)',
  p95: 'P95',
  p99: 'P99',
};

export function LatencyChart({
  latencyHistory,
  threshold = 100,
  className = '',
}: LatencyChartProps): React.ReactElement {
  const formatTimestamp = (timestamp: string): string => {
    try {
      const date = new Date(timestamp);
      return date.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return timestamp;
    }
  };

  const formatLatency = (value: number): string => {
    return `${value.toFixed(2)}ms`;
  };

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg p-3">
          <p className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-2">
            {formatTimestamp(label)}
          </p>
          {payload.map((entry: any, index: number) => (
            <div key={index} className="flex items-center gap-2 text-sm">
              <div
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: entry.color }}
                aria-hidden="true"
              />
              <span className="text-gray-700 dark:text-gray-300">{entry.name}:</span>
              <span className="font-medium text-gray-900 dark:text-gray-100">
                {formatLatency(entry.value)}
              </span>
            </div>
          ))}
          {threshold && (
            <div className="mt-2 pt-2 border-t border-gray-200 dark:border-gray-700">
              <span className="text-xs text-gray-600 dark:text-gray-400">
                SLA: {formatLatency(threshold)}
              </span>
            </div>
          )}
        </div>
      );
    }
    return null;
  };

  if (latencyHistory.length === 0) {
    return (
      <div
        className={`flex items-center justify-center h-64 text-gray-500 dark:text-gray-400 ${className}`}
      >
        <p>No latency data available</p>
      </div>
    );
  }

  const maxLatency = Math.max(
    ...latencyHistory.flatMap((d) => [d.p50, d.p95, d.p99]),
    threshold * 1.2
  );

  return (
    <div className={`w-full ${className}`} role="img" aria-label="Latency distribution over time">
      <div className="mb-4 flex items-center justify-between">
        <h4 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
          Latency Percentiles
        </h4>
        {threshold && (
          <span className="text-xs text-gray-600 dark:text-gray-400">
            SLA Threshold: {formatLatency(threshold)}
          </span>
        )}
      </div>

      <ResponsiveContainer width="100%" height={300}>
        <LineChart
          data={latencyHistory}
          margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
        >
          <CartesianGrid
            strokeDasharray="3 3"
            className="stroke-gray-200 dark:stroke-gray-700"
          />
          <XAxis
            dataKey="timestamp"
            tickFormatter={formatTimestamp}
            className="text-xs text-gray-600 dark:text-gray-400"
            stroke="currentColor"
          />
          <YAxis
            tickFormatter={(value) => `${value}ms`}
            className="text-xs text-gray-600 dark:text-gray-400"
            stroke="currentColor"
            domain={[0, maxLatency]}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend
            wrapperStyle={{
              paddingTop: '10px',
            }}
            formatter={(value: string) => (
              <span className="text-sm text-gray-700 dark:text-gray-300">
                {PERCENTILE_LABELS[value] || value}
              </span>
            )}
          />
          {threshold && (
            <ReferenceLine
              y={threshold}
              stroke="#dc2626"
              strokeDasharray="5 5"
              strokeWidth={2}
              label={{
                value: 'SLA',
                position: 'right',
                fill: '#dc2626',
                fontSize: 12,
              }}
            />
          )}
          <Line
            type="monotone"
            dataKey="p50"
            stroke={PERCENTILE_COLORS.p50}
            strokeWidth={2}
            dot={{ r: 3 }}
            activeDot={{ r: 5 }}
            name="p50"
          />
          <Line
            type="monotone"
            dataKey="p95"
            stroke={PERCENTILE_COLORS.p95}
            strokeWidth={2}
            dot={{ r: 3 }}
            activeDot={{ r: 5 }}
            name="p95"
          />
          <Line
            type="monotone"
            dataKey="p99"
            stroke={PERCENTILE_COLORS.p99}
            strokeWidth={2}
            dot={{ r: 3 }}
            activeDot={{ r: 5 }}
            name="p99"
          />
        </LineChart>
      </ResponsiveContainer>

      <div className="mt-4 grid grid-cols-3 gap-3" role="list" aria-label="Current latency values">
        {latencyHistory.length > 0 && (
          <>
            <div className="p-2 rounded bg-blue-50 dark:bg-blue-900/20" role="listitem">
              <div className="text-xs text-gray-600 dark:text-gray-400">
                {PERCENTILE_LABELS.p50}
              </div>
              <div className="text-lg font-semibold text-blue-700 dark:text-blue-300">
                {formatLatency(latencyHistory[latencyHistory.length - 1].p50)}
              </div>
            </div>
            <div className="p-2 rounded bg-amber-50 dark:bg-amber-900/20" role="listitem">
              <div className="text-xs text-gray-600 dark:text-gray-400">
                {PERCENTILE_LABELS.p95}
              </div>
              <div className="text-lg font-semibold text-amber-700 dark:text-amber-300">
                {formatLatency(latencyHistory[latencyHistory.length - 1].p95)}
              </div>
            </div>
            <div className="p-2 rounded bg-red-50 dark:bg-red-900/20" role="listitem">
              <div className="text-xs text-gray-600 dark:text-gray-400">
                {PERCENTILE_LABELS.p99}
              </div>
              <div className="text-lg font-semibold text-red-700 dark:text-red-300">
                {formatLatency(latencyHistory[latencyHistory.length - 1].p99)}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
