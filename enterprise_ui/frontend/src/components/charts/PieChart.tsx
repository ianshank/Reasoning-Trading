/**
 * PieChart component - Reusable pie and donut chart
 */

import React, { useState } from 'react';
import {
  PieChart as RechartsPieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Legend,
  Tooltip,
  TooltipProps,
  Sector,
} from 'recharts';
import { useChartTheme, getSeriesColor } from './hooks/useChartTheme';
import { formatNumber, formatPercentage } from './utils/chartUtils';

export interface PieDataItem {
  name: string;
  value: number;
  color?: string;
}

export interface PieChartProps {
  data: PieDataItem[];
  innerRadius?: number;
  outerRadius?: number;
  showLabels?: boolean;
  showLegend?: boolean;
  showPercentage?: boolean;
  height?: number;
  labelKey?: string;
  valueKey?: string;
  className?: string;
  ariaLabel?: string;
  onSegmentClick?: (data: PieDataItem, index: number) => void;
}

interface ActiveShapeProps {
  cx: number;
  cy: number;
  midAngle: number;
  innerRadius: number;
  outerRadius: number;
  startAngle: number;
  endAngle: number;
  fill: string;
  payload: any;
  percent: number;
  value: number;
}

const renderActiveShape = (props: ActiveShapeProps, theme: any) => {
  const RADIAN = Math.PI / 180;
  const {
    cx,
    cy,
    midAngle,
    innerRadius,
    outerRadius,
    startAngle,
    endAngle,
    fill,
    payload,
    percent,
    value,
  } = props;

  const sin = Math.sin(-RADIAN * midAngle);
  const cos = Math.cos(-RADIAN * midAngle);
  const sx = cx + (outerRadius + 10) * cos;
  const sy = cy + (outerRadius + 10) * sin;
  const mx = cx + (outerRadius + 20) * cos;
  const my = cy + (outerRadius + 20) * sin;
  const ex = mx + (cos >= 0 ? 1 : -1) * 22;
  const ey = my;
  const textAnchor = cos >= 0 ? 'start' : 'end';

  return (
    <g>
      <text
        x={cx}
        y={cy}
        dy={8}
        textAnchor="middle"
        fill={theme.text.primary}
        style={{ fontSize: '14px', fontWeight: 600 }}
      >
        {payload.name}
      </text>
      <Sector
        cx={cx}
        cy={cy}
        innerRadius={innerRadius}
        outerRadius={outerRadius}
        startAngle={startAngle}
        endAngle={endAngle}
        fill={fill}
      />
      <Sector
        cx={cx}
        cy={cy}
        startAngle={startAngle}
        endAngle={endAngle}
        innerRadius={outerRadius + 6}
        outerRadius={outerRadius + 10}
        fill={fill}
      />
      <path d={`M${sx},${sy}L${mx},${my}L${ex},${ey}`} stroke={fill} fill="none" />
      <circle cx={ex} cy={ey} r={2} fill={fill} stroke="none" />
      <text
        x={ex + (cos >= 0 ? 1 : -1) * 12}
        y={ey}
        textAnchor={textAnchor}
        fill={theme.text.primary}
        style={{ fontSize: '12px', fontWeight: 600 }}
      >
        {formatNumber(value)}
      </text>
      <text
        x={ex + (cos >= 0 ? 1 : -1) * 12}
        y={ey}
        dy={16}
        textAnchor={textAnchor}
        fill={theme.text.secondary}
        style={{ fontSize: '11px' }}
      >
        {formatPercentage(percent)}
      </text>
    </g>
  );
};

const CustomTooltip: React.FC<TooltipProps<any, any> & { theme: any; showPercentage: boolean }> = ({
  active,
  payload,
  theme,
  showPercentage,
}) => {
  if (!active || !payload || payload.length === 0) {
    return null;
  }

  const data = payload[0];

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
        {data.name}
      </p>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <div
          style={{
            width: '12px',
            height: '12px',
            backgroundColor: data.payload.fill,
            borderRadius: '2px',
          }}
        />
        <span style={{ fontSize: '11px', color: theme.text.secondary }}>Value:</span>
        <span
          style={{
            fontSize: '11px',
            fontWeight: 600,
            color: theme.tooltip.text,
            marginLeft: 'auto',
          }}
        >
          {formatNumber(data.value)}
        </span>
      </div>
      {showPercentage && data.percent !== undefined && (
        <div style={{ marginTop: '4px', fontSize: '11px', color: theme.text.secondary }}>
          {formatPercentage(data.percent)}
        </div>
      )}
    </div>
  );
};

const renderLabel = (entry: any, showPercentage: boolean) => {
  if (showPercentage && entry.percent !== undefined) {
    return `${entry.name} (${formatPercentage(entry.percent)})`;
  }
  return `${entry.name}: ${formatNumber(entry.value)}`;
};

export const PieChart: React.FC<PieChartProps> = ({
  data,
  innerRadius = 0,
  outerRadius = 80,
  showLabels = true,
  showLegend = true,
  showPercentage = true,
  height = 400,
  labelKey = 'name',
  valueKey = 'value',
  className = '',
  ariaLabel = 'Pie chart',
  onSegmentClick,
}) => {
  const theme = useChartTheme();
  const [activeIndex, setActiveIndex] = useState<number | undefined>(undefined);

  const chartData = data.map((item) => ({
    name: item.name,
    value: item.value,
    color: item.color,
  }));

  const total = chartData.reduce((sum, item) => sum + item.value, 0);

  const onPieEnter = (_: any, index: number) => {
    setActiveIndex(index);
  };

  const onPieLeave = () => {
    setActiveIndex(undefined);
  };

  const handleClick = (data: any, index: number) => {
    if (onSegmentClick) {
      onSegmentClick(data, index);
    }
  };

  return (
    <div
      className={`pie-chart ${className}`}
      role="img"
      aria-label={ariaLabel}
      style={{ width: '100%', height }}
    >
      <ResponsiveContainer width="100%" height="100%">
        <RechartsPieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            labelLine={showLabels}
            label={showLabels ? (entry) => renderLabel(entry, showPercentage) : false}
            innerRadius={innerRadius}
            outerRadius={outerRadius}
            fill="#8884d8"
            dataKey={valueKey}
            nameKey={labelKey}
            activeIndex={activeIndex}
            activeShape={(props: any) => renderActiveShape(props, theme)}
            onMouseEnter={onPieEnter}
            onMouseLeave={onPieLeave}
            onClick={handleClick}
            style={{ cursor: onSegmentClick ? 'pointer' : 'default' }}
            animationDuration={500}
          >
            {chartData.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={entry.color || getSeriesColor(theme, index)}
              />
            ))}
          </Pie>

          <Tooltip content={<CustomTooltip theme={theme} showPercentage={showPercentage} />} />

          {showLegend && (
            <Legend
              wrapperStyle={{
                fontSize: '12px',
                color: theme.text.secondary,
              }}
              formatter={(value, entry: any) => {
                const percentage = (entry.payload.value / total) * 100;
                return `${value} (${formatPercentage(percentage / 100)})`;
              }}
            />
          )}
        </RechartsPieChart>
      </ResponsiveContainer>
    </div>
  );
};

export default PieChart;
