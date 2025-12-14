/**
 * Current Regime Card Component
 *
 * Displays the current market regime with:
 * - Regime name and icon
 * - Confidence score with progress bar
 * - Time in current regime
 * - Indicator contributions
 */

import React from 'react';
import {
  TrendingUp,
  TrendingDown,
  Activity,
  Minimize2,
  Circle,
} from 'lucide-react';
import { Card, CardHeader, CardBody } from '../ui/Card';
import { Progress } from '../ui/progress';
import type { IndicatorContribution } from '../../types/regime';
import { getRegimeDisplayName, getRegimeColor } from '../../types/regime';

export interface CurrentRegimeCardProps {
  regime: string;
  confidence: number;
  since: string;
  indicators?: IndicatorContribution[];
  className?: string;
}

/**
 * Get icon for regime type
 */
function getRegimeIcon(regime: string): React.ReactNode {
  const iconProps = {
    size: 32,
    className: 'inline-block',
  };

  switch (regime.toLowerCase()) {
    case 'bull':
      return <TrendingUp {...iconProps} style={{ color: getRegimeColor('bull') }} />;
    case 'bear':
      return <TrendingDown {...iconProps} style={{ color: getRegimeColor('bear') }} />;
    case 'high_volatility':
      return <Activity {...iconProps} style={{ color: getRegimeColor('high_volatility') }} />;
    case 'low_volatility':
      return <Minimize2 {...iconProps} style={{ color: getRegimeColor('low_volatility') }} />;
    default:
      return <Circle {...iconProps} style={{ color: getRegimeColor('neutral') }} />;
  }
}

/**
 * Format time duration
 */
function formatDuration(since: string): string {
  const sinceDate = new Date(since);
  const now = new Date();
  const diffMs = now.getTime() - sinceDate.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHour = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHour / 24);

  if (diffDay > 0) {
    return `${diffDay} day${diffDay !== 1 ? 's' : ''}`;
  } else if (diffHour > 0) {
    return `${diffHour} hour${diffHour !== 1 ? 's' : ''}`;
  } else if (diffMin > 0) {
    return `${diffMin} minute${diffMin !== 1 ? 's' : ''}`;
  } else {
    return `${diffSec} second${diffSec !== 1 ? 's' : ''}`;
  }
}

/**
 * Get confidence level color
 */
function getConfidenceColor(confidence: number): string {
  if (confidence >= 0.8) return 'bg-green-500';
  if (confidence >= 0.6) return 'bg-yellow-500';
  return 'bg-orange-500';
}

export const CurrentRegimeCard: React.FC<CurrentRegimeCardProps> = ({
  regime,
  confidence,
  since,
  indicators = [],
  className = '',
}) => {
  const regimeColor = getRegimeColor(regime);
  const confidencePct = Math.round(confidence * 100);

  return (
    <Card
      className={`bg-white dark:bg-gray-800 ${className}`}
      role="article"
      aria-label="Current Market Regime"
    >
      <CardHeader>
        <div className="flex items-center justify-between w-full">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            Current Regime
          </h3>
          <div
            className="px-3 py-1 rounded-full text-xs font-medium text-white"
            style={{ backgroundColor: regimeColor }}
            role="status"
            aria-label={`Regime: ${regime}`}
          >
            {formatDuration(since)}
          </div>
        </div>
      </CardHeader>

      <CardBody>
        <div className="space-y-6">
          {/* Regime Display */}
          <div className="flex items-center space-x-4">
            <div className="flex-shrink-0" aria-hidden="true">
              {getRegimeIcon(regime)}
            </div>
            <div className="flex-1 min-w-0">
              <h4 className="text-2xl font-bold text-gray-900 dark:text-white truncate">
                {getRegimeDisplayName(regime)}
              </h4>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Since {new Date(since).toLocaleString()}
              </p>
            </div>
          </div>

          {/* Confidence Score */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Confidence
              </span>
              <span
                className="text-sm font-bold"
                style={{ color: regimeColor }}
                aria-label={`Confidence: ${confidencePct}%`}
              >
                {confidencePct}%
              </span>
            </div>
            <Progress
              value={confidencePct}
              className="h-3"
              indicatorClassName={getConfidenceColor(confidence)}
              aria-label={`Confidence level: ${confidencePct}%`}
            />
          </div>

          {/* Indicator Contributions */}
          {indicators.length > 0 && (
            <div className="space-y-3">
              <h5 className="text-sm font-semibold text-gray-700 dark:text-gray-300">
                Key Indicators
              </h5>
              <div className="space-y-2">
                {indicators.slice(0, 5).map((indicator, index) => (
                  <div
                    key={index}
                    className="flex items-center justify-between text-sm"
                  >
                    <span className="text-gray-600 dark:text-gray-400">
                      {indicator.name}
                    </span>
                    <div className="flex items-center space-x-2">
                      <span className="font-mono text-gray-900 dark:text-white">
                        {indicator.value.toFixed(2)}
                      </span>
                      <div
                        className="w-16 bg-gray-200 dark:bg-gray-700 rounded-full h-2"
                        role="progressbar"
                        aria-valuenow={Math.abs(indicator.impact) * 100}
                        aria-valuemin={0}
                        aria-valuemax={100}
                        aria-label={`${indicator.name} impact`}
                      >
                        <div
                          className={`h-2 rounded-full ${
                            indicator.impact > 0
                              ? 'bg-green-500'
                              : 'bg-red-500'
                          }`}
                          style={{
                            width: `${Math.abs(indicator.impact) * 100}%`,
                          }}
                        />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </CardBody>
    </Card>
  );
};
