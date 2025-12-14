/**
 * MCTS Search Control Panel Component
 *
 * Provides controls for configuring and managing MCTS search,
 * including iteration count, exploration parameters, and search mode.
 */

import React, { useState } from 'react';
import type { MCTSSearchConfig } from './hooks/useMCTSWebSocket';
import { Card, CardHeader, CardBody } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';

/**
 * MCTSControls component props
 */
export interface MCTSControlsProps {
  /**
   * Current search configuration
   */
  config: MCTSSearchConfig;

  /**
   * Callback when configuration changes
   */
  onConfigChange: (config: MCTSSearchConfig) => void;

  /**
   * Callback when search is started
   */
  onStartSearch: (config: MCTSSearchConfig) => void;

  /**
   * Callback when search is stopped
   */
  onStopSearch: () => void;

  /**
   * Whether the search is currently running
   * @default false
   */
  isSearching?: boolean;

  /**
   * Whether controls are disabled
   * @default false
   */
  disabled?: boolean;

  /**
   * Additional CSS classes
   */
  className?: string;
}

/**
 * Slider input component
 */
const SliderInput: React.FC<{
  label: string;
  value: number;
  onChange: (value: number) => void;
  min: number;
  max: number;
  step: number;
  disabled?: boolean;
  description?: string;
}> = ({ label, value, onChange, min, max, step, disabled, description }) => (
  <div className="space-y-2">
    <div className="flex items-center justify-between">
      <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
        {label}
      </label>
      <span className="text-sm font-semibold text-blue-600 dark:text-blue-400">
        {value}
      </span>
    </div>
    <input
      type="range"
      min={min}
      max={max}
      step={step}
      value={value}
      onChange={(e) => onChange(parseFloat(e.target.value))}
      disabled={disabled}
      className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer accent-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
      aria-label={label}
      aria-valuemin={min}
      aria-valuemax={max}
      aria-valuenow={value}
    />
    {description && (
      <p className="text-xs text-gray-500 dark:text-gray-400">{description}</p>
    )}
  </div>
);

/**
 * MCTS search control panel
 *
 * Features:
 * - Start/stop search buttons
 * - Simulation count slider (10-1000)
 * - Exploration weight slider (0.5-3.0)
 * - Temperature slider (0.1-2.0)
 * - Time budget input (optional)
 * - Parallel simulations slider
 * - Policy prior toggle
 *
 * @example
 * ```tsx
 * <MCTSControls
 *   config={searchConfig}
 *   onConfigChange={setSearchConfig}
 *   onStartSearch={handleStart}
 *   onStopSearch={handleStop}
 *   isSearching={isRunning}
 * />
 * ```
 */
