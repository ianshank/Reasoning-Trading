/**
 * BarChart component - Reusable bar chart with horizontal and vertical layouts
 */

import React from 'react';
import {
  BarChart as RechartsBarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
  TooltipProps,
} from 'recharts';
import { useChartTheme, getSeriesColor } from './hooks/useChartTheme';
import { formatNumber } from './utils/chartUtils';

export interface BarConfig {
  dataKey: string;
  name: string;
  color?: string;
  stackId?: string;
  radius?: [number, number, number, number];
}

export interface BarChartProps {
  data: Array<Record<string, any>>;
  bars: BarConfig[];
  layout?: 'vertical' | 'horizontal';
  stacked?: boolean;
  xAxisKey?: string;
  xAxisLabel?: string;
  yAxisLabel?: string;
  height?: number;
  showGrid?: boolean;
  showLegend?: boolean;
  colorByValue?: boolean;
  getBarColor?: (value: number, index: number) => string;
  margin?: { top?: number; right?: number; bottom?: number; left?: number };
  className?: string;
  ariaLabel?: string;
  onBarClick?: (data: any, index: number) => void;
}

const CustomTooltip: React.FC<TooltipProps<any, any> & { theme: any }> = ({
  active,
  payload,
  label,
  theme,
}) => {
  if (!active || !payload || payload.length === 0) {
    return null;
  }

  return (
    <div
      style={{
        backgroundColor: theme.tooltip.background,
        border: `1px solid ${theme.tooltip.border}`,
        borderRadius: '4px',
        padding: '12px',
        boxShadow: `0 2px 8px ${theme.tooltip.shadow}`,
      }}
    >
      <p
        style={{
          margin: '0 0 8px 0',
          fontWeight: 600,
          color: theme.tooltip.text,
          fontSize: '12px',
        }}
      >
        {label}
      </p>
      {payload.map((entry, index) => (
        <div
          key={`tooltip-${index}`}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            marginBottom: index < payload.length - 1 ? '4px' : '0',
          }}
        >
          <div
            style={{
              width: '12px',
              height: '12px',
              backgroundColor: entry.color,
              borderRadius: '2px',
            }}
          />
          <span style={{ fontSize: '11px', color: theme.text.secondary }}>
            {entry.name}:
          </span>
          <span
            style={{
              fontSize: '11px',
              fontWeight: 600,
              color: theme.tooltip.text,
              marginLeft: 'auto',
            }}
          >
            {formatNumber(entry.value)}
          </span>
        </div>
      ))}
    </div>
  );
};

export const BarChart: React.FC<BarChartProps> = ({
  data,
  bars,
  layout = 'horizontal',
  stacked = false,
  xAxisKey = 'name',
  xAxisLabel,
  yAxisLabel,
  height = 400,
  showGrid = true,
  showLegend = true,
  colorByValue = false,
  getBarColor,
  margin = { top: 20, right: 30, bottom: 50, left: 60 },
  className = '',
  ariaLabel = 'Bar chart',
  onBarClick,
}) => {
  const theme = useChartTheme();

  const renderBar = (barConfig: BarConfig, index: number) => {
    const barColor = barConfig.color || getSeriesColor(theme, index);
    const stackId = stacked ? (barConfig.stackId || 'stack') : undefined;
    const radius = barConfig.radius || (layout === 'horizontal' ? [0, 4, 4, 0] : [4, 4, 0, 0]);

    return (
      <Bar
        key={`bar-${barConfig.dataKey}`}
        dataKey={barConfig.dataKey}
        name={barConfig.name}
        fill={barColor}
        stackId={stackId}
        radius={radius}
        onClick={onBarClick}
        cursor={onBarClick ? 'pointer' : 'default'}
        animationDuration={500}
      >
        {colorByValue &&
          data.map((entry, cellIndex) => {
            const value = entry[barConfig.dataKey] as number;
            const color = getBarColor
              ? getBarColor(value, cellIndex)
              : value >= 0
              ? theme.colors.bullish
              : theme.colors.bearish;

            return <Cell key={`cell-${cellIndex}`} fill={color} />;
          })}
      </Bar>
    );
  };

  return (
    <div
      className={`bar-chart ${className}`}
      role="img"
      aria-label={ariaLabel}
      style={{ width: '100%', height }}
    >
      <ResponsiveContainer width="100%" height="100%">
        <RechartsBarChart
          data={data}
          layout={layout}
          margin={margin}
        >
          {showGrid && (
            <CartesianGrid
              strokeDasharray="3 3"
              stroke={theme.grid.line}
              vertical={layout === 'vertical'}
              horizontal={layout === 'horizontal'}
            />
          )}

          {layout === 'horizontal' ? (
            <>
              <XAxis
                dataKey={xAxisKey}
                stroke={theme.axis.line}
                tick={{ fill: theme.axis.label, fontSize: 11 }}
                label={
                  xAxisLabel
                    ? {
                        value: xAxisLabel,
                        position: 'insideBottom',
                        offset: -10,
                        style: { fill: theme.text.secondary, fontSize: 12 },
                      }
                    : undefined
                }
              />
              <YAxis
                stroke={theme.axis.line}
                tick={{ fill: theme.axis.label, fontSize: 11 }}
                tickFormatter={formatNumber}
                label={
                  yAxisLabel
                    ? {
                        value: yAxisLabel,
                        angle: -90,
                        position: 'insideLeft',
                        style: { fill: theme.text.secondary, fontSize: 12 },
                      }
                    : undefined
                }
              />
            </>
          ) : (
            <>
              <XAxis
                type="number"
                stroke={theme.axis.line}
                tick={{ fill: theme.axis.label, fontSize: 11 }}
                tickFormatter={formatNumber}
                label={
                  xAxisLabel
                    ? {
                        value: xAxisLabel,
                        position: 'insideBottom',
                        offset: -10,
                        style: { fill: theme.text.secondary, fontSize: 12 },
                      }
                    : undefined
                }
              />
              <YAxis
                dataKey={xAxisKey}
                type="category"
                stroke={theme.axis.line}
                tick={{ fill: theme.axis.label, fontSize: 11 }}
                width={100}
                label={
                  yAxisLabel
                    ? {
                        value: yAxisLabel,
                        angle: -90,
                        position: 'insideLeft',
                        style: { fill: theme.text.secondary, fontSize: 12 },
                      }
                    : undefined
                }
              />
            </>
          )}

          <Tooltip content={<CustomTooltip theme={theme} />} cursor={{ fill: theme.grid.line }} />

          {showLegend && (
            <Legend
              wrapperStyle={{
                fontSize: '12px',
                color: theme.text.secondary,
              }}
            />
          )}

          {bars.map((bar, index) => renderBar(bar, index))}
        </RechartsBarChart>
      </ResponsiveContainer>
    </div>
  );
};

export default BarChart;
