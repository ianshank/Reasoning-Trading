/**
 * MCTS Action Distribution Component
 *
 * Visualizes action probabilities and visit counts as a bar chart,
 * color-coded by trading direction.
 */

import React, { useState } from 'react';
import type { TradingAction, TradingDirection } from '../../types/actions';
import { Card, CardHeader, CardBody } from '../ui/card';
import { Badge } from '../ui/badge';

/**
 * Action distribution entry
 */
export interface ActionDistributionEntry {
  action: TradingAction;
  visitCount: number;
  meanValue: number;
  probability: number;
}

/**
 * MCTSActionDistribution component props
 */
export interface MCTSActionDistributionProps {
  /**
   * Action distribution data
   */
  distribution: ActionDistributionEntry[];

  /**
   * Currently selected action
   */
  selectedAction?: TradingAction | null;

  /**
   * Callback when an action is selected
   */
  onActionSelect?: (action: TradingAction) => void;

  /**
   * Additional CSS classes
   */
  className?: string;
}

/**
 * Sort mode for action distribution
 */
type SortMode = 'probability' | 'visitCount' | 'value';

/**
 * Get color for trading direction
 */
function getDirectionColor(
  direction: TradingDirection
): { bg: string; text: string; bar: string } {
  switch (direction) {
    case 'buy':
      return {
        bg: 'bg-green-100 dark:bg-green-900',
        text: 'text-green-800 dark:text-green-200',
        bar: 'bg-green-500 dark:bg-green-600',
      };
    case 'sell':
      return {
        bg: 'bg-red-100 dark:bg-red-900',
        text: 'text-red-800 dark:text-red-200',
        bar: 'bg-red-500 dark:bg-red-600',
      };
    case 'hold':
      return {
        bg: 'bg-gray-100 dark:bg-gray-700',
        text: 'text-gray-800 dark:text-gray-200',
        bar: 'bg-gray-500 dark:bg-gray-600',
      };
    case 'short':
      return {
        bg: 'bg-orange-100 dark:bg-orange-900',
        text: 'text-orange-800 dark:text-orange-200',
        bar: 'bg-orange-500 dark:bg-orange-600',
      };
    case 'cover':
      return {
        bg: 'bg-blue-100 dark:bg-blue-900',
        text: 'text-blue-800 dark:text-blue-200',
        bar: 'bg-blue-500 dark:bg-blue-600',
      };
    default:
      return {
        bg: 'bg-gray-100 dark:bg-gray-700',
        text: 'text-gray-800 dark:text-gray-200',
        bar: 'bg-gray-500 dark:bg-gray-600',
      };
  }
}

/**
 * Format action label
 */
function formatActionLabel(action: TradingAction): string {
  const direction = action.direction.toUpperCase();
  const size = (action.position_size.size_fraction * 100).toFixed(0);
  return `${direction} ${size}%`;
}

/**
 * Sort distribution by mode
 */
function sortDistribution(
  distribution: ActionDistributionEntry[],
  mode: SortMode
): ActionDistributionEntry[] {
  const sorted = [...distribution];
  switch (mode) {
    case 'probability':
      return sorted.sort((a, b) => b.probability - a.probability);
    case 'visitCount':
      return sorted.sort((a, b) => b.visitCount - a.visitCount);
    case 'value':
      return sorted.sort((a, b) => b.meanValue - a.meanValue);
    default:
      return sorted;
  }
}

/**
 * Action distribution bar chart
 *
 * Features:
 * - Bar chart showing action probabilities
 * - Color coded by trading direction
 * - Sortable by probability, visit count, or value
 * - Interactive selection
 * - Tooltip with detailed stats
 *
 * @example
 * ```tsx
 * <MCTSActionDistribution
 *   distribution={actions}
 *   selectedAction={currentAction}
 *   onActionSelect={(action) => console.log('Selected:', action)}
 * />
 * ```
 */
export const MCTSActionDistribution: React.FC<
  MCTSActionDistributionProps
