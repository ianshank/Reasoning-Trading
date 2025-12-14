/**
 * Signal Timeline Component
 *
 * Historical signal timeline with line chart showing analyst signals
 * over time, consensus line, and significant event markers.
 */

import React, { useState, useMemo } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
  ReferenceDot,
} from 'recharts';
import { Card, CardHeader, CardBody } from '../ui/card';
import { Badge } from '../ui/badge';
import type { SignalHistory } from './hooks/useAgentSignals';

/**
 * Props for SignalTimeline component
 */
export interface SignalTimelineProps {
  /**
   * Signal history data
   */
  history: SignalHistory;

  /**
   * Timeframe selection
   */
  timeframe?: '1H' | '4H' | '1D' | '1W' | '1M';

  /**
   * Custom className
   */
  className?: string;
}

const ANALYST_COLORS = {
  market: '#3b82f6', // blue
  news: '#10b981', // green
  social: '#f59e0b', // amber
  fundamental: '#8b5cf6', // violet
  macro: '#ec4899', // pink
  consensus: '#1f2937', // gray-800
};

const TIMEFRAME_OPTIONS = [
  { value: '1H', label: '1 Hour' },
  { value: '4H', label: '4 Hours' },
  { value: '1D', label: '1 Day' },
  { value: '1W', label: '1 Week' },
  { value: '1M', label: '1 Month' },
];

/**
 * Format timestamp for X-axis
 */
const formatTimestamp = (timestamp: string, timeframe: string): string => {
  const date = new Date(timestamp);

  if (timeframe === '1H' || timeframe === '4H') {
    return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
  }
  if (timeframe === '1D' || timeframe === '1W') {
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  }
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
};

/**
 * Get event badge variant
 */
const getEventBadgeVariant = (impact: number): 'success' | 'warning' | 'danger' | 'default' => {
  if (Math.abs(impact) > 0.5) return 'danger';
  if (Math.abs(impact) > 0.3) return 'warning';
  if (Math.abs(impact) > 0.1) return 'success';
  return 'default';
};

/**
 * Historical signal timeline component
 */
