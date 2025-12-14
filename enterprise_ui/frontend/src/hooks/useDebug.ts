/**
 * React debugging hook for component monitoring and performance tracking.
 *
 * Features:
 * - Component render tracking
 * - Prop change detection
 * - Performance metrics
 * - State change monitoring
 * - Lifecycle logging
 */

import { useEffect, useRef, useState, useMemo } from 'react';
import { logger, createLogger, LogContext } from '../lib/logger';
import { isDebugMode, StateDebugger } from '../lib/debug';

export interface RenderInfo {
  count: number;
  lastRender: number;
  averageRenderTime: number;
  totalRenderTime: number;
}

export interface PropChange {
  prop: string;
  oldValue: any;
  newValue: any;
  timestamp: number;
}

export interface UseDebugOptions {
  /** Component name for logging */
  component: string;
  /** Whether to log renders */
  logRenders?: boolean;
  /** Whether to track prop changes */
  trackProps?: boolean;
  /** Whether to track state changes */
  trackState?: boolean;
  /** Whether to measure render performance */
  measurePerformance?: boolean;
  /** Additional context for logging */
  context?: LogContext;
  /** Only enable in debug mode */
  enabledInProduction?: boolean;
}

export interface DebugInfo {
  renderInfo: RenderInfo;
  propChanges: PropChange[];
  lastProps: any;
  isEnabled: boolean;
  logRender: (message?: string, data?: any) => void;
  logStateChange: (stateName: string, oldValue: any, newValue: any) => void;
  startMeasure: (name: string) => void;
  endMeasure: (name: string) => void;
}

/**
 * Hook for debugging React components
 *
 * @example
 * ```tsx
 * function MyComponent({ userId, data }) {
 *   const debug = useDebug({
 *     component: 'MyComponent',
 *     logRenders: true,
 *     trackProps: true,
 *   });
 *
 *   const [state, setState] = useState(initialState);
 *
 *   useEffect(() => {
 *     debug.logRender('Component mounted');
 *   }, []);
 *
 *   return <div>...</div>;
 * }
 * ```
 */
