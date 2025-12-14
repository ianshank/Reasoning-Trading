import { useState, useEffect, useCallback, useRef } from 'react';
import { Settings } from '../types';

interface UseSettingsReturn {
  settings: Settings | null;
  updateSettings: (updates: Partial<Settings>) => Promise<void>;
  resetSettings: () => Promise<void>;
  isDirty: boolean;
  isSaving: boolean;
  isLoading: boolean;
  error: string | null;
  discardChanges: () => void;
}

/**
 * Custom hook for managing application settings.
 * Handles fetching, updating, and resetting settings with dirty state tracking.
 */
export function useSettings(): UseSettingsReturn {
  const [settings, setSettings] = useState<Settings | null>(null);
  const [originalSettings, setOriginalSettings] = useState<Settings | null>(null);
  const [isDirty, setIsDirty] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const abortControllerRef = useRef<AbortController | null>(null);

  /**
   * Fetch current settings from the API
   */
  const fetchSettings = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);

      abortControllerRef.current = new AbortController();

      const response = await fetch('/api/v1/settings', {
        signal: abortControllerRef.current.signal,
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch settings: ${response.statusText}`);
      }

      const data = await response.json();
      setSettings(data);
      setOriginalSettings(JSON.parse(JSON.stringify(data)));
      setIsDirty(false);
    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') {
        return;
      }
      setError(err instanceof Error ? err.message : 'Failed to fetch settings');
    } finally {
      setIsLoading(false);
    }
  }, []);

  /**
   * Update settings (partial update)
   */
  const updateSettings = useCallback(
    async (updates: Partial<Settings>) => {
      if (!settings) return;

      try {
        setIsSaving(true);
        setError(null);

        const updatedSettings = {
          ...settings,
          ...updates,
        };

        const response = await fetch('/api/v1/settings', {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(updates),
        });

        if (!response.ok) {
          throw new Error(`Failed to update settings: ${response.statusText}`);
        }

        const data = await response.json();
        setSettings(data);
        setOriginalSettings(JSON.parse(JSON.stringify(data)));
        setIsDirty(false);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to update settings');
        throw err;
      } finally {
        setIsSaving(false);
      }
    },
    [settings]
  );

  /**
   * Reset settings to defaults
   */
  const resetSettings = useCallback(async () => {
    try {
      setIsSaving(true);
      setError(null);

      const response = await fetch('/api/v1/settings/reset', {
        method: 'POST',
      });

      if (!response.ok) {
        throw new Error(`Failed to reset settings: ${response.statusText}`);
      }

      const data = await response.json();
      setSettings(data);
      setOriginalSettings(JSON.parse(JSON.stringify(data)));
      setIsDirty(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reset settings');
      throw err;
    } finally {
      setIsSaving(false);
    }
  }, []);

  /**
   * Discard unsaved changes
   */
  const discardChanges = useCallback(() => {
    if (originalSettings) {
      setSettings(JSON.parse(JSON.stringify(originalSettings)));
      setIsDirty(false);
    }
  }, [originalSettings]);

  /**
   * Update local settings state (marks as dirty)
   */
  const updateLocalSettings = useCallback(
    (updates: Partial<Settings>) => {
      if (!settings) return;

      const updatedSettings = {
        ...settings,
        ...updates,
      };

      setSettings(updatedSettings);
      setIsDirty(
        JSON.stringify(updatedSettings) !== JSON.stringify(originalSettings)
      );
    },
    [settings, originalSettings]
  );

  // Fetch settings on mount
  useEffect(() => {
    fetchSettings();

    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [fetchSettings]);

  return {
    settings,
    updateSettings,
    resetSettings,
    isDirty,
    isSaving,
    isLoading,
    error,
    discardChanges,
  };
}

/**
 * Hook for managing section-specific settings updates.
 * Provides optimistic updates with rollback on error.
 */
export function useSectionSettings<T>(
  settings: Settings | null,
  sectionKey: keyof Settings,
  onUpdate: (updates: Partial<Settings>) => Promise<void>
) {
  const [localSettings, setLocalSettings] = useState<T | null>(null);
  const [originalSettings, setOriginalSettings] = useState<T | null>(null);

  useEffect(() => {
    if (settings) {
      const sectionSettings = settings[sectionKey] as T;
      setLocalSettings(sectionSettings);
      setOriginalSettings(JSON.parse(JSON.stringify(sectionSettings)));
    }
  }, [settings, sectionKey]);

  const updateSection = useCallback(
    async (updates: Partial<T>) => {
      if (!localSettings) return;

      const previousSettings = localSettings;
      const updatedSettings = {
        ...localSettings,
        ...updates,
      };

      setLocalSettings(updatedSettings);

      try {
        await onUpdate({
          [sectionKey]: updatedSettings,
        } as Partial<Settings>);
      } catch (err) {
        setLocalSettings(previousSettings);
        throw err;
      }
    },
    [localSettings, sectionKey, onUpdate]
  );

  const resetSection = useCallback(() => {
    if (originalSettings) {
      setLocalSettings(JSON.parse(JSON.stringify(originalSettings)));
    }
  }, [originalSettings]);

  const isDirty =
    localSettings &&
    originalSettings &&
    JSON.stringify(localSettings) !== JSON.stringify(originalSettings);

  return {
    settings: localSettings,
    updateSettings: updateSection,
    resetSettings: resetSection,
    isDirty: Boolean(isDirty),
  };
}
