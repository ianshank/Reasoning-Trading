/**
 * Chart theming hook for dark/light mode support
 */

import { useMemo } from 'react';

export interface ChartTheme {
  background: string;
  text: {
    primary: string;
    secondary: string;
    muted: string;
  };
  grid: {
    line: string;
    stroke: string;
  };
  axis: {
    line: string;
    tick: string;
    label: string;
  };
  tooltip: {
    background: string;
    border: string;
    text: string;
    shadow: string;
  };
  colors: {
    primary: string;
    secondary: string;
    success: string;
    danger: string;
    warning: string;
    info: string;
    bullish: string;
    bearish: string;
    neutral: string;
  };
  series: string[];
  gradients: {
    primary: [string, string];
    secondary: [string, string];
    success: [string, string];
    danger: [string, string];
  };
}

export interface ResponsiveBreakpoints {
  xs: number;
  sm: number;
  md: number;
  lg: number;
  xl: number;
  xxl: number;
}

export const breakpoints: ResponsiveBreakpoints = {
  xs: 0,
  sm: 640,
  md: 768,
  lg: 1024,
  xl: 1280,
  xxl: 1536,
};

const darkTheme: ChartTheme = {
  background: '#0a0a0a',
  text: {
    primary: '#ffffff',
    secondary: '#b4b4b4',
    muted: '#6b6b6b',
  },
  grid: {
    line: '#1f1f1f',
    stroke: '#2a2a2a',
  },
  axis: {
    line: '#333333',
    tick: '#4a4a4a',
    label: '#888888',
  },
  tooltip: {
    background: '#1a1a1a',
    border: '#333333',
    text: '#ffffff',
    shadow: 'rgba(0, 0, 0, 0.5)',
  },
  colors: {
    primary: '#3b82f6',
    secondary: '#8b5cf6',
    success: '#10b981',
    danger: '#ef4444',
    warning: '#f59e0b',
    info: '#06b6d4',
    bullish: '#22c55e',
    bearish: '#ef4444',
    neutral: '#6b7280',
  },
  series: [
    '#3b82f6', // blue
    '#8b5cf6', // purple
    '#10b981', // green
    '#f59e0b', // amber
    '#ef4444', // red
    '#06b6d4', // cyan
    '#ec4899', // pink
    '#84cc16', // lime
    '#f97316', // orange
    '#6366f1', // indigo
  ],
  gradients: {
    primary: ['#3b82f6', '#1d4ed8'],
    secondary: ['#8b5cf6', '#6d28d9'],
    success: ['#10b981', '#047857'],
    danger: ['#ef4444', '#b91c1c'],
  },
};

const lightTheme: ChartTheme = {
  background: '#ffffff',
  text: {
    primary: '#0a0a0a',
    secondary: '#4a4a4a',
    muted: '#9ca3af',
  },
  grid: {
    line: '#e5e7eb',
    stroke: '#d1d5db',
  },
  axis: {
    line: '#d1d5db',
    tick: '#9ca3af',
    label: '#6b7280',
  },
  tooltip: {
    background: '#ffffff',
    border: '#e5e7eb',
    text: '#0a0a0a',
    shadow: 'rgba(0, 0, 0, 0.1)',
  },
  colors: {
    primary: '#2563eb',
    secondary: '#7c3aed',
    success: '#059669',
    danger: '#dc2626',
    warning: '#d97706',
    info: '#0891b2',
    bullish: '#16a34a',
    bearish: '#dc2626',
    neutral: '#6b7280',
  },
  series: [
    '#2563eb', // blue
    '#7c3aed', // purple
    '#059669', // green
    '#d97706', // amber
    '#dc2626', // red
    '#0891b2', // cyan
    '#db2777', // pink
    '#65a30d', // lime
    '#ea580c', // orange
    '#4f46e5', // indigo
  ],
  gradients: {
    primary: ['#3b82f6', '#93c5fd'],
    secondary: ['#8b5cf6', '#c4b5fd'],
    success: ['#10b981', '#6ee7b7'],
    danger: ['#ef4444', '#fca5a5'],
  },
};

export interface UseChartThemeOptions {
  mode?: 'light' | 'dark';
}

/**
 * Hook for accessing chart theme based on mode
 */
export const useChartTheme = (options?: UseChartThemeOptions): ChartTheme => {
  const { mode = 'dark' } = options || {};

  const theme = useMemo(() => {
    return mode === 'dark' ? darkTheme : lightTheme;
  }, [mode]);

  return theme;
};

/**
 * Hook for responsive chart dimensions
 */
export const useResponsiveChart = (baseWidth: number = 600, baseHeight: number = 400) => {
  const getResponsiveDimensions = (containerWidth: number) => {
    if (containerWidth < breakpoints.sm) {
      return { width: containerWidth, height: baseHeight * 0.6 };
    }
    if (containerWidth < breakpoints.md) {
      return { width: containerWidth, height: baseHeight * 0.75 };
    }
    if (containerWidth < breakpoints.lg) {
      return { width: containerWidth, height: baseHeight * 0.9 };
    }
    return { width: containerWidth, height: baseHeight };
  };

  const getFontSize = (containerWidth: number) => {
    if (containerWidth < breakpoints.sm) return 10;
    if (containerWidth < breakpoints.md) return 11;
    if (containerWidth < breakpoints.lg) return 12;
    return 14;
  };

  const getMargin = (containerWidth: number) => {
    if (containerWidth < breakpoints.sm) {
      return { top: 10, right: 10, bottom: 30, left: 40 };
    }
    if (containerWidth < breakpoints.md) {
      return { top: 15, right: 15, bottom: 40, left: 50 };
    }
    return { top: 20, right: 30, bottom: 50, left: 60 };
  };

  return {
    getResponsiveDimensions,
    getFontSize,
    getMargin,
  };
};

/**
 * Get color from theme palette
 */
export const getThemeColor = (
  theme: ChartTheme,
  colorKey: keyof ChartTheme['colors']
): string => {
  return theme.colors[colorKey];
};

/**
 * Get series color by index
 */
export const getSeriesColor = (theme: ChartTheme, index: number): string => {
  return theme.series[index % theme.series.length];
};

/**
 * Get gradient colors by type
 */
export const getGradient = (
  theme: ChartTheme,
  type: keyof ChartTheme['gradients']
): [string, string] => {
  return theme.gradients[type];
};

export default useChartTheme;
