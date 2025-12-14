/**
 * AreaChart component - Area chart with gradient fills and stacked support
 */

import React from 'react';
import {
  AreaChart as RechartsAreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceArea,
  TooltipProps,
} from 'recharts';
import { useChartTheme, getSeriesColor, getGradient } from './hooks/useChartTheme';
import { formatNumber, formatTimestamp, getGradientId } from './utils/chartUtils';

export interface AreaConfig {
  dataKey: string;
  name: string;
  color?: string;
  fillOpacity?: number;
  strokeWidth?: number;
  stackId?: string;
  gradient?: boolean;
}

export interface ReferenceAreaConfig {
  x1: number | string;
  x2: number | string;
  y1?: number;
  y2?: number;
  label?: string;
  fill?: string;
  fillOpacity?: number;
}

export interface AreaChartProps {
  data: Array<Record<string, any>>;
  areas: AreaConfig[];
  xAxisKey?: string;
  xAxisLabel?: string;
  yAxisLabel?: string;
  xAxisFormatter?: (value: any) => string;
  yAxisFormatter?: (value: any) => string;
  stacked?: boolean;
  gradient?: boolean;
  referenceAreas?: ReferenceAreaConfig[];
  height?: number;
  showGrid?: boolean;
  showLegend?: boolean;
  margin?: { top?: number; right?: number; bottom?: number; left?: number };
  className?: string;
  ariaLabel?: string;
  onAreaClick?: (data: any, index: number) => void;
}

const CustomTooltip: React.FC<TooltipProps<any, any> & { theme: any; xAxisFormatter?: (value: any) => string }> = ({
  active,
  payload,
  label,
  theme,
  xAxisFormatter,
}) => {
  if (!active || !payload || payload.length === 0) {
    return null;
  }

  const labelFormatter = xAxisFormatter || ((val) => String(val));

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

export const AreaChart: React.FC<AreaChartProps> = ({
  data,
  areas,
  xAxisKey = 'x',
  xAxisLabel,
  yAxisLabel,
  xAxisFormatter,
  yAxisFormatter,
  stacked = false,
  gradient = true,
  referenceAreas = [],
  height = 400,
  showGrid = true,
  showLegend = true,
  margin = { top: 20, right: 30, bottom: 50, left: 60 },
  className = '',
  ariaLabel = 'Area chart',
  onAreaClick,
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

  const xFormatter = xAxisFormatter || defaultXAxisFormatter;
  const yFormatter = yAxisFormatter || defaultYAxisFormatter;

  const renderArea = (areaConfig: AreaConfig, index: number) => {
    const areaColor = areaConfig.color || getSeriesColor(theme, index);
    const gradientId = gradient || areaConfig.gradient ? getGradientId(`area-${index}`) : undefined;
    const stackId = stacked ? (areaConfig.stackId || 'stack') : undefined;

    return (
      <React.Fragment key={`area-${areaConfig.dataKey}`}>
        {gradientId && (
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={areaColor} stopOpacity={0.8} />
              <stop offset="95%" stopColor={areaColor} stopOpacity={0.1} />
            </linearGradient>
          </defs>
        )}
        <Area
          type="monotone"
          dataKey={areaConfig.dataKey}
          name={areaConfig.name}
          stroke={areaColor}
          strokeWidth={areaConfig.strokeWidth || 2}
          fill={gradientId ? `url(#${gradientId})` : areaColor}
          fillOpacity={areaConfig.fillOpacity !== undefined ? areaConfig.fillOpacity : 0.6}
          stackId={stackId}
          onClick={onAreaClick}
          style={{ cursor: onAreaClick ? 'pointer' : 'default' }}
          animationDuration={500}
        />
      </React.Fragment>
    );
  };

  return (
    <div
      className={`area-chart ${className}`}
      role="img"
      aria-label={ariaLabel}
      style={{ width: '100%', height }}
    >
      <ResponsiveContainer width="100%" height="100%">
        <RechartsAreaChart data={data} margin={margin}>
          {showGrid && (
            <CartesianGrid
              strokeDasharray="3 3"
              stroke={theme.grid.line}
              vertical={false}
            />
          )}

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
            tickFormatter={xFormatter}
          />

          <YAxis
            stroke={theme.axis.line}
            tick={{ fill: theme.axis.label, fontSize: 11 }}
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
            tickFormatter={yFormatter}
          />

          <Tooltip
            content={<CustomTooltip theme={theme} xAxisFormatter={xFormatter} />}
            cursor={{ stroke: theme.grid.stroke, strokeWidth: 1 }}
          />

          {showLegend && (
            <Legend
              wrapperStyle={{
                fontSize: '12px',
                color: theme.text.secondary,
              }}
            />
          )}

          {referenceAreas.map((refArea, index) => (
            <ReferenceArea
              key={`ref-area-${index}`}
              x1={refArea.x1}
              x2={refArea.x2}
              y1={refArea.y1}
              y2={refArea.y2}
              fill={refArea.fill || theme.colors.warning}
              fillOpacity={refArea.fillOpacity || 0.2}
              label={
                refArea.label
                  ? {
                      value: refArea.label,
                      fill: theme.text.secondary,
                      fontSize: 11,
                    }
                  : undefined
              }
            />
          ))}

          {areas.map((area, index) => renderArea(area, index))}
        </RechartsAreaChart>
      </ResponsiveContainer>
    </div>
  );
};

export default AreaChart;
