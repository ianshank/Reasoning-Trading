/**
 * MCTS Statistics Panel Component
 *
 * Displays real-time search statistics including simulations,
 * performance metrics, and search progress.
 */

import React from 'react';
import type { MCTSSearchStats } from './hooks/useMCTSWebSocket';
import { Card, CardHeader, CardBody } from '../ui/card';
import { Badge } from '../ui/badge';
import { Spinner } from '../ui/spinner';
import { MCTSPhase } from '../../types/mcts';

/**
 * MCTSStats component props
 */
export interface MCTSStatsProps {
  /**
   * Search statistics to display
   */
  stats: MCTSSearchStats | null;

  /**
   * Whether the search is currently running
   * @default false
   */
  isSearching?: boolean;

  /**
   * Additional CSS classes
   */
  className?: string;
}

/**
 * Get color for search phase badge
 */
function getPhaseColor(phase: MCTSPhase): string {
  switch (phase) {
    case MCTSPhase.SELECTION:
      return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200';
    case MCTSPhase.EXPANSION:
      return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200';
    case MCTSPhase.SIMULATION:
      return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200';
    case MCTSPhase.BACKPROPAGATION:
      return 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200';
    case MCTSPhase.COMPLETE:
      return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200';
    case MCTSPhase.ERROR:
      return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200';
    default:
      return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200';
  }
}

/**
 * Format time in human-readable format
 */
function formatTime(milliseconds: number): string {
  if (milliseconds < 1000) {
    return `${milliseconds.toFixed(0)}ms`;
  }
  if (milliseconds < 60000) {
    return `${(milliseconds / 1000).toFixed(1)}s`;
  }
  const minutes = Math.floor(milliseconds / 60000);
  const seconds = ((milliseconds % 60000) / 1000).toFixed(0);
  return `${minutes}m ${seconds}s`;
}

/**
 * Format large numbers with commas
 */
function formatNumber(num: number): string {
  return num.toLocaleString('en-US');
}

/**
 * Format root value with color coding
 */
function formatRootValue(value: number): { text: string; color: string } {
  const text = value.toFixed(3);
  let color = 'text-gray-900 dark:text-gray-100';

  if (value > 1) {
    color = 'text-green-600 dark:text-green-400 font-bold';
  } else if (value < -1) {
    color = 'text-red-600 dark:text-red-400 font-bold';
  } else if (value > 0) {
    color = 'text-green-500 dark:text-green-300';
  } else if (value < 0) {
    color = 'text-red-500 dark:text-red-300';
  }

  return { text, color };
}

/**
 * Statistic display component
 */
const StatItem: React.FC<{
  label: string;
  value: string | number;
  className?: string;
  valueClassName?: string;
}> = ({ label, value, className = '', valueClassName = '' }) => (
  <div className={`space-y-1 ${className}`}>
    <p className="text-sm text-gray-500 dark:text-gray-400">{label}</p>
    <p
      className={`text-2xl font-semibold text-gray-900 dark:text-gray-100 ${valueClassName}`}
    >
      {value}
    </p>
  </div>
);

/**
 * MCTS search statistics panel
 *
 * Displays:
 * - Total simulations run
 * - Time elapsed
 * - Simulations per second
 * - Maximum depth reached
 * - Total nodes explored
 * - Best action summary
 * - Current search phase
 * - Root value estimate
 *
 * @example
 * ```tsx
 * <MCTSStats
 *   stats={searchStats}
 *   isSearching={true}
 * />
 * ```
 */
