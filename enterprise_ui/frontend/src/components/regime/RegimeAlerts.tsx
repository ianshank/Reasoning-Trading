/**
 * Regime Alerts Component
 *
 * Displays and manages regime change alerts
 * - List of recent regime changes
 * - Alert configuration
 * - Notification preferences
 * - Acknowledge/dismiss functionality
 */

import React, { useState } from 'react';
import {
  Bell,
  BellOff,
  Settings,
  Check,
  AlertTriangle,
  Info,
  AlertCircle,
} from 'lucide-react';
import { Card, CardHeader, CardBody } from '../ui/Card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Modal } from '../ui/modal';
import { Input } from '../ui/input';
import type { RegimeAlert, RegimeAlertConfig } from '../../types/regime';
import { getRegimeDisplayName, getRegimeColor } from '../../types/regime';

export interface RegimeAlertsProps {
  alerts: RegimeAlert[];
  config?: RegimeAlertConfig;
  onConfigure?: (config: RegimeAlertConfig) => void;
  onAcknowledge?: (alertId: string) => void;
  onDismiss?: (alertId: string) => void;
  className?: string;
}

/**
 * Get alert icon based on severity
 */
function getAlertIcon(severity: 'low' | 'medium' | 'high'): React.ReactNode {
  const iconProps = { size: 20 };

  switch (severity) {
    case 'high':
      return <AlertCircle {...iconProps} className="text-red-600 dark:text-red-400" />;
    case 'medium':
      return <AlertTriangle {...iconProps} className="text-yellow-600 dark:text-yellow-400" />;
    default:
      return <Info {...iconProps} className="text-blue-600 dark:text-blue-400" />;
  }
}

/**
 * Format relative time
 */
function formatRelativeTime(timestamp: string): string {
  const now = new Date();
  const then = new Date(timestamp);
  const diffMs = now.getTime() - then.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHour = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHour / 24);

  if (diffDay > 0) return `${diffDay} day${diffDay !== 1 ? 's' : ''} ago`;
  if (diffHour > 0) return `${diffHour} hour${diffHour !== 1 ? 's' : ''} ago`;
  if (diffMin > 0) return `${diffMin} minute${diffMin !== 1 ? 's' : ''} ago`;
  return `${diffSec} second${diffSec !== 1 ? 's' : ''} ago`;
}

