/**
 * Regime Strategy Mapping Component
 *
 * Maps market regimes to optimal trading strategies
 * - Table showing recommended strategy per regime
 * - Current regime recommendations
 * - Historical performance by regime
 */

import React from 'react';
import { TrendingUp, Award, BarChart3 } from 'lucide-react';
import { Card, CardHeader, CardBody } from '../ui/Card';
import { Badge } from '../ui/badge';
import type { RegimeStrategyMapping } from '../../types/regime';
import { getRegimeDisplayName, getRegimeColor } from '../../types/regime';

export interface RegimeStrategyMappingProps {
  mapping: RegimeStrategyMapping[];
  currentRegime: string;
  className?: string;
}

/**
 * Get performance color
 */
function getPerformanceColor(sharpe: number): string {
  if (sharpe > 1.5) return 'text-green-600 dark:text-green-400';
  if (sharpe > 0.5) return 'text-yellow-600 dark:text-yellow-400';
  return 'text-red-600 dark:text-red-400';
}

/**
 * Get badge variant based on win rate
 */
function getWinRateBadge(winRate: number): string {
  if (winRate >= 0.6) return 'success';
  if (winRate >= 0.45) return 'warning';
  return 'danger';
}

export const RegimeStrategyMapping: React.FC<RegimeStrategyMappingProps> = ({
  mapping,
  currentRegime,
  className = '',
}) => {
  const currentMapping = mapping.find((m) => m.regime === currentRegime);

  return (
    <Card
      className={`bg-white dark:bg-gray-800 ${className}`}
      role="article"
      aria-label="Regime to Strategy Mapping"
    >
      <CardHeader title="Strategy Recommendations by Regime" />

      <CardBody>
        <div className="space-y-6">
          {/* Current Recommendation Highlight */}
          {currentMapping && (
            <div className="p-4 rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center space-x-2 mb-2">
                    <div
                      className="w-3 h-3 rounded-full"
                      style={{ backgroundColor: getRegimeColor(currentRegime) }}
                      aria-hidden="true"
                    />
                    <h4 className="text-sm font-semibold text-gray-900 dark:text-white">
                      Current: {getRegimeDisplayName(currentRegime)}
                    </h4>
                  </div>
                  <div className="space-y-1">
                    <div className="flex items-center space-x-2">
                      <Award size={16} className="text-blue-600 dark:text-blue-400" />
                      <span className="text-lg font-bold text-gray-900 dark:text-white">
                        {currentMapping.recommended_strategy}
                      </span>
                    </div>
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      Confidence: {(currentMapping.confidence * 100).toFixed(0)}%
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">
                    Sharpe Ratio
                  </div>
                  <div
                    className={`text-2xl font-bold ${getPerformanceColor(currentMapping.historical_performance.sharpe_ratio)}`}
                  >
                    {currentMapping.historical_performance.sharpe_ratio.toFixed(2)}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Strategy Mapping Table */}
          <div className="overflow-hidden rounded-lg border border-gray-200 dark:border-gray-700">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead className="bg-gray-50 dark:bg-gray-900">
                <tr>
                  <th
                    scope="col"
                    className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider"
                  >
                    Regime
                  </th>
                  <th
                    scope="col"
                    className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider"
                  >
                    Strategy
                  </th>
                  <th
                    scope="col"
                    className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider"
                  >
                    Win Rate
                  </th>
                  <th
                    scope="col"
                    className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider"
                  >
                    Avg Return
                  </th>
                  <th
                    scope="col"
                    className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider"
                  >
                    Sharpe
                  </th>
                  <th
                    scope="col"
                    className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider"
                  >
                    Trades
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                {mapping.map((item) => {
                  const isCurrent = item.regime === currentRegime;
                  const perf = item.historical_performance;

                  return (
                    <tr
                      key={item.regime}
                      className={`${
                        isCurrent
                          ? 'bg-blue-50 dark:bg-blue-900/20'
                          : 'hover:bg-gray-50 dark:hover:bg-gray-700'
                      } transition-colors`}
                    >
                      <td className="px-4 py-3 whitespace-nowrap">
                        <div className="flex items-center space-x-2">
                          <div
                            className="w-3 h-3 rounded-full"
                            style={{ backgroundColor: getRegimeColor(item.regime) }}
                            aria-hidden="true"
                          />
                          <span className="text-sm font-medium text-gray-900 dark:text-white">
                            {getRegimeDisplayName(item.regime)}
                          </span>
                          {isCurrent && (
                            <Badge variant="info" size="sm">
                              Current
                            </Badge>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <div className="flex items-center space-x-2">
                          <BarChart3
                            size={16}
                            className="text-gray-400"
                            aria-hidden="true"
                          />
                          <span className="text-sm font-semibold text-gray-900 dark:text-white">
                            {item.recommended_strategy}
                          </span>
                        </div>
                        <div className="text-xs text-gray-500 dark:text-gray-400">
                          Confidence: {(item.confidence * 100).toFixed(0)}%
                        </div>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-right">
                        <Badge
                          variant={getWinRateBadge(perf.win_rate)}
                          size="sm"
                        >
                          {(perf.win_rate * 100).toFixed(1)}%
                        </Badge>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-right">
                        <span
                          className={`text-sm font-mono ${
                            perf.avg_return > 0
                              ? 'text-green-600 dark:text-green-400'
                              : 'text-red-600 dark:text-red-400'
                          }`}
                        >
                          {perf.avg_return > 0 ? '+' : ''}
                          {(perf.avg_return * 100).toFixed(2)}%
                        </span>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-right">
                        <span
                          className={`text-sm font-mono font-semibold ${getPerformanceColor(perf.sharpe_ratio)}`}
                        >
                          {perf.sharpe_ratio.toFixed(2)}
                        </span>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-right">
                        <span className="text-sm font-mono text-gray-600 dark:text-gray-400">
                          {perf.total_trades}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Performance Summary */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-4 rounded-lg bg-gray-50 dark:bg-gray-900">
              <div className="flex items-center space-x-2 mb-2">
                <TrendingUp
                  size={20}
                  className="text-green-600 dark:text-green-400"
                />
                <span className="text-sm font-medium text-gray-600 dark:text-gray-400">
                  Best Performing
                </span>
              </div>
              {mapping.length > 0 && (
                <>
                  <div className="text-lg font-bold text-gray-900 dark:text-white">
                    {
                      [...mapping].sort(
                        (a, b) =>
                          b.historical_performance.sharpe_ratio -
                          a.historical_performance.sharpe_ratio
                      )[0].recommended_strategy
                    }
                  </div>
                  <div className="text-xs text-gray-500 dark:text-gray-400">
                    in{' '}
                    {getRegimeDisplayName(
                      [...mapping].sort(
                        (a, b) =>
                          b.historical_performance.sharpe_ratio -
                          a.historical_performance.sharpe_ratio
                      )[0].regime
                    )}
                  </div>
                </>
              )}
            </div>

            <div className="p-4 rounded-lg bg-gray-50 dark:bg-gray-900">
              <div className="flex items-center space-x-2 mb-2">
                <Award
                  size={20}
                  className="text-blue-600 dark:text-blue-400"
                />
                <span className="text-sm font-medium text-gray-600 dark:text-gray-400">
                  Highest Win Rate
                </span>
              </div>
              {mapping.length > 0 && (
                <>
                  <div className="text-lg font-bold text-gray-900 dark:text-white">
                    {
                      (
                        [...mapping].sort(
                          (a, b) =>
                            b.historical_performance.win_rate -
                            a.historical_performance.win_rate
                        )[0].historical_performance.win_rate * 100
                      ).toFixed(1)
                    }
                    %
                  </div>
                  <div className="text-xs text-gray-500 dark:text-gray-400">
                    {
                      [...mapping].sort(
                        (a, b) =>
                          b.historical_performance.win_rate -
                          a.historical_performance.win_rate
                      )[0].recommended_strategy
                    }
                  </div>
                </>
              )}
            </div>

            <div className="p-4 rounded-lg bg-gray-50 dark:bg-gray-900">
              <div className="flex items-center space-x-2 mb-2">
                <BarChart3
                  size={20}
                  className="text-purple-600 dark:text-purple-400"
                />
                <span className="text-sm font-medium text-gray-600 dark:text-gray-400">
                  Total Trades
                </span>
              </div>
              <div className="text-lg font-bold text-gray-900 dark:text-white">
                {mapping
                  .reduce(
                    (sum, m) => sum + m.historical_performance.total_trades,
                    0
                  )
                  .toLocaleString()}
              </div>
              <div className="text-xs text-gray-500 dark:text-gray-400">
                across all regimes
              </div>
            </div>
          </div>
        </div>
      </CardBody>
    </Card>
  );
};
