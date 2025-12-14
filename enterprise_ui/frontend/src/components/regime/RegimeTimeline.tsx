/**
 * Regime Timeline Component
 *
 * Displays historical regime transitions over time
 * - Timeline view with regime segments
 * - Color coded by regime type
 * - Duration display
 * - Click to view details
 */

import React, { useState, useMemo } from 'react';
import { Clock, Info } from 'lucide-react';
import { Card, CardHeader, CardBody } from '../ui/Card';
import { Modal } from '../ui/modal';
import type { RegimeHistoryEntry } from '../../types/regime';
import { getRegimeDisplayName, getRegimeColor } from '../../types/regime';

export interface RegimeTimelineProps {
  history: RegimeHistoryEntry[];
  timeframe?: 'day' | 'week' | 'month' | 'year';
  className?: string;
}

interface SegmentDetails {
  regime: string;
  startTime: string;
  endTime?: string;
  duration: number;
  confidence: number;
}

/**
 * Format duration in human-readable format
 */
function formatDuration(seconds: number): string {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);

  if (hours > 0) {
    return `${hours}h ${minutes}m`;
  } else if (minutes > 0) {
    return `${minutes}m ${secs}s`;
  } else {
    return `${secs}s`;
  }
}

/**
 * Format date/time based on timeframe
 */
function formatDateTime(
  dateString: string,
  timeframe: string
): string {
  const date = new Date(dateString);

  if (timeframe === 'day') {
    return date.toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
    });
  } else if (timeframe === 'week') {
    return date.toLocaleDateString([], {
      weekday: 'short',
      hour: '2-digit',
      minute: '2-digit',
    });
  } else {
    return date.toLocaleDateString([], {
      month: 'short',
      day: 'numeric',
    });
  }
}

