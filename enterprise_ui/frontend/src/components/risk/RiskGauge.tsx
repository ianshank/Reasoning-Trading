/**
 * Risk Gauge Component
 *
 * Visual gauge/meter showing current risk level
 */

import React from 'react';
import { Card } from '../ui/Card';

interface RiskGaugeProps {
  riskLevel: number;
  maxRisk: number;
  label?: string;
}

export const RiskGauge: React.FC<RiskGaugeProps> = ({
  riskLevel,
  maxRisk,
  label = 'Portfolio Risk',
}) => {
  const normalizedRisk = maxRisk > 0 ? (riskLevel / maxRisk) * 100 : 0;
  const clampedRisk = Math.min(Math.max(normalizedRisk, 0), 100);

  const getRiskZone = (
    value: number
  ): { label: string; color: string; bgColor: string } => {
    if (value >= 80) {
      return {
        label: 'Critical',
        color: 'text-red-600 dark:text-red-400',
        bgColor: 'bg-red-500',
      };
    }
    if (value >= 60) {
      return {
        label: 'High',
        color: 'text-orange-600 dark:text-orange-400',
        bgColor: 'bg-orange-500',
      };
    }
    if (value >= 40) {
      return {
        label: 'Medium',
        color: 'text-yellow-600 dark:text-yellow-400',
        bgColor: 'bg-yellow-500',
      };
    }
    return {
      label: 'Low',
      color: 'text-green-600 dark:text-green-400',
      bgColor: 'bg-green-500',
    };
  };

  const zone = getRiskZone(clampedRisk);

  // Calculate SVG arc path for semi-circle gauge
  const radius = 90;
  const strokeWidth = 20;
  const centerX = 120;
  const centerY = 120;

  const getArcPath = (percentage: number): string => {
    const angle = (percentage / 100) * 180 - 180;
    const radians = (angle * Math.PI) / 180;
    const x = centerX + radius * Math.cos(radians);
    const y = centerY + radius * Math.sin(radians);
    const largeArc = percentage > 50 ? 1 : 0;

    return `M ${centerX - radius} ${centerY} A ${radius} ${radius} 0 ${largeArc} 1 ${x} ${y}`;
  };

  return (
    <Card className="bg-white dark:bg-gray-800">
      <div className="p-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-6 text-center">
          {label}
        </h3>

        <div className="flex flex-col items-center">
          {/* SVG Gauge */}
          <svg
            width="240"
            height="160"
            viewBox="0 0 240 160"
            className="overflow-visible"
            role="img"
            aria-label={`Risk gauge showing ${clampedRisk.toFixed(0)}% of maximum risk`}
          >
            {/* Background arc */}
            <path
              d={getArcPath(100)}
              fill="none"
              stroke="currentColor"
              strokeWidth={strokeWidth}
              strokeLinecap="round"
              className="stroke-gray-200 dark:stroke-gray-700"
            />

            {/* Color zones */}
            <defs>
              <linearGradient id="riskGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="#10b981" />
                <stop offset="33%" stopColor="#f59e0b" />
                <stop offset="66%" stopColor="#f97316" />
                <stop offset="100%" stopColor="#ef4444" />
              </linearGradient>
            </defs>

            {/* Active arc with gradient */}
            <path
              d={getArcPath(clampedRisk)}
              fill="none"
              stroke="url(#riskGradient)"
              strokeWidth={strokeWidth}
              strokeLinecap="round"
              className="transition-all duration-500"
            />

            {/* Pointer */}
            <g
              className="transition-all duration-500"
              style={{
                transformOrigin: `${centerX}px ${centerY}px`,
                transform: `rotate(${(clampedRisk / 100) * 180 - 180}deg)`,
              }}
            >
              <circle
                cx={centerX}
                cy={centerY}
                r="8"
                className="fill-gray-800 dark:fill-white"
              />
              <path
                d={`M ${centerX} ${centerY} L ${centerX} ${centerY - radius - 10}`}
                stroke="currentColor"
                strokeWidth="3"
                strokeLinecap="round"
                className="stroke-gray-800 dark:stroke-white"
              />
            </g>

            {/* Zone markers */}
            <text
              x={centerX - radius - 10}
              y={centerY + 20}
              className="fill-green-600 dark:fill-green-400 text-xs font-medium"
              textAnchor="end"
            >
              Low
            </text>
            <text
              x={centerX}
              y={centerY - radius - 25}
              className="fill-yellow-600 dark:fill-yellow-400 text-xs font-medium"
              textAnchor="middle"
            >
              Med
            </text>
            <text
              x={centerX + radius + 10}
              y={centerY + 20}
              className="fill-red-600 dark:fill-red-400 text-xs font-medium"
              textAnchor="start"
            >
              High
            </text>

            {/* Current value display */}
            <text
              x={centerX}
              y={centerY + 40}
              className="fill-gray-900 dark:fill-white text-3xl font-bold"
              textAnchor="middle"
            >
              {clampedRisk.toFixed(0)}%
            </text>
          </svg>

          {/* Risk zone label */}
          <div className="mt-6 text-center">
            <div
              className={`inline-flex items-center px-4 py-2 rounded-full ${zone.color} bg-opacity-10`}
            >
              <div className={`w-3 h-3 rounded-full ${zone.bgColor} mr-2`} />
              <span className={`text-lg font-semibold ${zone.color}`}>
                {zone.label} Risk
              </span>
            </div>
          </div>

          {/* Risk metrics */}
          <div className="mt-6 w-full grid grid-cols-2 gap-4">
            <div className="text-center p-3 bg-gray-50 dark:bg-gray-900/50 rounded-lg">
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Current Risk
              </p>
              <p className="mt-1 text-xl font-bold text-gray-900 dark:text-white">
                {riskLevel.toFixed(2)}
              </p>
            </div>
            <div className="text-center p-3 bg-gray-50 dark:bg-gray-900/50 rounded-lg">
              <p className="text-sm text-gray-500 dark:text-gray-400">Max Risk</p>
              <p className="mt-1 text-xl font-bold text-gray-900 dark:text-white">
                {maxRisk.toFixed(2)}
              </p>
            </div>
          </div>

          {/* Risk level descriptions */}
          <div className="mt-6 w-full space-y-2 text-xs">
            <div className="flex items-center justify-between p-2 rounded bg-gray-50 dark:bg-gray-900/50">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-green-500" />
                <span className="text-gray-700 dark:text-gray-300">
                  Low (0-40%)
                </span>
              </div>
              <span className="text-gray-500 dark:text-gray-400">Safe zone</span>
            </div>
            <div className="flex items-center justify-between p-2 rounded bg-gray-50 dark:bg-gray-900/50">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-yellow-500" />
                <span className="text-gray-700 dark:text-gray-300">
                  Medium (40-60%)
                </span>
              </div>
              <span className="text-gray-500 dark:text-gray-400">
                Monitor closely
              </span>
            </div>
            <div className="flex items-center justify-between p-2 rounded bg-gray-50 dark:bg-gray-900/50">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-orange-500" />
                <span className="text-gray-700 dark:text-gray-300">
                  High (60-80%)
                </span>
              </div>
              <span className="text-gray-500 dark:text-gray-400">
                Reduce exposure
              </span>
            </div>
            <div className="flex items-center justify-between p-2 rounded bg-gray-50 dark:bg-gray-900/50">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-red-500" />
                <span className="text-gray-700 dark:text-gray-300">
                  Critical (80-100%)
                </span>
              </div>
              <span className="text-gray-500 dark:text-gray-400">
                Immediate action
              </span>
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
};