export function useDebug(options: UseDebugOptions): DebugInfo {
  const {
    component,
    logRenders = true,
    trackProps = true,
    trackState = false,
    measurePerformance = true,
    context = {},
    enabledInProduction = false,
  } = options;

  // Check if debugging is enabled
  const isEnabled = enabledInProduction || isDebugMode();

  // Create component-specific logger
  const componentLogger = useMemo(
    () => createLogger(component, context),
    [component, context]
  );

  // Track render count and timing
  const renderCount = useRef(0);
  const renderTimes = useRef<number[]>([]);
  const renderStartTime = useRef<number>(0);
  const lastRenderTime = useRef<number>(Date.now());

  // Track prop changes
  const previousProps = useRef<any>(null);
  const propChanges = useRef<PropChange[]>([]);

  // Performance measurements
  const measurements = useRef<Map<string, number>>(new Map());

  // State debugger
  const stateDebugger = useRef<StateDebugger | null>(null);

  if (trackState && !stateDebugger.current && isEnabled) {
    stateDebugger.current = new StateDebugger(`${component}_state`);
  }

  // Track render start time
  if (measurePerformance && isEnabled) {
    renderStartTime.current = performance.now();
  }

  // Increment render count
  renderCount.current += 1;

  // Detect prop changes
  useEffect(() => {
    if (!isEnabled || !trackProps) return;

    // Skip first render
    if (previousProps.current !== null) {
      const changes = detectPropChanges(
        previousProps.current,
        options as any
      );

      if (changes.length > 0) {
        propChanges.current.push(...changes);

        // Keep only recent changes (last 50)
        if (propChanges.current.length > 50) {
          propChanges.current = propChanges.current.slice(-50);
        }

        componentLogger.debug('Props changed', {
          changes: changes.map((c) => ({
            prop: c.prop,
            oldValue: c.oldValue,
            newValue: c.newValue,
          })),
        });
      }
    }

    previousProps.current = { ...options };
  });

  // Log renders
  useEffect(() => {
    if (!isEnabled) return;

    const renderTime = measurePerformance
      ? performance.now() - renderStartTime.current
      : 0;

    if (measurePerformance) {
      renderTimes.current.push(renderTime);
      // Keep only last 100 render times
      if (renderTimes.current.length > 100) {
        renderTimes.current.shift();
      }
    }

    lastRenderTime.current = Date.now();

    if (logRenders) {
      const renderInfo: any = {
        renderCount: renderCount.current,
      };

      if (measurePerformance) {
        renderInfo.renderTime_ms = Math.round(renderTime * 100) / 100;
      }

      if (propChanges.current.length > 0) {
        renderInfo.recentPropChanges = propChanges.current.slice(-5).map(c => c.prop);
      }

      componentLogger.debug('Component rendered', renderInfo);
    }
  });

  // Log mount and unmount
  useEffect(() => {
    if (!isEnabled) return;

    componentLogger.info('Component mounted');

    return () => {
      componentLogger.info('Component unmounted', {
        totalRenders: renderCount.current,
        averageRenderTime:
          renderTimes.current.length > 0
            ? Math.round(
                (renderTimes.current.reduce((a, b) => a + b, 0) /
                  renderTimes.current.length) *
                  100
              ) / 100
            : 0,
      });
    };
  }, []);

  // Helper functions
  const logRender = (message?: string, data?: any) => {
    if (!isEnabled) return;
    componentLogger.debug(message || 'Manual render log', data);
  };

  const logStateChange = (stateName: string, oldValue: any, newValue: any) => {
    if (!isEnabled) return;

    componentLogger.debug('State changed', {
      stateName,
      oldValue,
      newValue,
    });

    if (stateDebugger.current) {
      stateDebugger.current.capture({ [stateName]: newValue }, stateName);
    }
  };

  const startMeasure = (name: string) => {
    if (!isEnabled || !measurePerformance) return;
    measurements.current.set(name, performance.now());
  };

  const endMeasure = (name: string) => {
    if (!isEnabled || !measurePerformance) return;

    const startTime = measurements.current.get(name);
    if (startTime) {
      const duration = performance.now() - startTime;
      measurements.current.delete(name);

      componentLogger.debug('Measurement complete', {
        measurement: name,
        duration_ms: Math.round(duration * 100) / 100,
      });
    }
  };

  // Calculate render info
  const renderInfo: RenderInfo = {
    count: renderCount.current,
    lastRender: lastRenderTime.current,
    totalRenderTime: renderTimes.current.reduce((a, b) => a + b, 0),
    averageRenderTime:
      renderTimes.current.length > 0
        ? renderTimes.current.reduce((a, b) => a + b, 0) /
          renderTimes.current.length
        : 0,
  };

  return {
    renderInfo,
    propChanges: propChanges.current,
    lastProps: previousProps.current,
    isEnabled,
    logRender,
    logStateChange,
    startMeasure,
    endMeasure,
  };
}

/**
 * Detect changes between old and new props
 */
function detectPropChanges(oldProps: any, newProps: any): PropChange[] {
  const changes: PropChange[] = [];
  const allKeys = new Set([
    ...Object.keys(oldProps),
    ...Object.keys(newProps),
  ]);

  allKeys.forEach((key) => {
    // Skip certain keys
    if (
      key === 'children' ||
      key === 'context' ||
      key === 'logRenders' ||
      key === 'trackProps' ||
      key === 'trackState' ||
      key === 'measurePerformance' ||
      key === 'enabledInProduction' ||
      key === 'component'
    ) {
      return;
    }

    const oldValue = oldProps[key];
    const newValue = newProps[key];

    if (oldValue !== newValue) {
      changes.push({
        prop: key,
        oldValue,
        newValue,
        timestamp: Date.now(),
      });
    }
  });

  return changes;
}

/**
 * Hook for tracking component performance
 *
 * @example
 * ```tsx
 * function ExpensiveComponent() {
 *   const perf = usePerformance('ExpensiveComponent');
 *
 *   useEffect(() => {
 *     perf.mark('data-fetch-start');
 *     fetchData().then(() => {
 *       perf.mark('data-fetch-end');
 *       perf.measure('data-fetch', 'data-fetch-start', 'data-fetch-end');
 *     });
 *   }, []);
 *
 *   return <div>...</div>;
 * }
 * ```
 */
