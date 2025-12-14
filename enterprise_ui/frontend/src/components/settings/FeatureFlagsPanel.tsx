import React from 'react';
import { ToggleLeft, AlertTriangle, Info, Zap } from 'lucide-react';
import { FeatureFlags } from './types';

interface FeatureFlagsPanelProps {
  flags: FeatureFlags | null;
  onChange: (updates: Partial<FeatureFlags>) => void;
}

interface FeatureFlag {
  key: keyof FeatureFlags;
  label: string;
  description: string;
  category: 'trading' | 'experimental';
  isExperimental?: boolean;
  isWarning?: boolean;
  warningMessage?: string;
}

const FEATURE_FLAGS: FeatureFlag[] = [
  {
    key: 'allow_shorts',
    label: 'Allow Short Selling',
    description: 'Enable short selling of securities',
    category: 'trading',
    isWarning: true,
    warningMessage: 'Short selling carries additional risk and requires margin approval',
  },
  {
    key: 'enable_margin_trading',
    label: 'Enable Margin Trading',
    description: 'Allow trading on margin with leverage',
    category: 'trading',
    isWarning: true,
    warningMessage: 'Margin trading increases both potential gains and losses',
  },
  {
    key: 'enable_crypto_trading',
    label: 'Enable Cryptocurrency Trading',
    description: 'Allow trading of cryptocurrencies (if supported by broker)',
    category: 'trading',
  },
  {
    key: 'auto_execute_trades',
    label: 'Auto-Execute Trades',
    description: 'Automatically execute recommended trades without manual confirmation',
    category: 'experimental',
    isExperimental: true,
    isWarning: true,
    warningMessage: 'Trades will be executed automatically. Use with caution.',
  },
];

interface FeatureFlagToggleProps {
  flag: FeatureFlag;
  checked: boolean;
  onChange: (checked: boolean) => void;
}

