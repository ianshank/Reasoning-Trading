/**
 * Position Card Component
 *
 * Displays detailed information about an individual position
 */

import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import type { Position } from '../../types/portfolio';
import { Card } from '../ui/Card';
import { Button } from '../ui/Button';

interface PositionCardProps {
  position: Position;
  onClose?: () => void;
  onModify?: () => void;
}

interface PnLHistoryPoint {
  timestamp: string;
  pnl: number;
}

export const PositionCard: React.FC<PositionCardProps> = ({
  position,
  onClose,
  onModify,
}) => {
  const formatCurrency = (value: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(value);
  };

  const formatPercent = (value: number): string => {
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
  };

  const formatDateTime = (dateString: string): string => {
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(new Date(dateString));
  };

  const getPnLColorClass = (value: number): string => {
    if (value > 0) return 'text-green-600 dark:text-green-400';
    if (value < 0) return 'text-red-600 dark:text-red-400';
    return 'text-gray-600 dark:text-gray-400';
  };

  const getPnLBgClass = (value: number): string => {
    if (value > 0) return 'bg-green-50 dark:bg-green-900/20';
    if (value < 0) return 'bg-red-50 dark:bg-red-900/20';
    return 'bg-gray-50 dark:bg-gray-900/20';
  };

  // Generate mock P&L history data for demonstration
  const generatePnLHistory = (): PnLHistoryPoint[] => {
    const points: PnLHistoryPoint[] = [];
    const entryTime = new Date(position.entry_time);
    const now = new Date();
    const diffHours = Math.floor(
      (now.getTime() - entryTime.getTime()) / (1000 * 60 * 60)
    );
    const numPoints = Math.min(Math.max(diffHours, 10), 50);

    for (let i = 0; i <= numPoints; i++) {
      const timestamp = new Date(
        entryTime.getTime() + (i / numPoints) * (now.getTime() - entryTime.getTime())
      );
      const pnl = (position.unrealized_pnl / numPoints) * i;
      points.push({
        timestamp: timestamp.toISOString(),
        pnl,
      });
    }

    return points;
  };

  const pnlHistory = generatePnLHistory();

  const calculateRiskReward = (): string => {
    if (!position.stop_loss_price || !position.take_profit_price) {
      return 'N/A';
    }
    const risk = Math.abs(position.entry_price - position.stop_loss_price);
    const reward = Math.abs(position.take_profit_price - position.entry_price);
    return `1:${(reward / risk).toFixed(2)}`;
  };

  const calculateMaxRisk = (): number => {
    if (!position.stop_loss_price) return 0;
    return Math.abs(
      (position.entry_price - position.stop_loss_price) * position.quantity
    );
  };

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg p-3">
          <p className="text-sm text-gray-600 dark:text-gray-400">
            {formatDateTime(payload[0].payload.timestamp)}
          </p>
          <p
            className={`text-lg font-semibold ${getPnLColorClass(payload[0].value)}`}
          >
            {formatCurrency(payload[0].value)}
          </p>
        </div>
      );
    }
    return null;
  };

  return (
    <Card className="bg-white dark:bg-gray-800">
      <div className="p-6">
        {/* Header */}
        <div className="flex justify-between items-start mb-6">
          <div>
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
              {position.symbol}
            </h2>
            <div className="mt-1 flex items-center gap-2">
              <span
                className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                  position.side === 'long'
                    ? 'bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-400'
                    : 'bg-purple-100 text-purple-800 dark:bg-purple-900/20 dark:text-purple-400'
                }`}
              >
                {position.side.toUpperCase()}
              </span>
              <span className="text-sm text-gray-500 dark:text-gray-400">
                {position.quantity.toLocaleString()} shares
              </span>
            </div>
          </div>
          <div className="flex gap-2">
            {onModify && (
              <Button
                variant="outline"
                onClick={onModify}
                aria-label="Modify position"
              >
                Modify
              </Button>
            )}
            {onClose && (
              <Button
                variant="outline"
                onClick={onClose}
                className="text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300"
                aria-label="Close position"
              >
                Close Position
              </Button>
            )}
          </div>
        </div>

        {/* P&L Summary */}
        <div className={`rounded-lg p-4 mb-6 ${getPnLBgClass(position.unrealized_pnl)}`}>
          <div className="flex justify-between items-center">
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">
                Unrealized P&L
              </p>
              <p
                className={`text-3xl font-bold ${getPnLColorClass(position.unrealized_pnl)}`}
              >
                {formatCurrency(position.unrealized_pnl)}
              </p>
            </div>
            <div className="text-right">
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">
                Return
              </p>
              <p
                className={`text-3xl font-bold ${getPnLColorClass(position.unrealized_pnl_pct)}`}
              >
                {formatPercent(position.unrealized_pnl_pct)}
              </p>
            </div>
          </div>
        </div>

        {/* Entry Details */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div>
            <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
              Entry Price
            </p>
            <p className="mt-1 text-lg font-semibold text-gray-900 dark:text-white">
              {formatCurrency(position.entry_price)}
            </p>
          </div>
          <div>
            <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
              Current Price
            </p>
            <p className="mt-1 text-lg font-semibold text-gray-900 dark:text-white">
              {formatCurrency(position.current_price)}
            </p>
          </div>
          <div>
            <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
              Cost Basis
            </p>
            <p className="mt-1 text-lg font-semibold text-gray-900 dark:text-white">
              {formatCurrency(position.cost_basis)}
            </p>
          </div>
          <div>
            <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
              Market Value
            </p>
            <p className="mt-1 text-lg font-semibold text-gray-900 dark:text-white">
              {formatCurrency(position.market_value)}
            </p>
          </div>
        </div>

        {/* P&L Chart */}
        <div className="mb-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            P&L Over Time
          </h3>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={pnlHistory}>
              <CartesianGrid
                strokeDasharray="3 3"
                className="stroke-gray-200 dark:stroke-gray-700"
              />
              <XAxis
                dataKey="timestamp"
                tickFormatter={(value) => {
                  const date = new Date(value);
                  return `${date.getHours()}:${date.getMinutes().toString().padStart(2, '0')}`;
                }}
                className="text-xs"
                stroke="currentColor"
              />
              <YAxis
                tickFormatter={(value) => formatCurrency(value)}
                className="text-xs"
                stroke="currentColor"
              />
              <Tooltip content={<CustomTooltip />} />
              <Line
                type="monotone"
                dataKey="pnl"
                stroke={position.unrealized_pnl >= 0 ? '#10b981' : '#ef4444'}
                strokeWidth={2}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Risk Metrics */}
        <div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Risk Metrics
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                Stop Loss
              </p>
              <p className="mt-1 text-lg font-semibold text-red-600 dark:text-red-400">
                {position.stop_loss_price
                  ? formatCurrency(position.stop_loss_price)
                  : 'Not set'}
              </p>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                Take Profit
              </p>
              <p className="mt-1 text-lg font-semibold text-green-600 dark:text-green-400">
                {position.take_profit_price
                  ? formatCurrency(position.take_profit_price)
                  : 'Not set'}
              </p>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                Risk/Reward
              </p>
              <p className="mt-1 text-lg font-semibold text-gray-900 dark:text-white">
                {calculateRiskReward()}
              </p>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                Max Risk
              </p>
              <p className="mt-1 text-lg font-semibold text-gray-900 dark:text-white">
                {formatCurrency(calculateMaxRisk())}
              </p>
            </div>
          </div>

          {position.trailing_stop && (
            <div className="mt-4 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
              <div className="flex items-center gap-2">
                <span className="text-blue-600 dark:text-blue-400 font-medium">
                  Trailing Stop Active
                </span>
                <span className="text-sm text-gray-600 dark:text-gray-400">
                  Distance: {(position.trailing_distance_pct * 100).toFixed(2)}%
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Entry Info */}
        <div className="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700">
          <div className="flex justify-between text-sm">
            <div>
              <span className="text-gray-500 dark:text-gray-400">Entered: </span>
              <span className="text-gray-900 dark:text-white font-medium">
                {formatDateTime(position.entry_time)}
              </span>
            </div>
            <div>
              <span className="text-gray-500 dark:text-gray-400">Horizon: </span>
              <span className="text-gray-900 dark:text-white font-medium">
                {position.time_horizon}
              </span>
            </div>
          </div>
          {position.notes && (
            <div className="mt-3">
              <p className="text-sm text-gray-500 dark:text-gray-400">Notes:</p>
              <p className="mt-1 text-sm text-gray-900 dark:text-white">
                {position.notes}
              </p>
            </div>
          )}
        </div>
      </div>
    </Card>
  );
};