export const RegimeAlerts: React.FC<RegimeAlertsProps> = ({
  alerts,
  config = {
    enabled: true,
    min_confidence: 0.6,
    notify_on_regimes: [],
    notification_channels: ['ui'],
  },
  onConfigure,
  onAcknowledge,
  onDismiss,
  className = '',
}) => {
  const [showConfig, setShowConfig] = useState(false);
  const [localConfig, setLocalConfig] = useState<RegimeAlertConfig>(config);

  const unacknowledgedCount = alerts.filter((a) => !a.acknowledged).length;

  const handleSaveConfig = () => {
    if (onConfigure) {
      onConfigure(localConfig);
    }
    setShowConfig(false);
  };

  return (
    <>
      <Card
        className={`bg-white dark:bg-gray-800 ${className}`}
        role="article"
        aria-label="Regime Change Alerts"
      >
        <CardHeader>
          <div className="flex items-center justify-between w-full">
            <div className="flex items-center space-x-2">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                Regime Alerts
              </h3>
              {unacknowledgedCount > 0 && (
                <Badge variant="danger" size="sm">
                  {unacknowledgedCount} new
                </Badge>
              )}
            </div>
            <div className="flex items-center space-x-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowConfig(true)}
                aria-label="Configure alerts"
              >
                <Settings size={16} />
              </Button>
              {config.enabled ? (
                <Bell
                  size={20}
                  className="text-blue-600 dark:text-blue-400"
                  aria-label="Alerts enabled"
                />
              ) : (
                <BellOff
                  size={20}
                  className="text-gray-400"
                  aria-label="Alerts disabled"
                />
              )}
            </div>
          </div>
        </CardHeader>

        <CardBody>
          {alerts.length > 0 ? (
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {alerts.map((alert) => (
                <div
                  key={alert.id}
                  className={`p-4 rounded-lg border transition-all ${
                    alert.acknowledged
                      ? 'bg-gray-50 dark:bg-gray-900 border-gray-200 dark:border-gray-700 opacity-60'
                      : 'bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-600 shadow-sm'
                  }`}
                >
                  <div className="flex items-start space-x-3">
                    <div className="flex-shrink-0 mt-0.5">
                      {getAlertIcon(alert.severity)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex items-center space-x-2">
                          <span className="text-sm font-semibold text-gray-900 dark:text-white">
                            Regime Change Detected
                          </span>
                          <Badge
                            variant={
                              alert.severity === 'high'
                                ? 'danger'
                                : alert.severity === 'medium'
                                ? 'warning'
                                : 'info'
                            }
                            size="sm"
                          >
                            {alert.severity}
                          </Badge>
                        </div>
                        <span className="text-xs text-gray-500 dark:text-gray-400 whitespace-nowrap ml-2">
                          {formatRelativeTime(alert.timestamp)}
                        </span>
                      </div>

                      <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
                        {alert.message}
                      </p>

                      <div className="flex items-center space-x-4 text-xs">
                        <div className="flex items-center space-x-2">
                          <span className="text-gray-500 dark:text-gray-400">
                            From:
                          </span>
                          <div className="flex items-center space-x-1">
                            <div
                              className="w-2 h-2 rounded-full"
                              style={{
                                backgroundColor: getRegimeColor(alert.from_regime),
                              }}
                              aria-hidden="true"
                            />
                            <span className="font-medium text-gray-900 dark:text-white">
                              {getRegimeDisplayName(alert.from_regime)}
                            </span>
                          </div>
                        </div>
                        <div className="flex items-center space-x-2">
                          <span className="text-gray-500 dark:text-gray-400">
                            To:
                          </span>
                          <div className="flex items-center space-x-1">
                            <div
                              className="w-2 h-2 rounded-full"
                              style={{
                                backgroundColor: getRegimeColor(alert.to_regime),
                              }}
                              aria-hidden="true"
                            />
                            <span className="font-medium text-gray-900 dark:text-white">
                              {getRegimeDisplayName(alert.to_regime)}
                            </span>
                          </div>
                        </div>
                        <div className="flex items-center space-x-2">
                          <span className="text-gray-500 dark:text-gray-400">
                            Confidence:
                          </span>
                          <span className="font-mono font-medium text-gray-900 dark:text-white">
                            {(alert.confidence * 100).toFixed(0)}%
                          </span>
                        </div>
                      </div>

                      {!alert.acknowledged && onAcknowledge && (
                        <div className="mt-3 flex items-center space-x-2">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => onAcknowledge(alert.id)}
                          >
                            <Check size={14} className="mr-1" />
                            Acknowledge
                          </Button>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="py-12 text-center">
              <Bell
                size={48}
                className="mx-auto text-gray-300 dark:text-gray-600 mb-4"
              />
              <p className="text-sm text-gray-500 dark:text-gray-400">
                No regime alerts
              </p>
              <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
                You will be notified when regime changes occur
              </p>
            </div>
          )}
        </CardBody>
      </Card>

      {/* Configuration Modal */}
      {showConfig && (
        <Modal
          isOpen={true}
          onClose={() => setShowConfig(false)}
          title="Alert Configuration"
          size="md"
        >
          <div className="space-y-6">
            {/* Enable/Disable */}
            <div className="flex items-center justify-between">
              <div>
                <label className="text-sm font-medium text-gray-900 dark:text-white">
                  Enable Alerts
                </label>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  Receive notifications for regime changes
                </p>
              </div>
              <button
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  localConfig.enabled ? 'bg-blue-600' : 'bg-gray-200 dark:bg-gray-700'
                }`}
                onClick={() =>
                  setLocalConfig({ ...localConfig, enabled: !localConfig.enabled })
                }
                role="switch"
                aria-checked={localConfig.enabled}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    localConfig.enabled ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>

            {/* Minimum Confidence */}
            <div>
              <label
                htmlFor="min-confidence"
                className="block text-sm font-medium text-gray-900 dark:text-white mb-2"
              >
                Minimum Confidence
              </label>
              <Input
                id="min-confidence"
                type="number"
                min="0"
                max="1"
                step="0.1"
                value={localConfig.min_confidence}
                onChange={(e) =>
                  setLocalConfig({
                    ...localConfig,
                    min_confidence: parseFloat(e.target.value),
                  })
                }
              />
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                Only alert when confidence is above this threshold (0-1)
              </p>
            </div>

            {/* Notification Channels */}
            <div>
              <label className="block text-sm font-medium text-gray-900 dark:text-white mb-2">
                Notification Channels
              </label>
              <div className="space-y-2">
                {(['ui', 'email', 'webhook'] as const).map((channel) => (
                  <label key={channel} className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      checked={localConfig.notification_channels.includes(channel)}
                      onChange={(e) => {
                        const channels = e.target.checked
                          ? [...localConfig.notification_channels, channel]
                          : localConfig.notification_channels.filter(
                              (c) => c !== channel
                            );
                        setLocalConfig({
                          ...localConfig,
                          notification_channels: channels,
                        });
                      }}
                      className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <span className="text-sm text-gray-700 dark:text-gray-300 capitalize">
                      {channel}
                    </span>
                  </label>
                ))}
              </div>
            </div>

            {/* Actions */}
            <div className="flex justify-end space-x-2 pt-4 border-t border-gray-200 dark:border-gray-700">
              <Button variant="outline" onClick={() => setShowConfig(false)}>
                Cancel
              </Button>
              <Button variant="primary" onClick={handleSaveConfig}>
                Save Configuration
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </>
  );
};