export const RegimeTimeline: React.FC<RegimeTimelineProps> = ({
  history,
  timeframe = 'day',
  className = '',
}) => {
  const [selectedSegment, setSelectedSegment] = useState<SegmentDetails | null>(
    null
  );

  // Calculate total timespan and segment widths
  const { segments, totalDuration } = useMemo(() => {
    if (history.length === 0) {
      return { segments: [], totalDuration: 0 };
    }

    const total = history.reduce((sum, entry) => sum + entry.duration, 0);

    const segs = history.map((entry) => ({
      ...entry,
      widthPercent: (entry.duration / total) * 100,
    }));

    return { segments: segs, totalDuration: total };
  }, [history]);

  const handleSegmentClick = (segment: RegimeHistoryEntry) => {
    setSelectedSegment({
      regime: segment.regime,
      startTime: segment.startTime,
      endTime: segment.endTime,
      duration: segment.duration,
      confidence: segment.confidence,
    });
  };

  const closeModal = () => {
    setSelectedSegment(null);
  };

  return (
    <>
      <Card
        className={`bg-white dark:bg-gray-800 ${className}`}
        role="article"
        aria-label="Regime Timeline"
      >
        <CardHeader>
          <div className="flex items-center justify-between w-full">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              Regime Timeline
            </h3>
            <div className="flex items-center space-x-2 text-sm text-gray-500 dark:text-gray-400">
              <Clock size={16} />
              <span>Total: {formatDuration(totalDuration)}</span>
            </div>
          </div>
        </CardHeader>

        <CardBody>
          <div className="space-y-4">
            {/* Timeline Bar */}
            {segments.length > 0 ? (
              <div
                className="flex h-16 rounded-lg overflow-hidden border border-gray-200 dark:border-gray-700"
                role="progressbar"
                aria-label="Regime timeline visualization"
              >
                {segments.map((segment, index) => (
                  <button
                    key={index}
                    className="relative transition-all duration-200 hover:opacity-80 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:z-10"
                    style={{
                      width: `${segment.widthPercent}%`,
                      backgroundColor: getRegimeColor(segment.regime),
                    }}
                    onClick={() => handleSegmentClick(segment)}
                    aria-label={`${getRegimeDisplayName(segment.regime)} for ${formatDuration(segment.duration)}`}
                    title={`${getRegimeDisplayName(segment.regime)}\n${formatDuration(segment.duration)}`}
                  >
                    {segment.widthPercent > 10 && (
                      <span className="absolute inset-0 flex items-center justify-center text-white text-xs font-medium drop-shadow-md">
                        {formatDuration(segment.duration)}
                      </span>
                    )}
                  </button>
                ))}
              </div>
            ) : (
              <div className="h-16 flex items-center justify-center bg-gray-100 dark:bg-gray-900 rounded-lg">
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  No regime history available
                </p>
              </div>
            )}

            {/* Legend */}
            <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
              {Array.from(new Set(segments.map((s) => s.regime))).map(
                (regime) => (
                  <div
                    key={regime}
                    className="flex items-center space-x-2 text-sm"
                  >
                    <div
                      className="w-4 h-4 rounded"
                      style={{ backgroundColor: getRegimeColor(regime) }}
                      aria-hidden="true"
                    />
                    <span className="text-gray-700 dark:text-gray-300">
                      {getRegimeDisplayName(regime)}
                    </span>
                  </div>
                )
              )}
            </div>

            {/* Recent Transitions Table */}
            <div className="mt-6">
              <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
                Recent Transitions
              </h4>
              <div className="overflow-hidden rounded-lg border border-gray-200 dark:border-gray-700">
                <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                  <thead className="bg-gray-50 dark:bg-gray-900">
                    <tr>
                      <th
                        scope="col"
                        className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase"
                      >
                        Regime
                      </th>
                      <th
                        scope="col"
                        className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase"
                      >
                        Start Time
                      </th>
                      <th
                        scope="col"
                        className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase"
                      >
                        Duration
                      </th>
                      <th
                        scope="col"
                        className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase"
                      >
                        Confidence
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                    {segments.slice(0, 10).map((segment, index) => (
                      <tr
                        key={index}
                        className="hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer transition-colors"
                        onClick={() => handleSegmentClick(segment)}
                      >
                        <td className="px-4 py-3 whitespace-nowrap">
                          <div className="flex items-center space-x-2">
                            <div
                              className="w-3 h-3 rounded-full"
                              style={{
                                backgroundColor: getRegimeColor(segment.regime),
                              }}
                              aria-hidden="true"
                            />
                            <span className="text-sm font-medium text-gray-900 dark:text-white">
                              {getRegimeDisplayName(segment.regime)}
                            </span>
                          </div>
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600 dark:text-gray-400">
                          {formatDateTime(segment.startTime, timeframe)}
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap text-right text-sm font-mono text-gray-900 dark:text-white">
                          {formatDuration(segment.duration)}
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap text-right text-sm font-mono text-gray-900 dark:text-white">
                          {(segment.confidence * 100).toFixed(0)}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </CardBody>
      </Card>

      {/* Segment Details Modal */}
      {selectedSegment && (
        <Modal
          isOpen={true}
          onClose={closeModal}
          title="Regime Details"
          size="md"
        >
          <div className="space-y-4">
            <div className="flex items-center space-x-3">
              <div
                className="w-8 h-8 rounded-lg"
                style={{
                  backgroundColor: getRegimeColor(selectedSegment.regime),
                }}
                aria-hidden="true"
              />
              <div>
                <h4 className="text-xl font-bold text-gray-900 dark:text-white">
                  {getRegimeDisplayName(selectedSegment.regime)}
                </h4>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Confidence: {(selectedSegment.confidence * 100).toFixed(1)}%
                </p>
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-gray-600 dark:text-gray-400">
                  Start Time:
                </span>
                <span className="font-mono text-gray-900 dark:text-white">
                  {new Date(selectedSegment.startTime).toLocaleString()}
                </span>
              </div>
              {selectedSegment.endTime && (
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600 dark:text-gray-400">
                    End Time:
                  </span>
                  <span className="font-mono text-gray-900 dark:text-white">
                    {new Date(selectedSegment.endTime).toLocaleString()}
                  </span>
                </div>
              )}
              <div className="flex justify-between text-sm">
                <span className="text-gray-600 dark:text-gray-400">
                  Duration:
                </span>
                <span className="font-mono text-gray-900 dark:text-white">
                  {formatDuration(selectedSegment.duration)}
                </span>
              </div>
            </div>

            <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
              <div className="flex items-start space-x-2 text-sm text-gray-600 dark:text-gray-400">
                <Info size={16} className="mt-0.5 flex-shrink-0" />
                <p>
                  This regime was active from{' '}
                  {new Date(selectedSegment.startTime).toLocaleString()} for a
                  total of {formatDuration(selectedSegment.duration)}.
                </p>
              </div>
            </div>
          </div>
        </Modal>
      )}
    </>
  );
};
