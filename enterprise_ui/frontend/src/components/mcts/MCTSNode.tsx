/**
 * MCTS Node Component
 *
 * Displays detailed information about an individual MCTS tree node,
 * including action, statistics, and LLM reasoning.
 */

import React, { useState } from 'react';
import type { MCTSNode as MCTSNodeType } from '../../types/mcts';
import { TradingDirection } from '../../types/actions';
import { Card, CardHeader, CardBody } from '../ui/card';
import { Badge } from '../ui/badge';

/**
 * MCTSNode component props
 */
export interface MCTSNodeProps {
  /**
   * MCTS node data to display
   */
  node: MCTSNodeType;

  /**
   * Whether this node is currently selected
   * @default false
   */
  isSelected?: boolean;

  /**
   * Whether this node is on the best action path
   * @default false
   */
  isOnBestPath?: boolean;

  /**
   * Callback when node is clicked
   */
  onClick?: (nodeId: string) => void;

  /**
   * Additional CSS classes
   */
  className?: string;
}

/**
 * Get color for trading direction
 */
function getDirectionColor(direction: TradingDirection): string {
  switch (direction) {
    case TradingDirection.BUY:
      return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200';
    case TradingDirection.SELL:
      return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200';
    case TradingDirection.HOLD:
      return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200';
    case TradingDirection.SHORT:
      return 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200';
    case TradingDirection.COVER:
      return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200';
    default:
      return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200';
  }
}

/**
 * Format Q-value with color coding
 */
function formatQValue(qValue: number): { text: string; color: string } {
  const text = qValue.toFixed(3);
  let color = 'text-gray-900 dark:text-gray-100';

  if (qValue > 1) {
    color = 'text-green-600 dark:text-green-400';
  } else if (qValue < -1) {
    color = 'text-red-600 dark:text-red-400';
  } else if (qValue > 0) {
    color = 'text-green-500 dark:text-green-300';
  } else if (qValue < 0) {
    color = 'text-red-500 dark:text-red-300';
  }

  return { text, color };
}

/**
 * Calculate UCB score for display
 */
function calculateUCBScore(
  node: MCTSNodeType,
  parentVisits: number,
  explorationConstant: number = 1.414
): number {
  if (node.visits === 0) return Infinity;
  if (parentVisits === 0) return node.value_sum / node.visits;

  const exploitation = node.value_sum / node.visits;
  const exploration =
    explorationConstant * Math.sqrt(Math.log(parentVisits) / node.visits);

  return exploitation + exploration;
}

/**
 * Individual MCTS node component
 *
 * Displays:
 * - Action details (direction, size, stop-loss)
 * - Visit statistics
 * - Q-value and UCB score
 * - Prior probability
 * - LLM reasoning and reflection
 * - Best path indicator
 *
 * @example
 * ```tsx
 * <MCTSNode
 *   node={nodeData}
 *   isSelected={true}
 *   isOnBestPath={true}
 *   onClick={(id) => console.log('Node clicked:', id)}
 * />
 * ```
 */
