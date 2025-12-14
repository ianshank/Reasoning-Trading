/**
 * GaugeChart component - Gauge/meter visualization with zones and needle
 */

import React, { useMemo } from 'react';
import { useChartTheme } from './hooks/useChartTheme';
import { formatNumber } from './utils/chartUtils';

export interface GaugeZone {
  min: number;
  max: number;
  color: string;
  label?: string;
}

export interface GaugeChartProps {
  value: number;
  min?: number;
  max?: number;
  zones?: GaugeZone[];
  label?: string;
  unit?: string;
  size?: number;
  showValue?: boolean;
  valueFormatter?: (value: number) => string;
  className?: string;
  ariaLabel?: string;
}

export const GaugeChart: React.FC<GaugeChartProps> = ({
  value,
  min = 0,
  max = 100,
  zones,
  label,
  unit = '',
  size = 200,
  showValue = true,
  valueFormatter = formatNumber,
  className = '',
  ariaLabel = 'Gauge chart',
}) => {
  const theme = useChartTheme();

  const defaultZones: GaugeZone[] = useMemo(
    () => [
      { min: 0, max: 33, color: theme.colors.danger, label: 'Low' },
      { min: 33, max: 66, color: theme.colors.warning, label: 'Medium' },
      { min: 66, max: 100, color: theme.colors.success, label: 'High' },
    ],
    [theme]
  );

  const gaugeZones = zones || defaultZones;

  const normalizedValue = Math.max(min, Math.min(max, value));
  const percentage = ((normalizedValue - min) / (max - min)) * 100;

  const centerX = size / 2;
  const centerY = size / 2;
  const radius = (size / 2) * 0.7;
  const startAngle = -135;
  const endAngle = 135;
  const angleRange = endAngle - startAngle;

  const polarToCartesian = (angle: number, r: number) => {
    const angleInRadians = ((angle - 90) * Math.PI) / 180;
    return {
      x: centerX + r * Math.cos(angleInRadians),
      y: centerY + r * Math.sin(angleInRadians),
    };
  };

  const createArc = (
    startAngle: number,
    endAngle: number,
    innerRadius: number,
    outerRadius: number
  ): string => {
    const start1 = polarToCartesian(startAngle, outerRadius);
    const end1 = polarToCartesian(endAngle, outerRadius);
    const start2 = polarToCartesian(endAngle, innerRadius);
    const end2 = polarToCartesian(startAngle, innerRadius);

    const largeArcFlag = endAngle - startAngle <= 180 ? '0' : '1';

    return [
      `M ${start1.x} ${start1.y}`,
      `A ${outerRadius} ${outerRadius} 0 ${largeArcFlag} 1 ${end1.x} ${end1.y}`,
      `L ${start2.x} ${start2.y}`,
      `A ${innerRadius} ${innerRadius} 0 ${largeArcFlag} 0 ${end2.x} ${end2.y}`,
      'Z',
    ].join(' ');
  };

  const renderZones = () => {
    const innerRadius = radius * 0.75;
    const outerRadius = radius;

    return gaugeZones.map((zone, index) => {
      const zoneMin = Math.max(zone.min, min);
      const zoneMax = Math.min(zone.max, max);
      const zoneRange = max - min;

      const zoneStartAngle = startAngle + ((zoneMin - min) / zoneRange) * angleRange;
      const zoneEndAngle = startAngle + ((zoneMax - min) / zoneRange) * angleRange;

      const arc = createArc(zoneStartAngle, zoneEndAngle, innerRadius, outerRadius);

      return (
        <path
          key={`zone-${index}`}
          d={arc}
          fill={zone.color}
          stroke={theme.background}
          strokeWidth={2}
        />
      );
    });
  };

  const renderNeedle = () => {
    const needleAngle = startAngle + (percentage / 100) * angleRange;
    const needleLength = radius * 0.7;
    const needleBase = 8;

    const tip = polarToCartesian(needleAngle, needleLength);
    const base1 = polarToCartesian(needleAngle - 90, needleBase / 2);
    const base2 = polarToCartesian(needleAngle + 90, needleBase / 2);

    return (
      <g>
        <polygon
          points={`${tip.x},${tip.y} ${base1.x},${base1.y} ${base2.x},${base2.y}`}
          fill={theme.colors.primary}
          style={{
            transition: 'all 0.5s ease-out',
          }}
        />
        <circle
          cx={centerX}
          cy={centerY}
          r={12}
          fill={theme.colors.primary}
          stroke={theme.background}
          strokeWidth={2}
        />
      </g>
    );
  };

  const renderTicks = () => {
    const tickCount = 11;
    const ticks = [];
    const tickInnerRadius = radius * 0.65;
    const tickOuterRadius = radius * 0.7;

    for (let i = 0; i < tickCount; i++) {
      const tickValue = min + (i / (tickCount - 1)) * (max - min);
      const tickAngle = startAngle + (i / (tickCount - 1)) * angleRange;

      const innerPoint = polarToCartesian(tickAngle, tickInnerRadius);
      const outerPoint = polarToCartesian(tickAngle, tickOuterRadius);

      ticks.push(
        <line
          key={`tick-${i}`}
          x1={innerPoint.x}
          y1={innerPoint.y}
          x2={outerPoint.x}
          y2={outerPoint.y}
          stroke={theme.axis.tick}
          strokeWidth={2}
        />
      );

      if (i % 2 === 0) {
        const labelRadius = radius * 0.55;
        const labelPoint = polarToCartesian(tickAngle, labelRadius);

        ticks.push(
          <text
            key={`tick-label-${i}`}
            x={labelPoint.x}
            y={labelPoint.y}
            textAnchor="middle"
            alignmentBaseline="middle"
            fill={theme.text.secondary}
            fontSize={10}
          >
            {Math.round(tickValue)}
          </text>
        );
      }
    }

    return ticks;
  };

  return (
    <div
      className={`gauge-chart ${className}`}
      role="img"
      aria-label={ariaLabel}
      aria-valuenow={value}
      aria-valuemin={min}
      aria-valuemax={max}
      style={{ width: size, height: size, display: 'inline-block' }}
    >
      <svg width={size} height={size}>
        {/* Background circle */}
        <circle
          cx={centerX}
          cy={centerY}
          r={radius}
          fill={theme.background}
          stroke={theme.grid.line}
          strokeWidth={1}
        />

        {/* Zones */}
        {renderZones()}

        {/* Ticks */}
        {renderTicks()}

        {/* Needle */}
        {renderNeedle()}
      </svg>

      {/* Value display */}
      {showValue && (
        <div
          style={{
            position: 'absolute',
            top: '65%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            textAlign: 'center',
          }}
        >
          <div
            style={{
              fontSize: size * 0.12,
              fontWeight: 700,
              color: theme.text.primary,
              lineHeight: 1,
            }}
          >
            {valueFormatter(value)}
            {unit && (
              <span
                style={{
                  fontSize: size * 0.08,
                  fontWeight: 400,
                  color: theme.text.secondary,
                  marginLeft: '4px',
                }}
              >
                {unit}
              </span>
            )}
          </div>
          {label && (
            <div
              style={{
                fontSize: size * 0.08,
                color: theme.text.secondary,
                marginTop: '4px',
              }}
            >
              {label}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default GaugeChart;
