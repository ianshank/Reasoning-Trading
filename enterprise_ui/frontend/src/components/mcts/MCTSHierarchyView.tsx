/**
 * MCTS Hierarchy View Component
 *
 * Visualizes the three-level hierarchical MCTS structure
 * (Strategic, Tactical, Execution) with MAXQ value decomposition.
 */

import React, { useState } from 'react';
import type { MCTSResult } from '../../types/mcts';
import type { TradingAction } from '../../types/actions';
import { Card, CardHeader, CardBody } from '../ui/card';
import { Badge } from '../ui/badge';

/**
 * Hierarchical MCTS result with level-specific data
 */
export interface HierarchicalMCTSResult {
  strategic: {
    action: TradingAction;
    value: number;
    completionValue: number;
    confidence: number;
    reasoning: string;
  };
  tactical: {
    action: TradingAction;
    value: number;
    completionValue: number;
    confidence: number;
    reasoning: string;
  };
  execution: {
    action: TradingAction;
    value: number;
    completionValue: number;
    confidence: number;
    reasoning: string;
  };
  totalValue: number;
  timestamp: string;
}

/**
 * MCTSHierarchyView component props
 */
export interface MCTSHierarchyViewProps {
  /**
   * Hierarchical MCTS result data
   */
  hierarchicalResult: HierarchicalMCTSResult | null;

  /**
   * Additional CSS classes
   */
  className?: string;
}

/**
 * Level type
 */
type LevelType = 'strategic' | 'tactical' | 'execution';

/**
 * Get color for hierarchy level
 */
function getLevelColor(level: LevelType): {
  bg: string;
  text: string;
  border: string;
} {
  switch (level) {
    case 'strategic':
      return {
        bg: 'bg-purple-50 dark:bg-purple-900/20',
        text: 'text-purple-700 dark:text-purple-300',
        border: 'border-purple-300 dark:border-purple-700',
      };
    case 'tactical':
      return {
        bg: 'bg-blue-50 dark:bg-blue-900/20',
        text: 'text-blue-700 dark:text-blue-300',
        border: 'border-blue-300 dark:border-blue-700',
      };
    case 'execution':
      return {
        bg: 'bg-green-50 dark:bg-green-900/20',
        text: 'text-green-700 dark:text-green-300',
        border: 'border-green-300 dark:border-green-700',
      };
  }
}

/**
 * Get level icon
 */
function getLevelIcon(level: LevelType): string {
  switch (level) {
    case 'strategic':
      return '🎯';
    case 'tactical':
      return '🎲';
    case 'execution':
      return '⚡';
  }
}

/**
 * Level card component
 */
