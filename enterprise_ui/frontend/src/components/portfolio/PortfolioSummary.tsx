/**
 * Portfolio Summary Component
 *
 * Displays overview of portfolio value, P&L, and margin usage
 */

import React from 'react';
import type { Portfolio } from '../../types/portfolio';
import { Card } from '../ui/Card';

interface PortfolioSummaryProps {
  portfolio: Portfolio | null;
  isLoading: boolean;
}

export const PortfolioSummary: React.FC<PortfolioSummaryProps> = ({
  portfolio,
  isLoading,
}) => {
  if (isLoading || !portfolio) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => (
          <Card key={i} className="animate-pulse">
            <div className="h-20 bg-gray-200 dark:bg-gray-700 rounded" />
          </Card>
        ))}
      </div>
    );
  }

  const totalPnL = portfolio.unrealized_pnl + portfolio.realized_pnl_today;
  const totalPnLPct =
    portfolio.total_value > 0
      ? (totalPnL / (portfolio.total_value - totalPnL)) * 100
      : 0;

  const marginUsagePct =
    portfolio.margin_used + portfolio.margin_available > 0
      ? (portfolio.margin_used /
          (portfolio.margin_used + portfolio.margin_available)) *
        100
      : 0;

  const formatCurrency = (value: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: portfolio.currency || 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(value);
  };

  const formatPercent = (value: number): string => {
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
  };

  const getPnLColorClass = (value: number): string => {
    if (value > 0) return 'text-green-600 dark:text-green-400';
    if (value < 0) return 'text-red-600 dark:text-red-400';
    return 'text-gray-600 dark:text-gray-400';
  };

  const getMarginColorClass = (pct: number): string => {
    if (pct >= 90) return 'bg-red-500';
    if (pct >= 70) return 'bg-orange-500';
    if (pct >= 50) return 'bg-yellow-500';
    return 'bg-green-500';
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {/* Total Value */}
      <Card
        className="bg-white dark:bg-gray-800"
        role="article"
        aria-label="Total Portfolio Value"
      >
        <div className="p-4">
          <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">
            Total Value
          </h3>
          <p className="mt-2 text-3xl font-semibold text-gray-900 dark:text-white">
            {formatCurrency(portfolio.total_value)}
          </p>
          <div className="mt-2 flex items-center text-sm">
            <span className="text-gray-600 dark:text-gray-400">
              Cash: {formatCurrency(portfolio.cash_balance)}
            </span>
          </div>
        </div>
      </Card>

      {/* Daily P&L */}
      <Card
        className="bg-white dark:bg-gray-800"
        role="article"
        aria-label="Daily Profit and Loss"
      >
        <div className="p-4">
          <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">
            Daily P&L
          </h3>
          <p
            className={`mt-2 text-3xl font-semibold ${getPnLColorClass(totalPnL)}`}
          >
            {formatCurrency(totalPnL)}
          </p>
          <div className="mt-2 flex items-center text-sm">
            <span className={getPnLColorClass(totalPnLPct)}>
              {formatPercent(totalPnLPct)}
            </span>
          </div>
        </div>
      </Card>

      {/* Unrealized/Realized P&L */}
      <Card
        className="bg-white dark:bg-gray-800"
        role="article"
        aria-label="Unrealized and Realized Profit and Loss"
      >
        <div className="p-4">
          <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">
            Unrealized / Realized
          </h3>
          <div className="mt-2 space-y-1">
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600 dark:text-gray-400">
                Unrealized:
              </span>
              <span
                className={`text-lg font-semibold ${getPnLColorClass(portfolio.unrealized_pnl)}`}
              >
                {formatCurrency(portfolio.unrealized_pnl)}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600 dark:text-gray-400">
                Realized:
              </span>
              <span
                className={`text-lg font-semibold ${getPnLColorClass(portfolio.realized_pnl_today)}`}
              >
                {formatCurrency(portfolio.realized_pnl_today)}
              </span>
            </div>
          </div>
        </div>
      </Card>

      {/* Margin Usage */}
      <Card
        className="bg-white dark:bg-gray-800"
        role="article"
        aria-label="Margin Usage"
      >
        <div className="p-4">
          <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">
            Margin Usage
          </h3>
          <p className="mt-2 text-3xl font-semibold text-gray-900 dark:text-white">
            {marginUsagePct.toFixed(1)}%
          </p>
          <div className="mt-2">
            <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
              <div
                className={`h-2 rounded-full transition-all duration-300 ${getMarginColorClass(marginUsagePct)}`}
                style={{ width: `${Math.min(marginUsagePct, 100)}%` }}
                role="progressbar"
                aria-valuenow={marginUsagePct}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-label={`Margin usage at ${marginUsagePct.toFixed(1)}%`}
              />
            </div>
            <div className="mt-1 flex justify-between text-xs text-gray-600 dark:text-gray-400">
              <span>{formatCurrency(portfolio.margin_used)} used</span>
              <span>{formatCurrency(portfolio.margin_available)} available</span>
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
};
