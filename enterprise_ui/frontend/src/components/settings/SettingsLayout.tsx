import React, { useState } from 'react';
import {
  Settings,
  Database,
  Shield,
  TrendingUp,
  Key,
  Bell,
  MessageSquare,
  Server,
  ToggleLeft,
  Save,
  RotateCcw,
  AlertTriangle,
} from 'lucide-react';

interface SettingsSection {
  id: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  description: string;
}

const SETTINGS_SECTIONS: SettingsSection[] = [
  {
    id: 'mcts',
    label: 'MCTS Configuration',
    icon: Settings,
    description: 'Monte Carlo Tree Search algorithm parameters',
  },
  {
    id: 'risk',
    label: 'Risk Management',
    icon: Shield,
    description: 'Position sizing and risk limits',
  },
  {
    id: 'trading',
    label: 'Trading Preferences',
    icon: TrendingUp,
    description: 'Default order types and trading modes',
  },
  {
    id: 'api-keys',
    label: 'API Keys',
    icon: Key,
    description: 'Manage API credentials',
  },
  {
    id: 'notifications',
    label: 'Notifications',
    icon: Bell,
    description: 'Alert and notification settings',
  },
  {
    id: 'debate',
    label: 'Multi-Agent Debate',
    icon: MessageSquare,
    description: 'Bull/Bear debate configuration',
  },
  {
    id: 'cache',
    label: 'Cache Settings',
    icon: Database,
    description: 'Redis cache configuration',
  },
  {
    id: 'feature-flags',
    label: 'Feature Flags',
    icon: ToggleLeft,
    description: 'Enable or disable features',
  },
  {
    id: 'api',
    label: 'API Server',
    icon: Server,
    description: 'REST API server configuration',
  },
];

interface SettingsLayoutProps {
  children: React.ReactNode;
  activeSection: string;
  onSectionChange: (section: string) => void;
  isDirty: boolean;
  isSaving: boolean;
  onSave: () => Promise<void>;
  onReset: () => void;
  onDiscardChanges: () => void;
}

