import React, { useState } from 'react';
import { Key, Eye, EyeOff, CheckCircle, XCircle, AlertCircle, Loader } from 'lucide-react';
import { LLMSettings, TradingSettings, DataAPISettings, APIKeyStatus } from './types';

interface APIKeysPanelProps {
  config: {
    llm: LLMSettings;
    trading: TradingSettings;
    data_apis: DataAPISettings;
  } | null;
  keyStatus: APIKeyStatus;
  onTest: (keyType: keyof APIKeyStatus) => Promise<void>;
  onUpdate: (updates: {
    llm?: Partial<LLMSettings>;
    trading?: Partial<TradingSettings>;
    data_apis?: Partial<DataAPISettings>;
  }) => Promise<void>;
}

interface APIKeyFieldProps {
  label: string;
  keyType: keyof APIKeyStatus;
  value: string | null;
  status: 'valid' | 'invalid' | 'expired' | 'not_set';
  onUpdate: (value: string) => Promise<void>;
  onTest: () => Promise<void>;
  description?: string;
}

function APIKeyField({
  label,
  keyType,
  value,
  status,
  onUpdate,
  onTest,
  description,
}: APIKeyFieldProps) {
  const [isVisible, setIsVisible] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editValue, setEditValue] = useState('');
  const [isTesting, setIsTesting] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  const statusConfig = {
    valid: {
      icon: CheckCircle,
      color: 'text-green-600 dark:text-green-400',
      bgColor: 'bg-green-50 dark:bg-green-900/20',
      label: 'Valid',
    },
    invalid: {
      icon: XCircle,
      color: 'text-red-600 dark:text-red-400',
      bgColor: 'bg-red-50 dark:bg-red-900/20',
      label: 'Invalid',
    },
    expired: {
      icon: AlertCircle,
      color: 'text-orange-600 dark:text-orange-400',
      bgColor: 'bg-orange-50 dark:bg-orange-900/20',
      label: 'Expired',
    },
    not_set: {
      icon: AlertCircle,
      color: 'text-gray-600 dark:text-gray-400',
      bgColor: 'bg-gray-50 dark:bg-gray-800',
      label: 'Not Set',
    },
  };

  const config = statusConfig[status];
  const StatusIcon = config.icon;

  const maskKey = (key: string) => {
    if (key.length <= 8) return '••••••••';
    return key.slice(0, 4) + '••••••••' + key.slice(-4);
  };

  const handleEdit = () => {
    setEditValue(value || '');
    setIsEditing(true);
  };

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await onUpdate(editValue);
      setIsEditing(false);
    } catch (error) {
      console.error('Failed to update API key:', error);
    } finally {
      setIsSaving(false);
    }
  };

  const handleCancel = () => {
    setEditValue('');
    setIsEditing(false);
  };

  const handleTest = async () => {
    setIsTesting(true);
    try {
      await onTest();
    } finally {
      setIsTesting(false);
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex items-start justify-between">
        <div>
          <label className="block text-sm font-medium text-gray-900 dark:text-white">
            {label}
          </label>
          {description && (
            <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">{description}</p>
          )}
        </div>
        <div className={`flex items-center gap-2 px-3 py-1 rounded-full ${config.bgColor}`}>
          <StatusIcon className={`w-4 h-4 ${config.color}`} />
          <span className={`text-xs font-medium ${config.color}`}>{config.label}</span>
        </div>
      </div>

      {isEditing ? (
        <div className="space-y-2">
          <div className="relative">
            <input
              type={isVisible ? 'text' : 'password'}
              value={editValue}
              onChange={(e) => setEditValue(e.target.value)}
              placeholder="Enter API key"
              className="
                w-full px-4 py-2 pr-12
                bg-white dark:bg-gray-800
                border border-gray-300 dark:border-gray-600
                rounded-lg text-sm
                focus:ring-2 focus:ring-blue-500 focus:border-transparent
              "
              aria-label={`${label} input`}
            />
            <button
              type="button"
              onClick={() => setIsVisible(!isVisible)}
              className="
                absolute right-3 top-1/2 -translate-y-1/2
                text-gray-500 dark:text-gray-400
                hover:text-gray-700 dark:hover:text-gray-300
              "
              aria-label={isVisible ? 'Hide API key' : 'Show API key'}
            >
              {isVisible ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          </div>
          <div className="flex gap-2">
            <button
              onClick={handleSave}
              disabled={isSaving}
              className="
                px-4 py-2 text-sm font-medium
                text-white bg-blue-600 hover:bg-blue-700
                dark:bg-blue-500 dark:hover:bg-blue-600
                rounded-lg transition-colors
                disabled:opacity-50 disabled:cursor-not-allowed
              "
            >
              {isSaving ? 'Saving...' : 'Save'}
            </button>
            <button
              onClick={handleCancel}
              disabled={isSaving}
              className="
                px-4 py-2 text-sm font-medium
                text-gray-700 dark:text-gray-300
                hover:bg-gray-100 dark:hover:bg-gray-700
                rounded-lg transition-colors
                disabled:opacity-50 disabled:cursor-not-allowed
              "
            >
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <div className="flex items-center gap-2">
          <div className="flex-1 px-4 py-2 bg-gray-50 dark:bg-gray-800 rounded-lg text-sm font-mono text-gray-700 dark:text-gray-300">
            {value ? (isVisible ? value : maskKey(value)) : 'Not configured'}
          </div>
          {value && (
            <button
              type="button"
              onClick={() => setIsVisible(!isVisible)}
              className="
                p-2 text-gray-500 dark:text-gray-400
                hover:bg-gray-100 dark:hover:bg-gray-700
                rounded-lg transition-colors
              "
              aria-label={isVisible ? 'Hide API key' : 'Show API key'}
            >
              {isVisible ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          )}
          <button
            onClick={handleEdit}
            className="
              px-4 py-2 text-sm font-medium
              text-gray-700 dark:text-gray-300
              hover:bg-gray-100 dark:hover:bg-gray-700
              rounded-lg transition-colors
            "
          >
            {value ? 'Update' : 'Set Key'}
          </button>
          {value && (
            <button
              onClick={handleTest}
              disabled={isTesting}
              className="
                px-4 py-2 text-sm font-medium
                text-blue-700 dark:text-blue-300
                hover:bg-blue-50 dark:hover:bg-blue-900/20
                rounded-lg transition-colors
                disabled:opacity-50 disabled:cursor-not-allowed
              "
            >
              {isTesting ? (
                <Loader className="w-4 h-4 animate-spin" />
              ) : (
                'Test'
              )}
            </button>
          )}
        </div>
      )}
    </div>
  );
}

export function APIKeysPanel({ config, keyStatus, onTest, onUpdate }: APIKeysPanelProps) {
  if (!config) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500 dark:text-gray-400">Loading API key settings...</p>
      </div>
    );
  }

  const { llm, trading, data_apis } = config;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
          API Keys
        </h2>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Manage API credentials for trading, LLM providers, and data sources
        </p>
      </div>

      {/* Security Notice */}
      <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
        <div className="flex gap-3">
          <Key className="w-5 h-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-blue-900 dark:text-blue-200">
            <p className="font-medium mb-1">Security Best Practices</p>
            <p>
              API keys are encrypted and stored securely. Never share your keys or commit
              them to version control. Test connections after updating keys to ensure
              they are valid.
            </p>
          </div>
        </div>
      </div>

      {/* Trading Platform */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
          Trading Platform (Alpaca)
        </h3>

        <APIKeyField
          label="Alpaca API Key"
          keyType="alpaca"
          value={trading.api_key}
          status={keyStatus.alpaca}
          onUpdate={async (value) => {
            await onUpdate({ trading: { api_key: value } });
          }}
          onTest={() => onTest('alpaca')}
          description="Your Alpaca API key for trading"
        />

        <APIKeyField
          label="Alpaca Secret Key"
          keyType="alpaca"
          value={trading.secret_key}
          status={keyStatus.alpaca}
          onUpdate={async (value) => {
            await onUpdate({ trading: { secret_key: value } });
          }}
          onTest={() => onTest('alpaca')}
          description="Your Alpaca secret key"
        />
      </div>

      {/* LLM Providers */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
          LLM Providers
        </h3>

        <APIKeyField
          label="OpenAI API Key"
          keyType="openai"
          value={llm.openai_api_key}
          status={keyStatus.openai}
          onUpdate={async (value) => {
            await onUpdate({ llm: { openai_api_key: value } });
          }}
          onTest={() => onTest('openai')}
          description="For GPT-4 and other OpenAI models"
        />

        <APIKeyField
          label="Anthropic API Key"
          keyType="anthropic"
          value={llm.anthropic_api_key}
          status={keyStatus.anthropic}
          onUpdate={async (value) => {
            await onUpdate({ llm: { anthropic_api_key: value } });
          }}
          onTest={() => onTest('anthropic')}
          description="For Claude and other Anthropic models"
        />

        <APIKeyField
          label="LangChain API Key"
          keyType="openai"
          value={llm.langchain_api_key}
          status={keyStatus.openai}
          onUpdate={async (value) => {
            await onUpdate({ llm: { langchain_api_key: value } });
          }}
          onTest={() => onTest('openai')}
          description="For LangSmith tracing (optional)"
        />
      </div>

      {/* Data APIs */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
          Data Sources
        </h3>

        <APIKeyField
          label="Finnhub API Key"
          keyType="finnhub"
          value={data_apis.finnhub_api_key}
          status={keyStatus.finnhub}
          onUpdate={async (value) => {
            await onUpdate({ data_apis: { finnhub_api_key: value } });
          }}
          onTest={() => onTest('finnhub')}
          description="For market data and financial news"
        />

        <APIKeyField
          label="FRED API Key"
          keyType="fred"
          value={data_apis.fred_api_key}
          status={keyStatus.fred}
          onUpdate={async (value) => {
            await onUpdate({ data_apis: { fred_api_key: value } });
          }}
          onTest={() => onTest('fred')}
          description="Federal Reserve Economic Data"
        />

        <APIKeyField
          label="CoinDesk API Key"
          keyType="coindesk"
          value={data_apis.coindesk_api_key}
          status={keyStatus.coindesk}
          onUpdate={async (value) => {
            await onUpdate({ data_apis: { coindesk_api_key: value } });
          }}
          onTest={() => onTest('coindesk')}
          description="For cryptocurrency data (optional)"
        />
      </div>
    </div>
  );
}
