/**
 * Analyst Grid Component
 *
 * Grid layout displaying all 5 analysts with responsive columns.
 */

import React, { useState, useMemo } from 'react';
import type { AnalystSignals } from '../../types/trading';
import { AnalystCard, AnalystType } from './AnalystCard';
import { Progress } from '../ui/progress';

/**
 * Props for AnalystGrid component
 */
export interface AnalystGridProps {
  /**
   * Analyst signals data
   */
  signals: AnalystSignals;

  /**
   * Callback when analyst card is clicked
   */
  onAnalystClick?: (analyst: AnalystType) => void;

  /**
   * Custom className
   */
  className?: string;
}

interface AnalystData {
  type: AnalystType;
  signal: number;
  confidence: number;
  reasoning: string[];
}

/**
 * Grid layout of all 5 analysts with signal summary
 */
export const AnalystGrid: React.FC<AnalystGridProps> = ({
  signals,
  onAnalystClick,
  className = '',
}) => {
  const [selectedAnalyst, setSelectedAnalyst] = useState<AnalystType | null>(null);

  const analysts = useMemo((): AnalystData[] => {
    return [
      {
        type: 'market',
        signal: signals.market_analyst_score,
        confidence: signals.market_analyst_confidence,
        reasoning: extractReasoning(signals.evidence_packets, 'market'),
      },
      {
        type: 'news',
        signal: signals.news_analyst_score,
        confidence: signals.news_analyst_confidence,
        reasoning: extractReasoning(signals.evidence_packets, 'news'),
      },
      {
        type: 'social',
        signal: signals.social_sentiment_score,
        confidence: signals.social_sentiment_confidence,
        reasoning: extractReasoning(signals.evidence_packets, 'social'),
      },
      {
        type: 'fundamental',
        signal: signals.fundamental_analyst_score,
        confidence: signals.fundamental_analyst_confidence,
        reasoning: extractReasoning(signals.evidence_packets, 'fundamental'),
      },
      {
        type: 'macro',
        signal: signals.macro_analyst_score,
        confidence: signals.macro_analyst_confidence,
        reasoning: extractReasoning(signals.evidence_packets, 'macro'),
      },
    ];
  }, [signals]);

  const summary = useMemo(() => {
    const totalSignal = analysts.reduce((sum, a) => sum + a.signal, 0);
    const avgSignal = totalSignal / analysts.length;
    const avgConfidence = analysts.reduce((sum, a) => sum + a.confidence, 0) / analysts.length;

    const bullishCount = analysts.filter((a) => a.signal > 0.3).length;
    const bearishCount = analysts.filter((a) => a.signal < -0.3).length;
    const neutralCount = analysts.length - bullishCount - bearishCount;

    return {
      avgSignal,
      avgConfidence,
      bullishCount,
      bearishCount,
      neutralCount,
    };
  }, [analysts]);

  const handleAnalystClick = (type: AnalystType) => {
    setSelectedAnalyst(type);
    onAnalystClick?.(type);
  };

  const getSummaryColor = (signal: number): string => {
    if (signal > 0.3) return 'text-green-600 dark:text-green-400';
    if (signal < -0.3) return 'text-red-600 dark:text-red-400';
    return 'text-gray-600 dark:text-gray-400';
  };

  const getSummaryLabel = (signal: number): string => {
    if (signal > 0.3) return 'Bullish Consensus';
    if (signal < -0.3) return 'Bearish Consensus';
    return 'Neutral Consensus';
  };

  return (
    <div className={className}>
      {/* Summary Bar */}
      <div className="mb-6 p-6 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
          {/* Overall Signal */}
          <div className="flex-1">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-medium text-gray-600 dark:text-gray-400">
                Overall Signal
              </h3>
              <span className={`text-lg font-bold ${getSummaryColor(summary.avgSignal)}`}>
                {summary.avgSignal > 0 ? '+' : ''}
                {summary.avgSignal.toFixed(3)}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <Progress
                value={(summary.avgSignal + 1) * 50}
                variant={
                  summary.avgSignal > 0.3 ? 'success' : summary.avgSignal < -0.3 ? 'danger' : 'default'
                }
                size="sm"
              />
              <span className="text-xs font-medium text-gray-700 dark:text-gray-300 whitespace-nowrap">
                {getSummaryLabel(summary.avgSignal)}
              </span>
            </div>
          </div>

          {/* Confidence */}
          <div className="flex-1">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-medium text-gray-600 dark:text-gray-400">
                Avg Confidence
              </h3>
              <span className="text-lg font-bold text-blue-600 dark:text-blue-400">
                {(summary.avgConfidence * 100).toFixed(0)}%
              </span>
            </div>
            <Progress
              value={summary.avgConfidence * 100}
              variant={
                summary.avgConfidence > 0.7 ? 'success' : summary.avgConfidence > 0.4 ? 'default' : 'warning'
              }
              size="sm"
            />
          </div>

          {/* Distribution */}
          <div className="flex-1">
            <h3 className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-2">
              Signal Distribution
            </h3>
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-1.5">
                <div className="w-3 h-3 rounded-full bg-green-500" aria-hidden="true" />
                <span className="text-sm text-gray-700 dark:text-gray-300">
                  {summary.bullishCount}
                </span>
              </div>
              <div className="flex items-center gap-1.5">
                <div className="w-3 h-3 rounded-full bg-gray-400" aria-hidden="true" />
                <span className="text-sm text-gray-700 dark:text-gray-300">
                  {summary.neutralCount}
                </span>
              </div>
              <div className="flex items-center gap-1.5">
                <div className="w-3 h-3 rounded-full bg-red-500" aria-hidden="true" />
                <span className="text-sm text-gray-700 dark:text-gray-300">
                  {summary.bearishCount}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Analyst Cards Grid */}
      <div
        className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
        role="grid"
        aria-label="Analyst signals grid"
      >
        {analysts.map((analyst) => (
          <div key={analyst.type} role="gridcell">
            <AnalystCard
              analyst={analyst.type}
              signal={analyst.signal}
              confidence={analyst.confidence}
              reasoning={analyst.reasoning}
              onClick={onAnalystClick ? () => handleAnalystClick(analyst.type) : undefined}
              isSelected={selectedAnalyst === analyst.type}
            />
          </div>
        ))}
      </div>
    </div>
  );
};

/**
 * Extract reasoning points from evidence packets
 */
function extractReasoning(
  evidencePackets: Record<string, unknown>,
  analystType: string
): string[] {
  const analystKey = `${analystType}_analyst`;
  const evidence = evidencePackets[analystKey];

  if (!evidence || typeof evidence !== 'object') {
    return [];
  }

  const data = evidence as Record<string, unknown>;

  // Try to extract reasoning from common fields
  const reasoning: string[] = [];

  if (Array.isArray(data.reasoning)) {
    reasoning.push(...(data.reasoning as string[]));
  } else if (typeof data.reasoning === 'string') {
    reasoning.push(data.reasoning);
  }

  if (Array.isArray(data.key_points)) {
    reasoning.push(...(data.key_points as string[]));
  }

  if (Array.isArray(data.factors)) {
    reasoning.push(...(data.factors as string[]));
  }

  if (typeof data.summary === 'string') {
    reasoning.push(data.summary);
  }

  return reasoning.slice(0, 5);
}