export function SettingsLayout({
  children,
  activeSection,
  onSectionChange,
  isDirty,
  isSaving,
  onSave,
  onReset,
  onDiscardChanges,
}: SettingsLayoutProps) {
  const [showDiscardDialog, setShowDiscardDialog] = useState(false);
  const [pendingSection, setPendingSection] = useState<string | null>(null);

  const handleSectionChange = (sectionId: string) => {
    if (isDirty) {
      setPendingSection(sectionId);
      setShowDiscardDialog(true);
    } else {
      onSectionChange(sectionId);
    }
  };

  const handleConfirmDiscard = () => {
    onDiscardChanges();
    if (pendingSection) {
      onSectionChange(pendingSection);
    }
    setShowDiscardDialog(false);
    setPendingSection(null);
  };

  const handleCancelDiscard = () => {
    setShowDiscardDialog(false);
    setPendingSection(null);
  };

  const handleSave = async () => {
    try {
      await onSave();
    } catch (error) {
      console.error('Failed to save settings:', error);
    }
  };

  return (
    <div className="flex h-full bg-gray-50 dark:bg-gray-900">
      {/* Sidebar Navigation */}
      <aside className="w-72 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 overflow-y-auto">
        <div className="p-6">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
            Settings
          </h1>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Configure your trading system
          </p>
        </div>

        <nav className="px-3 pb-6" role="navigation" aria-label="Settings sections">
          {SETTINGS_SECTIONS.map((section) => {
            const Icon = section.icon;
            const isActive = activeSection === section.id;

            return (
              <button
                key={section.id}
                onClick={() => handleSectionChange(section.id)}
                className={`
                  w-full flex items-start gap-3 px-3 py-3 mb-1 rounded-lg
                  transition-colors duration-150 text-left
                  ${
                    isActive
                      ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300'
                      : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                  }
                `}
                aria-current={isActive ? 'page' : undefined}
              >
                <Icon
                  className={`w-5 h-5 mt-0.5 flex-shrink-0 ${
                    isActive
                      ? 'text-blue-700 dark:text-blue-300'
                      : 'text-gray-500 dark:text-gray-400'
                  }`}
                />
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-sm">{section.label}</div>
                  <div className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                    {section.description}
                  </div>
                </div>
              </button>
            );
          })}
        </nav>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Unsaved Changes Banner */}
        {isDirty && (
          <div
            className="bg-amber-50 dark:bg-amber-900/20 border-b border-amber-200 dark:border-amber-800 px-6 py-3"
            role="alert"
            aria-live="polite"
          >
            <div className="flex items-center gap-2 text-amber-900 dark:text-amber-200">
              <AlertTriangle className="w-5 h-5" />
              <span className="font-medium">You have unsaved changes</span>
            </div>
          </div>
        )}

        {/* Content */}
        <div className="flex-1 overflow-y-auto">
          <div className="max-w-4xl mx-auto p-6">{children}</div>
        </div>

        {/* Action Bar */}
        <div className="border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-6 py-4">
          <div className="max-w-4xl mx-auto flex items-center justify-between">
            <button
              onClick={onReset}
              disabled={isSaving}
              className="
                flex items-center gap-2 px-4 py-2 text-sm font-medium
                text-gray-700 dark:text-gray-300
                hover:bg-gray-100 dark:hover:bg-gray-700
                rounded-lg transition-colors
                disabled:opacity-50 disabled:cursor-not-allowed
              "
              aria-label="Reset to default settings"
            >
              <RotateCcw className="w-4 h-4" />
              Reset to Defaults
            </button>

            <div className="flex items-center gap-3">
              {isDirty && (
                <button
                  onClick={onDiscardChanges}
                  disabled={isSaving}
                  className="
                    px-4 py-2 text-sm font-medium
                    text-gray-700 dark:text-gray-300
                    hover:bg-gray-100 dark:hover:bg-gray-700
                    rounded-lg transition-colors
                    disabled:opacity-50 disabled:cursor-not-allowed
                  "
                >
                  Discard Changes
                </button>
              )}
              <button
                onClick={handleSave}
                disabled={!isDirty || isSaving}
                className="
                  flex items-center gap-2 px-4 py-2 text-sm font-medium
                  text-white bg-blue-600 hover:bg-blue-700
                  dark:bg-blue-500 dark:hover:bg-blue-600
                  rounded-lg transition-colors
                  disabled:opacity-50 disabled:cursor-not-allowed
                "
                aria-label="Save settings"
              >
                <Save className="w-4 h-4" />
                {isSaving ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          </div>
        </div>
      </main>

      {/* Discard Changes Confirmation Dialog */}
      {showDiscardDialog && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
          role="dialog"
          aria-modal="true"
          aria-labelledby="discard-dialog-title"
        >
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full mx-4 p-6">
            <div className="flex items-start gap-4">
              <div className="flex-shrink-0 w-10 h-10 rounded-full bg-amber-100 dark:bg-amber-900/20 flex items-center justify-center">
                <AlertTriangle className="w-5 h-5 text-amber-600 dark:text-amber-400" />
              </div>
              <div className="flex-1">
                <h2
                  id="discard-dialog-title"
                  className="text-lg font-semibold text-gray-900 dark:text-white mb-2"
                >
                  Discard unsaved changes?
                </h2>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  You have unsaved changes in the current section. If you navigate away,
                  your changes will be lost.
                </p>
              </div>
            </div>

            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={handleCancelDiscard}
                className="
                  px-4 py-2 text-sm font-medium
                  text-gray-700 dark:text-gray-300
                  hover:bg-gray-100 dark:hover:bg-gray-700
                  rounded-lg transition-colors
                "
              >
                Keep Editing
              </button>
              <button
                onClick={handleConfirmDiscard}
                className="
                  px-4 py-2 text-sm font-medium
                  text-white bg-red-600 hover:bg-red-700
                  dark:bg-red-500 dark:hover:bg-red-600
                  rounded-lg transition-colors
                "
              >
                Discard Changes
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
