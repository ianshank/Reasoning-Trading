import React, { useMemo } from 'react';
import type { RegimeTrigger } from './hooks/useLambdaStats';

export interface RegimeTriggerTimelineProps {
  triggers: RegimeTrigger[];
  timeframe?: '1h' | '6h' | '24h' | '7d' | 'all';
  className?: string;
}

const ACTION_CONFIG: Record<
  RegimeTrigger['action'],
  { label: string; color: string; bgColor: string; icon: string }
> = {
  trigger_batch: {
    label: 'Trigger Batch',
    color: 'text-blue-700 dark:text-blue-300',
    bgColor: 'bg-blue-100 dark:bg-blue-900/30',
    icon: '▶',
  },
  invalidate_cache: {
    label: 'Invalidate Cache',
    color: 'text-red-700 dark:text-red-300',
    bgColor: 'bg-red-100 dark:bg-red-900/30',
    icon: '✕',
  },
  update_policies: {
    label: 'Update Policies',
    color: 'text-purple-700 dark:text-purple-300',
    bgColor: 'bg-purple-100 dark:bg-purple-900/30',
    icon: '↻',
  },
  alert_only: {
    label: 'Alert Only',
    color: 'text-yellow-700 dark:text-yellow-300',
    bgColor: 'bg-yellow-100 dark:bg-yellow-900/30',
    icon: '!',
  },
};

export function RegimeTriggerTimeline({
  triggers,
  timeframe = 'all',
  className = '',
}: RegimeTriggerTimelineProps): React.ReactElement {
  const filteredTriggers = useMemo(() => {
    if (timeframe === 'all') return triggers;

    const now = new Date();
    const cutoffTimes: Record<string, number> = {
      '1h': 60 * 60 * 1000,
      '6h': 6 * 60 * 60 * 1000,
      '24h': 24 * 60 * 60 * 1000,
      '7d': 7 * 24 * 60 * 60 * 1000,
    };

    const cutoff = cutoffTimes[timeframe];
    if (!cutoff) return triggers;

    return triggers.filter((trigger) => {
      const triggerTime = new Date(trigger.triggeredAt).getTime();
      return now.getTime() - triggerTime <= cutoff;
    });
  }, [triggers, timeframe]);

  const formatDateTime = (dateString: string): string => {
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

  const getRegimeColor = (regime: string): string => {
    const regimeLower = regime.toLowerCase();
    if (regimeLower.includes('volatile')) return 'text-red-600 dark:text-red-400';
    if (regimeLower.includes('trending_up')) return 'text-green-600 dark:text-green-400';
    if (regimeLower.includes('trending_down')) return 'text-orange-600 dark:text-orange-400';
    if (regimeLower.includes('mean_reverting')) return 'text-blue-600 dark:text-blue-400';
    return 'text-gray-600 dark:text-gray-400';
  };

  if (filteredTriggers.length === 0) {
    return (
      <div
        className={`bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 ${className}`}
        role="region"
        aria-label="Regime trigger timeline"
      >
        <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100 mb-6">
          Regime Change Timeline
        </h2>
        <div className="text-center text-gray-500 dark:text-gray-400 py-8">
          No regime changes in the selected timeframe
        </div>
      </div>
    );
  }

  return (
    <div
      className={`bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 ${className}`}
      role="region"
      aria-label="Regime trigger timeline"
    >
      <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100 mb-6">
        Regime Change Timeline
      </h2>

      <div className="relative">
        {/* Timeline line */}
        <div
          className="absolute left-6 top-0 bottom-0 w-0.5 bg-gray-300 dark:bg-gray-700"
          aria-hidden="true"
        />

        {/* Timeline items */}
        <div className="space-y-6">
          {filteredTriggers.map((trigger, index) => {
            const actionConfig = ACTION_CONFIG[trigger.action];

            return (
              <div key={index} className="relative flex gap-4">
                {/* Timeline dot */}
                <div
                  className={`flex-shrink-0 w-12 h-12 rounded-full ${actionConfig.bgColor} flex items-center justify-center z-10`}
                  aria-hidden="true"
                >
                  <span className={`text-lg ${actionConfig.color}`}>{actionConfig.icon}</span>
                </div>

                {/* Content */}
                <div className="flex-1 pb-6">
                  <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
                    <div className="flex items-start justify-between mb-2">
                      <div>
                        <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                          Regime Change Detected
                        </h3>
                        <p className="text-xs text-gray-500 dark:text-gray-400">
                          {formatDateTime(trigger.triggeredAt)}
                        </p>
                      </div>
                      {trigger.completed ? (
                        <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900/50 dark:text-green-200">
                          Completed
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800 dark:bg-yellow-900/50 dark:text-yellow-200">
                          Pending
                        </span>
                      )}
                    </div>

                    <div className="space-y-2 text-sm">
                      <div className="flex items-center gap-2">
                        <span className="text-gray-600 dark:text-gray-400">From:</span>
                        <span className={`font-medium ${getRegimeColor(trigger.previousRegime)}`}>
                          {trigger.previousRegime}
                        </span>
                        <span className="text-gray-400">→</span>
                        <span className={`font-medium ${getRegimeColor(trigger.newRegime)}`}>
                          {trigger.newRegime}
                        </span>
                      </div>

                      <div className="flex items-center gap-2">
                        <span className="text-gray-600 dark:text-gray-400">Confidence:</span>
                        <span className="font-medium text-gray-900 dark:text-gray-100">
                          {(trigger.confidence * 100).toFixed(1)}%
                        </span>
                      </div>

                      <div className="flex items-center gap-2">
                        <span className="text-gray-600 dark:text-gray-400">Action:</span>
                        <span className={`inline-flex items-center px-2 py-0.5 rounded ${actionConfig.bgColor} ${actionConfig.color} text-xs font-medium`}>
                          {actionConfig.label}
                        </span>
                      </div>

                      {trigger.batchJobId && (
                        <div className="flex items-center gap-2">
                          <span className="text-gray-600 dark:text-gray-400">Job ID:</span>
                          <span className="font-mono text-xs text-gray-700 dark:text-gray-300">
                            {trigger.batchJobId}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {filteredTriggers.length > 0 && (
        <div className="mt-6 pt-4 border-t border-gray-200 dark:border-gray-700">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <div className="text-xs text-gray-600 dark:text-gray-400">Total Changes</div>
              <div className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                {filteredTriggers.length}
              </div>
            </div>
            <div>
              <div className="text-xs text-gray-600 dark:text-gray-400">Batch Triggers</div>
              <div className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                {filteredTriggers.filter((t) => t.action === 'trigger_batch').length}
              </div>
            </div>
            <div>
              <div className="text-xs text-gray-600 dark:text-gray-400">Cache Invalidations</div>
              <div className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                {filteredTriggers.filter((t) => t.action === 'invalidate_cache').length}
              </div>
            </div>
            <div>
              <div className="text-xs text-gray-600 dark:text-gray-400">Completed</div>
              <div className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                {filteredTriggers.filter((t) => t.completed).length}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