export function usePerformance(componentName: string) {
  const marks = useRef<Map<string, number>>(new Map());
  const componentLogger = useMemo(
    () => createLogger(componentName),
    [componentName]
  );

  const mark = (markName: string) => {
    if (!isDebugMode()) return;
    marks.current.set(markName, performance.now());
  };

  const measure = (
    measureName: string,
    startMark: string,
    endMark: string
  ) => {
    if (!isDebugMode()) return;

    const startTime = marks.current.get(startMark);
    const endTime = marks.current.get(endMark);

    if (startTime !== undefined && endTime !== undefined) {
      const duration = endTime - startTime;

      componentLogger.debug('Performance measurement', {
        measure: measureName,
        duration_ms: Math.round(duration * 100) / 100,
      });

      return duration;
    }

    return null;
  };

  const clearMarks = () => {
    marks.current.clear();
  };

  return { mark, measure, clearMarks };
}

/**
 * Hook for tracking state changes with history
 *
 * @example
 * ```tsx
 * function StatefulComponent() {
 *   const [count, setCount] = useStateWithDebug(0, 'count');
 *
 *   // State changes are automatically logged
 *   const increment = () => setCount(c => c + 1);
 *
 *   return <button onClick={increment}>Count: {count}</button>;
 * }
 * ```
 */
export function useStateWithDebug<T>(
  initialState: T,
  stateName: string,
  componentName?: string
): [T, React.Dispatch<React.SetStateAction<T>>] {
  const [state, setState] = useState<T>(initialState);
  const previousState = useRef<T>(initialState);
  const componentLogger = useMemo(
    () => componentName ? createLogger(componentName) : logger,
    [componentName]
  );

  const setStateWithDebug: React.Dispatch<React.SetStateAction<T>> = (
    action
  ) => {
    setState((prevState) => {
      const newState =
        typeof action === 'function'
          ? (action as (prevState: T) => T)(prevState)
          : action;

      if (isDebugMode() && prevState !== newState) {
        componentLogger.debug('State changed', {
          stateName,
          oldValue: prevState,
          newValue: newState,
        });
      }

      previousState.current = prevState;
      return newState;
    });
  };

  return [state, setStateWithDebug];
}

/**
 * Hook for logging effect dependencies
 *
 * @example
 * ```tsx
 * function Component({ userId, data }) {
 *   useEffectDebug(() => {
 *     // Effect logic
 *   }, [userId, data], 'fetch-user-data');
 * }
 * ```
 */
export function useEffectDebug(
  effect: React.EffectCallback,
  deps: React.DependencyList,
  effectName: string,
  componentName?: string
): void {
  const previousDeps = useRef<React.DependencyList | undefined>();
  const componentLogger = useMemo(
    () => componentName ? createLogger(componentName) : logger,
    [componentName]
  );

  useEffect(() => {
    if (isDebugMode()) {
      if (previousDeps.current) {
        const changedDeps = deps.reduce((acc, dep, index) => {
          if (dep !== previousDeps.current![index]) {
            acc.push({ index, oldValue: previousDeps.current![index], newValue: dep });
          }
          return acc;
        }, [] as Array<{ index: number; oldValue: any; newValue: any }>);

        if (changedDeps.length > 0) {
          componentLogger.debug(`Effect triggered: ${effectName}`, {
            changedDeps,
          });
        }
      } else {
        componentLogger.debug(`Effect mounted: ${effectName}`);
      }

      previousDeps.current = deps;
    }

    return effect();
  }, deps);
}

/**
 * Hook for component why-did-you-render analysis
 *
 * @example
 * ```tsx
 * function Component(props) {
 *   useWhyDidYouUpdate('Component', props);
 *   return <div>...</div>;
 * }
 * ```
 */
export function useWhyDidYouUpdate(componentName: string, props: any): void {
  const previousProps = useRef<any>();
  const componentLogger = useMemo(
    () => createLogger(componentName),
    [componentName]
  );

  useEffect(() => {
    if (!isDebugMode()) return;

    if (previousProps.current) {
      const allKeys = Object.keys({ ...previousProps.current, ...props });
      const changedProps: any = {};

      allKeys.forEach((key) => {
        if (previousProps.current[key] !== props[key]) {
          changedProps[key] = {
            from: previousProps.current[key],
            to: props[key],
          };
        }
      });

      if (Object.keys(changedProps).length > 0) {
        componentLogger.debug('Component re-rendered due to prop changes', {
          changedProps,
        });
      }
    }

    previousProps.current = props;
  });
}

export default useDebug;
