/**
 * Market Regime Analysis Types
 *
 * TypeScript definitions for regime detection and visualization
 * Based on Python models from:
 * - src/reasoning_trading/regime/detector.py
 * - src/reasoning_trading/regime/hmm.py
 * - src/reasoning_trading/regime/features.py
 */

/**
 * Regime states from HMM model
 */
export enum RegimeState {
  BULL = 'bull',
  BEAR = 'bear',
  HIGH_VOLATILITY = 'high_volatility',
  LOW_VOLATILITY = 'low_volatility',
  NEUTRAL = 'neutral',
}

/**
 * Technical indicator contribution to regime detection
 */
export interface IndicatorContribution {
  name: string;
  value: number;
  weight: number;
  impact: number;
}

/**
 * Regime classification result
 */
export interface RegimeClassification {
  regime: string;
  confidence: number;
  regime_probabilities: Record<string, number>;
  hmm_regime: string | null;
  hmm_confidence: number;
  technical_regime: string | null;
  technical_confidence: number;
  timestamp: string;
  symbol: string;
}

/**
 * Regime history entry
 */
export interface RegimeHistoryEntry {
  regime: string;
  confidence: number;
  startTime: string;
  endTime?: string;
  duration: number;
}

/**
 * Regime history aggregation
 */
export interface RegimeHistory {
  classifications: RegimeClassification[];
  regime_durations: Record<string, number>;
  current_regime: string;
  current_regime_start: string;
}

/**
 * Transition matrix for HMM
 */
export interface TransitionMatrix {
  matrix: number[][];
  state_names: string[];
}

/**
 * HMM state data
 */
export interface HMMState {
  transition_matrix: TransitionMatrix;
  state_probabilities: Record<string, number>;
  current_state: string;
  emission_probabilities: Record<string, number[]>;
}

/**
 * Regime frequency data for heatmap
 */
export interface RegimeFrequencyData {
  regime: string;
  timeSlot: string;
  frequency: number;
  count: number;
}

/**
 * Regime to strategy mapping
 */
export interface RegimeStrategyMapping {
  regime: string;
  recommended_strategy: string;
  confidence: number;
  historical_performance: {
    total_trades: number;
    win_rate: number;
    avg_return: number;
    sharpe_ratio: number;
  };
}

/**
 * Regime change alert
 */
export interface RegimeAlert {
  id: string;
  timestamp: string;
  from_regime: string;
  to_regime: string;
  confidence: number;
  severity: 'low' | 'medium' | 'high';
  message: string;
  acknowledged: boolean;
}

/**
 * Alert configuration
 */
export interface RegimeAlertConfig {
  enabled: boolean;
  min_confidence: number;
  notify_on_regimes: string[];
  notification_channels: ('ui' | 'email' | 'webhook')[];
}

/**
 * Regime statistics
 */
export interface RegimeStatistics {
  current_regime: string;
  regime_start: string;
  time_in_current_regime: number;
  total_classifications: number;
  regime_frequency: Record<string, number>;
  regime_durations: Record<string, number>;
  average_confidence: number;
}

/**
 * Type guard for RegimeState
 */
export function isRegimeState(value: string): value is RegimeState {
  return Object.values(RegimeState).includes(value as RegimeState);
}

/**
 * Get display name for regime
 */
export function getRegimeDisplayName(regime: string): string {
  const names: Record<string, string> = {
    bull: 'Bullish Trend',
    bear: 'Bearish Trend',
    high_volatility: 'High Volatility',
    low_volatility: 'Low Volatility',
    neutral: 'Neutral',
  };
  return names[regime] || regime;
}

/**
 * Get color for regime
 */
export function getRegimeColor(regime: string): string {
  const colors: Record<string, string> = {
    bull: '#10b981', // green
    bear: '#ef4444', // red
    high_volatility: '#f59e0b', // orange
    low_volatility: '#3b82f6', // blue
    neutral: '#6b7280', // gray
  };
  return colors[regime] || '#6b7280';
}
