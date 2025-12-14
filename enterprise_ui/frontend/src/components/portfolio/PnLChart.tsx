/**
 * P&L Chart Component
 *
 * Displays profit and loss over time with multiple view options
 */

import React, { useState, useMemo } from 'react';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import type { PortfolioHistory } from '../../types/portfolio';
import { Card } from '../ui/Card';
import { Button } from '../ui/Button';

interface PnLChartProps {
  history: PortfolioHistory;
  timeframe?: '1D' | '1W' | '1M' | '3M' | '1Y' | 'ALL';
  showRealized?: boolean;
  showUnrealized?: boolean;
}

type ViewMode = 'cumulative' | 'daily';

export const PnLChart: React.FC<PnLChartProps> = ({
  history,
  timeframe = '1W',
  showRealized = true,
  showUnrealized = true,
}) => {
  const [viewMode, setViewMode] = useState<ViewMode>('cumulative');
  const [granularity, setGranularity] = useState<'hourly' | 'daily'>('daily');

  const chartData = useMemo(() => {
    if (!history.values || history.values.length === 0) {
      return [];
    }

    let data = [...history.values];

    // Filter by timeframe
    const now = new Date();
    const cutoffDate = new Date();

    switch (timeframe) {
      case '1D':
        cutoffDate.setDate(now.getDate() - 1);
        break;
      case '1W':
        cutoffDate.setDate(now.getDate() - 7);
        break;
      case '1M':
        cutoffDate.setMonth(now.getMonth() - 1);
        break;
      case '3M':
        cutoffDate.setMonth(now.getMonth() - 3);
        break;
      case '1Y':
        cutoffDate.setFullYear(now.getFullYear() - 1);
        break;
      case 'ALL':
      default:
        cutoffDate.setFullYear(1970);
    }

    data = data.filter((point) => new Date(point.timestamp) >= cutoffDate);

    // Calculate cumulative or daily P&L
    if (viewMode === 'cumulative') {
      return data.map((point) => ({
        timestamp: point.timestamp,
        total_pnl: point.pnl,
        realized_pnl: point.pnl * 0.4, // Mock realized portion
        unrealized_pnl: point.pnl * 0.6, // Mock unrealized portion
      }));
    } else {
      // Daily P&L changes
      return data.map((point, index) => {
        const prevPnl = index > 0 ? data[index - 1].pnl : 0;
        const dailyPnl = point.pnl - prevPnl;
        return {
          timestamp: point.timestamp,
          total_pnl: dailyPnl,
          realized_pnl: dailyPnl * 0.4,
          unrealized_pnl: dailyPnl * 0.6,
        };
      });
    }
  }, [history, timeframe, viewMode]);

  const formatCurrency = (value: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  const formatDate = (dateString: string): string => {
    const date = new Date(dateString);

    if (timeframe === '1D') {
      return date.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
      });
    }

    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
    });
  };

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg p-3">
          <p className="text-sm font-medium text-gray-900 dark:text-white mb-2">
            {new Date(label).toLocaleDateString('en-US', {
              month: 'short',
              day: 'numeric',
              year: 'numeric',
              hour: '2-digit',
              minute: '2-digit',
            })}
          </p>
          {payload.map((entry: any, index: number) => (
            <div key={index} className="flex items-center justify-between gap-4">
              <span className="text-sm" style={{ color: entry.color }}>
                {entry.name}:
              </span>
              <span className="text-sm font-semibold" style={{ color: entry.color }}>
                {formatCurrency(entry.value)}
              </span>
            </div>
          ))}
        </div>
      );
    }
    return null;
  };

  const totalReturn = history.total_return_pct;
  const totalReturnClass =
    totalReturn >= 0
      ? 'text-green-600 dark:text-green-400'
      : 'text-red-600 dark:text-red-400';

  if (chartData.length === 0) {
    return (
      <Card className="bg-white dark:bg-gray-800">
        <div className="p-8 text-center">
          <p className="text-gray-500 dark:text-gray-400">
            No P&L history available
          </p>
        </div>
      </Card>
    );
  }

  return (
    <Card className="bg-white dark:bg-gray-800">
      <div className="p-6">
        {/* Header with Controls */}
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-6">
          <div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              Profit & Loss
            </h3>
            <div className="mt-1 flex items-baseline gap-2">
              <span className="text-2xl font-bold text-gray-900 dark:text-white">
                {formatCurrency(history.final_value - history.initial_value)}
              </span>
              <span className={`text-lg font-semibold ${totalReturnClass}`}>
                ({totalReturn >= 0 ? '+' : ''}
                {totalReturn.toFixed(2)}%)
              </span>
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            {/* View Mode Toggle */}
            <div className="inline-flex rounded-lg border border-gray-200 dark:border-gray-700">
              <Button
                variant={viewMode === 'cumulative' ? 'primary' : 'ghost'}
                size="sm"
                onClick={() => setViewMode('cumulative')}
                className="rounded-r-none"
                aria-label="Show cumulative view"
              >
                Cumulative
              </Button>
              <Button
                variant={viewMode === 'daily' ? 'primary' : 'ghost'}
                size="sm"
                onClick={() => setViewMode('daily')}
                className="rounded-l-none"
                aria-label="Show daily view"
              >
                Daily
              </Button>
            </div>

            {/* Granularity Toggle */}
            <div className="inline-flex rounded-lg border border-gray-200 dark:border-gray-700">
              <Button
                variant={granularity === 'hourly' ? 'primary' : 'ghost'}
                size="sm"
                onClick={() => setGranularity('hourly')}
                className="rounded-r-none"
                aria-label="Show hourly granularity"
                disabled={timeframe !== '1D' && timeframe !== '1W'}
              >
                Hourly
              </Button>
              <Button
                variant={granularity === 'daily' ? 'primary' : 'ghost'}
                size="sm"
                onClick={() => setGranularity('daily')}
                className="rounded-l-none"
                aria-label="Show daily granularity"
              >
                Daily
              </Button>
            </div>
          </div>
        </div>

        {/* Chart */}
        <ResponsiveContainer width="100%" height={400}>
          {viewMode === 'cumulative' ? (
            <AreaChart data={chartData}>
              <defs>
                <linearGradient id="colorTotal" x1="0" y1="0" x2="0" y2="1">
                  <stop
                    offset="5%"
                    stopColor="#3b82f6"
                    stopOpacity={0.3}
                  />
                  <stop
                    offset="95%"
                    stopColor="#3b82f6"
                    stopOpacity={0}
                  />
                </linearGradient>
                <linearGradient id="colorRealized" x1="0" y1="0" x2="0" y2="1">
                  <stop
                    offset="5%"
                    stopColor="#10b981"
                    stopOpacity={0.3}
                  />
                  <stop
                    offset="95%"
                    stopColor="#10b981"
                    stopOpacity={0}
                  />
                </linearGradient>
                <linearGradient id="colorUnrealized" x1="0" y1="0" x2="0" y2="1">
                  <stop
                    offset="5%"
                    stopColor="#f59e0b"
                    stopOpacity={0.3}
                  />
                  <stop
                    offset="95%"
                    stopColor="#f59e0b"
                    stopOpacity={0}
                  />
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
                tickFormatter={formatCurrency}
                className="text-xs"
                stroke="currentColor"
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend />
              <Area
                type="monotone"
                dataKey="total_pnl"
                name="Total P&L"
                stroke="#3b82f6"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#colorTotal)"
              />
              {showRealized && (
                <Area
                  type="monotone"
                  dataKey="realized_pnl"
                  name="Realized P&L"
                  stroke="#10b981"
                  strokeWidth={1}
                  strokeDasharray="5 5"
                  fillOpacity={1}
                  fill="url(#colorRealized)"
                />
              )}
              {showUnrealized && (
                <Area
                  type="monotone"
                  dataKey="unrealized_pnl"
                  name="Unrealized P&L"
                  stroke="#f59e0b"
                  strokeWidth={1}
                  strokeDasharray="5 5"
                  fillOpacity={1}
                  fill="url(#colorUnrealized)"
                />
              )}
            </AreaChart>
          ) : (
            <LineChart data={chartData}>
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
                tickFormatter={formatCurrency}
                className="text-xs"
                stroke="currentColor"
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend />
              <Line
                type="monotone"
                dataKey="total_pnl"
                name="Daily P&L"
                stroke="#3b82f6"
                strokeWidth={2}
                dot={false}
              />
              {showRealized && (
                <Line
                  type="monotone"
                  dataKey="realized_pnl"
                  name="Daily Realized"
                  stroke="#10b981"
                  strokeWidth={1}
                  strokeDasharray="5 5"
                  dot={false}
                />
              )}
              {showUnrealized && (
                <Line
                  type="monotone"
                  dataKey="unrealized_pnl"
                  name="Daily Unrealized"
                  stroke="#f59e0b"
                  strokeWidth={1}
                  strokeDasharray="5 5"
                  dot={false}
                />
              )}
            </LineChart>
          )}
        </ResponsiveContainer>

        {/* Summary Stats */}
        <div className="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                Initial Value
              </p>
              <p className="mt-1 text-lg font-semibold text-gray-900 dark:text-white">
                {formatCurrency(history.initial_value)}
              </p>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                Current Value
              </p>
              <p className="mt-1 text-lg font-semibold text-gray-900 dark:text-white">
                {formatCurrency(history.final_value)}
              </p>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                Total Return
              </p>
              <p className={`mt-1 text-lg font-semibold ${totalReturnClass}`}>
                {formatCurrency(history.final_value - history.initial_value)}
              </p>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                Return %
              </p>
              <p className={`mt-1 text-lg font-semibold ${totalReturnClass}`}>
                {totalReturn >= 0 ? '+' : ''}
                {totalReturn.toFixed(2)}%
              </p>
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
};
