import React from 'react';

export type LayerStatus = 'healthy' | 'degraded' | 'unhealthy' | 'unknown';

export interface LayerMetrics {
  [key: string]: number | string | boolean;
}

export interface LayerHealthIndicatorProps {
  layer: 'batch' | 'speed' | 'serving';
  status: LayerStatus;
  metrics?: LayerMetrics;
  alertCount?: number;
  className?: string;
}

const layerNames: Record<string, string> = {
  batch: 'Batch Layer',
  speed: 'Speed Layer',
  serving: 'Serving Layer',
};

const statusConfig: Record<
  LayerStatus,
  { bgClass: string; textClass: string; borderClass: string; label: string }
> = {
  healthy: {
    bgClass: 'bg-green-100 dark:bg-green-900/30',
    textClass: 'text-green-800 dark:text-green-200',
    borderClass: 'border-green-300 dark:border-green-700',
    label: 'Healthy',
  },
  degraded: {
    bgClass: 'bg-yellow-100 dark:bg-yellow-900/30',
    textClass: 'text-yellow-800 dark:text-yellow-200',
    borderClass: 'border-yellow-300 dark:border-yellow-700',
    label: 'Degraded',
  },
  unhealthy: {
    bgClass: 'bg-red-100 dark:bg-red-900/30',
    textClass: 'text-red-800 dark:text-red-200',
    borderClass: 'border-red-300 dark:border-red-700',
    label: 'Unhealthy',
  },
  unknown: {
    bgClass: 'bg-gray-100 dark:bg-gray-900/30',
    textClass: 'text-gray-800 dark:text-gray-200',
    borderClass: 'border-gray-300 dark:border-gray-700',
    label: 'Unknown',
  },
};

export function LayerHealthIndicator({
  layer,
  status,
  metrics,
  alertCount = 0,
  className = '',
}: LayerHealthIndicatorProps): React.ReactElement {
  const config = statusConfig[status];
  const layerName = layerNames[layer] || layer;

  return (
    <div
      className={`rounded-lg border-2 ${config.borderClass} ${config.bgClass} p-4 ${className}`}
      role="status"
      aria-label={`${layerName} status: ${config.label}`}
    >
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          {layerName}
        </h3>
        <div className="flex items-center gap-2">
          {alertCount > 0 && (
            <span
              className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800 dark:bg-red-900/50 dark:text-red-200"
              aria-label={`${alertCount} alerts`}
            >
              {alertCount} {alertCount === 1 ? 'Alert' : 'Alerts'}
            </span>
          )}
          <span
            className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${config.textClass}`}
            aria-label={`Status: ${config.label}`}
          >
            <span
              className={`w-2 h-2 rounded-full mr-2 ${
                status === 'healthy'
                  ? 'bg-green-500'
                  : status === 'degraded'
                  ? 'bg-yellow-500'
                  : status === 'unhealthy'
                  ? 'bg-red-500'
                  : 'bg-gray-500'
              }`}
              aria-hidden="true"
            />
            {config.label}
          </span>
        </div>
      </div>

      {metrics && Object.keys(metrics).length > 0 && (
        <div className="grid grid-cols-2 gap-3">
          {Object.entries(metrics).map(([key, value]) => (
            <div key={key} className="flex flex-col">
              <span className="text-xs text-gray-600 dark:text-gray-400 capitalize">
                {key.replace(/([A-Z])/g, ' $1').trim()}
              </span>
              <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                {typeof value === 'number' ? value.toLocaleString() : value}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