function FeatureFlagToggle({ flag, checked, onChange }: FeatureFlagToggleProps) {
  const [showWarning, setShowWarning] = React.useState(false);

  const handleToggle = () => {
    if (flag.isWarning && !checked) {
      setShowWarning(true);
    } else {
      onChange(!checked);
    }
  };

  const handleConfirm = () => {
    onChange(true);
    setShowWarning(false);
  };

  return (
    <>
      <div className="flex items-start justify-between gap-4 p-4 rounded-lg bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <label
              htmlFor={flag.key}
              className="text-sm font-medium text-gray-900 dark:text-white cursor-pointer"
            >
              {flag.label}
            </label>
            {flag.isExperimental && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-purple-100 dark:bg-purple-900/20 text-purple-700 dark:text-purple-300 text-xs font-medium">
                <Zap className="w-3 h-3" />
                Experimental
              </span>
            )}
            {flag.isWarning && checked && (
              <AlertTriangle className="w-4 h-4 text-amber-600 dark:text-amber-400" />
            )}
          </div>
          <p className="text-xs text-gray-600 dark:text-gray-400">{flag.description}</p>
          {flag.isWarning && checked && flag.warningMessage && (
            <p className="text-xs text-amber-600 dark:text-amber-400 mt-2">
              {flag.warningMessage}
            </p>
          )}
        </div>
        <button
          type="button"
          role="switch"
          id={flag.key}
          aria-checked={checked}
          onClick={handleToggle}
          className={`
            relative inline-flex h-6 w-11 items-center rounded-full flex-shrink-0
            transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
            ${
              checked
                ? flag.isWarning
                  ? 'bg-amber-600 dark:bg-amber-500'
                  : 'bg-blue-600 dark:bg-blue-500'
                : 'bg-gray-300 dark:bg-gray-600'
            }
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

      {/* Warning Dialog */}
      {showWarning && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
          role="dialog"
          aria-modal="true"
          aria-labelledby="feature-warning-dialog-title"
        >
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full mx-4 p-6">
            <div className="flex items-start gap-4">
              <div className="flex-shrink-0 w-10 h-10 rounded-full bg-amber-100 dark:bg-amber-900/20 flex items-center justify-center">
                <AlertTriangle className="w-5 h-5 text-amber-600 dark:text-amber-400" />
              </div>
              <div className="flex-1">
                <h2
                  id="feature-warning-dialog-title"
                  className="text-lg font-semibold text-gray-900 dark:text-white mb-2"
                >
                  Enable {flag.label}?
                </h2>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  {flag.warningMessage}
                </p>
              </div>
            </div>

            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => setShowWarning(false)}
                className="
                  px-4 py-2 text-sm font-medium
                  text-gray-700 dark:text-gray-300
                  hover:bg-gray-100 dark:hover:bg-gray-700
                  rounded-lg transition-colors
                "
              >
                Cancel
              </button>
              <button
                onClick={handleConfirm}
                className="
                  px-4 py-2 text-sm font-medium
                  text-white bg-amber-600 hover:bg-amber-700
                  dark:bg-amber-500 dark:hover:bg-amber-600
                  rounded-lg transition-colors
                "
              >
                Enable Feature
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

export function FeatureFlagsPanel({ flags, onChange }: FeatureFlagsPanelProps) {
  if (!flags) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500 dark:text-gray-400">Loading feature flags...</p>
      </div>
    );
  }

  const tradingFeatures = FEATURE_FLAGS.filter((f) => f.category === 'trading');
  const experimentalFeatures = FEATURE_FLAGS.filter((f) => f.category === 'experimental');

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
          Feature Flags
        </h2>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Enable or disable features to customize your trading experience
        </p>
      </div>

      {/* Info Banner */}
      <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
        <div className="flex gap-3">
          <Info className="w-5 h-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-blue-900 dark:text-blue-200">
            <p className="font-medium mb-1">About Feature Flags</p>
            <p>
              Feature flags allow you to enable or disable specific functionality. Some
              features may require additional account permissions or API access. Changes
              take effect immediately.
            </p>
          </div>
        </div>
      </div>

      {/* Trading Features */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
          <ToggleLeft className="w-5 h-5" />
          Trading Features
        </h3>
        <div className="space-y-3">
          {tradingFeatures.map((flag) => (
            <FeatureFlagToggle
              key={flag.key}
              flag={flag}
              checked={flags[flag.key]}
              onChange={(checked) => onChange({ [flag.key]: checked })}
            />
          ))}
        </div>
      </div>

      {/* Experimental Features */}
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
            <Zap className="w-5 h-5" />
            Experimental Features
          </h3>
        </div>
        <div className="bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800 rounded-lg p-4 mb-4">
          <div className="flex gap-3">
            <Zap className="w-5 h-5 text-purple-600 dark:text-purple-400 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-purple-900 dark:text-purple-200">
              <p className="font-medium mb-1">Experimental Features</p>
              <p>
                These features are in active development and may not be fully stable. Use
                with caution and provide feedback to help improve them.
              </p>
            </div>
          </div>
        </div>
        <div className="space-y-3">
          {experimentalFeatures.map((flag) => (
            <FeatureFlagToggle
              key={flag.key}
              flag={flag}
              checked={flags[flag.key]}
              onChange={(checked) => onChange({ [flag.key]: checked })}
            />
          ))}
        </div>
      </div>

      {/* Active Features Summary */}
      <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-4">
          Active Features
        </h3>
        <div className="space-y-2 text-sm">
          {FEATURE_FLAGS.filter((f) => flags[f.key]).map((flag) => (
            <div
              key={flag.key}
              className="flex items-center gap-2 text-gray-700 dark:text-gray-300"
            >
              <div
                className={`w-2 h-2 rounded-full ${
                  flag.isWarning
                    ? 'bg-amber-500'
                    : flag.isExperimental
                    ? 'bg-purple-500'
                    : 'bg-blue-500'
                }`}
              />
              <span>{flag.label}</span>
            </div>
          ))}
          {FEATURE_FLAGS.filter((f) => flags[f.key]).length === 0 && (
            <p className="text-gray-500 dark:text-gray-400">No features enabled</p>
          )}
        </div>
      </div>
    </div>
  );
}
