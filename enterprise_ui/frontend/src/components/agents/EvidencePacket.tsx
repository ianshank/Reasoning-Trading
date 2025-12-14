/**
 * Evidence Packet Component
 *
 * Displays raw evidence data from analysts with collapsible sections,
 * data tables, and source tracking.
 */

import React, { useState, useMemo } from 'react';
import { Card, CardHeader, CardBody } from '../ui/card';
import { Badge } from '../ui/badge';
import { Table } from '../ui/table';
import type { EvidenceItem } from './hooks/useAgentSignals';

/**
 * Props for EvidencePacket component
 */
export interface EvidencePacketProps {
  /**
   * Evidence items to display
   */
  evidence: EvidenceItem[];

  /**
   * Filter by specific source (optional)
   */
  source?: string;

  /**
   * Custom className
   */
  className?: string;
}

/**
 * Get source icon
 */
const getSourceIcon = (source: string): string => {
  const lowerSource = source.toLowerCase();
  if (lowerSource.includes('market') || lowerSource.includes('price')) {
    return 'M13 7h8m0 0v8m0-8l-8 8-4-4-6 6';
  }
  if (lowerSource.includes('news')) {
    return 'M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z';
  }
  if (lowerSource.includes('social')) {
    return 'M17 8h2a2 2 0 012 2v6a2 2 0 01-2 2h-2v4l-4-4H9a1.994 1.994 0 01-1.414-.586m0 0L11 14h4a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2v4l.586-.586z';
  }
  if (lowerSource.includes('fundamental') || lowerSource.includes('financial')) {
    return 'M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z';
  }
  if (lowerSource.includes('macro') || lowerSource.includes('economic')) {
    return 'M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z';
  }
  return 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z';
};

/**
 * Get relevance badge variant
 */
const getRelevanceBadgeVariant = (score: number): 'success' | 'warning' | 'default' => {
  if (score >= 0.7) return 'success';
  if (score >= 0.4) return 'warning';
  return 'default';
};

/**
 * Format timestamp
 */
const formatTimestamp = (timestamp: string): string => {
  const date = new Date(timestamp);
  return date.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
};

/**
 * Raw evidence viewer component
 */
