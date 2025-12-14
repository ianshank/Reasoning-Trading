/**
 * LineChart component - Reusable line chart with multi-line support
 */

import React from 'react';
import {
  LineChart as RechartsLineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
  TooltipProps,
} from 'recharts';
import { useChartTheme, getSeriesColor } from './hooks/useChartTheme';
import { formatNumber, formatTimestamp } from './utils/chartUtils';

export interface LineConfig {
  dataKey: string;
  name: string;
  color?: string;
  strokeWidth?: number;
  strokeDasharray?: string;
  dot?: boolean;
}

export interface AxisConfig {
  dataKey?: string;
  label?: string;
  tickFormatter?: (value: any) => string;
  domain?: [number | string, number | string];
  hide?: boolean;
}

export interface TooltipConfig {
  formatter?: (value: any, name: string) => [string, string];
  labelFormatter?: (label: any) => string;
  enabled?: boolean;
}

export interface ReferenceLineConfig {
  y?: number;
  x?: number | string;
  label?: string;
  stroke?: string;
  strokeDasharray?: string;
}

export interface LineChartProps {
  data: Array<Record<string, any>>;
  lines: LineConfig[];
  xAxis?: AxisConfig;
  yAxis?: AxisConfig;
  tooltip?: TooltipConfig;
  referenceLines?: ReferenceLineConfig[];
  height?: number;
  showGrid?: boolean;
  showLegend?: boolean;
  margin?: { top?: number; right?: number; bottom?: number; left?: number };
  className?: string;
  ariaLabel?: string;
  onLineClick?: (data: any, index: number) => void;
}

const CustomTooltip: React.FC<TooltipProps<any, any> & { config?: TooltipConfig; theme: any }> = ({
  active,
  payload,
  label,
  config,
  theme,
}) => {
  if (!active || !payload || payload.length === 0) {
    return null;
  }

  const labelFormatter = config?.labelFormatter || ((val) => String(val));

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
        {labelFormatter(label)}
      </p>
      {payload.map((entry, index) => {
        const formatter = config?.formatter || ((val) => [formatNumber(val), entry.name]);
        const [formattedValue, formattedName] = formatter(entry.value, entry.name);

        return (
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
              {formattedName}:
            </span>
            <span
              style={{
                fontSize: '11px',
                fontWeight: 600,
                color: theme.tooltip.text,
                marginLeft: 'auto',
              }}
            >
              {formattedValue}
            </span>
          </div>
        );
      })}
    </div>
  );
};

export const LineChart: React.FC<LineChartProps> = ({
  data,
  lines,
  xAxis = {},
  yAxis = {},
  tooltip = { enabled: true },
  referenceLines = [],
  height = 400,
  showGrid = true,
  showLegend = true,
  margin = { top: 20, right: 30, bottom: 50, left: 60 },
  className = '',
  ariaLabel = 'Line chart',
  onLineClick,
}) => {
  const theme = useChartTheme();

  const defaultXAxisFormatter = (value: any) => {
    if (typeof value === 'number' && value > 1000000000) {
      return formatTimestamp(value, 'time');
    }
    return String(value);
  };

  const defaultYAxisFormatter = (value: any) => {
    return formatNumber(value);
  };

  return (
    <div
      className={`line-chart ${className}`}
      role="img"
      aria-label={ariaLabel}
      style={{ width: '100%', height }}
    >
      <ResponsiveContainer width="100%" height="100%">
        <RechartsLineChart data={data} margin={margin}>
          {showGrid && (
            <CartesianGrid
              strokeDasharray="3 3"
              stroke={theme.grid.line}
              vertical={false}
            />
          )}

          <XAxis
            dataKey={xAxis.dataKey || 'x'}
            stroke={theme.axis.line}
            tick={{ fill: theme.axis.label, fontSize: 11 }}
            label={
              xAxis.label
                ? {
                    value: xAxis.label,
                    position: 'insideBottom',
                    offset: -10,
                    style: { fill: theme.text.secondary, fontSize: 12 },
                  }
                : undefined
            }
            tickFormatter={xAxis.tickFormatter || defaultXAxisFormatter}
            domain={xAxis.domain}
            hide={xAxis.hide}
          />

          <YAxis
            stroke={theme.axis.line}
            tick={{ fill: theme.axis.label, fontSize: 11 }}
            label={
              yAxis.label
                ? {
                    value: yAxis.label,
                    angle: -90,
                    position: 'insideLeft',
                    style: { fill: theme.text.secondary, fontSize: 12 },
                  }
                : undefined
            }
            tickFormatter={yAxis.tickFormatter || defaultYAxisFormatter}
            domain={yAxis.domain}
            hide={yAxis.hide}
          />

          {tooltip.enabled && (
            <Tooltip
              content={<CustomTooltip config={tooltip} theme={theme} />}
              cursor={{ stroke: theme.grid.stroke, strokeWidth: 1 }}
            />
          )}

          {showLegend && (
            <Legend
              wrapperStyle={{
                fontSize: '12px',
                color: theme.text.secondary,
              }}
              iconType="line"
            />
          )}

          {referenceLines.map((refLine, index) => (
            <ReferenceLine
              key={`ref-line-${index}`}
              y={refLine.y}
              x={refLine.x}
              stroke={refLine.stroke || theme.colors.warning}
              strokeDasharray={refLine.strokeDasharray || '3 3'}
              label={
                refLine.label
                  ? {
                      value: refLine.label,
                      fill: theme.text.secondary,
                      fontSize: 11,
                    }
                  : undefined
              }
            />
          ))}

          {lines.map((line, index) => (
            <Line
              key={`line-${line.dataKey}`}
              type="monotone"
              dataKey={line.dataKey}
              name={line.name}
              stroke={line.color || getSeriesColor(theme, index)}
              strokeWidth={line.strokeWidth || 2}
              strokeDasharray={line.strokeDasharray}
              dot={line.dot !== undefined ? line.dot : false}
              activeDot={
                onLineClick
                  ? {
                      onClick: (data: any, index: number) => onLineClick(data, index),
                      r: 6,
                      style: { cursor: 'pointer' },
                    }
                  : { r: 4 }
              }
              animationDuration={500}
            />
          ))}
        </RechartsLineChart>
      </ResponsiveContainer>
    </div>
  );
};

export default LineChart;
