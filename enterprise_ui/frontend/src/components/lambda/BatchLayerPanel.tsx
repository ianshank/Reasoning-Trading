import React, { useState } from 'react';
import type { BatchStats } from './hooks/useLambdaStats';

export interface BatchLayerPanelProps {
  batchStats: BatchStats;
  onTriggerBatch?: () => void;
  className?: string;
}

export function BatchLayerPanel({
  batchStats,
  onTriggerBatch,
  className = '',
}: BatchLayerPanelProps): React.ReactElement {
  const [isTriggering, setIsTriggering] = useState(false);

  const handleTriggerBatch = async () => {
    if (!onTriggerBatch || isTriggering) return;

    setIsTriggering(true);
    try {
      await onTriggerBatch();
    } finally {
      setIsTriggering(false);
    }
  };

  const formatDuration = (seconds: number | null): string => {
    if (seconds === null) return 'N/A';

    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);

    if (hours > 0) {
      return `${hours}h ${minutes}m`;
    } else if (minutes > 0) {
      return `${minutes}m ${secs}s`;
    } else {
      return `${secs}s`;
    }
  };

  const formatDateTime = (dateString: string | null): string => {
    if (!dateString) return 'Never';

    try {
      const date = new Date(dateString);
      return date.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return 'Invalid date';
    }
  };

  const getStatusColor = () => {
    if (batchStats.isRunning) return 'text-blue-600 dark:text-blue-400';
    if (batchStats.successRate < 0.8) return 'text-red-600 dark:text-red-400';
    if (batchStats.successRate < 0.95) return 'text-yellow-600 dark:text-yellow-400';
    return 'text-green-600 dark:text-green-400';
  };

  return (
    <div
      className={`bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 ${className}`}
      role="region"
      aria-label="Batch layer panel"
    >
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100">
          Batch Layer
        </h2>
        <button
          onClick={handleTriggerBatch}
          disabled={isTriggering || batchStats.isRunning || !onTriggerBatch}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-white rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
          aria-label="Trigger manual batch processing"
        >
          {isTriggering ? 'Triggering...' : batchStats.isRunning ? 'Running' : 'Trigger Batch'}
        </button>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="p-3 rounded-lg bg-gray-50 dark:bg-gray-900">
          <div className="text-xs text-gray-600 dark:text-gray-400 mb-1">Status</div>
          <div className={`text-lg font-semibold ${getStatusColor()}`}>
            {batchStats.isRunning ? 'Running' : 'Idle'}
          </div>
        </div>

        <div className="p-3 rounded-lg bg-gray-50 dark:bg-gray-900">
          <div className="text-xs text-gray-600 dark:text-gray-400 mb-1">Pending Jobs</div>
          <div className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            {batchStats.pendingJobs.toLocaleString()}
          </div>
        </div>

        <div className="p-3 rounded-lg bg-gray-50 dark:bg-gray-900">
          <div className="text-xs text-gray-600 dark:text-gray-400 mb-1">Running Jobs</div>
          <div className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            {batchStats.runningJobs.toLocaleString()}
          </div>
        </div>

        <div className="p-3 rounded-lg bg-gray-50 dark:bg-gray-900">
          <div className="text-xs text-gray-600 dark:text-gray-400 mb-1">Completed Jobs</div>
          <div className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            {batchStats.completedJobs.toLocaleString()}
          </div>
        </div>
      </div>

      <div className="space-y-4">
        <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-3">
            Last Run
          </h3>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="text-xs text-gray-600 dark:text-gray-400">Time</div>
              <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                {formatDateTime(batchStats.lastBatchTime)}
              </div>
            </div>
            <div>
              <div className="text-xs text-gray-600 dark:text-gray-400">Duration</div>
              <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                {formatDuration(batchStats.lastRunDuration)}
              </div>
            </div>
          </div>
        </div>

        <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-3">
            Next Scheduled Run
          </h3>
          <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
            {formatDateTime(batchStats.nextScheduledRun)}
          </div>
        </div>

        <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-3">
            Processing Statistics
          </h3>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <div className="text-xs text-gray-600 dark:text-gray-400">Symbols Processed</div>
              <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                {batchStats.symbolsProcessed.toLocaleString()}
              </div>
            </div>
            <div>
              <div className="text-xs text-gray-600 dark:text-gray-400">Success Rate</div>
              <div className={`text-sm font-medium ${getStatusColor()}`}>
                {(batchStats.successRate * 100).toFixed(1)}%
              </div>
            </div>
            <div>
              <div className="text-xs text-gray-600 dark:text-gray-400">Avg Confidence</div>
              <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                {(batchStats.avgConfidence * 100).toFixed(1)}%
              </div>
            </div>
          </div>
        </div>

        <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-600 dark:text-gray-400">
              Total Results Cached
            </span>
            <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
              {batchStats.totalResults.toLocaleString()}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
