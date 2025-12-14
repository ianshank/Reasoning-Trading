/**
 * Regime Analysis Page - Example Implementation
 *
 * This example demonstrates how to use all regime components together
 * in a comprehensive market regime analysis dashboard.
 */

import React from 'react';
import {
  CurrentRegimeCard,
  RegimeProbabilities,
  RegimeTimeline,
  RegimeHeatmap,
  IndicatorContribution,
  HMMStateView,
  RegimeStrategyMapping,
  RegimeAlerts,
  useRegime,
} from './index';
import type {
  IndicatorContribution as IndicatorContributionType,
  RegimeHistoryEntry,
  RegimeFrequencyData,
  HMMState,
  RegimeStrategyMapping as RegimeStrategyMappingType,
} from '../../types/regime';

export const RegimeAnalysisPageExample: React.FC = () => {
  // Use the regime hook to fetch data
  const {
    current,
    history,
    statistics,
    alerts,
    isLoading,
    error,
    refresh,
    acknowledgeAlert,
  } = useRegime({
    symbol: 'SPY',
    autoRefresh: true,
    refreshInterval: 30000,
    enableWebSocket: true,
  });

  // Mock data for demonstration (in production, this comes from API)
  const mockIndicators: IndicatorContributionType[] = [
    { name: 'ADX', value: 35.5, weight: 0.3, impact: 0.25 },
    { name: 'RSI', value: 68.2, weight: 0.2, impact: 0.15 },
    { name: 'ATR', value: 2.5, weight: 0.25, impact: 0.18 },
    { name: 'Bollinger Width', value: 0.045, weight: 0.15, impact: 0.12 },
    { name: 'Volatility', value: 0.025, weight: 0.1, impact: -0.08 },
  ];

  const mockHistoryEntries: RegimeHistoryEntry[] = [
    {
      regime: 'bull',
      confidence: 0.85,
      startTime: '2024-01-15T09:30:00Z',
      endTime: '2024-01-15T14:30:00Z',
      duration: 18000,
    },
    {
      regime: 'neutral',
      confidence: 0.65,
      startTime: '2024-01-15T14:30:00Z',
      endTime: '2024-01-15T15:45:00Z',
      duration: 4500,
    },
    {
      regime: 'bear',
      confidence: 0.75,
      startTime: '2024-01-15T15:45:00Z',
      duration: 3600,
    },
  ];

  const mockFrequencyData: RegimeFrequencyData[] = [
    // Bull regime frequencies by hour
    { regime: 'bull', timeSlot: '9', frequency: 0.45, count: 15 },
    { regime: 'bull', timeSlot: '10', frequency: 0.55, count: 20 },
    { regime: 'bull', timeSlot: '11', frequency: 0.35, count: 12 },
    { regime: 'bull', timeSlot: '12', frequency: 0.25, count: 8 },
    { regime: 'bull', timeSlot: '13', frequency: 0.30, count: 10 },
    { regime: 'bull', timeSlot: '14', frequency: 0.20, count: 7 },
    { regime: 'bull', timeSlot: '15', frequency: 0.15, count: 5 },

    // Bear regime frequencies
    { regime: 'bear', timeSlot: '9', frequency: 0.15, count: 5 },
    { regime: 'bear', timeSlot: '10', frequency: 0.10, count: 3 },
    { regime: 'bear', timeSlot: '11', frequency: 0.20, count: 7 },
    { regime: 'bear', timeSlot: '12', frequency: 0.30, count: 10 },
    { regime: 'bear', timeSlot: '13', frequency: 0.25, count: 8 },
    { regime: 'bear', timeSlot: '14', frequency: 0.35, count: 12 },
    { regime: 'bear', timeSlot: '15', frequency: 0.45, count: 15 },

    // Neutral regime frequencies
    { regime: 'neutral', timeSlot: '9', frequency: 0.40, count: 13 },
    { regime: 'neutral', timeSlot: '10', frequency: 0.35, count: 12 },
    { regime: 'neutral', timeSlot: '11', frequency: 0.45, count: 15 },
    { regime: 'neutral', timeSlot: '12', frequency: 0.45, count: 15 },
    { regime: 'neutral', timeSlot: '13', frequency: 0.45, count: 15 },
    { regime: 'neutral', timeSlot: '14', frequency: 0.45, count: 15 },
    { regime: 'neutral', timeSlot: '15', frequency: 0.40, count: 13 },
  ];

  const mockHMMState: HMMState = {
    transition_matrix: {
      matrix: [
        [0.7, 0.1, 0.05, 0.1, 0.05],
        [0.1, 0.7, 0.1, 0.05, 0.05],
        [0.05, 0.1, 0.7, 0.1, 0.05],
        [0.1, 0.05, 0.1, 0.7, 0.05],
        [0.05, 0.05, 0.05, 0.05, 0.8],
      ],
      state_names: ['bull', 'bear', 'high_volatility', 'low_volatility', 'neutral'],
    },
    state_probabilities: {
      bull: 0.45,
      bear: 0.15,
      high_volatility: 0.10,
      low_volatility: 0.05,
      neutral: 0.25,
    },
    current_state: 'bull',
    emission_probabilities: {
      bull: [0.02, 0.05, 0.08, 0.10, 0.10, 0.08, 0.17, 0.22, 0.18],
      bear: [0.18, 0.22, 0.17, 0.08, 0.10, 0.10, 0.08, 0.05, 0.02],
      high_volatility: [0.20, 0.15, 0.10, 0.05, 0.05, 0.05, 0.10, 0.15, 0.15],
      low_volatility: [0.02, 0.05, 0.10, 0.18, 0.30, 0.18, 0.10, 0.05, 0.02],
      neutral: [0.08, 0.10, 0.12, 0.12, 0.16, 0.12, 0.12, 0.10, 0.08],
    },
  };

  const mockStrategyMapping: RegimeStrategyMappingType[] = [
    {
      regime: 'bull',
      recommended_strategy: 'Trend Following',
      confidence: 0.85,
      historical_performance: {
        total_trades: 150,
        win_rate: 0.62,
        avg_return: 0.025,
        sharpe_ratio: 1.85,
      },
    },
    {
      regime: 'bear',
      recommended_strategy: 'Short Selling',
      confidence: 0.78,
      historical_performance: {
        total_trades: 120,
        win_rate: 0.58,
        avg_return: 0.018,
        sharpe_ratio: 1.45,
      },
    },
    {
      regime: 'high_volatility',
      recommended_strategy: 'Mean Reversion',
      confidence: 0.72,
      historical_performance: {
        total_trades: 200,
        win_rate: 0.55,
        avg_return: 0.012,
        sharpe_ratio: 1.20,
      },
    },
    {
      regime: 'low_volatility',
      recommended_strategy: 'Range Trading',
      confidence: 0.68,
      historical_performance: {
        total_trades: 180,
        win_rate: 0.60,
        avg_return: 0.008,
        sharpe_ratio: 0.95,
      },
    },
    {
      regime: 'neutral',
      recommended_strategy: 'Market Making',
      confidence: 0.65,
      historical_performance: {
        total_trades: 250,
        win_rate: 0.52,
        avg_return: 0.005,
        sharpe_ratio: 0.75,
      },
    },
  ];

  if (error) {
    return (
      <div className="p-8 text-center">
        <div className="text-red-600 dark:text-red-400 mb-4">
          Error loading regime data: {error.message}
        </div>
        <button
          onClick={refresh}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6 bg-gray-50 dark:bg-gray-900 min-h-screen">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
            Market Regime Analysis
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            Real-time regime detection and strategy recommendations
          </p>
        </div>

        {/* Top Row - Current Regime and Alerts */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
          <div className="lg:col-span-2">
            <CurrentRegimeCard
              regime={current?.regime || 'neutral'}
              confidence={current?.confidence || 0.5}
              since={statistics?.regime_start || new Date().toISOString()}
              indicators={mockIndicators}
            />
          </div>
          <div>
            <RegimeAlerts
              alerts={alerts}
              onAcknowledge={acknowledgeAlert}
              onConfigure={(config) => {
                console.log('Alert config updated:', config);
              }}
            />
          </div>
        </div>

        {/* Probability and Timeline Row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          <RegimeProbabilities
            probabilities={current?.regime_probabilities || {}}
            currentRegime={current?.regime || 'neutral'}
            historicalProbabilities={{
              bull: 0.30,
              bear: 0.20,
              high_volatility: 0.15,
              low_volatility: 0.10,
              neutral: 0.25,
            }}
          />
          <RegimeTimeline
            history={mockHistoryEntries}
            timeframe="day"
          />
        </div>

        {/* Indicator Contribution */}
        <div className="mb-6">
          <IndicatorContribution contributions={mockIndicators} />
        </div>

        {/* HMM State View */}
        <div className="mb-6">
          <HMMStateView
            hmmState={mockHMMState}
            transitionMatrix={mockHMMState.transition_matrix.matrix}
          />
        </div>

        {/* Strategy Mapping */}
        <div className="mb-6">
          <RegimeStrategyMapping
            mapping={mockStrategyMapping}
            currentRegime={current?.regime || 'neutral'}
          />
        </div>

        {/* Heatmap */}
        <div className="mb-6">
          <RegimeHeatmap
            frequencyData={mockFrequencyData}
            groupBy="hour"
          />
        </div>

        {/* Footer Stats */}
        {statistics && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="p-4 bg-white dark:bg-gray-800 rounded-lg shadow">
              <div className="text-sm text-gray-500 dark:text-gray-400 mb-1">
                Current Regime
              </div>
              <div className="text-lg font-bold text-gray-900 dark:text-white">
                {statistics.current_regime}
              </div>
            </div>
            <div className="p-4 bg-white dark:bg-gray-800 rounded-lg shadow">
              <div className="text-sm text-gray-500 dark:text-gray-400 mb-1">
                Time in Regime
              </div>
              <div className="text-lg font-bold text-gray-900 dark:text-white">
                {Math.floor(statistics.time_in_current_regime / 3600)}h
              </div>
            </div>
            <div className="p-4 bg-white dark:bg-gray-800 rounded-lg shadow">
              <div className="text-sm text-gray-500 dark:text-gray-400 mb-1">
                Total Classifications
              </div>
              <div className="text-lg font-bold text-gray-900 dark:text-white">
                {statistics.total_classifications}
              </div>
            </div>
            <div className="p-4 bg-white dark:bg-gray-800 rounded-lg shadow">
              <div className="text-sm text-gray-500 dark:text-gray-400 mb-1">
                Avg Confidence
              </div>
              <div className="text-lg font-bold text-gray-900 dark:text-white">
                {(statistics.average_confidence * 100).toFixed(0)}%
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default RegimeAnalysisPageExample;