export const MCTSControls: React.FC<MCTSControlsProps> = ({
  config,
  onConfigChange,
  onStartSearch,
  onStopSearch,
  isSearching = false,
  disabled = false,
  className = '',
}) => {
  const [localConfig, setLocalConfig] = useState<MCTSSearchConfig>(config);

  const handleConfigChange = <K extends keyof MCTSSearchConfig>(
    key: K,
    value: MCTSSearchConfig[K]
  ) => {
    const newConfig = { ...localConfig, [key]: value };
    setLocalConfig(newConfig);
    onConfigChange(newConfig);
  };

  const handleStartSearch = () => {
    onStartSearch(localConfig);
  };

  const handleStopSearch = () => {
    onStopSearch();
  };

  const handleReset = () => {
    const defaultConfig: MCTSSearchConfig = {
      maxIterations: 100,
      explorationConstant: 1.414,
      temperature: 1.0,
      usePolicyPrior: true,
      parallelSimulations: 4,
      timeBudgetMs: undefined,
    };
    setLocalConfig(defaultConfig);
    onConfigChange(defaultConfig);
  };

  const isDisabled = disabled || isSearching;

  return (
    <Card className={className}>
      <CardHeader
        title="Search Controls"
        actions={
          <Button
            variant="ghost"
            size="sm"
            onClick={handleReset}
            disabled={isDisabled}
            aria-label="Reset to default settings"
          >
            Reset
          </Button>
        }
      />

      <CardBody>
        <div className="space-y-6">
          {/* Search Actions */}
          <div className="flex gap-3">
            {!isSearching ? (
              <Button
                variant="primary"
                fullWidth
                onClick={handleStartSearch}
                disabled={disabled}
                aria-label="Start MCTS search"
              >
                Start Search
              </Button>
            ) : (
              <Button
                variant="danger"
                fullWidth
                onClick={handleStopSearch}
                disabled={disabled}
                aria-label="Stop MCTS search"
              >
                Stop Search
              </Button>
            )}
          </div>

          {/* Simulation Count */}
          <SliderInput
            label="Max Iterations"
            value={localConfig.maxIterations}
            onChange={(value) =>
              handleConfigChange('maxIterations', Math.round(value))
            }
            min={10}
            max={1000}
            step={10}
            disabled={isDisabled}
            description="Number of MCTS iterations to perform"
          />

          {/* Exploration Constant */}
          <SliderInput
            label="Exploration Constant"
            value={localConfig.explorationConstant}
            onChange={(value) =>
              handleConfigChange('explorationConstant', value)
            }
            min={0.5}
            max={3.0}
            step={0.1}
            disabled={isDisabled}
            description="UCB exploration weight (√2 ≈ 1.414 is standard)"
          />

          {/* Temperature */}
          <SliderInput
            label="Temperature"
            value={localConfig.temperature}
            onChange={(value) => handleConfigChange('temperature', value)}
            min={0.1}
            max={2.0}
            step={0.1}
            disabled={isDisabled}
            description="Action selection temperature (higher = more exploration)"
          />

          {/* Parallel Simulations */}
          <SliderInput
            label="Parallel Simulations"
            value={localConfig.parallelSimulations}
            onChange={(value) =>
              handleConfigChange('parallelSimulations', Math.round(value))
            }
            min={1}
            max={16}
            step={1}
            disabled={isDisabled}
            description="Number of parallel rollouts per iteration"
          />

          {/* Time Budget */}
          <div className="space-y-2">
            <label
              htmlFor="timeBudget"
              className="text-sm font-medium text-gray-700 dark:text-gray-300"
            >
              Time Budget (ms)
            </label>
            <Input
              id="timeBudget"
              type="number"
              value={localConfig.timeBudgetMs ?? ''}
              onChange={(e) => {
                const value = e.target.value;
                handleConfigChange(
                  'timeBudgetMs',
                  value ? parseInt(value, 10) : undefined
                );
              }}
              placeholder="Optional (unlimited if empty)"
              disabled={isDisabled}
              min={1000}
              max={300000}
              step={1000}
              aria-label="Time budget in milliseconds"
            />
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Maximum time for search (optional)
            </p>
          </div>

          {/* Policy Prior Toggle */}
          <div className="flex items-center justify-between border-t border-gray-200 dark:border-gray-700 pt-4">
            <div className="flex-1">
              <label
                htmlFor="usePolicyPrior"
                className="text-sm font-medium text-gray-700 dark:text-gray-300 cursor-pointer"
              >
                Use Policy Prior
              </label>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                Use neural network priors for action selection (PUCT)
              </p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                id="usePolicyPrior"
                type="checkbox"
                checked={localConfig.usePolicyPrior}
                onChange={(e) =>
                  handleConfigChange('usePolicyPrior', e.target.checked)
                }
                disabled={isDisabled}
                className="sr-only peer"
                aria-label="Toggle policy prior"
              />
              <div className="w-11 h-6 bg-gray-200 dark:bg-gray-700 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 dark:peer-focus:ring-blue-800 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"></div>
            </label>
          </div>

          {/* Summary */}
          <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
            <h4 className="text-sm font-semibold mb-3 text-gray-900 dark:text-gray-100">
              Configuration Summary
            </h4>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">
                  Max Iterations:
                </span>
                <span className="font-medium text-gray-900 dark:text-gray-100">
                  {localConfig.maxIterations}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">
                  Exploration:
                </span>
                <span className="font-medium text-gray-900 dark:text-gray-100">
                  {localConfig.explorationConstant.toFixed(2)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">
                  Temperature:
                </span>
                <span className="font-medium text-gray-900 dark:text-gray-100">
                  {localConfig.temperature.toFixed(2)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">
                  Parallel:
                </span>
                <span className="font-medium text-gray-900 dark:text-gray-100">
                  {localConfig.parallelSimulations}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">
                  Time Budget:
                </span>
                <span className="font-medium text-gray-900 dark:text-gray-100">
                  {localConfig.timeBudgetMs
                    ? `${localConfig.timeBudgetMs}ms`
                    : 'Unlimited'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">
                  Policy Prior:
                </span>
                <span className="font-medium text-gray-900 dark:text-gray-100">
                  {localConfig.usePolicyPrior ? 'Yes' : 'No'}
                </span>
              </div>
            </div>
          </div>
        </div>
      </CardBody>
    </Card>
  );
};

MCTSControls.displayName = 'MCTSControls';
