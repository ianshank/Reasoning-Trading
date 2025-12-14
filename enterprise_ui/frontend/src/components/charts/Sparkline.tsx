/**
 * Sparkline component - Mini inline chart for trend visualization
 */

import React from 'react';
import { LineChart, Line, ResponsiveContainer, YAxis } from 'recharts';
import { useChartTheme } from './hooks/useChartTheme';

export interface SparklineProps {
  data: Array<{ value: number; timestamp?: number | string }>;
  color?: string;
  showTrend?: boolean;
  width?: number | string;
  height?: number;
  className?: string;
  ariaLabel?: string;
}

export const Sparkline: React.FC<SparklineProps> = ({
  data,
  color,
  showTrend = false,
  width = '100%',
  height = 40,
  className = '',
  ariaLabel = 'Sparkline chart',
}) => {
  const theme = useChartTheme();
  const lineColor = color || theme.colors.primary;

  const trend = React.useMemo(() => {
    if (!showTrend || data.length < 2) return null;

    const firstValue = data[0].value;
    const lastValue = data[data.length - 1].value;
    const change = lastValue - firstValue;
    const percentChange = (change / firstValue) * 100;

    return {
      direction: change >= 0 ? 'up' : 'down',
      change,
      percentChange,
    };
  }, [data, showTrend]);

  const minValue = Math.min(...data.map(d => d.value));
  const maxValue = Math.max(...data.map(d => d.value));
  const padding = (maxValue - minValue) * 0.1;

  return (
    <div
      className={`sparkline-container ${className}`}
      style={{ width, height, display: 'inline-flex', alignItems: 'center', gap: '8px' }}
      role="img"
      aria-label={ariaLabel}
    >
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={data} margin={{ top: 2, right: 2, bottom: 2, left: 2 }}>
          <YAxis
            domain={[minValue - padding, maxValue + padding]}
            hide
          />
          <Line
            type="monotone"
            dataKey="value"
            stroke={lineColor}
            strokeWidth={1.5}
            dot={false}
            animationDuration={300}
            isAnimationActive={true}
          />
        </LineChart>
      </ResponsiveContainer>
      {showTrend && trend && (
        <span
          className="sparkline-trend"
          style={{
            fontSize: '12px',
            fontWeight: 600,
            color: trend.direction === 'up' ? theme.colors.bullish : theme.colors.bearish,
            whiteSpace: 'nowrap',
          }}
          aria-label={`Trend: ${trend.direction} ${Math.abs(trend.percentChange).toFixed(2)}%`}
        >
          {trend.direction === 'up' ? '↑' : '↓'} {Math.abs(trend.percentChange).toFixed(2)}%
        </span>
      )}
    </div>
  );
};

export default Sparkline;
