/**
 * Indicator Contribution Component
 *
 * Shows which technical indicators contributed to regime classification
 * - Bar chart of indicator contributions
 * - ADX, RSI, ATR, Bollinger Band width, etc.
 * - Positive/negative impact visualization
 */

import React, { useMemo } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  ReferenceLine,
} from 'recharts';
import { Card, CardHeader, CardBody } from '../ui/Card';
import type { IndicatorContribution } from '../../types/regime';

export interface IndicatorContributionProps {
  contributions: IndicatorContribution[];
  className?: string;
}

interface ChartDataPoint {
  name: string;
  impact: number;
  value: number;
  weight: number;
  color: string;
}

export const IndicatorContribution: React.FC<IndicatorContributionProps> = ({
  contributions,
  className = '',
}) => {
  const chartData = useMemo<ChartDataPoint[]>(() => {
    return contributions
      .map((contrib) => ({
        name: contrib.name,
        impact: contrib.impact * 100,
        value: contrib.value,
        weight: contrib.weight,
        color: contrib.impact > 0 ? '#10b981' : '#ef4444',
      }))
      .sort((a, b) => Math.abs(b.impact) - Math.abs(a.impact));
  }, [contributions]);

  const formatPercent = (value: number): string => {
    return `${value >= 0 ? '+' : ''}${value.toFixed(1)}%`;
  };

  return (
    <Card
      className={`bg-white dark:bg-gray-800 ${className}`}
      role="article"
      aria-label="Technical Indicator Contributions"
    >
      <CardHeader title="Indicator Contributions" />

      <CardBody>
        <div className="space-y-4">
          {/* Bar Chart */}
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={chartData}
                layout="vertical"
                margin={{ top: 5, right: 30, left: 100, bottom: 5 }}
              >
                <CartesianGrid
                  strokeDasharray="3 3"
                  className="stroke-gray-200 dark:stroke-gray-700"
                  horizontal={false}
                />
                <XAxis
                  type="number"
                  domain={['auto', 'auto']}
                  label={{
                    value: 'Impact (%)',
                    position: 'insideBottom',
                    offset: -5,
                    className: 'fill-gray-600 dark:fill-gray-400',
                  }}
                  className="text-xs fill-gray-600 dark:fill-gray-400"
                />
                <YAxis
                  type="category"
                  dataKey="name"
                  width={90}
                  className="text-xs fill-gray-600 dark:fill-gray-400"
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'rgba(255, 255, 255, 0.95)',
                    border: '1px solid #e5e7eb',
                    borderRadius: '0.375rem',
                  }}
                  content={({ active, payload }) => {
                    if (!active || !payload || payload.length === 0) {
                      return null;
                    }

                    const data = payload[0].payload as ChartDataPoint;

                    return (
                      <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-3 shadow-lg">
                        <p className="font-semibold text-gray-900 dark:text-white mb-2">
                          {data.name}
                        </p>
                        <div className="space-y-1 text-sm">
                          <div className="flex justify-between space-x-4">
                            <span className="text-gray-600 dark:text-gray-400">
                              Impact:
                            </span>
                            <span
                              className={`font-mono ${
                                data.impact > 0
                                  ? 'text-green-600 dark:text-green-400'
                                  : 'text-red-600 dark:text-red-400'
                              }`}
                            >
                              {formatPercent(data.impact)}
                            </span>
                          </div>
                          <div className="flex justify-between space-x-4">
                            <span className="text-gray-600 dark:text-gray-400">
                              Value:
                            </span>
                            <span className="font-mono text-gray-900 dark:text-white">
                              {data.value.toFixed(2)}
                            </span>
                          </div>
                          <div className="flex justify-between space-x-4">
                            <span className="text-gray-600 dark:text-gray-400">
                              Weight:
                            </span>
                            <span className="font-mono text-gray-900 dark:text-white">
                              {data.weight.toFixed(2)}
                            </span>
                          </div>
                        </div>
                      </div>
                    );
                  }}
                />
                <ReferenceLine
                  x={0}
                  stroke="#6b7280"
                  strokeWidth={2}
                  strokeDasharray="3 3"
                />
                <Bar dataKey="impact" radius={[0, 4, 4, 0]} maxBarSize={40}>
                  {chartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Detailed Table */}
          <div className="overflow-hidden rounded-lg border border-gray-200 dark:border-gray-700">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead className="bg-gray-50 dark:bg-gray-900">
                <tr>
                  <th
                    scope="col"
                    className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider"
                  >
                    Indicator
                  </th>
                  <th
                    scope="col"
                    className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider"
                  >
                    Value
                  </th>
                  <th
                    scope="col"
                    className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider"
                  >
                    Weight
                  </th>
                  <th
                    scope="col"
                    className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider"
                  >
                    Impact
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                {chartData.map((item, index) => (
                  <tr
                    key={index}
                    className="hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                  >
                    <td className="px-4 py-3 whitespace-nowrap">
                      <div className="flex items-center space-x-2">
                        <div
                          className="w-3 h-3 rounded"
                          style={{ backgroundColor: item.color }}
                          aria-hidden="true"
                        />
                        <span className="text-sm font-medium text-gray-900 dark:text-white">
                          {item.name}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-right">
                      <span className="text-sm font-mono text-gray-900 dark:text-white">
                        {item.value.toFixed(2)}
                      </span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-right">
                      <span className="text-sm font-mono text-gray-600 dark:text-gray-400">
                        {item.weight.toFixed(2)}
                      </span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-right">
                      <span
                        className={`text-sm font-mono font-semibold ${
                          item.impact > 0
                            ? 'text-green-600 dark:text-green-400'
                            : 'text-red-600 dark:text-red-400'
                        }`}
                      >
                        {formatPercent(item.impact)}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Summary */}
          <div className="grid grid-cols-2 gap-4 pt-4">
            <div className="p-4 rounded-lg bg-green-50 dark:bg-green-900/20">
              <div className="text-sm text-gray-600 dark:text-gray-400 mb-1">
                Positive Impact
              </div>
              <div className="text-2xl font-bold text-green-600 dark:text-green-400">
                {formatPercent(
                  chartData
                    .filter((d) => d.impact > 0)
                    .reduce((sum, d) => sum + d.impact, 0)
                )}
              </div>
              <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                {chartData.filter((d) => d.impact > 0).length} indicators
              </div>
            </div>

            <div className="p-4 rounded-lg bg-red-50 dark:bg-red-900/20">
              <div className="text-sm text-gray-600 dark:text-gray-400 mb-1">
                Negative Impact
              </div>
              <div className="text-2xl font-bold text-red-600 dark:text-red-400">
                {formatPercent(
                  chartData
                    .filter((d) => d.impact < 0)
                    .reduce((sum, d) => sum + d.impact, 0)
                )}
              </div>
              <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                {chartData.filter((d) => d.impact < 0).length} indicators
              </div>
            </div>
          </div>
        </div>
      </CardBody>
    </Card>
  );
};
