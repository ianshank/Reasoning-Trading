/**
 * Analyst Radar Chart Component
 *
 * Displays 5 specialized analysts on a radar chart with signal strength
 * and confidence overlay.
 */

import React, { useMemo } from 'react';
import {
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Tooltip,
  Legend,
} from 'recharts';
import type { AnalystSignals } from '../../types/trading';
import { Card } from '../ui/card';

/**
 * Props for AnalystRadarChart component
 */
export interface AnalystRadarChartProps {
  /**
   * Analyst signals data
   */
  signals: AnalystSignals;

  /**
   * Whether to show confidence overlay
   * @default true
   */
  showConfidence?: boolean;

  /**
   * Highlighted analyst (if any)
   */
  highlightedAnalyst?: string | null;

  /**
   * Custom className for the component
   */
  className?: string;
}

interface RadarDataPoint {
  analyst: string;
  signal: number;
  confidence: number;
  fullName: string;
}

const ANALYST_LABELS: Record<string, string> = {
  Market: 'Market Analyst',
  News: 'News Analyst',
  Social: 'Social Sentiment',
  Fundamental: 'Fundamental Analyst',
  Macro: 'Macro Analyst',
};

/**
 * Radar chart showing 5 specialized analysts with signal strength
 */
export const AnalystRadarChart: React.FC<AnalystRadarChartProps> = ({
  signals,
  showConfidence = true,
  highlightedAnalyst = null,
  className = '',
}) => {
  const radarData = useMemo(() => {
    const data: RadarDataPoint[] = [
      {
        analyst: 'Market',
        fullName: ANALYST_LABELS.Market,
        signal: signals.market_analyst_score,
        confidence: signals.market_analyst_confidence,
      },
      {
        analyst: 'News',
        fullName: ANALYST_LABELS.News,
        signal: signals.news_analyst_score,
        confidence: signals.news_analyst_confidence,
      },
      {
        analyst: 'Social',
        fullName: ANALYST_LABELS.Social,
        signal: signals.social_sentiment_score,
        confidence: signals.social_sentiment_confidence,
      },
      {
        analyst: 'Fundamental',
        fullName: ANALYST_LABELS.Fundamental,
        signal: signals.fundamental_analyst_score,
        confidence: signals.fundamental_analyst_confidence,
      },
      {
        analyst: 'Macro',
        fullName: ANALYST_LABELS.Macro,
        signal: signals.macro_analyst_score,
        confidence: signals.macro_analyst_confidence,
      },
    ];

    return data;
  }, [signals]);

  const getSignalColor = (value: number): string => {
    if (value > 0.3) return '#10b981'; // green
    if (value < -0.3) return '#ef4444'; // red
    return '#6b7280'; // gray
  };

  const formatSignal = (value: number): string => {
    return value.toFixed(2);
  };

  const formatPercentage = (value: number): string => {
    return `${(value * 100).toFixed(0)}%`;
  };

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload as RadarDataPoint;
      return (
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg p-3">
          <p className="text-sm font-semibold text-gray-900 dark:text-white mb-2">
            {data.fullName}
          </p>
          <div className="space-y-1">
            <div className="flex justify-between gap-4">
              <span className="text-sm text-gray-600 dark:text-gray-400">Signal:</span>
              <span
                className="text-sm font-medium"
                style={{ color: getSignalColor(data.signal) }}
              >
                {formatSignal(data.signal)}
              </span>
            </div>
            <div className="flex justify-between gap-4">
              <span className="text-sm text-gray-600 dark:text-gray-400">Confidence:</span>
              <span className="text-sm font-medium text-blue-600 dark:text-blue-400">
                {formatPercentage(data.confidence)}
              </span>
            </div>
          </div>
        </div>
      );
    }
    return null;
  };

  const isHighlighted = (analyst: string): boolean => {
    return highlightedAnalyst === analyst;
  };

  return (
    <Card className={`bg-white dark:bg-gray-800 ${className}`}>
      <div className="p-6">
        <div className="flex justify-between items-center mb-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            Analyst Signals
          </h3>
          {showConfidence && (
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-500 dark:text-gray-400">
                Confidence overlay enabled
              </span>
            </div>
          )}
        </div>

        <div className="min-h-[400px]">
          <ResponsiveContainer width="100%" height={400}>
            <RadarChart data={radarData}>
              <PolarGrid
                stroke="#6b7280"
                className="dark:stroke-gray-600"
                strokeDasharray="3 3"
              />
              <PolarAngleAxis
                dataKey="analyst"
                tick={{
                  fill: 'currentColor',
                  fontSize: 12,
                  fontWeight: highlightedAnalyst ? 'normal' : 'medium',
                }}
                className="text-gray-700 dark:text-gray-300"
              />
              <PolarRadiusAxis
                angle={90}
                domain={[-1, 1]}
                tick={{
                  fill: 'currentColor',
                  fontSize: 10,
                }}
                className="text-gray-500 dark:text-gray-400"
              />

              {/* Signal strength radar */}
              <Radar
                name="Signal"
                dataKey="signal"
                stroke="#3b82f6"
                fill="#3b82f6"
                fillOpacity={0.6}
                strokeWidth={2}
                dot={{
                  fill: '#3b82f6',
                  r: 4,
                }}
                activeDot={{
                  fill: '#2563eb',
                  r: 6,
                }}
              />

              {/* Confidence overlay */}
              {showConfidence && (
                <Radar
                  name="Confidence"
                  dataKey={(data: RadarDataPoint) => data.confidence * 2 - 1}
                  stroke="#10b981"
                  fill="#10b981"
                  fillOpacity={0.2}
                  strokeWidth={1}
                  strokeDasharray="5 5"
                  dot={false}
                />
              )}

              <Tooltip content={<CustomTooltip />} />
              <Legend
                wrapperStyle={{
                  paddingTop: '20px',
                }}
                iconType="circle"
                formatter={(value: string) => (
                  <span className="text-sm text-gray-700 dark:text-gray-300">{value}</span>
                )}
              />
            </RadarChart>
          </ResponsiveContainer>
        </div>

        {/* Legend explanation */}
        <div className="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <div className="w-3 h-3 rounded-full bg-green-500" aria-hidden="true" />
                <span className="font-medium text-gray-700 dark:text-gray-300">
                  Bullish Signal
                </span>
              </div>
              <p className="text-xs text-gray-500 dark:text-gray-400 ml-5">
                Score above 0.3
              </p>
            </div>
            <div>
              <div className="flex items-center gap-2 mb-1">
                <div className="w-3 h-3 rounded-full bg-red-500" aria-hidden="true" />
                <span className="font-medium text-gray-700 dark:text-gray-300">
                  Bearish Signal
                </span>
              </div>
              <p className="text-xs text-gray-500 dark:text-gray-400 ml-5">
                Score below -0.3
              </p>
            </div>
            <div>
              <div className="flex items-center gap-2 mb-1">
                <div className="w-3 h-3 rounded-full bg-gray-500" aria-hidden="true" />
                <span className="font-medium text-gray-700 dark:text-gray-300">
                  Neutral Signal
                </span>
              </div>
              <p className="text-xs text-gray-500 dark:text-gray-400 ml-5">
                Score between -0.3 and 0.3
              </p>
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
};