export const EvidencePacket: React.FC<EvidencePacketProps> = ({
  evidence,
  source,
  className = '',
}) => {
  const [expandedSources, setExpandedSources] = useState<Set<string>>(new Set());

  const filteredEvidence = useMemo(() => {
    if (!source) return evidence;
    return evidence.filter((item) => item.source === source);
  }, [evidence, source]);

  const groupedEvidence = useMemo(() => {
    const groups = new Map<string, EvidenceItem[]>();

    filteredEvidence.forEach((item) => {
      const existing = groups.get(item.source) || [];
      existing.push(item);
      groups.set(item.source, existing);
    });

    // Sort each group by relevance score
    groups.forEach((items, key) => {
      items.sort((a, b) => b.relevance_score - a.relevance_score);
      groups.set(key, items);
    });

    return Array.from(groups.entries()).sort(
      ([, a], [, b]) => b[0].relevance_score - a[0].relevance_score
    );
  }, [filteredEvidence]);

  const toggleSource = (sourceName: string) => {
    setExpandedSources((prev) => {
      const next = new Set(prev);
      if (next.has(sourceName)) {
        next.delete(sourceName);
      } else {
        next.add(sourceName);
      }
      return next;
    });
  };

  const formatDataValue = (value: unknown): string => {
    if (value === null || value === undefined) return 'N/A';
    if (typeof value === 'number') return value.toFixed(4);
    if (typeof value === 'boolean') return value ? 'Yes' : 'No';
    if (typeof value === 'object') return JSON.stringify(value);
    return String(value);
  };

  if (filteredEvidence.length === 0) {
    return (
      <Card className={`bg-white dark:bg-gray-800 ${className}`}>
        <CardBody>
          <div className="text-center py-8">
            <p className="text-gray-500 dark:text-gray-400">No evidence available</p>
          </div>
        </CardBody>
      </Card>
    );
  }

  return (
    <div className={className}>
      <div className="space-y-4">
        {groupedEvidence.map(([sourceName, items]) => {
          const isExpanded = expandedSources.has(sourceName);
          const avgRelevance =
            items.reduce((sum, item) => sum + item.relevance_score, 0) / items.length;

          return (
            <Card key={sourceName} className="bg-white dark:bg-gray-800">
              <CardHeader className="cursor-pointer" onClick={() => toggleSource(sourceName)}>
                <div className="flex items-center justify-between">
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
                        <path d={getSourceIcon(sourceName)} />
                      </svg>
                    </div>
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                        {sourceName}
                      </h3>
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                        {items.length} evidence {items.length === 1 ? 'item' : 'items'}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <Badge variant={getRelevanceBadgeVariant(avgRelevance)} size="sm">
                      Avg Relevance: {(avgRelevance * 100).toFixed(0)}%
                    </Badge>
                    <svg
                      className={`w-5 h-5 text-gray-500 transition-transform ${
                        isExpanded ? 'rotate-180' : ''
                      }`}
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                      aria-hidden="true"
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                  </div>
                </div>
              </CardHeader>

              {isExpanded && (
                <CardBody>
                  <div className="space-y-4">
                    {items.map((item) => (
                      <div
                        key={item.id}
                        className="p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700"
                      >
                        <div className="flex items-start justify-between mb-3">
                          <div className="flex items-center gap-2">
                            <Badge variant="default" size="sm">
                              {item.id}
                            </Badge>
                            <span className="text-xs text-gray-500 dark:text-gray-400">
                              {formatTimestamp(item.timestamp)}
                            </span>
                          </div>
                          <Badge
                            variant={getRelevanceBadgeVariant(item.relevance_score)}
                            size="sm"
                          >
                            Relevance: {(item.relevance_score * 100).toFixed(0)}%
                          </Badge>
                        </div>

                        {/* Data Table */}
                        <div className="overflow-x-auto">
                          <table className="w-full text-sm">
                            <thead>
                              <tr className="border-b border-gray-200 dark:border-gray-700">
                                <th className="text-left py-2 px-3 font-medium text-gray-700 dark:text-gray-300">
                                  Field
                                </th>
                                <th className="text-left py-2 px-3 font-medium text-gray-700 dark:text-gray-300">
                                  Value
                                </th>
                              </tr>
                            </thead>
                            <tbody>
                              {Object.entries(item.data).map(([key, value]) => (
                                <tr
                                  key={key}
                                  className="border-b border-gray-100 dark:border-gray-800 last:border-0"
                                >
                                  <td className="py-2 px-3 text-gray-600 dark:text-gray-400 font-mono text-xs">
                                    {key}
                                  </td>
                                  <td className="py-2 px-3 text-gray-900 dark:text-white break-all">
                                    {formatDataValue(value)}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardBody>
              )}
            </Card>
          );
        })}
      </div>

      {/* Summary Stats */}
      <Card className="mt-6 bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800">
        <CardBody>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center">
              <div className="text-sm text-gray-600 dark:text-gray-400">Total Items</div>
              <div className="text-2xl font-bold text-gray-900 dark:text-white">
                {filteredEvidence.length}
              </div>
            </div>
            <div className="text-center">
              <div className="text-sm text-gray-600 dark:text-gray-400">Sources</div>
              <div className="text-2xl font-bold text-gray-900 dark:text-white">
                {groupedEvidence.length}
              </div>
            </div>
            <div className="text-center">
              <div className="text-sm text-gray-600 dark:text-gray-400">Avg Relevance</div>
              <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                {(
                  (filteredEvidence.reduce((sum, item) => sum + item.relevance_score, 0) /
                    filteredEvidence.length) *
                  100
                ).toFixed(0)}
                %
              </div>
            </div>
            <div className="text-center">
              <div className="text-sm text-gray-600 dark:text-gray-400">Last Updated</div>
              <div className="text-sm font-medium text-gray-900 dark:text-white">
                {formatTimestamp(
                  filteredEvidence.reduce((latest, item) =>
                    item.timestamp > latest ? item.timestamp : latest
                  , filteredEvidence[0].timestamp)
                )}
              </div>
            </div>
          </div>
        </CardBody>
      </Card>
    </div>
  );
};
