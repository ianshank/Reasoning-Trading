import React, { useState } from 'react';
import { Info, RotateCcw } from 'lucide-react';
import { MCTSSettings as MCTSSettingsType, MCTS_PRESETS, MCTSPreset } from './types';

interface MCTSSettingsProps {
  config: MCTSSettingsType | null;
  onChange: (updates: Partial<MCTSSettingsType>) => void;
  onReset: () => void;
}

interface SettingFieldProps {
  label: string;
  description: string;
  children: React.ReactNode;
  htmlFor?: string;
}

function SettingField({ label, description, children, htmlFor }: SettingFieldProps) {
  return (
    <div className="space-y-2">
      <label
        htmlFor={htmlFor}
        className="block text-sm font-medium text-gray-900 dark:text-white"
      >
        {label}
      </label>
      <p className="text-xs text-gray-600 dark:text-gray-400">{description}</p>
      {children}
    </div>
  );
}

export function MCTSSettings({ config, onChange, onReset }: MCTSSettingsProps) {
  const [selectedPreset, setSelectedPreset] = useState<string | null>(null);

  if (!config) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500 dark:text-gray-400">Loading MCTS settings...</p>
      </div>
    );
  }

  const handlePresetSelect = (preset: MCTSPreset) => {
    onChange(preset.settings);
    setSelectedPreset(preset.name);
  };

  const handleFieldChange = (field: keyof MCTSSettingsType, value: number) => {
    onChange({ [field]: value });
    setSelectedPreset(null);
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
          MCTS Configuration
        </h2>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Configure Monte Carlo Tree Search algorithm parameters for decision-making
        </p>
      </div>

      {/* Info Banner */}
      <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
        <div className="flex gap-3">
          <Info className="w-5 h-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-blue-900 dark:text-blue-200">
            <p className="font-medium mb-1">About MCTS Parameters</p>
            <p>
              These settings control the behavior of the Monte Carlo Tree Search algorithm
              used for trading decisions. Higher simulation counts provide more accurate
              results but take longer to compute.
            </p>
          </div>
        </div>
      </div>

      {/* Presets */}
      <div>
        <label className="block text-sm font-medium text-gray-900 dark:text-white mb-3">
          Quick Presets
        </label>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {MCTS_PRESETS.map((preset) => (
            <button
              key={preset.name}
              onClick={() => handlePresetSelect(preset)}
              className={`
                p-4 rounded-lg border-2 text-left transition-all
                ${
                  selectedPreset === preset.name
                    ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                    : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
                }
              `}
              aria-pressed={selectedPreset === preset.name}
            >
              <div className="font-medium text-gray-900 dark:text-white mb-1">
                {preset.name}
              </div>
              <div className="text-xs text-gray-600 dark:text-gray-400">
                {preset.description}
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Settings Fields */}
      <div className="space-y-6">
        {/* Max Simulations */}
        <SettingField
          label="Maximum Simulations"
          description="Number of MCTS simulations per decision (1-100,000)"
          htmlFor="max_simulations"
        >
          <div className="flex items-center gap-4">
            <input
              type="range"
              id="max_simulations"
              min="1"
              max="10000"
              step="100"
              value={config.max_simulations}
              onChange={(e) =>
                handleFieldChange('max_simulations', parseInt(e.target.value))
              }
              className="flex-1 h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer"
              aria-valuemin={1}
              aria-valuemax={10000}
              aria-valuenow={config.max_simulations}
            />
            <input
              type="number"
              min="1"
              max="100000"
              value={config.max_simulations}
              onChange={(e) =>
                handleFieldChange('max_simulations', parseInt(e.target.value) || 1)
              }
              className="w-24 px-3 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg text-sm"
              aria-label="Maximum simulations value"
            />
          </div>
        </SettingField>

        {/* Exploration Weight */}
        <SettingField
          label="Exploration Weight"
          description="UCB exploration parameter (0.0-10.0, √2 ≈ 1.414 is theoretically optimal)"
          htmlFor="exploration_weight"
        >
          <div className="flex items-center gap-4">
            <input
              type="range"
              id="exploration_weight"
              min="0"
              max="10"
              step="0.1"
              value={config.exploration_weight}
              onChange={(e) =>
                handleFieldChange('exploration_weight', parseFloat(e.target.value))
              }
              className="flex-1 h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer"
              aria-valuemin={0}
              aria-valuemax={10}
              aria-valuenow={config.exploration_weight}
            />
            <input
              type="number"
              min="0"
              max="10"
              step="0.1"
              value={config.exploration_weight}
              onChange={(e) =>
                handleFieldChange('exploration_weight', parseFloat(e.target.value) || 0)
              }
              className="w-24 px-3 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg text-sm"
              aria-label="Exploration weight value"
            />
          </div>
        </SettingField>

        {/* Rollout Horizon */}
        <SettingField
          label="Rollout Horizon (days)"
          description="Number of trading days to simulate in rollouts (1-365)"
          htmlFor="rollout_horizon_days"
        >
          <div className="flex items-center gap-4">
            <input
              type="range"
              id="rollout_horizon_days"
              min="1"
              max="365"
              step="1"
              value={config.rollout_horizon_days}
              onChange={(e) =>
                handleFieldChange('rollout_horizon_days', parseInt(e.target.value))
              }
              className="flex-1 h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer"
              aria-valuemin={1}
              aria-valuemax={365}
              aria-valuenow={config.rollout_horizon_days}
            />
            <input
              type="number"
              min="1"
              max="365"
              value={config.rollout_horizon_days}
              onChange={(e) =>
                handleFieldChange('rollout_horizon_days', parseInt(e.target.value) || 1)
              }
              className="w-24 px-3 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg text-sm"
              aria-label="Rollout horizon days value"
            />
          </div>
        </SettingField>

        {/* Confidence Threshold */}
        <SettingField
          label="Confidence Threshold"
          description="Early termination threshold (0.0-1.0, higher = more confident)"
          htmlFor="confidence_threshold"
        >
          <div className="flex items-center gap-4">
            <input
              type="range"
              id="confidence_threshold"
              min="0"
              max="1"
              step="0.01"
              value={config.confidence_threshold}
              onChange={(e) =>
                handleFieldChange('confidence_threshold', parseFloat(e.target.value))
              }
              className="flex-1 h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer"
              aria-valuemin={0}
              aria-valuemax={1}
              aria-valuenow={config.confidence_threshold}
            />
            <input
              type="number"
              min="0"
              max="1"
              step="0.01"
              value={config.confidence_threshold}
              onChange={(e) =>
                handleFieldChange('confidence_threshold', parseFloat(e.target.value) || 0)
              }
              className="w-24 px-3 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg text-sm"
              aria-label="Confidence threshold value"
            />
          </div>
        </SettingField>

        {/* Progressive Widening Alpha */}
        <SettingField
          label="Progressive Widening Alpha"
          description="Controls action space expansion (0.0-1.0)"
          htmlFor="progressive_widening_alpha"
        >
          <div className="flex items-center gap-4">
            <input
              type="range"
              id="progressive_widening_alpha"
              min="0"
              max="1"
              step="0.05"
              value={config.progressive_widening_alpha}
              onChange={(e) =>
                handleFieldChange('progressive_widening_alpha', parseFloat(e.target.value))
              }
              className="flex-1 h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer"
              aria-valuemin={0}
              aria-valuemax={1}
              aria-valuenow={config.progressive_widening_alpha}
            />
            <input
              type="number"
              min="0"
              max="1"
              step="0.05"
              value={config.progressive_widening_alpha}
              onChange={(e) =>
                handleFieldChange(
                  'progressive_widening_alpha',
                  parseFloat(e.target.value) || 0
                )
              }
              className="w-24 px-3 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg text-sm"
              aria-label="Progressive widening alpha value"
            />
          </div>
        </SettingField>

        {/* Discount Factor */}
        <SettingField
          label="Discount Factor"
          description="Future reward discount (0.0-1.0, 1.0 = no discount)"
          htmlFor="discount_factor"
        >
          <div className="flex items-center gap-4">
            <input
              type="range"
              id="discount_factor"
              min="0"
              max="1"
              step="0.01"
              value={config.discount_factor}
              onChange={(e) =>
                handleFieldChange('discount_factor', parseFloat(e.target.value))
              }
              className="flex-1 h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer"
              aria-valuemin={0}
              aria-valuemax={1}
              aria-valuenow={config.discount_factor}
            />
            <input
              type="number"
              min="0"
              max="1"
              step="0.01"
              value={config.discount_factor}
              onChange={(e) =>
                handleFieldChange('discount_factor', parseFloat(e.target.value) || 0)
              }
              className="w-24 px-3 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg text-sm"
              aria-label="Discount factor value"
            />
          </div>
        </SettingField>

        {/* Real-time Budget */}
        <SettingField
          label="Real-time Budget (ms)"
          description="Maximum time for real-time decisions (50-60,000 ms)"
          htmlFor="realtime_budget_ms"
        >
          <div className="flex items-center gap-4">
            <input
              type="range"
              id="realtime_budget_ms"
              min="50"
              max="5000"
              step="50"
              value={config.realtime_budget_ms}
              onChange={(e) =>
                handleFieldChange('realtime_budget_ms', parseInt(e.target.value))
              }
              className="flex-1 h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer"
              aria-valuemin={50}
              aria-valuemax={5000}
              aria-valuenow={config.realtime_budget_ms}
            />
            <input
              type="number"
              min="50"
              max="60000"
              step="50"
              value={config.realtime_budget_ms}
              onChange={(e) =>
                handleFieldChange('realtime_budget_ms', parseInt(e.target.value) || 50)
              }
              className="w-24 px-3 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg text-sm"
              aria-label="Real-time budget value"
            />
          </div>
        </SettingField>
      </div>

      {/* Reset Section Button */}
      <div className="pt-6 border-t border-gray-200 dark:border-gray-700">
        <button
          onClick={onReset}
          className="
            flex items-center gap-2 px-4 py-2 text-sm font-medium
            text-gray-700 dark:text-gray-300
            hover:bg-gray-100 dark:hover:bg-gray-700
            rounded-lg transition-colors
          "
          aria-label="Reset MCTS settings to defaults"
        >
          <RotateCcw className="w-4 h-4" />
          Reset to Defaults
        </button>
      </div>
    </div>
  );
}