export const MCTSStats: React.FC<MCTSStatsProps> = ({
  stats,
  isSearching = false,
  className = '',
}) => {
  if (!stats) {
    return (
      <Card className={className}>
        <CardBody>
          <div className="flex items-center justify-center py-8 text-gray-500 dark:text-gray-400">
            <p>No statistics available</p>
          </div>
        </CardBody>
      </Card>
    );
  }

  const rootValueDisplay = formatRootValue(stats.rootValue);

  return (
    <Card className={className}>
      <CardHeader
        title="Search Statistics"
        actions={
          <div className="flex items-center gap-2">
            {isSearching && (
              <Badge className="bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200 flex items-center gap-2">
                <Spinner className="w-3 h-3" />
                Running
              </Badge>
            )}
            <Badge className={getPhaseColor(stats.currentPhase)}>
              {stats.currentPhase}
            </Badge>
          </div>
        }
      />

      <CardBody>
        <div className="space-y-6">
          {/* Progress Indicator */}
          {isSearching && (
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Iteration Progress
                </span>
                <span className="text-sm text-gray-600 dark:text-gray-400">
                  {stats.iteration}
                </span>
              </div>
              <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                <div
                  className="bg-blue-600 dark:bg-blue-500 h-2 rounded-full transition-all duration-300"
                  style={{ width: '100%' }}
                  role="progressbar"
                  aria-label="Search progress"
                />
              </div>
            </div>
          )}

          {/* Main Statistics Grid */}
          <div className="grid grid-cols-2 gap-6">
            <StatItem
              label="Total Simulations"
              value={formatNumber(stats.totalSimulations)}
            />
            <StatItem
              label="Time Elapsed"
              value={formatTime(stats.timeElapsed)}
            />
            <StatItem
              label="Simulations/sec"
              value={formatNumber(Math.round(stats.simulationsPerSecond))}
            />
            <StatItem label="Max Depth" value={stats.maxDepth} />
            <StatItem
              label="Total Nodes"
              value={formatNumber(stats.totalNodes)}
            />
            <StatItem
              label="Root Value"
              value={rootValueDisplay.text}
              valueClassName={rootValueDisplay.color}
            />
          </div>

          {/* Best Action Summary */}
          {stats.bestAction && (
            <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
              <h4 className="text-sm font-semibold mb-3 text-gray-900 dark:text-gray-100">
                Best Action
              </h4>
              <div className="bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-900/20 dark:to-purple-900/20 rounded-lg p-4 border border-blue-200 dark:border-blue-800">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">
                      Selected Action
                    </p>
                    <p className="text-lg font-bold text-gray-900 dark:text-gray-100">
                      {stats.bestAction}
                    </p>
                  </div>
                  <Badge className="bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">
                    Best Path
                  </Badge>
                </div>
              </div>
            </div>
          )}

          {/* Performance Metrics */}
          <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
            <h4 className="text-sm font-semibold mb-3 text-gray-900 dark:text-gray-100">
              Performance
            </h4>
            <div className="space-y-2 text-sm">
              <div className="flex items-center justify-between">
                <span className="text-gray-600 dark:text-gray-400">
                  Avg. Time per Iteration
                </span>
                <span className="font-medium text-gray-900 dark:text-gray-100">
                  {stats.iteration > 0
                    ? formatTime(stats.timeElapsed / stats.iteration)
                    : '-'}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-600 dark:text-gray-400">
                  Nodes per Iteration
                </span>
                <span className="font-medium text-gray-900 dark:text-gray-100">
                  {stats.iteration > 0
                    ? formatNumber(
                        Math.round(stats.totalNodes / stats.iteration)
                      )
                    : '-'}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-600 dark:text-gray-400">
                  Tree Efficiency
                </span>
                <span className="font-medium text-gray-900 dark:text-gray-100">
                  {stats.totalSimulations > 0
                    ? `${((stats.totalNodes / stats.totalSimulations) * 100).toFixed(1)}%`
                    : '-'}
                </span>
              </div>
            </div>
          </div>

          {/* Search Status */}
          <div className="border-t border-gray-200 dark:border-gray-700 pt-3 text-xs text-gray-500 dark:text-gray-400 text-center">
            {isSearching
              ? 'Search in progress...'
              : stats.totalSimulations > 0
              ? 'Search completed'
              : 'Ready to start search'}
          </div>
        </div>
      </CardBody>
    </Card>
  );
};

MCTSStats.displayName = 'MCTSStats';
