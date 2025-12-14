import React, { useState } from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';

export interface SourceStats {
  policyNetworkPct: number;
  cacheHitPct: number;
  heuristicPct: number;
  mctsLitePct?: number;
}

export interface DecisionSourceChartProps {
  sourceStats: SourceStats;
  className?: string;
}

interface ChartData {
  name: string;
  value: number;
  color: string;
}

const COLORS = {
  policyNetwork: '#3b82f6', // blue-500
  cacheHit: '#10b981', // green-500
  heuristic: '#f59e0b', // amber-500
  mctsLite: '#8b5cf6', // violet-500
};

const SOURCE_LABELS: Record<string, string> = {
  policyNetwork: 'Policy Network',
  cacheHit: 'Cache Hit',
  heuristic: 'Heuristic',
  mctsLite: 'MCTS Lite',
};

export function DecisionSourceChart({
  sourceStats,
  className = '',
}: DecisionSourceChartProps): React.ReactElement {
  const [activeIndex, setActiveIndex] = useState<number | null>(null);

  const data: ChartData[] = [
    {
      name: SOURCE_LABELS.policyNetwork,
      value: sourceStats.policyNetworkPct,
      color: COLORS.policyNetwork,
    },
    {
      name: SOURCE_LABELS.cacheHit,
      value: sourceStats.cacheHitPct,
      color: COLORS.cacheHit,
    },
    {
      name: SOURCE_LABELS.heuristic,
      value: sourceStats.heuristicPct,
      color: COLORS.heuristic,
    },
  ];

  if (sourceStats.mctsLitePct !== undefined && sourceStats.mctsLitePct > 0) {
    data.push({
      name: SOURCE_LABELS.mctsLite,
      value: sourceStats.mctsLitePct,
      color: COLORS.mctsLite,
    });
  }

  const filteredData = data.filter((item) => item.value > 0);

  const handleMouseEnter = (_: unknown, index: number) => {
    setActiveIndex(index);
  };

  const handleMouseLeave = () => {
    setActiveIndex(null);
  };

  const renderCustomLabel = ({
    cx,
    cy,
    midAngle,
    innerRadius,
    outerRadius,
    percent,
  }: {
    cx: number;
    cy: number;
    midAngle: number;
    innerRadius: number;
    outerRadius: number;
    percent: number;
  }) => {
    if (percent < 0.05) return null; // Don't show labels for segments < 5%

    const RADIAN = Math.PI / 180;
    const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
    const x = cx + radius * Math.cos(-midAngle * RADIAN);
    const y = cy + radius * Math.sin(-midAngle * RADIAN);

    return (
      <text
        x={x}
        y={y}
        fill="white"
        textAnchor={x > cx ? 'start' : 'end'}
        dominantBaseline="central"
        className="text-sm font-semibold"
      >
        {`${(percent * 100).toFixed(0)}%`}
      </text>
    );
  };

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0];
      return (
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg p-3">
          <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">
            {data.name}
          </p>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            {data.value.toFixed(2)}%
          </p>
        </div>
      );
    }
    return null;
  };

  if (filteredData.length === 0) {
    return (
      <div
        className={`flex items-center justify-center h-64 text-gray-500 dark:text-gray-400 ${className}`}
      >
        <p>No decision data available</p>
      </div>
    );
  }

  return (
    <div className={`w-full ${className}`} role="img" aria-label="Decision source distribution">
      <ResponsiveContainer width="100%" height={300}>
        <PieChart>
          <Pie
            data={filteredData}
            cx="50%"
            cy="50%"
            labelLine={false}
            label={renderCustomLabel}
            outerRadius={100}
            fill="#8884d8"
            dataKey="value"
            onMouseEnter={handleMouseEnter}
            onMouseLeave={handleMouseLeave}
            aria-label="Decision source breakdown"
          >
            {filteredData.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={entry.color}
                opacity={activeIndex === null || activeIndex === index ? 1 : 0.6}
                className="transition-opacity duration-200 cursor-pointer"
              />
            ))}
          </Pie>
          <Tooltip content={<CustomTooltip />} />
          <Legend
            verticalAlign="bottom"
            height={36}
            iconType="circle"
            formatter={(value: string) => (
              <span className="text-sm text-gray-700 dark:text-gray-300">{value}</span>
            )}
          />
        </PieChart>
      </ResponsiveContainer>

      <div className="mt-4 grid grid-cols-2 gap-3" role="list" aria-label="Decision source details">
        {filteredData.map((item, index) => (
          <div
            key={index}
            className="flex items-center gap-2 p-2 rounded hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
            role="listitem"
          >
            <div
              className="w-3 h-3 rounded-full"
              style={{ backgroundColor: item.color }}
              aria-hidden="true"
            />
            <div className="flex-1">
              <div className="text-xs text-gray-600 dark:text-gray-400">{item.name}</div>
              <div className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                {item.value.toFixed(2)}%
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
