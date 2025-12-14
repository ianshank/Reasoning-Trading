import React from 'react';
import { Bell, Mail, Smartphone, RotateCcw } from 'lucide-react';
import { NotificationSettings as NotificationSettingsType } from './types';

interface NotificationSettingsProps {
  config: NotificationSettingsType | null;
  onChange: (updates: Partial<NotificationSettingsType>) => void;
  onReset: () => void;
}

interface ToggleSwitchProps {
  id: string;
  label: string;
  description: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  icon?: React.ComponentType<{ className?: string }>;
}

function ToggleSwitch({
  id,
  label,
  description,
  checked,
  onChange,
  icon: Icon,
}: ToggleSwitchProps) {
  return (
    <div className="flex items-start justify-between gap-4">
      <div className="flex-1 flex gap-3">
        {Icon && <Icon className="w-5 h-5 text-gray-500 dark:text-gray-400 mt-0.5" />}
        <div>
          <label
            htmlFor={id}
            className="block text-sm font-medium text-gray-900 dark:text-white cursor-pointer"
          >
            {label}
          </label>
          <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">{description}</p>
        </div>
      </div>
      <button
        type="button"
        role="switch"
        id={id}
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className={`
          relative inline-flex h-6 w-11 items-center rounded-full
          transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
          ${checked ? 'bg-blue-600 dark:bg-blue-500' : 'bg-gray-300 dark:bg-gray-600'}
        `}
      >
        <span
          className={`
            inline-block h-4 w-4 transform rounded-full bg-white transition-transform
            ${checked ? 'translate-x-6' : 'translate-x-1'}
          `}
        />
      </button>
    </div>
  );
}

export function NotificationSettings({
  config,
  onChange,
  onReset,
}: NotificationSettingsProps) {
  if (!config) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500 dark:text-gray-400">
          Loading notification settings...
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
          Notifications
        </h2>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Configure alerts and notifications for important trading events
        </p>
      </div>

      {/* Notification Channels */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
          Notification Channels
        </h3>

        <div className="space-y-4">
          <ToggleSwitch
            id="email_notifications"
            label="Email Notifications"
            description="Receive alerts via email"
            checked={config.email_notifications}
            onChange={(checked) => onChange({ email_notifications: checked })}
            icon={Mail}
          />

          <ToggleSwitch
            id="push_notifications"
            label="Push Notifications"
            description="Receive browser push notifications"
            checked={config.push_notifications}
            onChange={(checked) => onChange({ push_notifications: checked })}
            icon={Smartphone}
          />
        </div>
      </div>

      {/* Alert Types */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
          Alert Types
        </h3>

        <div className="space-y-4">
          <ToggleSwitch
            id="regime_change_alerts"
            label="Market Regime Change Alerts"
            description="Get notified when market regime changes are detected"
            checked={config.regime_change_alerts}
            onChange={(checked) => onChange({ regime_change_alerts: checked })}
            icon={Bell}
          />

          <ToggleSwitch
            id="trade_execution_alerts"
            label="Trade Execution Alerts"
            description="Get notified when trades are executed"
            checked={config.trade_execution_alerts}
            onChange={(checked) => onChange({ trade_execution_alerts: checked })}
            icon={Bell}
          />

          <ToggleSwitch
            id="risk_threshold_alerts"
            label="Risk Threshold Alerts"
            description="Get notified when risk thresholds are approached or breached"
            checked={config.risk_threshold_alerts}
            onChange={(checked) => onChange({ risk_threshold_alerts: checked })}
            icon={Bell}
          />
        </div>
      </div>

      {/* Alert Threshold */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
          Alert Thresholds
        </h3>

        <div className="space-y-2">
          <label
            htmlFor="alert_threshold"
            className="block text-sm font-medium text-gray-900 dark:text-white"
          >
            Price Movement Alert Threshold
          </label>
          <p className="text-xs text-gray-600 dark:text-gray-400">
            Alert when positions move by this percentage (1%-50%)
          </p>
          <div className="flex items-center gap-4">
            <input
              type="range"
              id="alert_threshold"
              min="1"
              max="50"
              step="1"
              value={config.alert_threshold_percent * 100}
              onChange={(e) =>
                onChange({
                  alert_threshold_percent: parseFloat(e.target.value) / 100,
                })
              }
              className="flex-1 h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer"
              aria-valuemin={1}
              aria-valuemax={50}
              aria-valuenow={config.alert_threshold_percent * 100}
            />
            <div className="flex items-center gap-2 w-32">
              <input
                type="number"
                min="1"
                max="50"
                step="1"
                value={config.alert_threshold_percent * 100}
                onChange={(e) =>
                  onChange({
                    alert_threshold_percent: parseFloat(e.target.value) / 100 || 0.01,
                  })
                }
                className="w-20 px-3 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg text-sm"
                aria-label="Alert threshold percentage"
              />
              <span className="text-sm text-gray-600 dark:text-gray-400">%</span>
            </div>
          </div>
        </div>
      </div>

      {/* Preview */}
      <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-4">
          Active Notifications
        </h3>
        <div className="space-y-3 text-sm">
          {config.email_notifications && (
            <div className="flex items-center gap-2 text-gray-700 dark:text-gray-300">
              <Mail className="w-4 h-4 text-blue-600 dark:text-blue-400" />
              <span>Email notifications enabled</span>
            </div>
          )}
          {config.push_notifications && (
            <div className="flex items-center gap-2 text-gray-700 dark:text-gray-300">
              <Smartphone className="w-4 h-4 text-blue-600 dark:text-blue-400" />
              <span>Push notifications enabled</span>
            </div>
          )}
          {config.regime_change_alerts && (
            <div className="flex items-center gap-2 text-gray-700 dark:text-gray-300">
              <Bell className="w-4 h-4 text-blue-600 dark:text-blue-400" />
              <span>Market regime change alerts</span>
            </div>
          )}
          {config.trade_execution_alerts && (
            <div className="flex items-center gap-2 text-gray-700 dark:text-gray-300">
              <Bell className="w-4 h-4 text-blue-600 dark:text-blue-400" />
              <span>Trade execution alerts</span>
            </div>
          )}
          {config.risk_threshold_alerts && (
            <div className="flex items-center gap-2 text-gray-700 dark:text-gray-300">
              <Bell className="w-4 h-4 text-blue-600 dark:text-blue-400" />
              <span>Risk threshold alerts</span>
            </div>
          )}
          {!config.email_notifications &&
            !config.push_notifications &&
            !config.regime_change_alerts &&
            !config.trade_execution_alerts &&
            !config.risk_threshold_alerts && (
              <p className="text-gray-500 dark:text-gray-400">
                No notifications enabled
              </p>
            )}
        </div>
      </div>

      {/* Reset Button */}
      <div className="pt-6 border-t border-gray-200 dark:border-gray-700">
        <button
          onClick={onReset}
          className="
            flex items-center gap-2 px-4 py-2 text-sm font-medium
            text-gray-700 dark:text-gray-300
            hover:bg-gray-100 dark:hover:bg-gray-700
            rounded-lg transition-colors
          "
          aria-label="Reset notification settings to defaults"
        >
          <RotateCcw className="w-4 h-4" />
          Reset to Defaults
        </button>
      </div>
    </div>
  );
}
