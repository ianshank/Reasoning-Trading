/**
 * Regime Heatmap Component
 *
 * Displays regime frequency patterns by time
 * - Heatmap showing regime occurrence by time of day/week
 * - X-axis: time slots (hour of day or day of week)
 * - Y-axis: regime types
 * - Color intensity by frequency
 */

import React, { useMemo } from 'react';
import { Card, CardHeader, CardBody } from '../ui/Card';
import type { RegimeFrequencyData } from '../../types/regime';
import { getRegimeDisplayName, getRegimeColor } from '../../types/regime';

export interface RegimeHeatmapProps {
  frequencyData: RegimeFrequencyData[];
  groupBy: 'hour' | 'day';
  className?: string;
}

interface HeatmapCell {
  regime: string;
  timeSlot: string;
  frequency: number;
  count: number;
  color: string;
}

/**
 * Get color intensity based on frequency
 */
function getColorIntensity(
  baseColor: string,
  frequency: number
): string {
  // Convert hex to RGB
  const hex = baseColor.replace('#', '');
  const r = parseInt(hex.substring(0, 2), 16);
  const g = parseInt(hex.substring(2, 4), 16);
  const b = parseInt(hex.substring(4, 6), 16);

  // Apply opacity based on frequency
  const opacity = 0.2 + frequency * 0.8;

  return `rgba(${r}, ${g}, ${b}, ${opacity})`;
}

/**
 * Get time slot label
 */
function getTimeSlotLabel(slot: string, groupBy: 'hour' | 'day'): string {
  if (groupBy === 'hour') {
    const hour = parseInt(slot);
    const period = hour >= 12 ? 'PM' : 'AM';
    const displayHour = hour % 12 || 12;
    return `${displayHour}${period}`;
  } else {
    const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    return days[parseInt(slot)] || slot;
  }
}

