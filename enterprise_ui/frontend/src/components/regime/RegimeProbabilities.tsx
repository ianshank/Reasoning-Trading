/**
 * Regime Probabilities Component
 *
 * Displays probability distribution across all possible regimes
 * - Bar chart of regime probabilities
 * - Highlighted current regime
 * - Historical comparison
 */

import React, { useMemo } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import { Card, CardHeader, CardBody } from '../ui/Card';
import { getRegimeDisplayName, getRegimeColor } from '../../types/regime';

export interface RegimeProbabilitiesProps {
  probabilities: Record<string, number>;
  currentRegime: string;
  historicalProbabilities?: Record<string, number>;
  className?: string;
}

interface ChartDataPoint {
  regime: string;
  displayName: string;
  current: number;
  historical?: number;
  color: string;
}

export const RegimeProbabilities: React.FC<RegimeProbabilitiesProps> = ({
  probabilities,
  currentRegime,
  historicalProbabilities,
  className = '',
}) => {
  const chartData = useMemo<ChartDataPoint[]>(() => {
    return Object.entries(probabilities)
      .map(([regime, probability]) => ({
        regime,
        displayName: getRegimeDisplayName(regime),
        current: probability * 100,
        historical: historicalProbabilities
          ? (historicalProbabilities[regime] || 0) * 100
          : undefined,
        color: getRegimeColor(regime),
      }))
      .sort((a, b) => b.current - a.current);
  }, [probabilities, historicalProbabilities]);

  const formatPercent = (value: number): string => {
    return `${value.toFixed(1)}%`;
  };

  return (
    <Card
      className={`bg-white dark:bg-gray-800 ${className}`}
      role="article"
      aria-label="Regime Probabilities"
    >
      <CardHeader title="Regime Probabilities" />

      <CardBody>
        <div className="space-y-4">
          {/* Bar Chart */}
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={chartData}
                margin={{ top: 20, right: 30, left: 20, bottom: 60 }}
              >
                <CartesianGrid
                  strokeDasharray="3 3"
                  className="stroke-gray-200 dark:stroke-gray-700"
                />
                <XAxis
                  dataKey="displayName"
                  angle={-45}
                  textAnchor="end"
                  height={80}
                  className="text-xs fill-gray-600 dark:fill-gray-400"
                  tick={{ fontSize: 12 }}
                />
                <YAxis
                  label={{
                    value: 'Probability (%)',
                    angle: -90,
                    position: 'insideLeft',
                    className: 'fill-gray-600 dark:fill-gray-400',
                  }}
                  className="text-xs fill-gray-600 dark:fill-gray-400"
                  domain={[0, 100]}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'rgba(255, 255, 255, 0.95)',
                    border: '1px solid #e5e7eb',
                    borderRadius: '0.375rem',
                  }}
                  formatter={(value: number) => formatPercent(value)}
                  labelClassName="font-semibold text-gray-900"
                />
                {historicalProbabilities && (
                  <Legend
                    wrapperStyle={{ paddingTop: '20px' }}
                    iconType="rect"
                  />
                )}
                <Bar
                  dataKey="current"
                  name="Current"
                  radius={[4, 4, 0, 0]}
                  maxBarSize={60}
                >
                  {chartData.map((entry, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={entry.color}
                      opacity={entry.regime === currentRegime ? 1 : 0.6}
                      stroke={
                        entry.regime === currentRegime
                          ? '#1f2937'
                          : 'transparent'
                      }
                      strokeWidth={entry.regime === currentRegime ? 2 : 0}
                    />
                  ))}
                </Bar>
                {historicalProbabilities && (
                  <Bar
                    dataKey="historical"
                    name="Historical Average"
                    fill="#9ca3af"
                    opacity={0.4}
                    radius={[4, 4, 0, 0]}
                    maxBarSize={60}
                  />
                )}
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Probability Table */}
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
                    className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider"
                  >
                    Probability
                  </th>
                  {historicalProbabilities && (
                    <th
                      scope="col"
                      className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider"
                    >
                      Change
                    </th>
                  )}
                </tr>
              </thead>
              <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                {chartData.map((item) => {
                  const change =
                    item.historical !== undefined
                      ? item.current - item.historical
                      : null;

                  return (
                    <tr
                      key={item.regime}
                      className={
                        item.regime === currentRegime
                          ? 'bg-blue-50 dark:bg-blue-900/20'
                          : ''
                      }
                    >
                      <td className="px-4 py-3 whitespace-nowrap">
                        <div className="flex items-center space-x-2">
                          <div
                            className="w-3 h-3 rounded-full"
                            style={{ backgroundColor: item.color }}
                            aria-hidden="true"
                          />
                          <span className="text-sm font-medium text-gray-900 dark:text-white">
                            {item.displayName}
                          </span>
                          {item.regime === currentRegime && (
                            <span className="text-xs text-blue-600 dark:text-blue-400 font-semibold">
                              (Current)
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-right">
                        <span className="text-sm font-mono font-semibold text-gray-900 dark:text-white">
                          {formatPercent(item.current)}
                        </span>
                      </td>
                      {historicalProbabilities && (
                        <td className="px-4 py-3 whitespace-nowrap text-right">
                          {change !== null && (
                            <span
                              className={`text-sm font-mono ${
                                change > 0
                                  ? 'text-green-600 dark:text-green-400'
                                  : change < 0
                                  ? 'text-red-600 dark:text-red-400'
                                  : 'text-gray-600 dark:text-gray-400'
                              }`}
                            >
                              {change > 0 ? '+' : ''}
                              {formatPercent(change)}
                            </span>
                          )}
                        </td>
                      )}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </CardBody>
    </Card>
  );
};
