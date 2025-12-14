/**
 * Debate View Component
 *
 * Two-column layout showing Bull/Bear debate transcript with verdict.
 */

import React, { useMemo } from 'react';
import { Card, CardHeader, CardBody } from '../ui/card';
import { Badge } from '../ui/badge';
import type { Debate, DebateVerdict, Consensus } from './hooks/useAgentSignals';

/**
 * Props for DebateView component
 */
export interface DebateViewProps {
  /**
   * Debate transcript
   */
  debate: Debate;

  /**
   * Final verdict
   */
  verdict: DebateVerdict | null;

  /**
   * Consensus score
   */
  consensus: Consensus | null;

  /**
   * Custom className
   */
  className?: string;
}

/**
 * Format timestamp to readable time
 */
const formatTime = (timestamp: string): string => {
  const date = new Date(timestamp);
  return date.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
};

/**
 * Format duration in seconds to readable format
 */
const formatDuration = (seconds: number): string => {
  if (seconds < 60) {
    return `${seconds}s`;
  }
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes}m ${remainingSeconds}s`;
};

/**
 * Get verdict color
 */
const getVerdictColor = (recommendation: string): string => {
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
 * Get verdict badge variant
 */
const getVerdictBadgeVariant = (
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
 * Bull/Bear debate transcript viewer
 */
export const DebateView: React.FC<DebateViewProps> = ({
  debate,
  verdict,
  consensus,
  className = '',
}) => {
  const { bullArguments, bearArguments } = useMemo(() => {
    const bull = debate.arguments.filter((arg) => arg.speaker === 'bull');
    const bear = debate.arguments.filter((arg) => arg.speaker === 'bear');
    return { bullArguments: bull, bearArguments: bear };
  }, [debate.arguments]);

  const maxLength = Math.max(bullArguments.length, bearArguments.length);

  return (
    <div className={className}>
      {/* Header */}
      <Card className="mb-6">
        <CardHeader>
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <h2 className="text-xl font-bold text-gray-900 dark:text-white">
                Bull vs Bear Debate
              </h2>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                {debate.symbol} • {formatTime(debate.timestamp)}
              </p>
            </div>
            <div className="flex items-center gap-4">
              <div className="text-center">
                <div className="text-sm text-gray-600 dark:text-gray-400">Duration</div>
                <div className="text-lg font-semibold text-gray-900 dark:text-white">
                  {formatDuration(debate.duration_seconds)}
                </div>
              </div>
              <div className="text-center">
                <div className="text-sm text-gray-600 dark:text-gray-400">Exchanges</div>
                <div className="text-lg font-semibold text-gray-900 dark:text-white">
                  {debate.total_exchanges}
                </div>
              </div>
            </div>
          </div>
        </CardHeader>
      </Card>

      {/* Debate Transcript - Two Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* Bull Column */}
        <div>
          <div className="flex items-center gap-2 mb-4">
            <div className="flex-1 h-1 bg-green-200 dark:bg-green-800 rounded" />
            <h3 className="text-lg font-semibold text-green-600 dark:text-green-400 px-4">
              Bull Case
            </h3>
            <div className="flex-1 h-1 bg-green-200 dark:bg-green-800 rounded" />
          </div>
          <div className="space-y-4">
            {bullArguments.length === 0 ? (
              <div className="text-center text-gray-500 dark:text-gray-400 py-8">
                No bull arguments
              </div>
            ) : (
              bullArguments.map((arg, index) => (
                <Card
                  key={index}
                  className="bg-green-50 dark:bg-green-900/10 border-green-200 dark:border-green-800"
                >
                  <CardBody>
                    <div className="flex items-start justify-between mb-2">
                      <Badge variant="success" size="sm">
                        Round {index + 1}
                      </Badge>
                      <span className="text-xs text-gray-500 dark:text-gray-400">
                        {formatTime(arg.timestamp)}
                      </span>
                    </div>
                    <p className="text-sm text-gray-700 dark:text-gray-300 mb-3">
                      {arg.argument}
                    </p>
                    {arg.evidence_references.length > 0 && (
                      <div className="pt-3 border-t border-green-200 dark:border-green-800">
                        <div className="text-xs text-gray-600 dark:text-gray-400 mb-1">
                          Evidence:
                        </div>
                        <div className="flex flex-wrap gap-1">
                          {arg.evidence_references.slice(0, 3).map((ref, refIndex) => (
                            <Badge
                              key={refIndex}
                              variant="default"
                              size="sm"
                              className="text-xs"
                            >
                              {ref}
                            </Badge>
                          ))}
                          {arg.evidence_references.length > 3 && (
                            <Badge variant="default" size="sm" className="text-xs">
                              +{arg.evidence_references.length - 3} more
                            </Badge>
                          )}
                        </div>
                      </div>
                    )}
                    <div className="flex items-center gap-2 mt-3">
                      <span className="text-xs text-gray-500 dark:text-gray-400">
                        Confidence:
                      </span>
                      <div className="flex-1 h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-green-500 rounded-full"
                          style={{ width: `${arg.confidence * 100}%` }}
                        />
                      </div>
                      <span className="text-xs font-medium text-gray-700 dark:text-gray-300">
                        {(arg.confidence * 100).toFixed(0)}%
                      </span>
                    </div>
                  </CardBody>
                </Card>
              ))
            )}
          </div>
        </div>

        {/* Bear Column */}
        <div>
          <div className="flex items-center gap-2 mb-4">
            <div className="flex-1 h-1 bg-red-200 dark:bg-red-800 rounded" />
            <h3 className="text-lg font-semibold text-red-600 dark:text-red-400 px-4">
              Bear Case
            </h3>
            <div className="flex-1 h-1 bg-red-200 dark:bg-red-800 rounded" />
          </div>
          <div className="space-y-4">
            {bearArguments.length === 0 ? (
              <div className="text-center text-gray-500 dark:text-gray-400 py-8">
                No bear arguments
              </div>
            ) : (
              bearArguments.map((arg, index) => (
                <Card
                  key={index}
                  className="bg-red-50 dark:bg-red-900/10 border-red-200 dark:border-red-800"
                >
                  <CardBody>
                    <div className="flex items-start justify-between mb-2">
                      <Badge variant="danger" size="sm">
                        Round {index + 1}
                      </Badge>
                      <span className="text-xs text-gray-500 dark:text-gray-400">
                        {formatTime(arg.timestamp)}
                      </span>
                    </div>
                    <p className="text-sm text-gray-700 dark:text-gray-300 mb-3">
                      {arg.argument}
                    </p>
                    {arg.evidence_references.length > 0 && (
                      <div className="pt-3 border-t border-red-200 dark:border-red-800">
                        <div className="text-xs text-gray-600 dark:text-gray-400 mb-1">
                          Evidence:
                        </div>
                        <div className="flex flex-wrap gap-1">
                          {arg.evidence_references.slice(0, 3).map((ref, refIndex) => (
                            <Badge
                              key={refIndex}
                              variant="default"
                              size="sm"
                              className="text-xs"
                            >
                              {ref}
                            </Badge>
                          ))}
                          {arg.evidence_references.length > 3 && (
                            <Badge variant="default" size="sm" className="text-xs">
                              +{arg.evidence_references.length - 3} more
                            </Badge>
                          )}
                        </div>
                      </div>
                    )}
                    <div className="flex items-center gap-2 mt-3">
                      <span className="text-xs text-gray-500 dark:text-gray-400">
                        Confidence:
                      </span>
                      <div className="flex-1 h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-red-500 rounded-full"
                          style={{ width: `${arg.confidence * 100}%` }}
                        />
                      </div>
                      <span className="text-xs font-medium text-gray-700 dark:text-gray-300">
                        {(arg.confidence * 100).toFixed(0)}%
                      </span>
                    </div>
                  </CardBody>
                </Card>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Verdict & Consensus */}
      {(verdict || consensus) && (
        <Card className="bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 border-blue-200 dark:border-blue-800">
          <CardHeader>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              Final Verdict
            </h3>
          </CardHeader>
          <CardBody>
            {verdict && (
              <div className="mb-6">
                <div className="flex items-center gap-4 mb-4">
                  <Badge
                    variant={getVerdictBadgeVariant(verdict.recommendation)}
                    className="text-lg px-4 py-2"
                  >
                    {verdict.recommendation}
                  </Badge>
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-gray-600 dark:text-gray-400">Strength:</span>
                    <div className="w-32 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                      <div
                        className={`h-full ${
                          verdict.recommendation === 'BUY'
                            ? 'bg-green-500'
                            : verdict.recommendation === 'SELL'
                            ? 'bg-red-500'
                            : 'bg-gray-500'
                        }`}
                        style={{ width: `${Math.abs(verdict.strength) * 100}%` }}
                      />
                    </div>
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                      {(Math.abs(verdict.strength) * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
                <div className="space-y-2">
                  <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300">
                    Key Reasoning:
                  </h4>
                  <ul className="space-y-1">
                    {verdict.reasoning.map((reason, index) => (
                      <li
                        key={index}
                        className="flex items-start gap-2 text-sm text-gray-600 dark:text-gray-400"
                      >
                        <span className="text-blue-500 mt-1 flex-shrink-0" aria-hidden="true">
                          •
                        </span>
                        <span>{reason}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            )}

            {consensus && (
              <div className="pt-6 border-t border-blue-200 dark:border-blue-800">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                    Weighted Consensus Score
                  </span>
                  <span className={`text-xl font-bold ${getVerdictColor(consensus.recommendation)}`}>
                    {consensus.weighted_score > 0 ? '+' : ''}
                    {consensus.weighted_score.toFixed(3)}
                  </span>
                </div>
                <div className="text-xs text-gray-500 dark:text-gray-400">
                  Confidence Interval: [{consensus.confidence_interval[0].toFixed(3)},{' '}
                  {consensus.confidence_interval[1].toFixed(3)}]
                </div>
              </div>
            )}
          </CardBody>
        </Card>
      )}
    </div>
  );
};