export const MCTSNode: React.FC<MCTSNodeProps> = ({
  node,
  isSelected = false,
  isOnBestPath = false,
  onClick,
  className = '',
}) => {
  const [showDetails, setShowDetails] = useState(false);

  const qValueDisplay = formatQValue(node.q_value);
  const meanValue = node.visits > 0 ? node.value_sum / node.visits : 0;

  // Assume parent has 100 visits for UCB calculation (simplified)
  const ucbScore = calculateUCBScore(node, 100);

  const handleClick = () => {
    if (onClick) {
      onClick(node.id);
    }
  };

  const toggleDetails = (e: React.MouseEvent) => {
    e.stopPropagation();
    setShowDetails(!showDetails);
  };

  return (
    <Card
      className={`transition-all duration-200 ${
        isSelected
          ? 'ring-2 ring-blue-500 dark:ring-blue-400'
          : 'hover:shadow-lg'
      } ${className}`}
      onClick={handleClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          handleClick();
        }
      }}
      aria-label={`MCTS node ${node.id}`}
      aria-pressed={isSelected}
    >
      <CardHeader
        className="flex items-center justify-between"
        title={node.action ? `Action: ${node.action.direction}` : 'Root Node'}
        actions={
          <div className="flex items-center gap-2">
            {isOnBestPath && (
              <Badge className="bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200">
                Best Path
              </Badge>
            )}
            {node.is_terminal && (
              <Badge className="bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200">
                Terminal
              </Badge>
            )}
            {node.action && (
              <Badge className={getDirectionColor(node.action.direction)}>
                {node.action.direction.toUpperCase()}
              </Badge>
            )}
          </div>
        }
      />

      <CardBody>
        <div className="space-y-4">
          {/* Statistics Grid */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Visits
              </p>
              <p className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                {node.visits}
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Q-Value
              </p>
              <p className={`text-lg font-semibold ${qValueDisplay.color}`}>
                {qValueDisplay.text}
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Mean Value
              </p>
              <p className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                {meanValue.toFixed(3)}
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                UCB Score
              </p>
              <p className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                {ucbScore === Infinity ? '∞' : ucbScore.toFixed(3)}
              </p>
            </div>
          </div>

          {/* Prior Probability */}
          <div>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-1">
              Prior Probability
            </p>
            <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
              <div
                className="bg-blue-600 dark:bg-blue-500 h-2 rounded-full transition-all duration-300"
                style={{ width: `${node.prior * 100}%` }}
                role="progressbar"
                aria-valuenow={node.prior * 100}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-label="Prior probability"
              />
            </div>
            <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
              {(node.prior * 100).toFixed(1)}%
            </p>
          </div>

          {/* Action Details */}
          {node.action && (
            <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
              <h4 className="text-sm font-semibold mb-2 text-gray-900 dark:text-gray-100">
                Action Details
              </h4>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div>
                  <span className="text-gray-500 dark:text-gray-400">
                    Position Size:
                  </span>
                  <span className="ml-2 font-medium text-gray-900 dark:text-gray-100">
                    {(node.action.position_size.size_fraction * 100).toFixed(1)}%
                  </span>
                </div>
                <div>
                  <span className="text-gray-500 dark:text-gray-400">
                    Kelly Fraction:
                  </span>
                  <span className="ml-2 font-medium text-gray-900 dark:text-gray-100">
                    {node.action.position_size.kelly_fraction.toFixed(2)}
                  </span>
                </div>
                <div>
                  <span className="text-gray-500 dark:text-gray-400">
                    Stop Loss:
                  </span>
                  <span className="ml-2 font-medium text-gray-900 dark:text-gray-100">
                    {(node.action.stop_loss.stop_loss_pct * 100).toFixed(1)}%
                  </span>
                </div>
                <div>
                  <span className="text-gray-500 dark:text-gray-400">
                    Time Horizon:
                  </span>
                  <span className="ml-2 font-medium text-gray-900 dark:text-gray-100">
                    {node.action.time_horizon}
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Expandable Details */}
          {(node.reflection || node.action?.reasoning) && (
            <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
              <button
                onClick={toggleDetails}
                className="flex items-center justify-between w-full text-sm font-semibold text-gray-900 dark:text-gray-100 hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
                aria-expanded={showDetails}
                aria-controls={`details-${node.id}`}
              >
                <span>Reasoning & Reflection</span>
                <span className="text-gray-500 dark:text-gray-400">
                  {showDetails ? '▼' : '▶'}
                </span>
              </button>

              {showDetails && (
                <div
                  id={`details-${node.id}`}
                  className="mt-3 space-y-3 text-sm"
                >
                  {node.action?.reasoning && (
                    <div>
                      <h5 className="font-medium text-gray-700 dark:text-gray-300 mb-1">
                        LLM Reasoning:
                      </h5>
                      <p className="text-gray-600 dark:text-gray-400 whitespace-pre-wrap">
                        {node.action.reasoning}
                      </p>
                    </div>
                  )}
                  {node.reflection && (
                    <div>
                      <h5 className="font-medium text-gray-700 dark:text-gray-300 mb-1">
                        Self-Evaluation:
                      </h5>
                      <p className="text-gray-600 dark:text-gray-400 whitespace-pre-wrap">
                        {node.reflection}
                      </p>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Metadata */}
          <div className="border-t border-gray-200 dark:border-gray-700 pt-3 flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
            <span>Depth: {node.depth}</span>
            <span>
              Children: {node.children_ids.length}
            </span>
            <span>
              Created:{' '}
              {new Date(node.created_at).toLocaleTimeString()}
            </span>
          </div>
        </div>
      </CardBody>
    </Card>
  );
};

MCTSNode.displayName = 'MCTSNode';
