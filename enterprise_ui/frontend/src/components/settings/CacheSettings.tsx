import React, { useState } from 'react';
import { Database, Trash2, Eye, EyeOff, RotateCcw, AlertTriangle } from 'lucide-react';
import { CacheSettings as CacheSettingsType, CacheStats } from './types';

interface CacheSettingsProps {
  config: CacheSettingsType | null;
  stats: CacheStats | null;
  onClear: () => Promise<void>;
  onChange: (updates: Partial<CacheSettingsType>) => void;
  onReset: () => void;
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
}

export function CacheSettings({
  config,
  stats,
  onClear,
  onChange,
  onReset,
}: CacheSettingsProps) {
  const [isRedisUrlVisible, setIsRedisUrlVisible] = useState(false);
  const [isClearing, setIsClearing] = useState(false);
  const [showClearDialog, setShowClearDialog] = useState(false);

  if (!config) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500 dark:text-gray-400">Loading cache settings...</p>
      </div>
    );
  }

  const maskRedisUrl = (url: string) => {
    try {
      const urlObj = new URL(url);
      if (urlObj.password) {
        return url.replace(urlObj.password, '••••••••');
      }
      return url;
    } catch {
      return url;
    }
  };

  const handleClearCache = async () => {
    setIsClearing(true);
    try {
      await onClear();
      setShowClearDialog(false);
    } catch (error) {
      console.error('Failed to clear cache:', error);
    } finally {
      setIsClearing(false);
    }
  };

  const hitRate = stats ? (stats.hit_rate * 100).toFixed(1) : '0.0';

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
          Cache Configuration
        </h2>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Configure Redis cache settings and view cache statistics
        </p>
      </div>

      {/* Cache Statistics */}
      {stats && (
        <div className="bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 rounded-lg p-6 border border-blue-200 dark:border-blue-800">
          <div className="flex items-center gap-2 mb-4">
            <Database className="w-5 h-5 text-blue-600 dark:text-blue-400" />
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              Cache Statistics
            </h3>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            <div>
              <div className="text-sm text-gray-600 dark:text-gray-400 mb-1">
                Total Keys
              </div>
              <div className="text-2xl font-bold text-gray-900 dark:text-white">
                {stats.total_keys.toLocaleString()}
              </div>
            </div>
            <div>
              <div className="text-sm text-gray-600 dark:text-gray-400 mb-1">
                Memory Used
              </div>
              <div className="text-2xl font-bold text-gray-900 dark:text-white">
                {stats.used_memory}
              </div>
            </div>
            <div>
              <div className="text-sm text-gray-600 dark:text-gray-400 mb-1">
                Hit Rate
              </div>
              <div className="text-2xl font-bold text-gray-900 dark:text-white">
                {hitRate}%
              </div>
            </div>
            <div>
              <div className="text-sm text-gray-600 dark:text-gray-400 mb-1">
                Total Hits
              </div>
              <div className="text-2xl font-bold text-gray-900 dark:text-white">
                {stats.total_hits.toLocaleString()}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Redis Configuration */}
      <div className="space-y-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
          Redis Configuration
        </h3>

        {/* Redis URL */}
        <div className="space-y-2">
          <label
            htmlFor="redis_url"
            className="block text-sm font-medium text-gray-900 dark:text-white"
          >
            Redis URL
          </label>
          <p className="text-xs text-gray-600 dark:text-gray-400">
            Connection string for Redis server
          </p>
          <div className="flex items-center gap-2">
            <input
              type="text"
              id="redis_url"
              value={isRedisUrlVisible ? config.redis_url : maskRedisUrl(config.redis_url)}
              onChange={(e) => onChange({ redis_url: e.target.value })}
              className="
                flex-1 px-4 py-2 bg-white dark:bg-gray-800
                border border-gray-300 dark:border-gray-600
                rounded-lg text-sm font-mono
                focus:ring-2 focus:ring-blue-500 focus:border-transparent
              "
              placeholder="redis://localhost:6379/0"
              aria-label="Redis URL"
            />
            <button
              type="button"
              onClick={() => setIsRedisUrlVisible(!isRedisUrlVisible)}
              className="
                p-2 text-gray-500 dark:text-gray-400
                hover:bg-gray-100 dark:hover:bg-gray-700
                rounded-lg transition-colors
              "
              aria-label={isRedisUrlVisible ? 'Hide Redis URL' : 'Show Redis URL'}
            >
              {isRedisUrlVisible ? (
                <EyeOff className="w-4 h-4" />
              ) : (
                <Eye className="w-4 h-4" />
              )}
            </button>
          </div>
        </div>

        {/* Cache TTL */}
        <div className="space-y-2">
          <label
            htmlFor="cache_ttl"
            className="block text-sm font-medium text-gray-900 dark:text-white"
          >
            Cache TTL (Time To Live)
          </label>
          <p className="text-xs text-gray-600 dark:text-gray-400">
            Default cache expiration time in seconds (60-86,400)
          </p>
          <div className="flex items-center gap-4">
            <input
              type="range"
              id="cache_ttl"
              min="60"
              max="86400"
              step="60"
              value={config.cache_ttl_seconds}
              onChange={(e) =>
                onChange({
                  cache_ttl_seconds: parseInt(e.target.value),
                })
              }
              className="flex-1 h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer"
              aria-valuemin={60}
              aria-valuemax={86400}
              aria-valuenow={config.cache_ttl_seconds}
            />
            <div className="flex items-center gap-2 w-40">
              <input
                type="number"
                min="60"
                max="86400"
                step="60"
                value={config.cache_ttl_seconds}
                onChange={(e) =>
                  onChange({
                    cache_ttl_seconds: parseInt(e.target.value) || 60,
                  })
                }
                className="w-24 px-3 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg text-sm"
                aria-label="Cache TTL value"
              />
              <span className="text-sm text-gray-600 dark:text-gray-400">sec</span>
            </div>
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-500">
            {config.cache_ttl_seconds < 3600
              ? `${Math.round(config.cache_ttl_seconds / 60)} minutes`
              : `${Math.round(config.cache_ttl_seconds / 3600)} hours`}
          </div>
        </div>
      </div>

      {/* Cache Management */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
          Cache Management
        </h3>

        <button
          onClick={() => setShowClearDialog(true)}
          disabled={isClearing}
          className="
            flex items-center gap-2 px-4 py-2 text-sm font-medium
            text-white bg-red-600 hover:bg-red-700
            dark:bg-red-500 dark:hover:bg-red-600
            rounded-lg transition-colors
            disabled:opacity-50 disabled:cursor-not-allowed
          "
        >
          <Trash2 className="w-4 h-4" />
          {isClearing ? 'Clearing Cache...' : 'Clear All Cache'}
        </button>

        <p className="text-xs text-gray-600 dark:text-gray-400">
          Clearing the cache will remove all cached data. This may temporarily slow down
          the system until the cache is rebuilt.
        </p>
      </div>

      {/* Quick TTL Presets */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
          Quick TTL Presets
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: '1 minute', value: 60 },
            { label: '15 minutes', value: 900 },
            { label: '1 hour', value: 3600 },
            { label: '24 hours', value: 86400 },
          ].map((preset) => (
            <button
              key={preset.value}
              onClick={() => onChange({ cache_ttl_seconds: preset.value })}
              className={`
                p-3 rounded-lg border-2 text-center transition-all
                ${
                  config.cache_ttl_seconds === preset.value
                    ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                    : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
                }
              `}
              aria-pressed={config.cache_ttl_seconds === preset.value}
            >
              <div className="font-medium text-sm text-gray-900 dark:text-white">
                {preset.label}
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Reset Button */}
      <div className="pt-6 border-t border-gray-200 dark:border-gray-700">
        <button
          onClick={onReset}
          className="
            flex items-center gap-2 px-4 py-2 text-sm font-medium
            text-gray-700 dark:text-gray-300
            hover:bg-gray-100 dark:hover:bg-gray-700
            rounded-lg transition-colors
          "
          aria-label="Reset cache settings to defaults"
        >
          <RotateCcw className="w-4 h-4" />
          Reset to Defaults
        </button>
      </div>

      {/* Clear Cache Confirmation Dialog */}
      {showClearDialog && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
          role="dialog"
          aria-modal="true"
          aria-labelledby="clear-cache-dialog-title"
        >
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full mx-4 p-6">
            <div className="flex items-start gap-4">
              <div className="flex-shrink-0 w-10 h-10 rounded-full bg-red-100 dark:bg-red-900/20 flex items-center justify-center">
                <AlertTriangle className="w-5 h-5 text-red-600 dark:text-red-400" />
              </div>
              <div className="flex-1">
                <h2
                  id="clear-cache-dialog-title"
                  className="text-lg font-semibold text-gray-900 dark:text-white mb-2"
                >
                  Clear all cache?
                </h2>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  This will delete all cached data from Redis. The cache will be rebuilt
                  automatically as needed, but this may temporarily impact performance.
                </p>
              </div>
            </div>

            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => setShowClearDialog(false)}
                disabled={isClearing}
                className="
                  px-4 py-2 text-sm font-medium
                  text-gray-700 dark:text-gray-300
                  hover:bg-gray-100 dark:hover:bg-gray-700
                  rounded-lg transition-colors
                  disabled:opacity-50 disabled:cursor-not-allowed
                "
              >
                Cancel
              </button>
              <button
                onClick={handleClearCache}
                disabled={isClearing}
                className="
                  px-4 py-2 text-sm font-medium
                  text-white bg-red-600 hover:bg-red-700
                  dark:bg-red-500 dark:hover:bg-red-600
                  rounded-lg transition-colors
                  disabled:opacity-50 disabled:cursor-not-allowed
                "
              >
                {isClearing ? 'Clearing...' : 'Clear Cache'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
