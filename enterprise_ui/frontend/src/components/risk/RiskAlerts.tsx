/**
 * Risk Alerts Component
 *
 * Displays risk alerts with severity levels and actions
 */

import React from 'react';
import { Card } from '../ui/Card';
import { Button } from '../ui/Button';

export enum AlertSeverity {
  INFO = 'info',
  WARNING = 'warning',
  ERROR = 'error',
  CRITICAL = 'critical',
}

export interface RiskAlert {
  id: string;
  severity: AlertSeverity;
  title: string;
  message: string;
  timestamp: string;
  dismissible?: boolean;
  actionLabel?: string;
  actionData?: any;
}

interface RiskAlertsProps {
  alerts: RiskAlert[];
  onDismiss?: (alertId: string) => void;
  onAction?: (alertId: string, actionData?: any) => void;
}

export const RiskAlerts: React.FC<RiskAlertsProps> = ({
  alerts,
  onDismiss,
  onAction,
}) => {
  const getSeverityStyles = (severity: AlertSeverity) => {
    switch (severity) {
      case AlertSeverity.CRITICAL:
        return {
          container: 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800',
          icon: 'text-red-600 dark:text-red-400',
          title: 'text-red-900 dark:text-red-400',
          message: 'text-red-800 dark:text-red-300',
          badge: 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-400',
        };
      case AlertSeverity.ERROR:
        return {
          container:
            'bg-orange-50 dark:bg-orange-900/20 border-orange-200 dark:border-orange-800',
          icon: 'text-orange-600 dark:text-orange-400',
          title: 'text-orange-900 dark:text-orange-400',
          message: 'text-orange-800 dark:text-orange-300',
          badge:
            'bg-orange-100 text-orange-800 dark:bg-orange-900/40 dark:text-orange-400',
        };
      case AlertSeverity.WARNING:
        return {
          container:
            'bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-800',
          icon: 'text-yellow-600 dark:text-yellow-400',
          title: 'text-yellow-900 dark:text-yellow-400',
          message: 'text-yellow-800 dark:text-yellow-300',
          badge:
            'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-400',
        };
      case AlertSeverity.INFO:
      default:
        return {
          container:
            'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800',
          icon: 'text-blue-600 dark:text-blue-400',
          title: 'text-blue-900 dark:text-blue-400',
          message: 'text-blue-800 dark:text-blue-300',
          badge: 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-400',
        };
    }
  };

  const getSeverityIcon = (severity: AlertSeverity) => {
    switch (severity) {
      case AlertSeverity.CRITICAL:
      case AlertSeverity.ERROR:
        return (
          <svg
            className="w-6 h-6"
            fill="currentColor"
            viewBox="0 0 20 20"
            aria-hidden="true"
          >
            <path
              fillRule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
              clipRule="evenodd"
            />
          </svg>
        );
      case AlertSeverity.WARNING:
        return (
          <svg
            className="w-6 h-6"
            fill="currentColor"
            viewBox="0 0 20 20"
            aria-hidden="true"
          >
            <path
              fillRule="evenodd"
              d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
              clipRule="evenodd"
            />
          </svg>
        );
      case AlertSeverity.INFO:
      default:
        return (
          <svg
            className="w-6 h-6"
            fill="currentColor"
            viewBox="0 0 20 20"
            aria-hidden="true"
          >
            <path
              fillRule="evenodd"
              d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
              clipRule="evenodd"
            />
          </svg>
        );
    }
  };

  const formatTime = (timestamp: string): string => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / (1000 * 60));
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };

  const sortedAlerts = [...alerts].sort((a, b) => {
    const severityOrder = {
      [AlertSeverity.CRITICAL]: 0,
      [AlertSeverity.ERROR]: 1,
      [AlertSeverity.WARNING]: 2,
      [AlertSeverity.INFO]: 3,
    };
    const severityDiff = severityOrder[a.severity] - severityOrder[b.severity];
    if (severityDiff !== 0) return severityDiff;
    return new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime();
  });

  if (alerts.length === 0) {
    return (
      <Card className="bg-white dark:bg-gray-800">
        <div className="p-8 text-center">
          <svg
            className="mx-auto h-12 w-12 text-green-400"
            fill="currentColor"
            viewBox="0 0 20 20"
            aria-hidden="true"
          >
            <path
              fillRule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
              clipRule="evenodd"
            />
          </svg>
          <h3 className="mt-2 text-sm font-medium text-gray-900 dark:text-white">
            No Active Alerts
          </h3>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            All risk metrics are within acceptable ranges
          </p>
        </div>
      </Card>
    );
  }

  return (
    <Card className="bg-white dark:bg-gray-800">
      <div className="p-6">
        <div className="flex justify-between items-center mb-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            Risk Alerts
          </h3>
          <span className="text-sm text-gray-500 dark:text-gray-400">
            {alerts.length} active {alerts.length === 1 ? 'alert' : 'alerts'}
          </span>
        </div>

        <div className="space-y-3" role="list">
          {sortedAlerts.map((alert) => {
            const styles = getSeverityStyles(alert.severity);

            return (
              <div
                key={alert.id}
                className={`border rounded-lg p-4 ${styles.container}`}
                role="listitem"
                aria-label={`${alert.severity} alert: ${alert.title}`}
              >
                <div className="flex items-start gap-3">
                  <div className={`flex-shrink-0 ${styles.icon}`}>
                    {getSeverityIcon(alert.severity)}
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 flex-wrap">
                          <h4 className={`text-sm font-semibold ${styles.title}`}>
                            {alert.title}
                          </h4>
                          <span
                            className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${styles.badge}`}
                          >
                            {alert.severity.toUpperCase()}
                          </span>
                        </div>
                        <p className={`mt-1 text-sm ${styles.message}`}>
                          {alert.message}
                        </p>
                        <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                          {formatTime(alert.timestamp)}
                        </p>
                      </div>

                      {alert.dismissible && onDismiss && (
                        <button
                          onClick={() => onDismiss(alert.id)}
                          className="flex-shrink-0 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                          aria-label="Dismiss alert"
                        >
                          <svg
                            className="w-5 h-5"
                            fill="currentColor"
                            viewBox="0 0 20 20"
                          >
                            <path
                              fillRule="evenodd"
                              d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                              clipRule="evenodd"
                            />
                          </svg>
                        </button>
                      )}
                    </div>

                    {alert.actionLabel && onAction && (
                      <div className="mt-3">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => onAction(alert.id, alert.actionData)}
                          aria-label={alert.actionLabel}
                        >
                          {alert.actionLabel}
                        </Button>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Summary Stats */}
        <div className="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center">
              <p className="text-sm text-gray-500 dark:text-gray-400">Critical</p>
              <p className="mt-1 text-2xl font-bold text-red-600 dark:text-red-400">
                {alerts.filter((a) => a.severity === AlertSeverity.CRITICAL).length}
              </p>
            </div>
            <div className="text-center">
              <p className="text-sm text-gray-500 dark:text-gray-400">Error</p>
              <p className="mt-1 text-2xl font-bold text-orange-600 dark:text-orange-400">
                {alerts.filter((a) => a.severity === AlertSeverity.ERROR).length}
              </p>
            </div>
            <div className="text-center">
              <p className="text-sm text-gray-500 dark:text-gray-400">Warning</p>
              <p className="mt-1 text-2xl font-bold text-yellow-600 dark:text-yellow-400">
                {alerts.filter((a) => a.severity === AlertSeverity.WARNING).length}
              </p>
            </div>
            <div className="text-center">
              <p className="text-sm text-gray-500 dark:text-gray-400">Info</p>
              <p className="mt-1 text-2xl font-bold text-blue-600 dark:text-blue-400">
                {alerts.filter((a) => a.severity === AlertSeverity.INFO).length}
              </p>
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
};
