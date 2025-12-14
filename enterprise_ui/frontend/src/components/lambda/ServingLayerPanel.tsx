import React, { useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import type { CacheStats } from './hooks/useLambdaStats';

export interface ServingLayerPanelProps {
  cacheStats: CacheStats;
  onInvalidate?: (key?: string) => Promise<void>;
  className?: string;
}

export function ServingLayerPanel({
  cacheStats,
  onInvalidate,
  className = '',
}: ServingLayerPanelProps): React.ReactElement {
  const [isInvalidating, setIsInvalidating] = useState(false);

  const handleInvalidateAll = async () => {
    if (!onInvalidate || isInvalidating) return;

    if (!confirm('Are you sure you want to invalidate the entire cache?')) {
      return;
    }

    setIsInvalidating(true);
    try {
      await onInvalidate();
    } finally {
      setIsInvalidating(false);
    }
  };

  const handleInvalidateKey = async (key: string) => {
    if (!onInvalidate || isInvalidating) return;

    setIsInvalidating(true);
    try {
      await onInvalidate(key);
    } finally {
      setIsInvalidating(false);
    }
  };

  const capacityPct = (cacheStats.totalEntries / cacheStats.maxEntries) * 100;

  const getCapacityColor = () => {
    if (capacityPct < 70) return 'bg-green-500';
    if (capacityPct < 90) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  const getHitRateColor = () => {
    if (cacheStats.hitRate >= 0.8) return 'text-green-600 dark:text-green-400';
    if (cacheStats.hitRate >= 0.6) return 'text-yellow-600 dark:text-yellow-400';
    return 'text-red-600 dark:text-red-400';
  };

  return (
    <div
      className={`bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 ${className}`}
      role="region"
      aria-label="Serving layer panel"
    >
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100">
          Serving Layer (Cache)
        </h2>
        <button
          onClick={handleInvalidateAll}
          disabled={isInvalidating || !onInvalidate}
          className="px-4 py-2 bg-red-600 hover:bg-red-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-white rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2"
          aria-label="Invalidate entire cache"
        >
          {isInvalidating ? 'Invalidating...' : 'Invalidate Cache'}
        </button>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="p-3 rounded-lg bg-gray-50 dark:bg-gray-900">
          <div className="text-xs text-gray-600 dark:text-gray-400 mb-1">Backend</div>
          <div className="text-lg font-semibold text-gray-900 dark:text-gray-100 capitalize">
            {cacheStats.backend}
          </div>
        </div>

        <div className="p-3 rounded-lg bg-gray-50 dark:bg-gray-900">
          <div className="text-xs text-gray-600 dark:text-gray-400 mb-1">Hit Rate</div>
          <div className={`text-lg font-semibold ${getHitRateColor()}`}>
            {(cacheStats.hitRate * 100).toFixed(1)}%
          </div>
        </div>

        <div className="p-3 rounded-lg bg-gray-50 dark:bg-gray-900">
          <div className="text-xs text-gray-600 dark:text-gray-400 mb-1">Total Entries</div>
          <div className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            {cacheStats.totalEntries.toLocaleString()}
          </div>
        </div>

        <div className="p-3 rounded-lg bg-gray-50 dark:bg-gray-900">
          <div className="text-xs text-gray-600 dark:text-gray-400 mb-1">Active Entries</div>
          <div className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            {cacheStats.activeEntries.toLocaleString()}
          </div>
        </div>
      </div>

      <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4 mb-6">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-3">
          Cache Capacity
        </h3>
        <div className="mb-2">
          <div className="flex justify-between text-sm mb-1">
            <span className="text-gray-600 dark:text-gray-400">
              {cacheStats.totalEntries.toLocaleString()} / {cacheStats.maxEntries.toLocaleString()} entries
            </span>
            <span className="font-medium text-gray-900 dark:text-gray-100">
              {capacityPct.toFixed(1)}%
            </span>
          </div>
          <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2.5">
            <div
              className={`h-2.5 rounded-full transition-all ${getCapacityColor()}`}
              style={{ width: `${Math.min(capacityPct, 100)}%` }}
              role="progressbar"
              aria-valuenow={capacityPct}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label="Cache capacity percentage"
            />
          </div>
        </div>
        <div className="grid grid-cols-3 gap-4 mt-4 text-sm">
          <div>
            <div className="text-xs text-gray-600 dark:text-gray-400">Expired</div>
            <div className="font-medium text-gray-900 dark:text-gray-100">
              {cacheStats.expiredEntries.toLocaleString()}
            </div>
          </div>
          <div>
            <div className="text-xs text-gray-600 dark:text-gray-400">Total Accesses</div>
            <div className="font-medium text-gray-900 dark:text-gray-100">
              {cacheStats.totalAccesses.toLocaleString()}
            </div>
          </div>
          <div>
            <div className="text-xs text-gray-600 dark:text-gray-400">Avg TTL</div>
            <div className="font-medium text-gray-900 dark:text-gray-100">
              {Math.floor(cacheStats.avgTtl / 60)}m
            </div>
          </div>
        </div>
      </div>

      <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4 mb-6">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-3">
          Semantic Index
        </h3>
        <div className="flex items-center justify-between">
          <span className="text-xs text-gray-600 dark:text-gray-400">Index Size</span>
          <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
            {cacheStats.semanticIndexSize.toLocaleString()} entries
          </span>
        </div>
      </div>

      {cacheStats.popularKeys.length > 0 && (
        <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-4">
            Popular Keys
          </h3>

          <div className="mb-4">
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={cacheStats.popularKeys.slice(0, 5)}>
                <CartesianGrid
                  strokeDasharray="3 3"
                  className="stroke-gray-200 dark:stroke-gray-700"
                />
                <XAxis
                  dataKey="key"
                  className="text-xs text-gray-600 dark:text-gray-400"
                  stroke="currentColor"
                  tickFormatter={(value) => value.substring(0, 8)}
                />
                <YAxis
                  className="text-xs text-gray-600 dark:text-gray-400"
                  stroke="currentColor"
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'rgb(31 41 55)',
                    border: '1px solid rgb(75 85 99)',
                    borderRadius: '0.5rem',
                  }}
                  labelStyle={{ color: 'rgb(229 231 235)' }}
                  itemStyle={{ color: 'rgb(156 163 175)' }}
                />
                <Bar dataKey="accessCount" fill="#3b82f6" />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="space-y-2 max-h-64 overflow-y-auto">
            {cacheStats.popularKeys.map((item, index) => (
              <div
                key={index}
                className="flex items-center justify-between p-2 rounded hover:bg-gray-50 dark:hover:bg-gray-900 transition-colors"
              >
                <div className="flex-1 min-w-0">
                  <div className="text-xs font-mono text-gray-700 dark:text-gray-300 truncate">
                    {item.key}
                  </div>
                  <div className="text-xs text-gray-500 dark:text-gray-500">
                    {item.accessCount.toLocaleString()} accesses
                  </div>
                </div>
                {onInvalidate && (
                  <button
                    onClick={() => handleInvalidateKey(item.key)}
                    disabled={isInvalidating}
                    className="ml-2 px-2 py-1 text-xs text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300 disabled:opacity-50 disabled:cursor-not-allowed"
                    aria-label={`Invalidate cache key ${item.key}`}
                  >
                    Invalidate
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
