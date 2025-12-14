/**
 * Risk Metrics Hook
 *
 * Fetches and monitors risk metrics with threshold alerts
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import type { RiskMetrics } from '../../../types/portfolio';
import { getRiskLevel } from '../../../types/portfolio';
import type { RiskAlert } from '../RiskAlerts';
import { AlertSeverity } from '../RiskAlerts';

interface UseRiskMetricsResult {
  metrics: RiskMetrics | null;
  alerts: RiskAlert[];
  isLoading: boolean;
  error: Error | null;
  refresh: () => Promise<void>;
}

interface RiskThresholds {
  var95Threshold: number;
  var99Threshold: number;
  maxDrawdownThreshold: number;
  currentDrawdownThreshold: number;
  marginUtilizationWarning: number;
  marginUtilizationCritical: number;
  concentrationWarning: number;
  concentrationCritical: number;
}

const DEFAULT_THRESHOLDS: RiskThresholds = {
  var95Threshold: 10000,
  var99Threshold: 15000,
  maxDrawdownThreshold: 0.15,
  currentDrawdownThreshold: 0.1,
  marginUtilizationWarning: 0.7,
  marginUtilizationCritical: 0.9,
  concentrationWarning: 0.25,
  concentrationCritical: 0.4,
};

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export const useRiskMetrics = (
  accountId?: string,
  thresholds: Partial<RiskThresholds> = {}
): UseRiskMetricsResult => {
  const [metrics, setMetrics] = useState<RiskMetrics | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<Error | null>(null);

  const mergedThresholds = useMemo(
    () => ({ ...DEFAULT_THRESHOLDS, ...thresholds }),
    [thresholds]
  );

  const fetchRiskMetrics = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);

      const endpoint = accountId
        ? `${API_BASE_URL}/api/v1/risk/metrics/${accountId}`
        : `${API_BASE_URL}/api/v1/risk/metrics`;

      const response = await fetch(endpoint, {
        headers: {
          'Content-Type': 'application/json',
          // Add authentication headers as needed
          // 'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch risk metrics: ${response.statusText}`);
      }

      const data: RiskMetrics = await response.json();
      setMetrics(data);
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Unknown error');
      setError(error);
      console.error('Error fetching risk metrics:', error);
    } finally {
      setIsLoading(false);
    }
  }, [accountId]);

  const generateAlerts = useCallback(
    (metrics: RiskMetrics): RiskAlert[] => {
      const alerts: RiskAlert[] = [];
      const now = new Date().toISOString();

      // VaR alerts
      if (metrics.daily_var_95 && metrics.daily_var_95 > mergedThresholds.var95Threshold) {
        alerts.push({
          id: `var95-${Date.now()}`,
          severity: AlertSeverity.WARNING,
          title: 'High Value at Risk (95%)',
          message: `Daily VaR (95%) of $${Math.abs(metrics.daily_var_95).toLocaleString()} exceeds threshold of $${mergedThresholds.var95Threshold.toLocaleString()}`,
          timestamp: now,
          dismissible: true,
        });
      }

      if (metrics.daily_var_99 && metrics.daily_var_99 > mergedThresholds.var99Threshold) {
        alerts.push({
          id: `var99-${Date.now()}`,
          severity: AlertSeverity.ERROR,
          title: 'Critical Value at Risk (99%)',
          message: `Daily VaR (99%) of $${Math.abs(metrics.daily_var_99).toLocaleString()} exceeds threshold of $${mergedThresholds.var99Threshold.toLocaleString()}`,
          timestamp: now,
          dismissible: true,
          actionLabel: 'Review Positions',
          actionData: { action: 'review_positions' },
        });
      }

      // Drawdown alerts
      if (metrics.max_drawdown > mergedThresholds.maxDrawdownThreshold) {
        alerts.push({
          id: `maxdd-${Date.now()}`,
          severity: AlertSeverity.ERROR,
          title: 'Maximum Drawdown Exceeded',
          message: `Maximum drawdown of ${(metrics.max_drawdown * 100).toFixed(2)}% exceeds threshold of ${(mergedThresholds.maxDrawdownThreshold * 100).toFixed(2)}%`,
          timestamp: now,
          dismissible: true,
        });
      }

      if (metrics.current_drawdown > mergedThresholds.currentDrawdownThreshold) {
        const severity =
          metrics.current_drawdown > mergedThresholds.maxDrawdownThreshold
            ? AlertSeverity.CRITICAL
            : AlertSeverity.WARNING;

        alerts.push({
          id: `currentdd-${Date.now()}`,
          severity,
          title: 'Current Drawdown Alert',
          message: `Current drawdown of ${(metrics.current_drawdown * 100).toFixed(2)}% requires attention`,
          timestamp: now,
          dismissible: false,
          actionLabel: 'Review Strategy',
          actionData: { action: 'review_strategy' },
        });
      }

      // Margin utilization alerts
      if (metrics.margin_utilization >= mergedThresholds.marginUtilizationCritical) {
        alerts.push({
          id: `margin-critical-${Date.now()}`,
          severity: AlertSeverity.CRITICAL,
          title: 'Critical Margin Utilization',
          message: `Margin utilization at ${(metrics.margin_utilization * 100).toFixed(1)}% - immediate action required`,
          timestamp: now,
          dismissible: false,
          actionLabel: 'Reduce Positions',
          actionData: { action: 'reduce_positions' },
        });
      } else if (
        metrics.margin_utilization >= mergedThresholds.marginUtilizationWarning
      ) {
        alerts.push({
          id: `margin-warning-${Date.now()}`,
          severity: AlertSeverity.WARNING,
          title: 'High Margin Utilization',
          message: `Margin utilization at ${(metrics.margin_utilization * 100).toFixed(1)}% - consider reducing exposure`,
          timestamp: now,
          dismissible: true,
        });
      }

      // Concentration alerts
      if (metrics.largest_position_pct >= mergedThresholds.concentrationCritical) {
        alerts.push({
          id: `concentration-critical-${Date.now()}`,
          severity: AlertSeverity.CRITICAL,
          title: 'Critical Position Concentration',
          message: `Largest position represents ${(metrics.largest_position_pct * 100).toFixed(1)}% of portfolio - diversify immediately`,
          timestamp: now,
          dismissible: false,
          actionLabel: 'Rebalance Portfolio',
          actionData: { action: 'rebalance' },
        });
      } else if (metrics.largest_position_pct >= mergedThresholds.concentrationWarning) {
        alerts.push({
          id: `concentration-warning-${Date.now()}`,
          severity: AlertSeverity.WARNING,
          title: 'High Position Concentration',
          message: `Largest position represents ${(metrics.largest_position_pct * 100).toFixed(1)}% of portfolio - consider rebalancing`,
          timestamp: now,
          dismissible: true,
        });
      }

      // Risk-adjusted returns alerts
      if (metrics.sharpe_ratio !== null && metrics.sharpe_ratio < 0.5) {
        alerts.push({
          id: `sharpe-${Date.now()}`,
          severity: AlertSeverity.INFO,
          title: 'Low Sharpe Ratio',
          message: `Sharpe ratio of ${metrics.sharpe_ratio.toFixed(2)} indicates suboptimal risk-adjusted returns`,
          timestamp: now,
          dismissible: true,
        });
      }

      // Portfolio volatility
      if (metrics.portfolio_volatility > 0.3) {
        alerts.push({
          id: `volatility-${Date.now()}`,
          severity: AlertSeverity.WARNING,
          title: 'High Portfolio Volatility',
          message: `Annualized volatility of ${(metrics.portfolio_volatility * 100).toFixed(1)}% is elevated`,
          timestamp: now,
          dismissible: true,
        });
      }

      return alerts;
    },
    [mergedThresholds]
  );

  const alerts = useMemo(() => {
    if (!metrics) return [];
    return generateAlerts(metrics);
  }, [metrics, generateAlerts]);

  const refresh = useCallback(async () => {
    await fetchRiskMetrics();
  }, [fetchRiskMetrics]);

  useEffect(() => {
    // Initial fetch
    fetchRiskMetrics();

    // Set up polling for risk metrics (every 30 seconds)
    const intervalId = setInterval(() => {
      fetchRiskMetrics();
    }, 30000);

    // Cleanup
    return () => {
      clearInterval(intervalId);
    };
  }, [fetchRiskMetrics]);

  return {
    metrics,
    alerts,
    isLoading,
    error,
    refresh,
  };
};
