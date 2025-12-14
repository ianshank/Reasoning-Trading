/**
 * Drawdown Chart Component
 *
 * Displays drawdown visualization over time with recovery periods
 */

import React from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  ReferenceArea,
} from 'recharts';
import { Card } from '../ui/Card';

interface DrawdownPoint {
  timestamp: string;
  drawdown: number;
  is_recovery?: boolean;
}

interface DrawdownChartProps {
  drawdownHistory: DrawdownPoint[];
}

export const DrawdownChart: React.FC<DrawdownChartProps> = ({
  drawdownHistory,
}) => {
  const formatPercent = (value: number): string => {
    return `${(value * 100).toFixed(2)}%`;
  };

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
    });
  };

  const maxDrawdown = Math.min(
    ...drawdownHistory.map((point) => point.drawdown)
  );

  const maxDrawdownPoint = drawdownHistory.find(
    (point) => point.drawdown === maxDrawdown
  );

  const getDrawdownColor = (value: number): string => {
    const absValue = Math.abs(value);
    if (absValue >= 0.2) return '#ef4444'; // red
    if (absValue >= 0.15) return '#f97316'; // orange
    if (absValue >= 0.1) return '#f59e0b'; // amber
    return '#10b981'; // green
  };

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const drawdown = payload[0].value;
      return (
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg p-3">
          <p className="text-sm font-medium text-gray-900 dark:text-white mb-1">
            {new Date(label).toLocaleDateString('en-US', {
              month: 'short',
              day: 'numeric',
              year: 'numeric',
            })}
          </p>
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-600 dark:text-gray-400">
              Drawdown:
            </span>
            <span
              className="text-lg font-semibold"
              style={{ color: getDrawdownColor(drawdown) }}
            >
              {formatPercent(drawdown)}
            </span>
          </div>
          {payload[0].payload.is_recovery && (
            <p className="text-xs text-green-600 dark:text-green-400 mt-1">
              Recovery period
            </p>
          )}
        </div>
      );
    }
    return null;
  };

  if (drawdownHistory.length === 0) {
    return (
      <Card className="bg-white dark:bg-gray-800">
        <div className="p-8 text-center">
          <p className="text-gray-500 dark:text-gray-400">
            No drawdown history available
          </p>
        </div>
      </Card>
    );
  }

  const recoveryPeriods = drawdownHistory.reduce(
    (periods: Array<{ start: string; end: string }>, point, index) => {
      if (point.is_recovery && index > 0) {
        const lastPeriod = periods[periods.length - 1];
        if (lastPeriod && !lastPeriod.end) {
          // Continue existing recovery period
          return periods;
        } else {
          // Start new recovery period
          periods.push({
            start: point.timestamp,
            end: '',
          });
        }
      } else if (!point.is_recovery && periods.length > 0) {
        const lastPeriod = periods[periods.length - 1];
        if (lastPeriod && !lastPeriod.end) {
          lastPeriod.end =
            index > 0 ? drawdownHistory[index - 1].timestamp : point.timestamp;
        }
      }
      return periods;
    },
    []
  );

  return (
    <Card className="bg-white dark:bg-gray-800">
      <div className="p-6">
        <div className="flex justify-between items-center mb-6">
          <div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              Drawdown Analysis
            </h3>
            <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
              Peak-to-trough decline over time
            </p>
          </div>
          <div className="text-right">
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Max Drawdown
            </p>
            <p
              className="text-2xl font-bold"
              style={{ color: getDrawdownColor(maxDrawdown) }}
            >
              {formatPercent(maxDrawdown)}
            </p>
            {maxDrawdownPoint && (
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                {formatDate(maxDrawdownPoint.timestamp)}
              </p>
            )}
          </div>
        </div>

        <ResponsiveContainer width="100%" height={300}>
          <AreaChart data={drawdownHistory}>
            <defs>
              <linearGradient id="drawdownGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#ef4444" stopOpacity={0.1} />
              </linearGradient>
            </defs>
            <CartesianGrid
              strokeDasharray="3 3"
              className="stroke-gray-200 dark:stroke-gray-700"
            />
            <XAxis
              dataKey="timestamp"
              tickFormatter={formatDate}
              className="text-xs"
              stroke="currentColor"
            />
            <YAxis
              tickFormatter={formatPercent}
              className="text-xs"
              stroke="currentColor"
              domain={[maxDrawdown * 1.2, 0]}
            />
            <Tooltip content={<CustomTooltip />} />

            {/* Zero line */}
            <ReferenceLine
              y={0}
              stroke="currentColor"
              strokeDasharray="3 3"
              label={{
                value: 'Baseline',
                position: 'right',
                className: 'text-xs fill-gray-500',
              }}
            />

            {/* Max drawdown line */}
            {maxDrawdown < 0 && (
              <ReferenceLine
                y={maxDrawdown}
                stroke={getDrawdownColor(maxDrawdown)}
                strokeDasharray="5 5"
                strokeWidth={2}
                label={{
                  value: `Max: ${formatPercent(maxDrawdown)}`,
                  position: 'right',
                  className: 'text-xs',
                  fill: getDrawdownColor(maxDrawdown),
                }}
              />
            )}

            {/* Recovery periods */}
            {recoveryPeriods.map((period, index) => {
              if (period.end) {
                return (
                  <ReferenceArea
                    key={index}
                    x1={period.start}
                    x2={period.end}
                    fill="#10b981"
                    fillOpacity={0.1}
                    label={{
                      value: 'Recovery',
                      position: 'top',
                      className: 'text-xs fill-green-600',
                    }}
                  />
                );
              }
              return null;
            })}

            <Area
              type="monotone"
              dataKey="drawdown"
              stroke="#ef4444"
              strokeWidth={2}
              fill="url(#drawdownGradient)"
            />
          </AreaChart>
        </ResponsiveContainer>

        <div className="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                Current Drawdown
              </p>
              <p
                className="mt-1 text-lg font-semibold"
                style={{
                  color: getDrawdownColor(
                    drawdownHistory[drawdownHistory.length - 1]?.drawdown || 0
                  ),
                }}
              >
                {formatPercent(
                  drawdownHistory[drawdownHistory.length - 1]?.drawdown || 0
                )}
              </p>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                Max Drawdown
              </p>
              <p
                className="mt-1 text-lg font-semibold"
                style={{ color: getDrawdownColor(maxDrawdown) }}
              >
                {formatPercent(maxDrawdown)}
              </p>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                Recovery Periods
              </p>
              <p className="mt-1 text-lg font-semibold text-gray-900 dark:text-white">
                {recoveryPeriods.filter((p) => p.end).length}
              </p>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                Days Tracked
              </p>
              <p className="mt-1 text-lg font-semibold text-gray-900 dark:text-white">
                {drawdownHistory.length}
              </p>
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
};