> = ({ distribution, selectedAction = null, onActionSelect, className = '' }) => {
  const [sortMode, setSortMode] = useState<SortMode>('probability');

  const sortedDistribution = sortDistribution(distribution, sortMode);
  const maxValue = Math.max(...sortedDistribution.map((d) => d.probability));

  if (distribution.length === 0) {
    return (
      <Card className={className}>
        <CardBody>
          <div className="flex items-center justify-center py-8 text-gray-500 dark:text-gray-400">
            <p>No action distribution available</p>
          </div>
        </CardBody>
      </Card>
    );
  }

  return (
    <Card className={className}>
      <CardHeader
        title="Action Distribution"
        actions={
          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-500 dark:text-gray-400">
              Sort by:
            </span>
            <select
              value={sortMode}
              onChange={(e) => setSortMode(e.target.value as SortMode)}
              className="text-xs border border-gray-300 dark:border-gray-600 rounded px-2 py-1 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
              aria-label="Sort action distribution"
            >
              <option value="probability">Probability</option>
              <option value="visitCount">Visit Count</option>
              <option value="value">Mean Value</option>
            </select>
          </div>
        }
      />

      <CardBody>
        <div className="space-y-3">
          {sortedDistribution.map((entry, index) => {
            const colors = getDirectionColor(entry.action.direction);
            const isSelected =
              selectedAction &&
              selectedAction.direction === entry.action.direction &&
              selectedAction.position_size.size_fraction ===
                entry.action.position_size.size_fraction;
            const barWidth = (entry.probability / maxValue) * 100;

            return (
              <div
                key={index}
                className={`p-3 rounded-lg border transition-all duration-200 cursor-pointer ${
                  isSelected
                    ? 'border-blue-500 dark:border-blue-400 bg-blue-50 dark:bg-blue-900/20'
                    : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600 hover:shadow-md'
                }`}
                onClick={() => onActionSelect?.(entry.action)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    onActionSelect?.(entry.action);
                  }
                }}
                aria-label={`Action: ${formatActionLabel(entry.action)}`}
                aria-pressed={isSelected}
              >
                {/* Header */}
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <Badge className={`${colors.bg} ${colors.text}`}>
                      {formatActionLabel(entry.action)}
                    </Badge>
                    {index === 0 && (
                      <Badge className="bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200">
                        Top
                      </Badge>
                    )}
                  </div>
                  <span className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                    {(entry.probability * 100).toFixed(1)}%
                  </span>
                </div>

                {/* Progress Bar */}
                <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3 mb-2">
                  <div
                    className={`${colors.bar} h-3 rounded-full transition-all duration-500`}
                    style={{ width: `${barWidth}%` }}
                    role="progressbar"
                    aria-valuenow={entry.probability * 100}
                    aria-valuemin={0}
                    aria-valuemax={100}
                    aria-label="Action probability"
                  />
                </div>

                {/* Stats Grid */}
                <div className="grid grid-cols-3 gap-2 text-xs">
                  <div>
                    <span className="text-gray-500 dark:text-gray-400">
                      Visits:
                    </span>
                    <span className="ml-1 font-medium text-gray-900 dark:text-gray-100">
                      {entry.visitCount}
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-500 dark:text-gray-400">
                      Value:
                    </span>
                    <span
                      className={`ml-1 font-medium ${
                        entry.meanValue > 0
                          ? 'text-green-600 dark:text-green-400'
                          : entry.meanValue < 0
                          ? 'text-red-600 dark:text-red-400'
                          : 'text-gray-900 dark:text-gray-100'
                      }`}
                    >
                      {entry.meanValue.toFixed(3)}
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-500 dark:text-gray-400">
                      Size:
                    </span>
                    <span className="ml-1 font-medium text-gray-900 dark:text-gray-100">
                      {(entry.action.position_size.size_fraction * 100).toFixed(
                        1
                      )}
                      %
                    </span>
                  </div>
                </div>

                {/* Additional Action Details (collapsible) */}
                {isSelected && entry.action.reasoning && (
                  <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
                    <p className="text-xs text-gray-600 dark:text-gray-400 mb-1 font-medium">
                      Reasoning:
                    </p>
                    <p className="text-xs text-gray-700 dark:text-gray-300 line-clamp-2">
                      {entry.action.reasoning}
                    </p>
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Summary */}
        <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-600 dark:text-gray-400">
              Total Actions:
            </span>
            <span className="font-semibold text-gray-900 dark:text-gray-100">
              {distribution.length}
            </span>
          </div>
          <div className="flex items-center justify-between text-sm mt-1">
            <span className="text-gray-600 dark:text-gray-400">
              Total Visits:
            </span>
            <span className="font-semibold text-gray-900 dark:text-gray-100">
              {distribution.reduce((sum, d) => sum + d.visitCount, 0)}
            </span>
          </div>
        </div>
      </CardBody>
    </Card>
  );
};

MCTSActionDistribution.displayName = 'MCTSActionDistribution';
