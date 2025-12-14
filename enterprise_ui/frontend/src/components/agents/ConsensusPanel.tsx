/**
 * Consensus Panel Component
 *
 * Displays overall recommendation, weighted consensus score,
 * confidence interval, and contributing factors breakdown.
 */

import React, { useMemo } from 'react';
import { Card, CardHeader, CardBody } from '../ui/card';
import { Badge } from '../ui/badge';
import { Progress } from '../ui/progress';
import type { AnalystSignals } from '../../types/trading';
import type { Consensus } from './hooks/useAgentSignals';

/**
 * Props for ConsensusPanel component
 */
export interface ConsensusPanelProps {
  /**
   * Consensus calculation result
   */
  consensus: Consensus;

  /**
   * Analyst signals (for factor breakdown)
   */
  signals: AnalystSignals;

  /**
   * Custom className
   */
  className?: string;
}

interface Factor {
  name: string;
  displayName: string;
  score: number;
  confidence: number;
  weight: number;
  contribution: number;
}

const ANALYST_NAMES: Record<string, string> = {
  market_analyst: 'Market Analysis',
  news_analyst: 'News Sentiment',
  social_sentiment: 'Social Media',
  fundamental_analyst: 'Fundamentals',
  macro_analyst: 'Macro Trends',
};

/**
 * Get recommendation color
 */
const getRecommendationColor = (recommendation: string): string => {
  switch (recommendation) {
    case 'BUY':
      return 'bg-green-500 dark:bg-green-600';
    case 'SELL':
      return 'bg-red-500 dark:bg-red-600';
    default:
      return 'bg-gray-500 dark:bg-gray-600';
  }
};

/**
 * Get recommendation text color
 */
const getRecommendationTextColor = (recommendation: string): string => {
  switch (recommendation) {
    case 'BUY':
      return 'text-green-600 dark:text-green-400';
    case 'SELL':
      return 'text-red-600 dark:text-red-400';
    default:
      return 'text-gray-600 dark:text-gray-400';
  }
};

/**
 * Get recommendation badge variant
 */
const getRecommendationBadgeVariant = (
  recommendation: string
): 'success' | 'danger' | 'warning' | 'default' => {
  switch (recommendation) {
    case 'BUY':
      return 'success';
    case 'SELL':
      return 'danger';
    default:
      return 'default';
  }
};

/**
 * Get score color
 */
const getScoreColor = (score: number): string => {
  if (score > 0.3) return 'text-green-600 dark:text-green-400';
  if (score < -0.3) return 'text-red-600 dark:text-red-400';
  return 'text-gray-600 dark:text-gray-400';
};

/**
 * Consensus summary panel
 */