export const RegimeHeatmap: React.FC<RegimeHeatmapProps> = ({
  frequencyData,
  groupBy,
  className = '',
}) => {
  const { heatmapData, timeSlots, regimes, maxFrequency } = useMemo(() => {
    // Extract unique time slots and regimes
    const uniqueTimeSlots = Array.from(
      new Set(frequencyData.map((d) => d.timeSlot))
    ).sort();

    const uniqueRegimes = Array.from(
      new Set(frequencyData.map((d) => d.regime))
    );

    // Find maximum frequency for normalization
    const max = Math.max(...frequencyData.map((d) => d.frequency), 1);

    // Build heatmap data structure
    const data: HeatmapCell[][] = uniqueRegimes.map((regime) => {
      return uniqueTimeSlots.map((timeSlot) => {
        const dataPoint = frequencyData.find(
          (d) => d.regime === regime && d.timeSlot === timeSlot
        );

        return {
          regime,
          timeSlot,
          frequency: dataPoint ? dataPoint.frequency : 0,
          count: dataPoint ? dataPoint.count : 0,
          color: getRegimeColor(regime),
        };
      });
    });

    return {
      heatmapData: data,
      timeSlots: uniqueTimeSlots,
      regimes: uniqueRegimes,
      maxFrequency: max,
    };
  }, [frequencyData]);

  return (
    <Card
      className={`bg-white dark:bg-gray-800 ${className}`}
      role="article"
      aria-label="Regime Frequency Heatmap"
    >
      <CardHeader>
        <div className="flex items-center justify-between w-full">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            Regime Frequency by {groupBy === 'hour' ? 'Hour' : 'Day'}
          </h3>
          <div className="flex items-center space-x-2 text-xs text-gray-500 dark:text-gray-400">
            <span>Low</span>
            <div className="flex space-x-1">
              {[0.2, 0.4, 0.6, 0.8, 1.0].map((intensity, idx) => (
                <div
                  key={idx}
                  className="w-4 h-4 rounded"
                  style={{
                    backgroundColor: `rgba(59, 130, 246, ${intensity})`,
                  }}
                  aria-hidden="true"
                />
              ))}
            </div>
            <span>High</span>
          </div>
        </div>
      </CardHeader>

      <CardBody>
        {heatmapData.length > 0 && timeSlots.length > 0 ? (
          <div className="overflow-x-auto">
            <div className="inline-block min-w-full align-middle">
              <table className="min-w-full border-collapse">
                <thead>
                  <tr>
                    <th
                      className="sticky left-0 z-10 bg-white dark:bg-gray-800 px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase border-b border-r border-gray-200 dark:border-gray-700"
                      scope="col"
                    >
                      Regime
                    </th>
                    {timeSlots.map((slot) => (
                      <th
                        key={slot}
                        className="px-2 py-2 text-center text-xs font-medium text-gray-500 dark:text-gray-400 border-b border-gray-200 dark:border-gray-700"
                        scope="col"
                      >
                        {getTimeSlotLabel(slot, groupBy)}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {heatmapData.map((row, rowIdx) => (
                    <tr key={regimes[rowIdx]}>
                      <td className="sticky left-0 z-10 bg-white dark:bg-gray-800 px-4 py-2 text-sm font-medium text-gray-900 dark:text-white border-r border-gray-200 dark:border-gray-700">
                        <div className="flex items-center space-x-2">
                          <div
                            className="w-3 h-3 rounded-full"
                            style={{
                              backgroundColor: getRegimeColor(regimes[rowIdx]),
                            }}
                            aria-hidden="true"
                          />
                          <span className="whitespace-nowrap">
                            {getRegimeDisplayName(regimes[rowIdx])}
                          </span>
                        </div>
                      </td>
                      {row.map((cell, cellIdx) => (
                        <td
                          key={cellIdx}
                          className="relative group"
                          role="gridcell"
                          aria-label={`${getRegimeDisplayName(cell.regime)} at ${getTimeSlotLabel(cell.timeSlot, groupBy)}: ${(cell.frequency * 100).toFixed(1)}%`}
                        >
                          <div
                            className="w-full h-12 border border-gray-200 dark:border-gray-700 transition-all hover:scale-105 hover:z-20 hover:shadow-lg cursor-pointer"
                            style={{
                              backgroundColor: getColorIntensity(
                                cell.color,
                                cell.frequency
                              ),
                            }}
                            title={`${getRegimeDisplayName(cell.regime)}\n${getTimeSlotLabel(cell.timeSlot, groupBy)}\nFrequency: ${(cell.frequency * 100).toFixed(1)}%\nCount: ${cell.count}`}
                          >
                            {cell.frequency > 0 && (
                              <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                                <span className="text-xs font-semibold text-gray-900 dark:text-white drop-shadow">
                                  {(cell.frequency * 100).toFixed(0)}%
                                </span>
                              </div>
                            )}
                          </div>
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : (
          <div className="h-64 flex items-center justify-center bg-gray-100 dark:bg-gray-900 rounded-lg">
            <p className="text-sm text-gray-500 dark:text-gray-400">
              No frequency data available
            </p>
          </div>
        )}

        {/* Summary Statistics */}
        {heatmapData.length > 0 && (
          <div className="mt-6 grid grid-cols-2 md:grid-cols-4 gap-4">
            {regimes.map((regime) => {
              const regimeData = frequencyData.filter((d) => d.regime === regime);
              const totalCount = regimeData.reduce((sum, d) => sum + d.count, 0);
              const avgFrequency =
                regimeData.reduce((sum, d) => sum + d.frequency, 0) /
                (regimeData.length || 1);

              return (
                <div
                  key={regime}
                  className="p-3 rounded-lg bg-gray-50 dark:bg-gray-900"
                >
                  <div className="flex items-center space-x-2 mb-1">
                    <div
                      className="w-3 h-3 rounded-full"
                      style={{ backgroundColor: getRegimeColor(regime) }}
                      aria-hidden="true"
                    />
                    <span className="text-xs font-medium text-gray-600 dark:text-gray-400">
                      {getRegimeDisplayName(regime)}
                    </span>
                  </div>
                  <div className="text-sm">
                    <span className="font-semibold text-gray-900 dark:text-white">
                      {totalCount}
                    </span>
                    <span className="text-gray-500 dark:text-gray-400 ml-1">
                      occurrences
                    </span>
                  </div>
                  <div className="text-xs text-gray-500 dark:text-gray-400">
                    Avg: {(avgFrequency * 100).toFixed(1)}%
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </CardBody>
    </Card>
  );
};
