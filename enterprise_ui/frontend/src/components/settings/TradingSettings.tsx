import React from 'react';
import { TrendingUp, RotateCcw, Info } from 'lucide-react';
import {
  FeatureFlags,
  TradingPreferences,
  OrderType,
  TimeInForce,
  TradingMode,
  TradingSettings as TradingSettingsType,
} from './types';

interface TradingSettingsProps {
  config: {
    trading: TradingSettingsType;
    features: FeatureFlags;
    trading_preferences: TradingPreferences;
  } | null;
  onChange: (updates: {
    trading?: Partial<TradingSettingsType>;
    features?: Partial<FeatureFlags>;
    trading_preferences?: Partial<TradingPreferences>;
  }) => void;
  onReset: () => void;
}

interface ToggleSwitchProps {
  id: string;
  label: string;
  description: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
  warningColor?: boolean;
}

function ToggleSwitch({
  id,
  label,
  description,
  checked,
  onChange,
  disabled = false,
  warningColor = false,
}: ToggleSwitchProps) {
  return (
    <div className="flex items-start justify-between gap-4">
      <div className="flex-1">
        <label
          htmlFor={id}
          className="block text-sm font-medium text-gray-900 dark:text-white cursor-pointer"
        >
          {label}
        </label>
        <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">{description}</p>
      </div>
      <button
        type="button"
        role="switch"
        id={id}
        aria-checked={checked}
        disabled={disabled}
        onClick={() => onChange(!checked)}
        className={`
          relative inline-flex h-6 w-11 items-center rounded-full
          transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
          disabled:opacity-50 disabled:cursor-not-allowed
          ${
            checked
              ? warningColor
                ? 'bg-red-600 dark:bg-red-500'
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
  );
}

export function TradingSettings({ config, onChange, onReset }: TradingSettingsProps) {
  if (!config) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500 dark:text-gray-400">Loading trading settings...</p>
      </div>
    );
  }

  const { trading, features, trading_preferences } = config;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
          Trading Preferences
        </h2>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Configure default order types, trading modes, and execution settings
        </p>
      </div>

      {/* Trading Mode Section */}
      <div>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Trading Mode
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <button
            onClick={() => onChange({ trading: { trading_mode: TradingMode.PAPER } })}
            className={`
              p-4 rounded-lg border-2 text-left transition-all
              ${
                trading.trading_mode === TradingMode.PAPER
                  ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                  : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
              }
            `}
            aria-pressed={trading.trading_mode === TradingMode.PAPER}
          >
            <div className="flex items-center gap-2 mb-2">
              <div className="w-2 h-2 rounded-full bg-green-500" />
              <div className="font-medium text-gray-900 dark:text-white">Paper Trading</div>
            </div>
            <div className="text-xs text-gray-600 dark:text-gray-400">
              Simulated trading with no real money at risk
            </div>
          </button>

          <button
            onClick={() => onChange({ trading: { trading_mode: TradingMode.LIVE } })}
            className={`
              p-4 rounded-lg border-2 text-left transition-all
              ${
                trading.trading_mode === TradingMode.LIVE
                  ? 'border-red-500 bg-red-50 dark:bg-red-900/20'
                  : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
              }
            `}
            aria-pressed={trading.trading_mode === TradingMode.LIVE}
          >
            <div className="flex items-center gap-2 mb-2">
              <div className="w-2 h-2 rounded-full bg-red-500" />
              <div className="font-medium text-gray-900 dark:text-white">Live Trading</div>
            </div>
            <div className="text-xs text-gray-600 dark:text-gray-400">
              Real money trading - use with caution
            </div>
          </button>
        </div>

        {trading.trading_mode === TradingMode.LIVE && (
          <div className="mt-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
            <div className="flex gap-3">
              <Info className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
              <div className="text-sm text-red-900 dark:text-red-200">
                <p className="font-medium mb-1">Live Trading Enabled</p>
                <p>
                  You are trading with real money. All orders will be executed on the live
                  market. Ensure your API keys are properly configured and risk settings
                  are appropriate.
                </p>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Default Order Settings */}
      <div className="space-y-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
          Default Order Settings
        </h3>

        {/* Default Order Type */}
        <div className="space-y-2">
          <label
            htmlFor="order_type"
            className="block text-sm font-medium text-gray-900 dark:text-white"
          >
            Default Order Type
          </label>
          <p className="text-xs text-gray-600 dark:text-gray-400">
            Order type to use by default when placing trades
          </p>
          <select
            id="order_type"
            value={trading_preferences.default_order_type}
            onChange={(e) =>
              onChange({
                trading_preferences: {
                  default_order_type: e.target.value as OrderType,
                },
              })
            }
            className="
              w-full md:w-64 px-4 py-2 bg-white dark:bg-gray-800
              border border-gray-300 dark:border-gray-600
              rounded-lg text-sm
              focus:ring-2 focus:ring-blue-500 focus:border-transparent
            "
          >
            <option value={OrderType.MARKET}>Market Order</option>
            <option value={OrderType.LIMIT}>Limit Order</option>
            <option value={OrderType.STOP}>Stop Order</option>
            <option value={OrderType.STOP_LIMIT}>Stop-Limit Order</option>
          </select>
        </div>

        {/* Default Time in Force */}
        <div className="space-y-2">
          <label
            htmlFor="time_in_force"
            className="block text-sm font-medium text-gray-900 dark:text-white"
          >
            Default Time in Force
          </label>
          <p className="text-xs text-gray-600 dark:text-gray-400">
            How long orders remain active
          </p>
          <select
            id="time_in_force"
            value={trading_preferences.default_time_in_force}
            onChange={(e) =>
              onChange({
                trading_preferences: {
                  default_time_in_force: e.target.value as TimeInForce,
                },
              })
            }
            className="
              w-full md:w-64 px-4 py-2 bg-white dark:bg-gray-800
              border border-gray-300 dark:border-gray-600
              rounded-lg text-sm
              focus:ring-2 focus:ring-blue-500 focus:border-transparent
            "
          >
            <option value={TimeInForce.DAY}>Day (until market close)</option>
            <option value={TimeInForce.GTC}>Good Till Canceled</option>
            <option value={TimeInForce.IOC}>Immediate or Cancel</option>
            <option value={TimeInForce.FOK}>Fill or Kill</option>
          </select>
        </div>
      </div>

      {/* Feature Toggles */}
      <div className="space-y-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
          Trading Features
        </h3>

        <div className="space-y-4">
          <ToggleSwitch
            id="allow_shorts"
            label="Allow Short Selling"
            description="Enable short selling of securities"
            checked={features.allow_shorts}
            onChange={(checked) => onChange({ features: { allow_shorts: checked } })}
          />

          <ToggleSwitch
            id="enable_margin"
            label="Enable Margin Trading"
            description="Allow trading on margin (requires approved margin account)"
            checked={features.enable_margin_trading}
            onChange={(checked) =>
              onChange({ features: { enable_margin_trading: checked } })
            }
            warningColor
          />

          <ToggleSwitch
            id="enable_crypto"
            label="Enable Cryptocurrency Trading"
            description="Allow trading of cryptocurrencies"
            checked={features.enable_crypto_trading}
            onChange={(checked) =>
              onChange({ features: { enable_crypto_trading: checked } })
            }
          />

          <ToggleSwitch
            id="auto_execute"
            label="Auto-Execute Trades"
            description="Automatically execute recommended trades without confirmation"
            checked={features.auto_execute_trades}
            onChange={(checked) =>
              onChange({ features: { auto_execute_trades: checked } })
            }
            warningColor
          />
        </div>

        {features.auto_execute_trades && (
          <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-4">
            <div className="flex gap-3">
              <Info className="w-5 h-5 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
              <div className="text-sm text-amber-900 dark:text-amber-200">
                <p className="font-medium mb-1">Auto-Execute Enabled</p>
                <p>
                  Trades will be executed automatically without manual confirmation.
                  Ensure your risk settings are properly configured.
                </p>
              </div>
            </div>
          </div>
        )}
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
          aria-label="Reset trading settings to defaults"
        >
          <RotateCcw className="w-4 h-4" />
          Reset to Defaults
        </button>
      </div>
    </div>
  );
}