export const ConsensusPanel: React.FC<ConsensusPanelProps> = ({
  consensus,
  signals,
  className = '',
}) => {
  const factors = useMemo((): Factor[] => {
    if (!consensus.contributing_factors || consensus.contributing_factors.length === 0) {
      // Build factors from signals if not provided
      const totalConfidence =
        signals.market_analyst_confidence +
        signals.news_analyst_confidence +
        signals.social_sentiment_confidence +
        signals.fundamental_analyst_confidence +
        signals.macro_analyst_confidence;

      return [
        {
          name: 'market_analyst',
          displayName: ANALYST_NAMES.market_analyst,
          score: signals.market_analyst_score,
          confidence: signals.market_analyst_confidence,
          weight: totalConfidence > 0 ? signals.market_analyst_confidence / totalConfidence : 0.2,
          contribution:
            signals.market_analyst_score *
            (totalConfidence > 0 ? signals.market_analyst_confidence / totalConfidence : 0.2),
        },
        {
          name: 'news_analyst',
          displayName: ANALYST_NAMES.news_analyst,
          score: signals.news_analyst_score,
          confidence: signals.news_analyst_confidence,
          weight: totalConfidence > 0 ? signals.news_analyst_confidence / totalConfidence : 0.2,
          contribution:
            signals.news_analyst_score *
            (totalConfidence > 0 ? signals.news_analyst_confidence / totalConfidence : 0.2),
        },
        {
          name: 'social_sentiment',
          displayName: ANALYST_NAMES.social_sentiment,
          score: signals.social_sentiment_score,
          confidence: signals.social_sentiment_confidence,
          weight: totalConfidence > 0 ? signals.social_sentiment_confidence / totalConfidence : 0.2,
          contribution:
            signals.social_sentiment_score *
            (totalConfidence > 0 ? signals.social_sentiment_confidence / totalConfidence : 0.2),
        },
        {
          name: 'fundamental_analyst',
          displayName: ANALYST_NAMES.fundamental_analyst,
          score: signals.fundamental_analyst_score,
          confidence: signals.fundamental_analyst_confidence,
          weight:
            totalConfidence > 0 ? signals.fundamental_analyst_confidence / totalConfidence : 0.2,
          contribution:
            signals.fundamental_analyst_score *
            (totalConfidence > 0 ? signals.fundamental_analyst_confidence / totalConfidence : 0.2),
        },
        {
          name: 'macro_analyst',
          displayName: ANALYST_NAMES.macro_analyst,
          score: signals.macro_analyst_score,
          confidence: signals.macro_analyst_confidence,
          weight: totalConfidence > 0 ? signals.macro_analyst_confidence / totalConfidence : 0.2,
          contribution:
            signals.macro_analyst_score *
            (totalConfidence > 0 ? signals.macro_analyst_confidence / totalConfidence : 0.2),
        },
      ].sort((a, b) => Math.abs(b.contribution) - Math.abs(a.contribution));
    }

    return consensus.contributing_factors
      .map((f) => ({
        name: f.name,
        displayName: ANALYST_NAMES[f.name] || f.name,
        score: f.score,
        confidence: f.confidence,
        weight: f.weight,
        contribution: f.score * f.weight,
      }))
      .sort((a, b) => Math.abs(b.contribution) - Math.abs(a.contribution));
  }, [consensus, signals]);

  const confidenceIntervalWidth = useMemo(() => {
    const range = consensus.confidence_interval[1] - consensus.confidence_interval[0];
    return (range / 2) * 100;
  }, [consensus.confidence_interval]);

  return (
    <Card className={`bg-white dark:bg-gray-800 ${className}`}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold text-gray-900 dark:text-white">
            Consensus Analysis
          </h2>
          <Badge
            variant={getRecommendationBadgeVariant(consensus.recommendation)}
            className="text-base px-4 py-2"
          >
            {consensus.recommendation}
          </Badge>
        </div>
      </CardHeader>

      <CardBody>
        {/* Overall Score */}
        <div className="mb-8">
          <div className="flex items-end justify-between mb-3">
            <div>
              <h3 className="text-sm font-medium text-gray-600 dark:text-gray-400">
                Weighted Consensus Score
              </h3>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                Combined signal from all analysts
              </p>
            </div>
            <div className={`text-4xl font-bold ${getScoreColor(consensus.weighted_score)}`}>
              {consensus.weighted_score > 0 ? '+' : ''}
              {consensus.weighted_score.toFixed(3)}
            </div>
          </div>

          {/* Score bar */}
          <div className="relative">
            <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
              <div
                className={`h-full transition-all duration-500 ${
                  consensus.weighted_score > 0
                    ? 'bg-gradient-to-r from-green-400 to-green-600'
                    : consensus.weighted_score < 0
                    ? 'bg-gradient-to-r from-red-600 to-red-400'
                    : 'bg-gray-400'
                }`}
                style={{
                  width: `${Math.abs(consensus.weighted_score) * 50}%`,
                  marginLeft: consensus.weighted_score < 0 ? `${50 - Math.abs(consensus.weighted_score) * 50}%` : '50%',
                }}
              />
            </div>
            {/* Center line */}
            <div className="absolute top-0 left-1/2 w-0.5 h-3 bg-gray-400 dark:bg-gray-600" />
          </div>

          {/* Scale labels */}
          <div className="flex justify-between mt-2 text-xs text-gray-500 dark:text-gray-400">
            <span>-1.0 (Strong Sell)</span>
            <span>0.0 (Neutral)</span>
            <span>+1.0 (Strong Buy)</span>
          </div>
        </div>

        {/* Confidence Interval */}
        <div className="mb-8 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
          <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
            Confidence Interval (95%)
          </h3>
          <div className="flex items-center justify-between">
            <div className="text-center">
              <div className="text-xs text-gray-600 dark:text-gray-400">Lower Bound</div>
              <div className="text-lg font-semibold text-blue-600 dark:text-blue-400">
                {consensus.confidence_interval[0].toFixed(3)}
              </div>
            </div>
            <div className="flex-1 mx-4 relative h-2 bg-blue-200 dark:bg-blue-800 rounded-full">
              <div
                className="absolute top-0 h-2 bg-blue-500 rounded-full"
                style={{
                  left: '50%',
                  width: `${confidenceIntervalWidth}%`,
                  transform: `translateX(-50%)`,
                }}
              />
            </div>
            <div className="text-center">
              <div className="text-xs text-gray-600 dark:text-gray-400">Upper Bound</div>
              <div className="text-lg font-semibold text-blue-600 dark:text-blue-400">
                {consensus.confidence_interval[1].toFixed(3)}
              </div>
            </div>
          </div>
          <p className="text-xs text-gray-600 dark:text-gray-400 mt-3 text-center">
            95% confidence that true consensus is within this range
          </p>
        </div>

        {/* Contributing Factors Breakdown */}
        <div>
          <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-4">
            Contributing Factors
          </h3>
          <div className="space-y-4">
            {factors.map((factor) => (
              <div
                key={factor.name}
                className="p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700"
              >
                <div className="flex items-center justify-between mb-3">
                  <div className="flex-1">
                    <h4 className="text-sm font-semibold text-gray-900 dark:text-white">
                      {factor.displayName}
                    </h4>
                    <div className="flex items-center gap-4 mt-1">
                      <span className="text-xs text-gray-500 dark:text-gray-400">
                        Weight: {(factor.weight * 100).toFixed(1)}%
                      </span>
                      <span className="text-xs text-gray-500 dark:text-gray-400">
                        Confidence: {(factor.confidence * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className={`text-lg font-bold ${getScoreColor(factor.score)}`}>
                      {factor.score > 0 ? '+' : ''}
                      {factor.score.toFixed(3)}
                    </div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">
                      Contribution: {factor.contribution > 0 ? '+' : ''}
                      {factor.contribution.toFixed(3)}
                    </div>
                  </div>
                </div>

                {/* Contribution bar */}
                <div className="relative">
                  <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                    <div
                      className={`h-full ${
                        factor.contribution > 0
                          ? 'bg-green-500'
                          : factor.contribution < 0
                          ? 'bg-red-500'
                          : 'bg-gray-400'
                      }`}
                      style={{
                        width: `${Math.abs(factor.contribution) * 50}%`,
                        marginLeft:
                          factor.contribution < 0
                            ? `${50 - Math.abs(factor.contribution) * 50}%`
                            : '50%',
                      }}
                    />
                  </div>
                  <div className="absolute top-0 left-1/2 w-0.5 h-2 bg-gray-400 dark:bg-gray-600" />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Timestamp */}
        <div className="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700">
          <p className="text-xs text-gray-500 dark:text-gray-400 text-center">
            Last updated: {new Date(consensus.timestamp).toLocaleString()}
          </p>
        </div>
      </CardBody>
    </Card>
  );
};