export const SignalTimeline: React.FC<SignalTimelineProps> = ({
  history,
  timeframe = '1D',
  className = '',
}) => {
  const [selectedTimeframe, setSelectedTimeframe] = useState(timeframe);
  const [visibleLines, setVisibleLines] = useState<Set<string>>(
    new Set(['market', 'news', 'social', 'fundamental', 'macro', 'consensus'])
  );
  const [hoveredEvent, setHoveredEvent] = useState<number | null>(null);

  const chartData = useMemo(() => {
    return history.data_points.map((point) => ({
      timestamp: point.timestamp,
      market: point.market_analyst_score,
      news: point.news_analyst_score,
      social: point.social_sentiment_score,
      fundamental: point.fundamental_analyst_score,
      macro: point.macro_analyst_score,
      consensus: point.consensus,
      formattedTime: formatTimestamp(point.timestamp, selectedTimeframe),
    }));
  }, [history.data_points, selectedTimeframe]);

  const toggleLine = (line: string) => {
    setVisibleLines((prev) => {
      const next = new Set(prev);
      if (next.has(line)) {
        next.delete(line);
      } else {
        next.add(line);
      }
      return next;
    });
  };

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg p-3">
          <p className="text-sm font-semibold text-gray-900 dark:text-white mb-2">{label}</p>
          <div className="space-y-1">
            {payload.map((entry: any) => (
              <div key={entry.dataKey} className="flex items-center justify-between gap-4">
                <div className="flex items-center gap-2">
                  <div
                    className="w-3 h-3 rounded-full"
                    style={{ backgroundColor: entry.color }}
                    aria-hidden="true"
                  />
                  <span className="text-xs text-gray-600 dark:text-gray-400 capitalize">
                    {entry.name}:
                  </span>
                </div>
                <span className="text-xs font-medium text-gray-900 dark:text-white">
                  {entry.value > 0 ? '+' : ''}
                  {entry.value.toFixed(3)}
                </span>
              </div>
            ))}
          </div>
        </div>
      );
    }
    return null;
  };

  if (chartData.length === 0) {
    return (
      <Card className={`bg-white dark:bg-gray-800 ${className}`}>
        <CardBody>
          <div className="text-center py-8">
            <p className="text-gray-500 dark:text-gray-400">No historical data available</p>
          </div>
        </CardBody>
      </Card>
    );
  }

  return (
    <Card className={`bg-white dark:bg-gray-800 ${className}`}>
      <CardHeader>
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h2 className="text-xl font-bold text-gray-900 dark:text-white">
              Signal Timeline
            </h2>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              {history.symbol} • Historical analyst signals
            </p>
          </div>

          {/* Timeframe Selector */}
          <div className="flex gap-2">
            {TIMEFRAME_OPTIONS.map((option) => (
              <button
                key={option.value}
                onClick={() => setSelectedTimeframe(option.value as any)}
                className={`px-3 py-1.5 text-sm font-medium rounded-lg transition-colors ${
                  selectedTimeframe === option.value
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                }`}
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>
      </CardHeader>

      <CardBody>
        {/* Line Chart */}
        <div className="mb-6">
          <ResponsiveContainer width="100%" height={400}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-gray-300 dark:stroke-gray-600" />
              <XAxis
                dataKey="formattedTime"
                tick={{ fill: 'currentColor', fontSize: 12 }}
                className="text-gray-600 dark:text-gray-400"
              />
              <YAxis
                domain={[-1, 1]}
                tick={{ fill: 'currentColor', fontSize: 12 }}
                className="text-gray-600 dark:text-gray-400"
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend
                onClick={(e) => toggleLine(e.dataKey as string)}
                wrapperStyle={{ cursor: 'pointer', paddingTop: '20px' }}
                iconType="line"
                formatter={(value: string) => (
                  <span
                    className={`text-sm ${
                      visibleLines.has(value)
                        ? 'text-gray-700 dark:text-gray-300'
                        : 'text-gray-400 dark:text-gray-600 line-through'
                    }`}
                  >
                    {value.charAt(0).toUpperCase() + value.slice(1)}
                  </span>
                )}
              />

              {/* Reference line at 0 */}
              <ReferenceLine y={0} stroke="#9ca3af" strokeDasharray="3 3" />

              {/* Analyst lines */}
              {visibleLines.has('market') && (
                <Line
                  type="monotone"
                  dataKey="market"
                  name="market"
                  stroke={ANALYST_COLORS.market}
                  strokeWidth={2}
                  dot={false}
                  activeDot={{ r: 6 }}
                />
              )}
              {visibleLines.has('news') && (
                <Line
                  type="monotone"
                  dataKey="news"
                  name="news"
                  stroke={ANALYST_COLORS.news}
                  strokeWidth={2}
                  dot={false}
                  activeDot={{ r: 6 }}
                />
              )}
              {visibleLines.has('social') && (
                <Line
                  type="monotone"
                  dataKey="social"
                  name="social"
                  stroke={ANALYST_COLORS.social}
                  strokeWidth={2}
                  dot={false}
                  activeDot={{ r: 6 }}
                />
              )}
              {visibleLines.has('fundamental') && (
                <Line
                  type="monotone"
                  dataKey="fundamental"
                  name="fundamental"
                  stroke={ANALYST_COLORS.fundamental}
                  strokeWidth={2}
                  dot={false}
                  activeDot={{ r: 6 }}
                />
              )}
              {visibleLines.has('macro') && (
                <Line
                  type="monotone"
                  dataKey="macro"
                  name="macro"
                  stroke={ANALYST_COLORS.macro}
                  strokeWidth={2}
                  dot={false}
                  activeDot={{ r: 6 }}
                />
              )}
              {visibleLines.has('consensus') && (
                <Line
                  type="monotone"
                  dataKey="consensus"
                  name="consensus"
                  stroke={ANALYST_COLORS.consensus}
                  strokeWidth={3}
                  dot={false}
                  activeDot={{ r: 8 }}
                  strokeDasharray="5 5"
                />
              )}

              {/* Event markers */}
              {history.significant_events.map((event, index) => {
                const dataPoint = chartData.find((d) => d.timestamp === event.timestamp);
                if (!dataPoint) return null;

                return (
                  <ReferenceDot
                    key={index}
                    x={dataPoint.formattedTime}
                    y={event.impact}
                    r={8}
                    fill="#ef4444"
                    stroke="#fff"
                    strokeWidth={2}
                    onMouseEnter={() => setHoveredEvent(index)}
                    onMouseLeave={() => setHoveredEvent(null)}
                  />
                );
              })}
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Significant Events */}
        {history.significant_events.length > 0 && (
          <div>
            <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
              Significant Events
            </h3>
            <div className="space-y-2">
              {history.significant_events.map((event, index) => (
                <div
                  key={index}
                  className={`p-3 rounded-lg border transition-all ${
                    hoveredEvent === index
                      ? 'bg-red-50 dark:bg-red-900/20 border-red-300 dark:border-red-700'
                      : 'bg-gray-50 dark:bg-gray-800/50 border-gray-200 dark:border-gray-700'
                  }`}
                  onMouseEnter={() => setHoveredEvent(index)}
                  onMouseLeave={() => setHoveredEvent(null)}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <Badge variant={getEventBadgeVariant(event.impact)} size="sm">
                          {event.event_type}
                        </Badge>
                        <span className="text-xs text-gray-500 dark:text-gray-400">
                          {formatTimestamp(event.timestamp, selectedTimeframe)}
                        </span>
                      </div>
                      <p className="text-sm text-gray-700 dark:text-gray-300">
                        {event.description}
                      </p>
                    </div>
                    <div className="text-right">
                      <div className="text-sm text-gray-600 dark:text-gray-400">Impact</div>
                      <div
                        className={`text-lg font-bold ${
                          event.impact > 0
                            ? 'text-green-600 dark:text-green-400'
                            : event.impact < 0
                            ? 'text-red-600 dark:text-red-400'
                            : 'text-gray-600 dark:text-gray-400'
                        }`}
                      >
                        {event.impact > 0 ? '+' : ''}
                        {event.impact.toFixed(3)}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Stats */}
        <div className="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center">
              <div className="text-sm text-gray-600 dark:text-gray-400">Data Points</div>
              <div className="text-xl font-bold text-gray-900 dark:text-white">
                {chartData.length}
              </div>
            </div>
            <div className="text-center">
              <div className="text-sm text-gray-600 dark:text-gray-400">Events</div>
              <div className="text-xl font-bold text-gray-900 dark:text-white">
                {history.significant_events.length}
              </div>
            </div>
            <div className="text-center">
              <div className="text-sm text-gray-600 dark:text-gray-400">Timeframe</div>
              <div className="text-xl font-bold text-gray-900 dark:text-white">
                {TIMEFRAME_OPTIONS.find((o) => o.value === selectedTimeframe)?.label}
              </div>
            </div>
            <div className="text-center">
              <div className="text-sm text-gray-600 dark:text-gray-400">Current Consensus</div>
              <div
                className={`text-xl font-bold ${
                  chartData[chartData.length - 1].consensus > 0
                    ? 'text-green-600 dark:text-green-400'
                    : chartData[chartData.length - 1].consensus < 0
                    ? 'text-red-600 dark:text-red-400'
                    : 'text-gray-600 dark:text-gray-400'
                }`}
              >
                {chartData[chartData.length - 1].consensus > 0 ? '+' : ''}
                {chartData[chartData.length - 1].consensus.toFixed(3)}
              </div>
            </div>
          </div>
        </div>
      </CardBody>
    </Card>
  );
};
