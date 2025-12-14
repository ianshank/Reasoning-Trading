import React from 'react';
import { Shield, AlertTriangle, RotateCcw } from 'lucide-react';
import { RiskSettings as RiskSettingsType, RiskProfile } from './types';

interface RiskSettingsProps {
  config: RiskSettingsType | null;
  onChange: (updates: Partial<RiskSettingsType>) => void;
  onReset: () => void;
}

interface RiskProfileOption {
  value: RiskProfile;
  label: string;
  description: string;
  color: string;
}

const RISK_PROFILES: RiskProfileOption[] = [
  {
    value: RiskProfile.CONSERVATIVE,
    label: 'Conservative',
    description: 'Lower position sizes, tighter stop losses',
    color: 'text-green-600 dark:text-green-400',
  },
  {
    value: RiskProfile.MODERATE,
    label: 'Moderate',
    description: 'Balanced risk with standard limits',
    color: 'text-blue-600 dark:text-blue-400',
  },
  {
    value: RiskProfile.AGGRESSIVE,
    label: 'Aggressive',
    description: 'Larger positions, wider stop losses',
    color: 'text-orange-600 dark:text-orange-400',
  },
];

export function RiskSettings({ config, onChange, onReset }: RiskSettingsProps) {
  if (!config) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500 dark:text-gray-400">Loading risk settings...</p>
      </div>
    );
  }

  const handleProfileChange = (profile: RiskProfile) => {
    const presets: Record<RiskProfile, Partial<RiskSettingsType>> = {
      [RiskProfile.CONSERVATIVE]: {
        default_risk_profile: profile,
        max_position_size_fraction: 0.15,
        default_stop_loss_percent: 0.03,
        max_daily_loss_percent: 0.05,
      },
      [RiskProfile.MODERATE]: {
        default_risk_profile: profile,
        max_position_size_fraction: 0.25,
        default_stop_loss_percent: 0.05,
        max_daily_loss_percent: 0.10,
      },
      [RiskProfile.AGGRESSIVE]: {
        default_risk_profile: profile,
        max_position_size_fraction: 0.40,
        default_stop_loss_percent: 0.08,
        max_daily_loss_percent: 0.15,
      },
    };

    onChange(presets[profile]);
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
          Risk Management
        </h2>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Configure position sizing, stop losses, and risk limits
        </p>
      </div>

      {/* Warning Banner */}
      <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-4">
        <div className="flex gap-3">
          <AlertTriangle className="w-5 h-5 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-amber-900 dark:text-amber-200">
            <p className="font-medium mb-1">Important Risk Notice</p>
            <p>
              These settings control your risk exposure. Lower values provide more
              protection but may limit potential gains. Always ensure settings align with
              your risk tolerance and account size.
            </p>
          </div>
        </div>
      </div>

      {/* Risk Profile Selector */}
      <div>
        <label className="block text-sm font-medium text-gray-900 dark:text-white mb-3">
          Risk Profile
        </label>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {RISK_PROFILES.map((profile) => {
            const isSelected = config.default_risk_profile === profile.value;
            return (
              <button
                key={profile.value}
                onClick={() => handleProfileChange(profile.value)}
                className={`
                  p-4 rounded-lg border-2 text-left transition-all
                  ${
                    isSelected
                      ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                      : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
                  }
                `}
                aria-pressed={isSelected}
              >
                <div className="flex items-center gap-2 mb-2">
                  <Shield className={`w-5 h-5 ${profile.color}`} />
                  <div className="font-medium text-gray-900 dark:text-white">
                    {profile.label}
                  </div>
                </div>
                <div className="text-xs text-gray-600 dark:text-gray-400">
                  {profile.description}
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Risk Parameters */}
      <div className="space-y-6">
        {/* Max Position Size */}
        <div className="space-y-2">
          <label
            htmlFor="max_position_size"
            className="block text-sm font-medium text-gray-900 dark:text-white"
          >
            Maximum Position Size
          </label>
          <p className="text-xs text-gray-600 dark:text-gray-400">
            Maximum position size as fraction of portfolio (0.01-1.0)
          </p>
          <div className="flex items-center gap-4">
            <input
              type="range"
              id="max_position_size"
              min="0.01"
              max="1.0"
              step="0.01"
              value={config.max_position_size_fraction}
              onChange={(e) =>
                onChange({
                  max_position_size_fraction: parseFloat(e.target.value),
                })
              }
              className="flex-1 h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer"
              aria-valuemin={0.01}
              aria-valuemax={1.0}
              aria-valuenow={config.max_position_size_fraction}
            />
            <div className="flex items-center gap-2 w-32">
              <input
                type="number"
                min="0.01"
                max="1.0"
                step="0.01"
                value={config.max_position_size_fraction}
                onChange={(e) =>
                  onChange({
                    max_position_size_fraction: parseFloat(e.target.value) || 0.01,
                  })
                }
                className="w-20 px-3 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg text-sm"
                aria-label="Maximum position size value"
              />
              <span className="text-sm text-gray-600 dark:text-gray-400">
                ({(config.max_position_size_fraction * 100).toFixed(0)}%)
              </span>
            </div>
          </div>
        </div>

        {/* Default Stop Loss */}
        <div className="space-y-2">
          <label
            htmlFor="stop_loss"
            className="block text-sm font-medium text-gray-900 dark:text-white"
          >
            Default Stop Loss
          </label>
          <p className="text-xs text-gray-600 dark:text-gray-400">
            Default stop loss percentage (0.1%-50%)
          </p>
          <div className="flex items-center gap-4">
            <input
              type="range"
              id="stop_loss"
              min="0.001"
              max="0.50"
              step="0.001"
              value={config.default_stop_loss_percent}
              onChange={(e) =>
                onChange({
                  default_stop_loss_percent: parseFloat(e.target.value),
                })
              }
              className="flex-1 h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer"
              aria-valuemin={0.001}
              aria-valuemax={0.50}
              aria-valuenow={config.default_stop_loss_percent}
            />
            <div className="flex items-center gap-2 w-32">
              <input
                type="number"
                min="0.001"
                max="0.50"
                step="0.001"
                value={config.default_stop_loss_percent}
                onChange={(e) =>
                  onChange({
                    default_stop_loss_percent: parseFloat(e.target.value) || 0.001,
                  })
                }
                className="w-20 px-3 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg text-sm"
                aria-label="Default stop loss value"
              />
              <span className="text-sm text-gray-600 dark:text-gray-400">
                ({(config.default_stop_loss_percent * 100).toFixed(1)}%)
              </span>
            </div>
          </div>
        </div>

        {/* Max Daily Loss */}
        <div className="space-y-2">
          <label
            htmlFor="max_daily_loss"
            className="block text-sm font-medium text-gray-900 dark:text-white"
          >
            Maximum Daily Loss (Circuit Breaker)
          </label>
          <p className="text-xs text-gray-600 dark:text-gray-400">
            Maximum daily loss percentage before trading halt (1%-50%)
          </p>
          <div className="flex items-center gap-4">
            <input
              type="range"
              id="max_daily_loss"
              min="0.01"
              max="0.50"
              step="0.01"
              value={config.max_daily_loss_percent}
              onChange={(e) =>
                onChange({
                  max_daily_loss_percent: parseFloat(e.target.value),
                })
              }
              className="flex-1 h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer"
              aria-valuemin={0.01}
              aria-valuemax={0.50}
              aria-valuenow={config.max_daily_loss_percent}
            />
            <div className="flex items-center gap-2 w-32">
              <input
                type="number"
                min="0.01"
                max="0.50"
                step="0.01"
                value={config.max_daily_loss_percent}
                onChange={(e) =>
                  onChange({
                    max_daily_loss_percent: parseFloat(e.target.value) || 0.01,
                  })
                }
                className="w-20 px-3 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg text-sm"
                aria-label="Maximum daily loss value"
              />
              <span className="text-sm text-gray-600 dark:text-gray-400">
                ({(config.max_daily_loss_percent * 100).toFixed(0)}%)
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Risk Summary */}
      <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-4">
          Risk Summary
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
          <div>
            <div className="text-gray-600 dark:text-gray-400 mb-1">Max Position</div>
            <div className="text-lg font-semibold text-gray-900 dark:text-white">
              {(config.max_position_size_fraction * 100).toFixed(0)}%
            </div>
          </div>
          <div>
            <div className="text-gray-600 dark:text-gray-400 mb-1">Stop Loss</div>
            <div className="text-lg font-semibold text-gray-900 dark:text-white">
              {(config.default_stop_loss_percent * 100).toFixed(1)}%
            </div>
          </div>
          <div>
            <div className="text-gray-600 dark:text-gray-400 mb-1">Daily Loss Limit</div>
            <div className="text-lg font-semibold text-gray-900 dark:text-white">
              {(config.max_daily_loss_percent * 100).toFixed(0)}%
            </div>
          </div>
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
          aria-label="Reset risk settings to defaults"
        >
          <RotateCcw className="w-4 h-4" />
          Reset to Defaults
        </button>
      </div>
    </div>
  );
}
