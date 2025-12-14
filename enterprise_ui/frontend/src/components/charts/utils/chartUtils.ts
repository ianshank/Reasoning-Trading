/**
 * Chart utility functions for data formatting, color generation, and calculations
 */

export interface DataPoint {
  [key: string]: string | number | Date | null | undefined;
}

/**
 * Format number to specified decimal places
 */
export const formatNumber = (value: number, decimals: number = 2): string => {
  return value.toFixed(decimals);
};

/**
 * Format large numbers with K, M, B suffixes
 */
export const formatCompactNumber = (value: number): string => {
  const absValue = Math.abs(value);
  const sign = value < 0 ? '-' : '';

  if (absValue >= 1e9) {
    return `${sign}${(absValue / 1e9).toFixed(2)}B`;
  }
  if (absValue >= 1e6) {
    return `${sign}${(absValue / 1e6).toFixed(2)}M`;
  }
  if (absValue >= 1e3) {
    return `${sign}${(absValue / 1e3).toFixed(2)}K`;
  }
  return `${sign}${absValue.toFixed(2)}`;
};

/**
 * Format currency values
 */
export const formatCurrency = (value: number, currency: string = 'USD'): string => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
};

/**
 * Format percentage values
 */
export const formatPercentage = (value: number, decimals: number = 2): string => {
  return `${(value * 100).toFixed(decimals)}%`;
};

/**
 * Format timestamp to readable date/time
 */
export const formatTimestamp = (
  timestamp: number | Date | string,
  format: 'date' | 'time' | 'datetime' = 'datetime'
): string => {
  const date = new Date(timestamp);

  const dateOptions: Intl.DateTimeFormatOptions = {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  };

  const timeOptions: Intl.DateTimeFormatOptions = {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  };

  const datetimeOptions: Intl.DateTimeFormatOptions = {
    ...dateOptions,
    ...timeOptions,
  };

  const options = format === 'date'
    ? dateOptions
    : format === 'time'
    ? timeOptions
    : datetimeOptions;

  return new Intl.DateTimeFormat('en-US', options).format(date);
};

/**
 * Generate array of colors based on count
 */
export const generateColors = (count: number, baseHue: number = 210): string[] => {
  const colors: string[] = [];
  const hueStep = 360 / count;

  for (let i = 0; i < count; i++) {
    const hue = (baseHue + i * hueStep) % 360;
    colors.push(`hsl(${hue}, 70%, 50%)`);
  }

  return colors;
};

/**
 * Generate color based on value and thresholds
 */
export const getColorByValue = (
  value: number,
  thresholds: { min: number; max: number; color: string }[]
): string => {
  for (const threshold of thresholds) {
    if (value >= threshold.min && value <= threshold.max) {
      return threshold.color;
    }
  }
  return '#888888';
};

/**
 * Calculate min and max values from dataset
 */
export const calculateDomain = (
  data: DataPoint[],
  key: string,
  padding: number = 0.1
): [number, number] => {
  const values = data
    .map(item => item[key])
    .filter((val): val is number => typeof val === 'number');

  if (values.length === 0) {
    return [0, 100];
  }

  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min;

  return [
    min - range * padding,
    max + range * padding,
  ];
};

/**
 * Calculate percentage change
 */
export const calculatePercentageChange = (
  current: number,
  previous: number
): number => {
  if (previous === 0) return 0;
  return ((current - previous) / previous) * 100;
};

/**
 * Calculate moving average
 */
export const calculateMovingAverage = (
  data: number[],
  period: number
): (number | null)[] => {
  const result: (number | null)[] = [];

  for (let i = 0; i < data.length; i++) {
    if (i < period - 1) {
      result.push(null);
    } else {
      const slice = data.slice(i - period + 1, i + 1);
      const sum = slice.reduce((acc, val) => acc + val, 0);
      result.push(sum / period);
    }
  }

  return result;
};

/**
 * Normalize data to 0-1 range
 */
export const normalizeData = (values: number[]): number[] => {
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min;

  if (range === 0) {
    return values.map(() => 0.5);
  }

  return values.map(val => (val - min) / range);
};

/**
 * Interpolate color between two colors
 */
export const interpolateColor = (
  color1: string,
  color2: string,
  factor: number
): string => {
  const c1 = parseInt(color1.slice(1), 16);
  const c2 = parseInt(color2.slice(1), 16);

  const r1 = (c1 >> 16) & 0xff;
  const g1 = (c1 >> 8) & 0xff;
  const b1 = c1 & 0xff;

  const r2 = (c2 >> 16) & 0xff;
  const g2 = (c2 >> 8) & 0xff;
  const b2 = c2 & 0xff;

  const r = Math.round(r1 + (r2 - r1) * factor);
  const g = Math.round(g1 + (g2 - g1) * factor);
  const b = Math.round(b1 + (b2 - b1) * factor);

  return `#${((r << 16) | (g << 8) | b).toString(16).padStart(6, '0')}`;
};

/**
 * Get gradient ID for chart fills
 */
export const getGradientId = (prefix: string): string => {
  return `${prefix}-gradient-${Math.random().toString(36).substr(2, 9)}`;
};

/**
 * Debounce function for resize handlers
 */
export const debounce = <T extends (...args: any[]) => any>(
  func: T,
  wait: number
): ((...args: Parameters<T>) => void) => {
  let timeout: NodeJS.Timeout | null = null;

  return (...args: Parameters<T>) => {
    if (timeout) {
      clearTimeout(timeout);
    }
    timeout = setTimeout(() => func(...args), wait);
  };
};

/**
 * Calculate tick values for axis
 */
export const calculateTicks = (
  min: number,
  max: number,
  count: number = 5
): number[] => {
  const range = max - min;
  const step = range / (count - 1);
  const ticks: number[] = [];

  for (let i = 0; i < count; i++) {
    ticks.push(min + step * i);
  }

  return ticks;
};

/**
 * Aggregate data by time period
 */
export const aggregateByPeriod = (
  data: DataPoint[],
  timestampKey: string,
  valueKey: string,
  period: 'minute' | 'hour' | 'day' | 'week' | 'month'
): DataPoint[] => {
  const groups = new Map<string, number[]>();

  data.forEach(item => {
    const timestamp = new Date(item[timestampKey] as string | number | Date);
    let groupKey: string;

    switch (period) {
      case 'minute':
        groupKey = `${timestamp.getFullYear()}-${timestamp.getMonth()}-${timestamp.getDate()}-${timestamp.getHours()}-${timestamp.getMinutes()}`;
        break;
      case 'hour':
        groupKey = `${timestamp.getFullYear()}-${timestamp.getMonth()}-${timestamp.getDate()}-${timestamp.getHours()}`;
        break;
      case 'day':
        groupKey = `${timestamp.getFullYear()}-${timestamp.getMonth()}-${timestamp.getDate()}`;
        break;
      case 'week':
        const weekNum = Math.floor(timestamp.getDate() / 7);
        groupKey = `${timestamp.getFullYear()}-${timestamp.getMonth()}-${weekNum}`;
        break;
      case 'month':
        groupKey = `${timestamp.getFullYear()}-${timestamp.getMonth()}`;
        break;
    }

    const value = item[valueKey] as number;
    if (!groups.has(groupKey)) {
      groups.set(groupKey, []);
    }
    groups.get(groupKey)!.push(value);
  });

  const result: DataPoint[] = [];
  groups.forEach((values, key) => {
    const avg = values.reduce((sum, val) => sum + val, 0) / values.length;
    result.push({
      [timestampKey]: key,
      [valueKey]: avg,
    });
  });

  return result;
};