const LevelCard: React.FC<{
  level: LevelType;
  data: {
    action: TradingAction;
    value: number;
    completionValue: number;
    confidence: number;
    reasoning: string;
  };
  isExpanded: boolean;
  onToggle: () => void;
}> = ({ level, data, isExpanded, onToggle }) => {
  const colors = getLevelColor(level);
  const icon = getLevelIcon(level);

  return (
    <div
      className={`border-2 rounded-lg p-4 ${colors.bg} ${colors.border} transition-all duration-200`}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-2xl" aria-hidden="true">
            {icon}
          </span>
          <h3 className={`text-lg font-bold ${colors.text} capitalize`}>
            {level} Level
          </h3>
        </div>
        <button
          onClick={onToggle}
          className={`text-sm font-medium ${colors.text} hover:underline`}
          aria-expanded={isExpanded}
          aria-controls={`${level}-details`}
        >
          {isExpanded ? 'Collapse' : 'Expand'}
        </button>
      </div>

      {/* Action & Value Summary */}
      <div className="grid grid-cols-2 gap-4 mb-3">
        <div>
          <p className="text-xs text-gray-600 dark:text-gray-400 mb-1">
            Action
          </p>
          <Badge className={`${colors.bg} ${colors.text} border ${colors.border}`}>
            {data.action.direction.toUpperCase()}{' '}
            {(data.action.position_size.size_fraction * 100).toFixed(0)}%
          </Badge>
        </div>
        <div>
          <p className="text-xs text-gray-600 dark:text-gray-400 mb-1">
            Confidence
          </p>
          <p className={`font-semibold ${colors.text}`}>
            {(data.confidence * 100).toFixed(1)}%
          </p>
        </div>
      </div>

      {/* MAXQ Value Decomposition */}
      <div className="bg-white dark:bg-gray-800 rounded-lg p-3 mb-3">
        <h4 className="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-2">
          MAXQ Value Decomposition
        </h4>
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-600 dark:text-gray-400">
              Task Value
            </span>
            <span
              className={`font-semibold ${
                data.value > 0
                  ? 'text-green-600 dark:text-green-400'
                  : data.value < 0
                  ? 'text-red-600 dark:text-red-400'
                  : 'text-gray-900 dark:text-gray-100'
              }`}
            >
              {data.value.toFixed(3)}
            </span>
          </div>
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-600 dark:text-gray-400">
              Completion Value
            </span>
            <span
              className={`font-semibold ${
                data.completionValue > 0
                  ? 'text-green-600 dark:text-green-400'
                  : data.completionValue < 0
                  ? 'text-red-600 dark:text-red-400'
                  : 'text-gray-900 dark:text-gray-100'
              }`}
            >
              {data.completionValue.toFixed(3)}
            </span>
          </div>
          <div className="border-t border-gray-200 dark:border-gray-700 pt-2 mt-2">
            <div className="flex items-center justify-between text-sm font-semibold">
              <span className="text-gray-900 dark:text-gray-100">
                Total Q-value
              </span>
              <span
                className={
                  data.value + data.completionValue > 0
                    ? 'text-green-600 dark:text-green-400'
                    : data.value + data.completionValue < 0
                    ? 'text-red-600 dark:text-red-400'
                    : 'text-gray-900 dark:text-gray-100'
                }
              >
                {(data.value + data.completionValue).toFixed(3)}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Expanded Details */}
      {isExpanded && (
        <div id={`${level}-details`} className="space-y-3">
          {/* Action Details */}
          <div className="bg-white dark:bg-gray-800 rounded-lg p-3">
            <h4 className="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-2">
              Action Details
            </h4>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div>
                <span className="text-gray-500 dark:text-gray-400">
                  Position Size:
                </span>
                <span className="ml-1 font-medium text-gray-900 dark:text-gray-100">
                  {(data.action.position_size.size_fraction * 100).toFixed(1)}%
                </span>
              </div>
              <div>
                <span className="text-gray-500 dark:text-gray-400">
                  Kelly Fraction:
                </span>
                <span className="ml-1 font-medium text-gray-900 dark:text-gray-100">
                  {data.action.position_size.kelly_fraction.toFixed(2)}
                </span>
              </div>
              <div>
                <span className="text-gray-500 dark:text-gray-400">
                  Stop Loss:
                </span>
                <span className="ml-1 font-medium text-gray-900 dark:text-gray-100">
                  {(data.action.stop_loss.stop_loss_pct * 100).toFixed(1)}%
                </span>
              </div>
              <div>
                <span className="text-gray-500 dark:text-gray-400">
                  Time Horizon:
                </span>
                <span className="ml-1 font-medium text-gray-900 dark:text-gray-100">
                  {data.action.time_horizon}
                </span>
              </div>
            </div>
          </div>

          {/* Reasoning */}
          {data.reasoning && (
            <div className="bg-white dark:bg-gray-800 rounded-lg p-3">
              <h4 className="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-2">
                LLM Reasoning
              </h4>
              <p className="text-xs text-gray-600 dark:text-gray-400 whitespace-pre-wrap">
                {data.reasoning}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

/**
 * Hierarchical MCTS visualization
 *
 * Displays:
 * - Three-level view (Strategic, Tactical, Execution)
 * - Collapsible sections for each level
 * - MAXQ value decomposition
 * - Action details at each level
 * - LLM reasoning for each decision
 *
 * @example
 * ```tsx
 * <MCTSHierarchyView
 *   hierarchicalResult={result}
 * />
 * ```
 */
export const MCTSHierarchyView: React.FC<MCTSHierarchyViewProps> = ({
  hierarchicalResult,
  className = '',
}) => {
  const [expandedLevels, setExpandedLevels] = useState<Set<LevelType>>(
    new Set(['strategic'])
  );

  const toggleLevel = (level: LevelType) => {
    setExpandedLevels((prev) => {
      const next = new Set(prev);
      if (next.has(level)) {
        next.delete(level);
      } else {
        next.add(level);
      }
      return next;
    });
  };

  const toggleAll = () => {
    if (expandedLevels.size === 3) {
      setExpandedLevels(new Set());
    } else {
      setExpandedLevels(new Set(['strategic', 'tactical', 'execution']));
    }
  };

  if (!hierarchicalResult) {
    return (
      <Card className={className}>
        <CardBody>
          <div className="flex items-center justify-center py-8 text-gray-500 dark:text-gray-400">
            <p>No hierarchical result available</p>
          </div>
        </CardBody>
      </Card>
    );
  }

  return (
    <Card className={className}>
      <CardHeader
        title="Hierarchical MCTS"
        actions={
          <Button
            variant="ghost"
            size="sm"
            onClick={toggleAll}
            aria-label={
              expandedLevels.size === 3 ? 'Collapse all' : 'Expand all'
            }
          >
            {expandedLevels.size === 3 ? 'Collapse All' : 'Expand All'}
          </Button>
        }
      />

      <CardBody>
        <div className="space-y-4">
          {/* Total Value Summary */}
          <div className="bg-gradient-to-r from-purple-50 to-blue-50 dark:from-purple-900/20 dark:to-blue-900/20 rounded-lg p-4 border border-purple-200 dark:border-purple-800">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">
                  Total Hierarchical Value
                </p>
                <p
                  className={`text-3xl font-bold ${
                    hierarchicalResult.totalValue > 0
                      ? 'text-green-600 dark:text-green-400'
                      : hierarchicalResult.totalValue < 0
                      ? 'text-red-600 dark:text-red-400'
                      : 'text-gray-900 dark:text-gray-100'
                  }`}
                >
                  {hierarchicalResult.totalValue.toFixed(3)}
                </p>
              </div>
              <div className="text-right">
                <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">
                  Timestamp
                </p>
                <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
                  {new Date(hierarchicalResult.timestamp).toLocaleString()}
                </p>
              </div>
            </div>
          </div>

          {/* Hierarchy Flow Indicator */}
          <div className="flex items-center justify-center gap-4 py-2">
            <div className="flex items-center gap-2">
              <Badge className="bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200">
                Strategic
              </Badge>
              <span className="text-gray-400 dark:text-gray-600">→</span>
              <Badge className="bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
                Tactical
              </Badge>
              <span className="text-gray-400 dark:text-gray-600">→</span>
              <Badge className="bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">
                Execution
              </Badge>
            </div>
          </div>

          {/* Level Cards */}
          <div className="space-y-4">
            <LevelCard
              level="strategic"
              data={hierarchicalResult.strategic}
              isExpanded={expandedLevels.has('strategic')}
              onToggle={() => toggleLevel('strategic')}
            />
            <LevelCard
              level="tactical"
              data={hierarchicalResult.tactical}
              isExpanded={expandedLevels.has('tactical')}
              onToggle={() => toggleLevel('tactical')}
            />
            <LevelCard
              level="execution"
              data={hierarchicalResult.execution}
              isExpanded={expandedLevels.has('execution')}
              onToggle={() => toggleLevel('execution')}
            />
          </div>

          {/* Value Breakdown */}
          <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
            <h4 className="text-sm font-semibold mb-3 text-gray-900 dark:text-gray-100">
              Value Breakdown
            </h4>
            <div className="space-y-2 text-sm">
              <div className="flex items-center justify-between">
                <span className="text-gray-600 dark:text-gray-400">
                  Strategic Contribution
                </span>
                <span className="font-medium text-gray-900 dark:text-gray-100">
                  {(
                    hierarchicalResult.strategic.value +
                    hierarchicalResult.strategic.completionValue
                  ).toFixed(3)}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-600 dark:text-gray-400">
                  Tactical Contribution
                </span>
                <span className="font-medium text-gray-900 dark:text-gray-100">
                  {(
                    hierarchicalResult.tactical.value +
                    hierarchicalResult.tactical.completionValue
                  ).toFixed(3)}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-600 dark:text-gray-400">
                  Execution Contribution
                </span>
                <span className="font-medium text-gray-900 dark:text-gray-100">
                  {(
                    hierarchicalResult.execution.value +
                    hierarchicalResult.execution.completionValue
                  ).toFixed(3)}
                </span>
              </div>
            </div>
          </div>
        </div>
      </CardBody>
    </Card>
  );
};

MCTSHierarchyView.displayName = 'MCTSHierarchyView';

/**
 * Missing Button import - add to ui components if not exists
 */
const Button: React.FC<{
  variant: string;
  size: string;
  onClick: () => void;
  children: React.ReactNode;
  'aria-label': string;
}> = ({ onClick, children }) => (
  <button
    onClick={onClick}
    className="text-sm text-blue-600 dark:text-blue-400 hover:underline"
  >
    {children}
  </button>
);
