/**
 * HeatmapChart component - Heatmap visualization with color intensity mapping
 */

import React, { useState } from 'react';
import { useChartTheme } from './hooks/useChartTheme';
import { interpolateColor, formatNumber } from './utils/chartUtils';

export interface HeatmapDataPoint {
  x: number | string;
  y: number | string;
  value: number;
}

export interface ColorScale {
  min: string;
  mid?: string;
  max: string;
}

export interface HeatmapChartProps {
  data: HeatmapDataPoint[];
  xLabels: Array<string | number>;
  yLabels: Array<string | number>;
  colorScale?: ColorScale;
  width?: number | string;
  height?: number;
  cellSize?: number;
  showValues?: boolean;
  valueFormatter?: (value: number) => string;
  className?: string;
  ariaLabel?: string;
  onCellClick?: (data: HeatmapDataPoint) => void;
}

interface TooltipState {
  visible: boolean;
  x: number;
  y: number;
  data: HeatmapDataPoint | null;
}

export const HeatmapChart: React.FC<HeatmapChartProps> = ({
  data,
  xLabels,
  yLabels,
  colorScale,
  width = '100%',
  height = 400,
  cellSize = 40,
  showValues = false,
  valueFormatter = formatNumber,
  className = '',
  ariaLabel = 'Heatmap chart',
  onCellClick,
}) => {
  const theme = useChartTheme();
  const [tooltip, setTooltip] = useState<TooltipState>({
    visible: false,
    x: 0,
    y: 0,
    data: null,
  });

  const defaultColorScale: ColorScale = {
    min: theme.colors.info,
    mid: theme.colors.warning,
    max: theme.colors.danger,
  };

  const scale = colorScale || defaultColorScale;

  const values = data.map(d => d.value);
  const minValue = Math.min(...values);
  const maxValue = Math.max(...values);
  const range = maxValue - minValue;

  const getCellColor = (value: number): string => {
    if (range === 0) {
      return scale.mid || scale.min;
    }

    const normalized = (value - minValue) / range;

    if (scale.mid) {
      if (normalized < 0.5) {
        return interpolateColor(scale.min, scale.mid, normalized * 2);
      } else {
        return interpolateColor(scale.mid, scale.max, (normalized - 0.5) * 2);
      }
    }

    return interpolateColor(scale.min, scale.max, normalized);
  };

  const getDataPoint = (x: string | number, y: string | number): HeatmapDataPoint | undefined => {
    return data.find(d => d.x === x && d.y === y);
  };

  const handleCellMouseEnter = (
    event: React.MouseEvent<SVGRectElement>,
    dataPoint: HeatmapDataPoint
  ) => {
    const rect = event.currentTarget.getBoundingClientRect();
    setTooltip({
      visible: true,
      x: rect.left + rect.width / 2,
      y: rect.top,
      data: dataPoint,
    });
  };

  const handleCellMouseLeave = () => {
    setTooltip({ visible: false, x: 0, y: 0, data: null });
  };

  const handleCellClick = (dataPoint: HeatmapDataPoint) => {
    if (onCellClick) {
      onCellClick(dataPoint);
    }
  };

  const labelFontSize = 11;
  const marginLeft = 80;
  const marginTop = 60;
  const svgWidth = typeof width === 'number' ? width : xLabels.length * cellSize + marginLeft;
  const svgHeight = yLabels.length * cellSize + marginTop;

  return (
    <div
      className={`heatmap-chart ${className}`}
      role="img"
      aria-label={ariaLabel}
      style={{ width, height, position: 'relative', overflow: 'auto' }}
    >
      <svg
        width={svgWidth}
        height={svgHeight}
        style={{ display: 'block' }}
      >
        <defs>
          <linearGradient id="legend-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor={scale.min} />
            {scale.mid && <stop offset="50%" stopColor={scale.mid} />}
            <stop offset="100%" stopColor={scale.max} />
          </linearGradient>
        </defs>

        {/* Y-axis labels */}
        {yLabels.map((label, index) => (
          <text
            key={`y-label-${index}`}
            x={marginLeft - 10}
            y={marginTop + index * cellSize + cellSize / 2}
            textAnchor="end"
            alignmentBaseline="middle"
            fill={theme.axis.label}
            fontSize={labelFontSize}
          >
            {label}
          </text>
        ))}

        {/* X-axis labels */}
        {xLabels.map((label, index) => (
          <text
            key={`x-label-${index}`}
            x={marginLeft + index * cellSize + cellSize / 2}
            y={marginTop - 10}
            textAnchor="middle"
            alignmentBaseline="baseline"
            fill={theme.axis.label}
            fontSize={labelFontSize}
            transform={`rotate(-45, ${marginLeft + index * cellSize + cellSize / 2}, ${marginTop - 10})`}
          >
            {label}
          </text>
        ))}

        {/* Heatmap cells */}
        {yLabels.map((yLabel, yIndex) =>
          xLabels.map((xLabel, xIndex) => {
            const dataPoint = getDataPoint(xLabel, yLabel);
            if (!dataPoint) return null;

            const cellColor = getCellColor(dataPoint.value);
            const textColor = theme.text.primary;

            return (
              <g key={`cell-${xIndex}-${yIndex}`}>
                <rect
                  x={marginLeft + xIndex * cellSize}
                  y={marginTop + yIndex * cellSize}
                  width={cellSize}
                  height={cellSize}
                  fill={cellColor}
                  stroke={theme.grid.line}
                  strokeWidth={1}
                  style={{ cursor: onCellClick ? 'pointer' : 'default' }}
                  onMouseEnter={(e) => handleCellMouseEnter(e, dataPoint)}
                  onMouseLeave={handleCellMouseLeave}
                  onClick={() => handleCellClick(dataPoint)}
                />
                {showValues && (
                  <text
                    x={marginLeft + xIndex * cellSize + cellSize / 2}
                    y={marginTop + yIndex * cellSize + cellSize / 2}
                    textAnchor="middle"
                    alignmentBaseline="middle"
                    fill={textColor}
                    fontSize={10}
                    fontWeight={600}
                    pointerEvents="none"
                  >
                    {valueFormatter(dataPoint.value)}
                  </text>
                )}
              </g>
            );
          })
        )}

        {/* Color legend */}
        <rect
          x={marginLeft}
          y={10}
          width={200}
          height={20}
          fill="url(#legend-gradient)"
          stroke={theme.grid.line}
          strokeWidth={1}
        />
        <text
          x={marginLeft - 5}
          y={20}
          textAnchor="end"
          alignmentBaseline="middle"
          fill={theme.text.secondary}
          fontSize={10}
        >
          {formatNumber(minValue)}
        </text>
        <text
          x={marginLeft + 205}
          y={20}
          textAnchor="start"
          alignmentBaseline="middle"
          fill={theme.text.secondary}
          fontSize={10}
        >
          {formatNumber(maxValue)}
        </text>
      </svg>

      {/* Tooltip */}
      {tooltip.visible && tooltip.data && (
        <div
          style={{
            position: 'fixed',
            left: `${tooltip.x}px`,
            top: `${tooltip.y - 60}px`,
            transform: 'translateX(-50%)',
            backgroundColor: theme.tooltip.background,
            border: `1px solid ${theme.tooltip.border}`,
            borderRadius: '4px',
            padding: '8px 12px',
            boxShadow: `0 2px 8px ${theme.tooltip.shadow}`,
            pointerEvents: 'none',
            zIndex: 1000,
          }}
        >
          <div style={{ fontSize: '11px', color: theme.text.secondary, marginBottom: '4px' }}>
            X: {tooltip.data.x}, Y: {tooltip.data.y}
          </div>
          <div style={{ fontSize: '12px', fontWeight: 600, color: theme.tooltip.text }}>
            Value: {valueFormatter(tooltip.data.value)}
          </div>
        </div>
      )}
    </div>
  );
};

export default HeatmapChart;
