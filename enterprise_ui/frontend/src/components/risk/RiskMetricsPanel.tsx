/**
 * Risk Metrics Panel Component
 *
 * Displays comprehensive risk metrics dashboard
 */

import React from 'react';
import type { RiskMetrics } from '../../types/portfolio';
import { Card } from '../ui/Card';

interface RiskMetricsPanelProps {
  metrics: RiskMetrics | null;
  isLoading: boolean;
}

export const RiskMetricsPanel: React.FC<RiskMetricsPanelProps> = ({
  metrics,
  isLoading,
}) => {
  if (isLoading || !metrics) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {[...Array(6)].map((_, i) => (
          <Card key={i} className="animate-pulse">
            <div className="h-24 bg-gray-200 dark:bg-gray-700 rounded" />
          </Card>
        ))}
      </div>
    );
  }

  const formatCurrency = (value: number | null): string => {
    if (value === null) return 'N/A';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  const formatPercent = (value: number | null): string => {
    if (value === null) return 'N/A';
    return `${(value * 100).toFixed(2)}%`;
  };

  const formatRatio = (value: number | null): string => {
    if (value === null) return 'N/A';
    return value.toFixed(2);
  };

  const getDrawdownColorClass = (value: number): string => {
    if (value >= 0.2) return 'text-red-600 dark:text-red-400';
    if (value >= 0.15) return 'text-orange-600 dark:text-orange-400';
    if (value >= 0.1) return 'text-yellow-600 dark:text-yellow-400';
    return 'text-green-600 dark:text-green-400';
  };

  const getMarginColorClass = (value: number): string => {
    if (value >= 0.9) return 'text-red-600 dark:text-red-400';
    if (value >= 0.7) return 'text-orange-600 dark:text-orange-400';
    if (value >= 0.5) return 'text-yellow-600 dark:text-yellow-400';
    return 'text-green-600 dark:text-green-400';
  };

  const getSharpeColorClass = (value: number | null): string => {
    if (value === null) return 'text-gray-600 dark:text-gray-400';
    if (value >= 2.0) return 'text-green-600 dark:text-green-400';
    if (value >= 1.0) return 'text-blue-600 dark:text-blue-400';
    if (value >= 0.5) return 'text-yellow-600 dark:text-yellow-400';
    return 'text-red-600 dark:text-red-400';
  };

  const getConcentrationColorClass = (value: number): string => {
    if (value >= 0.4) return 'text-red-600 dark:text-red-400';
    if (value >= 0.3) return 'text-orange-600 dark:text-orange-400';
    if (value >= 0.2) return 'text-yellow-600 dark:text-yellow-400';
    return 'text-green-600 dark:text-green-400';
  };

  return (
    <div className="space-y-6">
      {/* Value at Risk */}
      <div>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Value at Risk
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Card className="bg-white dark:bg-gray-800" role="article">
            <div className="p-4">
              <div className="flex items-center justify-between">
                <h4 className="text-sm font-medium text-gray-500 dark:text-gray-400">
                  Daily VaR (95%)
                </h4>
                <span
                  className="text-xs bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-400 px-2 py-1 rounded-full"
                  aria-label="95% confidence level"
                >
                  95%
                </span>
              </div>
              <p className="mt-2 text-2xl font-bold text-gray-900 dark:text-white">
                {formatCurrency(metrics.daily_var_95)}
              </p>
              <p className="mt-1 text-xs text-gray-600 dark:text-gray-400">
                Maximum expected daily loss
              </p>
            </div>
          </Card>

          <Card className="bg-white dark:bg-gray-800" role="article">
            <div className="p-4">
              <div className="flex items-center justify-between">
                <h4 className="text-sm font-medium text-gray-500 dark:text-gray-400">
                  Daily VaR (99%)
                </h4>
                <span
                  className="text-xs bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-400 px-2 py-1 rounded-full"
                  aria-label="99% confidence level"
                >
                  99%
                </span>
              </div>
              <p className="mt-2 text-2xl font-bold text-gray-900 dark:text-white">
                {formatCurrency(metrics.daily_var_99)}
              </p>
              <p className="mt-1 text-xs text-gray-600 dark:text-gray-400">
                Extreme loss scenario
              </p>
            </div>
          </Card>
        </div>
      </div>

      {/* Drawdown Metrics */}
      <div>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Drawdown Analysis
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Card className="bg-white dark:bg-gray-800" role="article">
            <div className="p-4">
              <h4 className="text-sm font-medium text-gray-500 dark:text-gray-400">
                Maximum Drawdown
              </h4>
              <p
                className={`mt-2 text-2xl font-bold ${getDrawdownColorClass(metrics.max_drawdown)}`}
              >
                {formatPercent(metrics.max_drawdown)}
              </p>
              <p className="mt-1 text-xs text-gray-600 dark:text-gray-400">
                Largest peak-to-trough decline
              </p>
            </div>
          </Card>

          <Card className="bg-white dark:bg-gray-800" role="article">
            <div className="p-4">
              <h4 className="text-sm font-medium text-gray-500 dark:text-gray-400">
                Current Drawdown
              </h4>
              <p
                className={`mt-2 text-2xl font-bold ${getDrawdownColorClass(metrics.current_drawdown)}`}
              >
                {formatPercent(metrics.current_drawdown)}
              </p>
              {metrics.drawdown_start && (
                <p className="mt-1 text-xs text-gray-600 dark:text-gray-400">
                  Started:{' '}
                  {new Date(metrics.drawdown_start).toLocaleDateString()}
                </p>
              )}
            </div>
          </Card>
        </div>
      </div>

      {/* Performance Ratios */}
      <div>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Risk-Adjusted Returns
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card className="bg-white dark:bg-gray-800" role="article">
            <div className="p-4">
              <h4 className="text-sm font-medium text-gray-500 dark:text-gray-400">
                Sharpe Ratio
              </h4>
              <p
                className={`mt-2 text-2xl font-bold ${getSharpeColorClass(metrics.sharpe_ratio)}`}
              >
                {formatRatio(metrics.sharpe_ratio)}
              </p>
              <p className="mt-1 text-xs text-gray-600 dark:text-gray-400">
                Risk-adjusted return
              </p>
            </div>
          </Card>

          <Card className="bg-white dark:bg-gray-800" role="article">
            <div className="p-4">
              <h4 className="text-sm font-medium text-gray-500 dark:text-gray-400">
                Sortino Ratio
              </h4>
              <p
                className={`mt-2 text-2xl font-bold ${getSharpeColorClass(metrics.sortino_ratio)}`}
              >
                {formatRatio(metrics.sortino_ratio)}
              </p>
              <p className="mt-1 text-xs text-gray-600 dark:text-gray-400">
                Downside risk-adjusted
              </p>
            </div>
          </Card>

          <Card className="bg-white dark:bg-gray-800" role="article">
            <div className="p-4">
              <h4 className="text-sm font-medium text-gray-500 dark:text-gray-400">
                Volatility
              </h4>
              <p className="mt-2 text-2xl font-bold text-gray-900 dark:text-white">
                {formatPercent(metrics.portfolio_volatility)}
              </p>
              <p className="mt-1 text-xs text-gray-600 dark:text-gray-400">
                Annualized portfolio vol
              </p>
            </div>
          </Card>
        </div>
      </div>

      {/* Concentration & Leverage */}
      <div>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Concentration & Leverage
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card className="bg-white dark:bg-gray-800" role="article">
            <div className="p-4">
              <h4 className="text-sm font-medium text-gray-500 dark:text-gray-400">
                Largest Position
              </h4>
              <p
                className={`mt-2 text-2xl font-bold ${getConcentrationColorClass(metrics.largest_position_pct)}`}
              >
                {formatPercent(metrics.largest_position_pct)}
              </p>
              <p className="mt-1 text-xs text-gray-600 dark:text-gray-400">
                Of total portfolio
              </p>
            </div>
          </Card>

          <Card className="bg-white dark:bg-gray-800" role="article">
            <div className="p-4">
              <h4 className="text-sm font-medium text-gray-500 dark:text-gray-400">
                Top 5 Concentration
              </h4>
              <p
                className={`mt-2 text-2xl font-bold ${getConcentrationColorClass(metrics.top5_concentration)}`}
              >
                {formatPercent(metrics.top5_concentration)}
              </p>
              <p className="mt-1 text-xs text-gray-600 dark:text-gray-400">
                Top 5 positions
              </p>
            </div>
          </Card>

          <Card className="bg-white dark:bg-gray-800" role="article">
            <div className="p-4">
              <h4 className="text-sm font-medium text-gray-500 dark:text-gray-400">
                Leverage Ratio
              </h4>
              <p className="mt-2 text-2xl font-bold text-gray-900 dark:text-white">
                {formatRatio(metrics.leverage_ratio)}x
              </p>
              <p className="mt-1 text-xs text-gray-600 dark:text-gray-400">
                Total leverage
              </p>
            </div>
          </Card>

          <Card className="bg-white dark:bg-gray-800" role="article">
            <div className="p-4">
              <h4 className="text-sm font-medium text-gray-500 dark:text-gray-400">
                Margin Utilization
              </h4>
              <p
                className={`mt-2 text-2xl font-bold ${getMarginColorClass(metrics.margin_utilization)}`}
              >
                {formatPercent(metrics.margin_utilization)}
              </p>
              <div className="mt-2 w-full bg-gray-200 dark:bg-gray-700 rounded-full h-1.5">
                <div
                  className={`h-1.5 rounded-full transition-all duration-300 ${
                    metrics.margin_utilization >= 0.9
                      ? 'bg-red-500'
                      : metrics.margin_utilization >= 0.7
                        ? 'bg-orange-500'
                        : metrics.margin_utilization >= 0.5
                          ? 'bg-yellow-500'
                          : 'bg-green-500'
                  }`}
                  style={{
                    width: `${Math.min(metrics.margin_utilization * 100, 100)}%`,
                  }}
                  role="progressbar"
                  aria-valuenow={metrics.margin_utilization * 100}
                  aria-valuemin={0}
                  aria-valuemax={100}
                />
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
};
