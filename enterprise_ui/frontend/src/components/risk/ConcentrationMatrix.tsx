/**
 * Concentration Matrix Component
 *
 * Displays position concentration heatmap by symbol and sector
 */

import React, { useMemo } from 'react';
import type { Position } from '../../types/portfolio';
import { Card } from '../ui/Card';

interface ConcentrationMatrixProps {
  positions: Position[];
  thresholds?: {
    warning: number;
    danger: number;
  };
}

interface MatrixCell {
  symbol: string;
  sector: string;
  concentration: number;
  value: number;
}

export const ConcentrationMatrix: React.FC<ConcentrationMatrixProps> = ({
  positions,
  thresholds = { warning: 0.15, danger: 0.25 },
}) => {
  const matrixData = useMemo(() => {
    if (positions.length === 0) return [];

    const totalValue = positions.reduce((sum, pos) => sum + pos.market_value, 0);

    // Simple sector classification
    const getSector = (symbol: string): string => {
      if (['AAPL', 'MSFT', 'GOOGL', 'META', 'NVDA'].includes(symbol))
        return 'Technology';
      if (['JPM', 'BAC', 'WFC', 'GS', 'C'].includes(symbol)) return 'Financial';
      if (['JNJ', 'PFE', 'UNH', 'ABBV', 'MRK'].includes(symbol))
        return 'Healthcare';
      if (['XOM', 'CVX', 'COP', 'SLB', 'EOG'].includes(symbol)) return 'Energy';
      if (['TSLA', 'F', 'GM', 'TM', 'HMC'].includes(symbol))
        return 'Automotive';
      if (['AMZN', 'WMT', 'HD', 'TGT', 'COST'].includes(symbol)) return 'Retail';
      return 'Other';
    };

    return positions.map((pos) => ({
      symbol: pos.symbol,
      sector: getSector(pos.symbol),
      concentration: totalValue > 0 ? pos.market_value / totalValue : 0,
      value: pos.market_value,
    }));
  }, [positions]);

  const sectors = useMemo(() => {
    const sectorSet = new Set(matrixData.map((cell) => cell.sector));
    return Array.from(sectorSet).sort();
  }, [matrixData]);

  const sectorConcentrations = useMemo(() => {
    const concentrations = new Map<string, number>();
    matrixData.forEach((cell) => {
      const current = concentrations.get(cell.sector) || 0;
      concentrations.set(cell.sector, current + cell.concentration);
    });
    return concentrations;
  }, [matrixData]);

  const getCellColor = (concentration: number): string => {
    if (concentration >= thresholds.danger) {
      return 'bg-red-500 dark:bg-red-600';
    }
    if (concentration >= thresholds.warning) {
      return 'bg-orange-500 dark:bg-orange-600';
    }
    if (concentration >= 0.1) {
      return 'bg-yellow-500 dark:bg-yellow-600';
    }
    if (concentration >= 0.05) {
      return 'bg-blue-500 dark:bg-blue-600';
    }
    return 'bg-green-500 dark:bg-green-600';
  };

  const getCellOpacity = (concentration: number): string => {
    if (concentration >= 0.2) return 'opacity-100';
    if (concentration >= 0.15) return 'opacity-90';
    if (concentration >= 0.1) return 'opacity-70';
    if (concentration >= 0.05) return 'opacity-50';
    return 'opacity-30';
  };

  const formatCurrency = (value: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  const formatPercent = (value: number): string => {
    return `${(value * 100).toFixed(2)}%`;
  };

  if (positions.length === 0) {
    return (
      <Card className="bg-white dark:bg-gray-800">
        <div className="p-8 text-center">
          <p className="text-gray-500 dark:text-gray-400">
            No positions to analyze
          </p>
        </div>
      </Card>
    );
  }

  const maxConcentration = Math.max(...matrixData.map((c) => c.concentration));
  const hasWarnings = matrixData.some((c) => c.concentration >= thresholds.warning);

  return (
    <Card className="bg-white dark:bg-gray-800">
      <div className="p-6">
        <div className="flex justify-between items-start mb-6">
          <div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              Position Concentration Matrix
            </h3>
            <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
              Concentration by symbol and sector
            </p>
          </div>
          {hasWarnings && (
            <div className="flex items-center gap-2 text-orange-600 dark:text-orange-400">
              <svg
                className="w-5 h-5"
                fill="currentColor"
                viewBox="0 0 20 20"
                aria-hidden="true"
              >
                <path
                  fillRule="evenodd"
                  d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                  clipRule="evenodd"
                />
              </svg>
              <span className="text-sm font-medium">High concentration detected</span>
            </div>
          )}
        </div>

        {/* Matrix Grid */}
        <div className="overflow-x-auto">
          <div className="grid grid-cols-1 gap-4">
            {sectors.map((sector) => {
              const sectorPositions = matrixData.filter(
                (cell) => cell.sector === sector
              );
              const sectorConcentration = sectorConcentrations.get(sector) || 0;

              return (
                <div key={sector} className="space-y-2">
                  <div className="flex items-center justify-between">
                    <h4 className="text-sm font-semibold text-gray-900 dark:text-white">
                      {sector}
                    </h4>
                    <div className="flex items-center gap-2">
                      <span
                        className={`text-sm font-medium ${
                          sectorConcentration >= thresholds.danger
                            ? 'text-red-600 dark:text-red-400'
                            : sectorConcentration >= thresholds.warning
                              ? 'text-orange-600 dark:text-orange-400'
                              : 'text-gray-600 dark:text-gray-400'
                        }`}
                      >
                        {formatPercent(sectorConcentration)}
                      </span>
                      {sectorConcentration >= thresholds.warning && (
                        <span
                          className="text-xs bg-orange-100 text-orange-800 dark:bg-orange-900/20 dark:text-orange-400 px-2 py-0.5 rounded-full"
                          role="status"
                          aria-label="Warning: High concentration"
                        >
                          Warning
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="flex flex-wrap gap-2">
                    {sectorPositions.map((cell) => (
                      <div
                        key={cell.symbol}
                        className={`group relative px-3 py-2 rounded-lg transition-all hover:scale-105 ${getCellColor(cell.concentration)} ${getCellOpacity(cell.concentration)}`}
                        role="gridcell"
                        aria-label={`${cell.symbol}: ${formatPercent(cell.concentration)} concentration`}
                      >
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-semibold text-white">
                            {cell.symbol}
                          </span>
                          <span className="text-xs text-white/90">
                            {formatPercent(cell.concentration)}
                          </span>
                        </div>

                        {/* Tooltip */}
                        <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 hidden group-hover:block z-10">
                          <div className="bg-gray-900 dark:bg-gray-700 text-white text-xs rounded-lg py-2 px-3 whitespace-nowrap shadow-lg">
                            <div className="font-semibold">{cell.symbol}</div>
                            <div className="mt-1">
                              Concentration: {formatPercent(cell.concentration)}
                            </div>
                            <div>Value: {formatCurrency(cell.value)}</div>
                            <div className="mt-1 text-gray-400">
                              Sector: {cell.sector}
                            </div>
                            <div
                              className="absolute top-full left-1/2 transform -translate-x-1/2 -mt-1 border-4 border-transparent border-t-gray-900 dark:border-t-gray-700"
                              aria-hidden="true"
                            />
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Legend */}
        <div className="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div>
              <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Concentration Level
              </p>
              <div className="flex items-center gap-3 flex-wrap">
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 rounded bg-green-500 opacity-50" />
                  <span className="text-xs text-gray-600 dark:text-gray-400">
                    Low (&lt;5%)
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 rounded bg-blue-500 opacity-70" />
                  <span className="text-xs text-gray-600 dark:text-gray-400">
                    Moderate (5-10%)
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 rounded bg-yellow-500 opacity-70" />
                  <span className="text-xs text-gray-600 dark:text-gray-400">
                    Medium (10-15%)
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 rounded bg-orange-500 opacity-90" />
                  <span className="text-xs text-gray-600 dark:text-gray-400">
                    High (15-25%)
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 rounded bg-red-500" />
                  <span className="text-xs text-gray-600 dark:text-gray-400">
                    Critical (&gt;25%)
                  </span>
                </div>
              </div>
            </div>

            <div className="text-right">
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                Max Single Position
              </p>
              <p
                className={`mt-1 text-2xl font-bold ${
                  maxConcentration >= thresholds.danger
                    ? 'text-red-600 dark:text-red-400'
                    : maxConcentration >= thresholds.warning
                      ? 'text-orange-600 dark:text-orange-400'
                      : 'text-green-600 dark:text-green-400'
                }`}
              >
                {formatPercent(maxConcentration)}
              </p>
            </div>
          </div>
        </div>

        {/* Recommendations */}
        {hasWarnings && (
          <div className="mt-4 p-4 bg-orange-50 dark:bg-orange-900/20 rounded-lg">
            <div className="flex items-start gap-3">
              <svg
                className="w-5 h-5 text-orange-600 dark:text-orange-400 mt-0.5 flex-shrink-0"
                fill="currentColor"
                viewBox="0 0 20 20"
                aria-hidden="true"
              >
                <path
                  fillRule="evenodd"
                  d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                  clipRule="evenodd"
                />
              </svg>
              <div>
                <h5 className="text-sm font-semibold text-orange-900 dark:text-orange-400">
                  Concentration Warning
                </h5>
                <p className="mt-1 text-sm text-orange-800 dark:text-orange-300">
                  One or more positions exceed recommended concentration thresholds.
                  Consider rebalancing to reduce risk.
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </Card>
  );
};
