/**
 * Allocation Chart Component
 *
 * Displays portfolio allocation as a pie/donut chart
 */

import React, { useState, useMemo } from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts';
import type { Position } from '../../types/portfolio';
import { Card } from '../ui/Card';

interface AllocationChartProps {
  positions: Position[];
  groupBy?: 'symbol' | 'sector';
}

interface AllocationData {
  name: string;
  value: number;
  percentage: number;
}

const COLORS = [
  '#3b82f6', // blue
  '#10b981', // green
  '#f59e0b', // amber
  '#ef4444', // red
  '#8b5cf6', // violet
  '#ec4899', // pink
  '#06b6d4', // cyan
  '#84cc16', // lime
  '#f97316', // orange
  '#6366f1', // indigo
];

export const AllocationChart: React.FC<AllocationChartProps> = ({
  positions,
  groupBy = 'symbol',
}) => {
  const [activeIndex, setActiveIndex] = useState<number | null>(null);

  const allocationData = useMemo(() => {
    if (positions.length === 0) return [];

    const totalValue = positions.reduce((sum, pos) => sum + pos.market_value, 0);

    if (groupBy === 'symbol') {
      return positions
        .map((pos) => ({
          name: pos.symbol,
          value: pos.market_value,
          percentage: totalValue > 0 ? (pos.market_value / totalValue) * 100 : 0,
        }))
        .sort((a, b) => b.value - a.value);
    } else {
      // For sector grouping, we'll use a simple heuristic based on symbol
      // In a real application, this would come from position metadata
      const sectorMap = new Map<string, number>();

      positions.forEach((pos) => {
        // Simple sector classification based on symbol patterns
        let sector = 'Other';
        if (['AAPL', 'MSFT', 'GOOGL', 'META'].includes(pos.symbol)) {
          sector = 'Technology';
        } else if (['JPM', 'BAC', 'WFC', 'GS'].includes(pos.symbol)) {
          sector = 'Financial';
        } else if (['JNJ', 'PFE', 'UNH', 'ABBV'].includes(pos.symbol)) {
          sector = 'Healthcare';
        } else if (['XOM', 'CVX', 'COP', 'SLB'].includes(pos.symbol)) {
          sector = 'Energy';
        } else if (['TSLA', 'F', 'GM', 'TM'].includes(pos.symbol)) {
          sector = 'Automotive';
        }

        sectorMap.set(sector, (sectorMap.get(sector) || 0) + pos.market_value);
      });

      return Array.from(sectorMap.entries())
        .map(([name, value]) => ({
          name,
          value,
          percentage: totalValue > 0 ? (value / totalValue) * 100 : 0,
        }))
        .sort((a, b) => b.value - a.value);
    }
  }, [positions, groupBy]);

  const formatCurrency = (value: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg p-3">
          <p className="text-sm font-semibold text-gray-900 dark:text-white">
            {data.name}
          </p>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            {formatCurrency(data.value)}
          </p>
          <p className="text-sm font-medium text-blue-600 dark:text-blue-400">
            {data.percentage.toFixed(2)}%
          </p>
        </div>
      );
    }
    return null;
  };

  const onPieEnter = (_: any, index: number) => {
    setActiveIndex(index);
  };

  const onPieLeave = () => {
    setActiveIndex(null);
  };

  if (positions.length === 0) {
    return (
      <Card className="bg-white dark:bg-gray-800">
        <div className="p-8 text-center">
          <p className="text-gray-500 dark:text-gray-400">
            No positions to display
          </p>
        </div>
      </Card>
    );
  }

  return (
    <Card className="bg-white dark:bg-gray-800">
      <div className="p-6">
        <div className="flex justify-between items-center mb-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            Portfolio Allocation
          </h3>
          <span className="text-sm text-gray-500 dark:text-gray-400">
            By {groupBy === 'symbol' ? 'Symbol' : 'Sector'}
          </span>
        </div>

        <div className="flex flex-col lg:flex-row gap-6">
          {/* Chart */}
          <div className="flex-1 min-h-[300px]">
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={allocationData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ percentage }) =>
                    percentage > 5 ? `${percentage.toFixed(1)}%` : ''
                  }
                  outerRadius={100}
                  innerRadius={60}
                  fill="#8884d8"
                  dataKey="value"
                  onMouseEnter={onPieEnter}
                  onMouseLeave={onPieLeave}
                >
                  {allocationData.map((entry, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={COLORS[index % COLORS.length]}
                      opacity={activeIndex === null || activeIndex === index ? 1 : 0.6}
                    />
                  ))}
                </Pie>
                <Tooltip content={<CustomTooltip />} />
              </PieChart>
            </ResponsiveContainer>
          </div>

          {/* Legend */}
          <div className="lg:w-64">
            <div className="space-y-2 max-h-[300px] overflow-y-auto">
              {allocationData.map((item, index) => (
                <div
                  key={item.name}
                  className={`flex items-center justify-between p-2 rounded-lg transition-colors ${
                    activeIndex === index
                      ? 'bg-gray-100 dark:bg-gray-700'
                      : 'hover:bg-gray-50 dark:hover:bg-gray-800'
                  }`}
                  onMouseEnter={() => setActiveIndex(index)}
                  onMouseLeave={() => setActiveIndex(null)}
                  role="listitem"
                >
                  <div className="flex items-center gap-2 flex-1 min-w-0">
                    <div
                      className="w-3 h-3 rounded-full flex-shrink-0"
                      style={{ backgroundColor: COLORS[index % COLORS.length] }}
                      aria-hidden="true"
                    />
                    <span className="text-sm font-medium text-gray-900 dark:text-white truncate">
                      {item.name}
                    </span>
                  </div>
                  <div className="text-right ml-2 flex-shrink-0">
                    <div className="text-sm font-semibold text-gray-900 dark:text-white">
                      {item.percentage.toFixed(1)}%
                    </div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">
                      {formatCurrency(item.value)}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Summary Stats */}
        <div className="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                Total Positions
              </p>
              <p className="mt-1 text-lg font-semibold text-gray-900 dark:text-white">
                {groupBy === 'symbol' ? positions.length : allocationData.length}
              </p>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                Largest Position
              </p>
              <p className="mt-1 text-lg font-semibold text-gray-900 dark:text-white">
                {allocationData[0]?.percentage.toFixed(1)}%
              </p>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                Top 3 Concentration
              </p>
              <p className="mt-1 text-lg font-semibold text-gray-900 dark:text-white">
                {allocationData
                  .slice(0, 3)
                  .reduce((sum, item) => sum + item.percentage, 0)
                  .toFixed(1)}
                %
              </p>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                Total Value
              </p>
              <p className="mt-1 text-lg font-semibold text-gray-900 dark:text-white">
                {formatCurrency(
                  allocationData.reduce((sum, item) => sum + item.value, 0)
                )}
              </p>
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
};
