import React from 'react';
import { MessageSquare, Users, Globe, RotateCcw, Info } from 'lucide-react';
import { DebateSettings as DebateSettingsType } from './types';

interface DebateSettingsProps {
  config: DebateSettingsType | null;
  onChange: (updates: Partial<DebateSettingsType>) => void;
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

export function DebateSettings({ config, onChange, onReset }: DebateSettingsProps) {
  if (!config) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500 dark:text-gray-400">Loading debate settings...</p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
          Multi-Agent Debate Configuration
        </h2>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Configure the Bull/Bear debate and multi-agent reasoning system
        </p>
      </div>

      {/* Info Banner */}
      <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
        <div className="flex gap-3">
          <Info className="w-5 h-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-blue-900 dark:text-blue-200">
            <p className="font-medium mb-1">About Multi-Agent Debate</p>
            <p>
              The system uses multiple AI agents (Bull, Bear, Risk Manager, etc.) that
              debate trading decisions. More rounds lead to more thorough analysis but
              increase LLM API costs and response time.
            </p>
          </div>
        </div>
      </div>

      {/* Debate Rounds */}
      <div className="space-y-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
          Debate Parameters
        </h3>

        {/* Max Debate Rounds */}
        <div className="space-y-2">
          <label
            htmlFor="max_debate_rounds"
            className="block text-sm font-medium text-gray-900 dark:text-white"
          >
            Maximum Debate Rounds
          </label>
          <p className="text-xs text-gray-600 dark:text-gray-400">
            Number of Bull/Bear debate rounds (1-10)
          </p>
          <div className="flex items-center gap-4">
            <input
              type="range"
              id="max_debate_rounds"
              min="1"
              max="10"
              step="1"
              value={config.max_debate_rounds}
              onChange={(e) =>
                onChange({
                  max_debate_rounds: parseInt(e.target.value),
                })
              }
              className="flex-1 h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer"
              aria-valuemin={1}
              aria-valuemax={10}
              aria-valuenow={config.max_debate_rounds}
            />
            <input
              type="number"
              min="1"
              max="10"
              value={config.max_debate_rounds}
              onChange={(e) =>
                onChange({
                  max_debate_rounds: parseInt(e.target.value) || 1,
                })
              }
              className="w-20 px-3 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg text-sm"
              aria-label="Maximum debate rounds value"
            />
          </div>
        </div>

        {/* Max Risk Discussion Rounds */}
        <div className="space-y-2">
          <label
            htmlFor="max_risk_rounds"
            className="block text-sm font-medium text-gray-900 dark:text-white"
          >
            Maximum Risk Discussion Rounds
          </label>
          <p className="text-xs text-gray-600 dark:text-gray-400">
            Number of risk assessment rounds (1-10)
          </p>
          <div className="flex items-center gap-4">
            <input
              type="range"
              id="max_risk_rounds"
              min="1"
              max="10"
              step="1"
              value={config.max_risk_discuss_rounds}
              onChange={(e) =>
                onChange({
                  max_risk_discuss_rounds: parseInt(e.target.value),
                })
              }
              className="flex-1 h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer"
              aria-valuemin={1}
              aria-valuemax={10}
              aria-valuenow={config.max_risk_discuss_rounds}
            />
            <input
              type="number"
              min="1"
              max="10"
              value={config.max_risk_discuss_rounds}
              onChange={(e) =>
                onChange({
                  max_risk_discuss_rounds: parseInt(e.target.value) || 1,
                })
              }
              className="w-20 px-3 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg text-sm"
              aria-label="Maximum risk discussion rounds value"
            />
          </div>
        </div>
      </div>

      {/* Feature Toggles */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
          Agent Features
        </h3>

        <div className="space-y-4">
          <ToggleSwitch
            id="enable_parallel"
            label="Enable Parallel Analysts"
            description="Run multiple analysts simultaneously for faster processing"
            checked={config.enable_parallel_analysts}
            onChange={(checked) =>
              onChange({ enable_parallel_analysts: checked })
            }
            icon={Users}
          />

          <ToggleSwitch
            id="enable_online_tools"
            label="Enable Online Tools"
            description="Allow agents to fetch real-time data from the internet"
            checked={config.enable_online_tools}
            onChange={(checked) => onChange({ enable_online_tools: checked })}
            icon={Globe}
          />
        </div>
      </div>

      {/* Performance Impact */}
      <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-4">
          Performance Impact
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          <div>
            <div className="text-gray-600 dark:text-gray-400 mb-1">
              Estimated Analysis Time
            </div>
            <div className="text-lg font-semibold text-gray-900 dark:text-white">
              {config.enable_parallel_analysts
                ? Math.ceil(
                    (config.max_debate_rounds + config.max_risk_discuss_rounds) * 15
                  )
                : (config.max_debate_rounds + config.max_risk_discuss_rounds) * 30}
              s
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-500 mt-1">
              {config.enable_parallel_analysts ? 'Parallel mode' : 'Sequential mode'}
            </div>
          </div>
          <div>
            <div className="text-gray-600 dark:text-gray-400 mb-1">
              Estimated LLM Calls
            </div>
            <div className="text-lg font-semibold text-gray-900 dark:text-white">
              {(config.max_debate_rounds * 2 + config.max_risk_discuss_rounds * 3) +
                (config.enable_online_tools ? 5 : 0)}
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-500 mt-1">
              {config.enable_online_tools
                ? 'Including online tool calls'
                : 'Offline analysis only'}
            </div>
          </div>
        </div>
      </div>

      {/* Preset Configurations */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
          Quick Presets
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <button
            onClick={() =>
              onChange({
                max_debate_rounds: 2,
                max_risk_discuss_rounds: 2,
                enable_parallel_analysts: true,
                enable_online_tools: false,
              })
            }
            className="
              p-4 rounded-lg border-2 border-gray-200 dark:border-gray-700
              hover:border-blue-500 dark:hover:border-blue-500
              text-left transition-all
            "
          >
            <div className="font-medium text-gray-900 dark:text-white mb-1">Fast</div>
            <div className="text-xs text-gray-600 dark:text-gray-400">
              Quick decisions with minimal debate
            </div>
          </button>

          <button
            onClick={() =>
              onChange({
                max_debate_rounds: 4,
                max_risk_discuss_rounds: 3,
                enable_parallel_analysts: true,
                enable_online_tools: true,
              })
            }
            className="
              p-4 rounded-lg border-2 border-gray-200 dark:border-gray-700
              hover:border-blue-500 dark:hover:border-blue-500
              text-left transition-all
            "
          >
            <div className="font-medium text-gray-900 dark:text-white mb-1">
              Balanced
            </div>
            <div className="text-xs text-gray-600 dark:text-gray-400">
              Standard debate with online tools
            </div>
          </button>

          <button
            onClick={() =>
              onChange({
                max_debate_rounds: 6,
                max_risk_discuss_rounds: 5,
                enable_parallel_analysts: true,
                enable_online_tools: true,
              })
            }
            className="
              p-4 rounded-lg border-2 border-gray-200 dark:border-gray-700
              hover:border-blue-500 dark:hover:border-blue-500
              text-left transition-all
            "
          >
            <div className="font-medium text-gray-900 dark:text-white mb-1">
              Thorough
            </div>
            <div className="text-xs text-gray-600 dark:text-gray-400">
              Deep analysis with extensive debate
            </div>
          </button>
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
          aria-label="Reset debate settings to defaults"
        >
          <RotateCcw className="w-4 h-4" />
          Reset to Defaults
        </button>
      </div>
    </div>
  );
}
