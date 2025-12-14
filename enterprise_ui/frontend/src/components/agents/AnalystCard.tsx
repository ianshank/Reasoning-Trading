/**
 * Analyst Card Component
 *
 * Individual card displaying analyst signal, confidence, and reasoning.
 */

import React from 'react';
import { Card, CardHeader, CardBody } from '../ui/card';
import { Badge } from '../ui/badge';
import { Progress } from '../ui/progress';

/**
 * Analyst type identifier
 */
export type AnalystType = 'market' | 'news' | 'social' | 'fundamental' | 'macro';

/**
 * Props for AnalystCard component
 */
export interface AnalystCardProps {
  /**
   * Analyst type/name
   */
  analyst: AnalystType;

  /**
   * Signal value (-1 to 1)
   */
  signal: number;

  /**
   * Confidence level (0 to 1)
   */
  confidence: number;

  /**
   * Key reasoning points
   */
  reasoning?: string[];

  /**
   * Click handler
   */
  onClick?: () => void;

  /**
   * Whether the card is selected/highlighted
   */
  isSelected?: boolean;

  /**
   * Custom className
   */
  className?: string;
}

const ANALYST_INFO: Record<AnalystType, { name: string; icon: string; description: string }> = {
  market: {
    name: 'Market Analyst',
    icon: 'M13 7h8m0 0v8m0-8l-8 8-4-4-6 6',
    description: 'Technical and price action analysis',
  },
  news: {
    name: 'News Analyst',
    icon: 'M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z',
    description: 'News sentiment and event analysis',
  },
  social: {
    name: 'Social Sentiment',
    icon: 'M17 8h2a2 2 0 012 2v6a2 2 0 01-2 2h-2v4l-4-4H9a1.994 1.994 0 01-1.414-.586m0 0L11 14h4a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2v4l.586-.586z',
    description: 'Social media and community sentiment',
  },
  fundamental: {
    name: 'Fundamental Analyst',
    icon: 'M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z',
    description: 'Financial metrics and valuation',
  },
  macro: {
    name: 'Macro Analyst',
    icon: 'M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
    description: 'Macroeconomic trends and indicators',
  },
};

/**
 * Get signal color based on value
 */
const getSignalColor = (signal: number): string => {
  if (signal > 0.3) return 'text-green-600 dark:text-green-400';
  if (signal < -0.3) return 'text-red-600 dark:text-red-400';
  return 'text-gray-600 dark:text-gray-400';
};

/**
 * Get signal background color based on value
 */
const getSignalBgColor = (signal: number): string => {
  if (signal > 0.3) return 'bg-green-50 dark:bg-green-900/20';
  if (signal < -0.3) return 'bg-red-50 dark:bg-red-900/20';
  return 'bg-gray-50 dark:bg-gray-800/50';
};

/**
 * Get signal label
 */
const getSignalLabel = (signal: number): string => {
  if (signal > 0.5) return 'Strong Bullish';
  if (signal > 0.3) return 'Bullish';
  if (signal > 0.1) return 'Slightly Bullish';
  if (signal > -0.1) return 'Neutral';
  if (signal > -0.3) return 'Slightly Bearish';
  if (signal > -0.5) return 'Bearish';
  return 'Strong Bearish';
};

/**
 * Get badge variant based on signal
 */
const getSignalBadgeVariant = (signal: number): 'success' | 'danger' | 'warning' | 'default' => {
  if (signal > 0.3) return 'success';
  if (signal < -0.3) return 'danger';
  if (Math.abs(signal) > 0.1) return 'warning';
  return 'default';
};

/**
 * Individual analyst card component
 */
export const AnalystCard: React.FC<AnalystCardProps> = ({
  analyst,
  signal,
  confidence,
  reasoning = [],
  onClick,
  isSelected = false,
  className = '',
}) => {
  const info = ANALYST_INFO[analyst];
  const signalColor = getSignalColor(signal);
  const signalBgColor = getSignalBgColor(signal);
  const signalLabel = getSignalLabel(signal);
  const badgeVariant = getSignalBadgeVariant(signal);

  return (
    <Card
      className={`transition-all duration-200 ${
        onClick ? 'cursor-pointer hover:shadow-lg' : ''
      } ${isSelected ? 'ring-2 ring-blue-500 shadow-lg' : ''} ${className}`}
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={
        onClick
          ? (e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                onClick();
              }
            }
          : undefined
      }
    >
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-blue-50 dark:bg-blue-900/20">
              <svg
                className="w-5 h-5 text-blue-600 dark:text-blue-400"
                fill="none"
                stroke="currentColor"
                strokeWidth={2}
                strokeLinecap="round"
                strokeLinejoin="round"
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <path d={info.icon} />
              </svg>
            </div>
            <div>
              <h4 className="text-sm font-semibold text-gray-900 dark:text-white">
                {info.name}
              </h4>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                {info.description}
              </p>
            </div>
          </div>
        </div>
      </CardHeader>

      <CardBody>
        {/* Signal Value */}
        <div className={`rounded-lg p-4 mb-4 ${signalBgColor}`}>
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-gray-600 dark:text-gray-400">
              Signal Strength
            </span>
            <Badge variant={badgeVariant} size="sm">
              {signalLabel}
            </Badge>
          </div>
          <div className={`text-2xl font-bold ${signalColor}`}>
            {signal > 0 ? '+' : ''}
            {signal.toFixed(3)}
          </div>
        </div>

        {/* Confidence Bar */}
        <div className="mb-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-gray-600 dark:text-gray-400">
              Confidence
            </span>
            <span className="text-xs font-semibold text-gray-900 dark:text-white">
              {(confidence * 100).toFixed(0)}%
            </span>
          </div>
          <Progress
            value={confidence * 100}
            variant={confidence > 0.7 ? 'success' : confidence > 0.4 ? 'default' : 'warning'}
            size="sm"
          />
        </div>

        {/* Key Reasoning Points */}
        {reasoning.length > 0 && (
          <div>
            <h5 className="text-xs font-medium text-gray-600 dark:text-gray-400 mb-2">
              Key Factors
            </h5>
            <ul className="space-y-1.5">
              {reasoning.slice(0, 3).map((point, index) => (
                <li
                  key={index}
                  className="flex items-start gap-2 text-xs text-gray-700 dark:text-gray-300"
                >
                  <span className="text-blue-500 mt-0.5 flex-shrink-0" aria-hidden="true">
                    •
                  </span>
                  <span className="flex-1">{point}</span>
                </li>
              ))}
            </ul>
            {reasoning.length > 3 && (
              <button
                className="text-xs text-blue-600 dark:text-blue-400 hover:underline mt-2"
                onClick={(e) => {
                  e.stopPropagation();
                }}
              >
                View {reasoning.length - 3} more
              </button>
            )}
          </div>
        )}
      </CardBody>
    </Card>
  );
};
