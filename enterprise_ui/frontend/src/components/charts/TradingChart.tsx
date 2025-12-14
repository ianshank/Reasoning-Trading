/**
 * TradingChart component - Advanced price chart with candlesticks and indicators
 */

import React, { useState, useMemo } from 'react';
import {
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  TooltipProps,
  ReferenceLine,
} from 'recharts';
import { useChartTheme } from './hooks/useChartTheme';
import { formatTimestamp, formatNumber, calculateMovingAverage } from './utils/chartUtils';

export interface CandleData {
  timestamp: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export type Timeframe = '1m' | '5m' | '15m' | '1H' | '4H' | '1D';

export interface Indicator {
  type: 'SMA' | 'EMA' | 'BB_UPPER' | 'BB_LOWER' | 'BB_MIDDLE';
  period: number;
  color?: string;
  name: string;
}

export interface TradingChartProps {
  symbol: string;
  data: CandleData[];
  indicators?: Indicator[];
  timeframe: Timeframe;
  onTimeframeChange?: (timeframe: Timeframe) => void;
  height?: number;
  showVolume?: boolean;
  showGrid?: boolean;
  className?: string;
  ariaLabel?: string;
}

interface ProcessedData extends CandleData {
  candleColor: string;
  candleBody: [number, number];
  wickHigh: number;
  wickLow: number;
  [key: string]: any;
}

const CustomTooltip: React.FC<TooltipProps<any, any> & { theme: any; symbol: string }> = ({
  active,
  payload,
  theme,
  symbol,
}) => {
  if (!active || !payload || payload.length === 0) {
    return null;
  }

  const data = payload[0].payload as ProcessedData;

  return (
    <div
      style={{
        backgroundColor: theme.tooltip.background,
        border: `1px solid ${theme.tooltip.border}`,
        borderRadius: '4px',
        padding: '12px',
        boxShadow: `0 2px 8px ${theme.tooltip.shadow}`,
        minWidth: '200px',
      }}
    >
      <div
        style={{
          fontSize: '12px',
          fontWeight: 600,
          color: theme.tooltip.text,
          marginBottom: '8px',
        }}
      >
        {symbol} - {formatTimestamp(data.timestamp, 'datetime')}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '80px 1fr', gap: '4px' }}>
        <span style={{ fontSize: '11px', color: theme.text.secondary }}>Open:</span>
        <span style={{ fontSize: '11px', color: theme.tooltip.text, fontWeight: 600 }}>
          {formatNumber(data.open, 2)}
        </span>

        <span style={{ fontSize: '11px', color: theme.text.secondary }}>High:</span>
        <span style={{ fontSize: '11px', color: theme.tooltip.text, fontWeight: 600 }}>
          {formatNumber(data.high, 2)}
        </span>

        <span style={{ fontSize: '11px', color: theme.text.secondary }}>Low:</span>
        <span style={{ fontSize: '11px', color: theme.tooltip.text, fontWeight: 600 }}>
          {formatNumber(data.low, 2)}
        </span>

        <span style={{ fontSize: '11px', color: theme.text.secondary }}>Close:</span>
        <span
          style={{
            fontSize: '11px',
            fontWeight: 600,
            color: data.close >= data.open ? theme.colors.bullish : theme.colors.bearish,
          }}
        >
          {formatNumber(data.close, 2)}
        </span>

        <span style={{ fontSize: '11px', color: theme.text.secondary }}>Volume:</span>
        <span style={{ fontSize: '11px', color: theme.tooltip.text, fontWeight: 600 }}>
          {formatNumber(data.volume, 0)}
        </span>
      </div>

      {/* Show indicator values */}
      {Object.keys(data)
        .filter((key) => key.startsWith('indicator_'))
        .map((key) => {
          const indicatorName = key.replace('indicator_', '').replace(/_/g, ' ');
          return (
            <div
              key={key}
              style={{
                marginTop: '4px',
                fontSize: '10px',
                color: theme.text.secondary,
              }}
            >
              {indicatorName}: {formatNumber(data[key], 2)}
            </div>
          );
        })}
    </div>
  );
};

const Candlestick: React.FC<any> = (props) => {
  const { x, y, width, height, payload } = props;
  const data = payload as ProcessedData;

  if (!data) return null;

  const bodyX = x;
  const bodyWidth = Math.max(width * 0.8, 1);
  const wickX = x + width / 2;

  const isUp = data.close >= data.open;
  const bodyTop = Math.min(y + (data.open - data.high) * height / (data.high - data.low), y + height);
  const bodyHeight = Math.abs((data.close - data.open) * height / (data.high - data.low)) || 1;

  const wickTop = y;
  const wickBottom = y + height;

  return (
    <g>
      {/* Wick line */}
      <line
        x1={wickX}
        y1={wickTop}
        x2={wickX}
        y2={wickBottom}
        stroke={data.candleColor}
        strokeWidth={1}
      />

      {/* Candle body */}
      <rect
        x={bodyX}
        y={bodyTop}
        width={bodyWidth}
        height={bodyHeight}
        fill={isUp ? data.candleColor : 'transparent'}
        stroke={data.candleColor}
        strokeWidth={1}
      />
    </g>
  );
};

export const TradingChart: React.FC<TradingChartProps> = ({
  symbol,
  data,
  indicators = [],
  timeframe,
  onTimeframeChange,
  height = 600,
  showVolume = true,
  showGrid = true,
  className = '',
  ariaLabel = `Trading chart for ${symbol}`,
}) => {
  const theme = useChartTheme();
  const [hoveredBar, setHoveredBar] = useState<number | null>(null);

  const timeframes: Timeframe[] = ['1m', '5m', '15m', '1H', '4H', '1D'];

  const processedData: ProcessedData[] = useMemo(() => {
    const prices = data.map((d) => d.close);

    const processed = data.map((candle) => {
      const isUp = candle.close >= candle.open;
      const candleColor = isUp ? theme.colors.bullish : theme.colors.bearish;

      return {
        ...candle,
        candleColor,
        candleBody: [Math.min(candle.open, candle.close), Math.max(candle.open, candle.close)] as [number, number],
        wickHigh: candle.high,
        wickLow: candle.low,
      };
    });

    indicators.forEach((indicator) => {
      let values: (number | null)[] = [];

      switch (indicator.type) {
        case 'SMA':
        case 'EMA':
          values = calculateMovingAverage(prices, indicator.period);
          break;
        case 'BB_UPPER':
        case 'BB_MIDDLE':
        case 'BB_LOWER':
          const sma = calculateMovingAverage(prices, indicator.period);
          const std = prices.map((_, i) => {
            if (i < indicator.period - 1) return null;
            const slice = prices.slice(i - indicator.period + 1, i + 1);
            const mean = slice.reduce((sum, val) => sum + val, 0) / slice.length;
            const variance = slice.reduce((sum, val) => sum + Math.pow(val - mean, 2), 0) / slice.length;
            return Math.sqrt(variance);
          });

          if (indicator.type === 'BB_UPPER') {
            values = sma.map((val, i) => (val !== null && std[i] !== null ? val + 2 * std[i]! : null));
          } else if (indicator.type === 'BB_LOWER') {
            values = sma.map((val, i) => (val !== null && std[i] !== null ? val - 2 * std[i]! : null));
          } else {
            values = sma;
          }
          break;
      }

      processed.forEach((item, index) => {
        item[`indicator_${indicator.name.replace(/\s+/g, '_')}`] = values[index];
      });
    });

    return processed;
  }, [data, indicators, theme]);

  const priceRange = useMemo(() => {
    const prices = data.flatMap((d) => [d.high, d.low]);
    const min = Math.min(...prices);
    const max = Math.max(...prices);
    const padding = (max - min) * 0.05;
    return [min - padding, max + padding];
  }, [data]);

  const volumeRange = useMemo(() => {
    const volumes = data.map((d) => d.volume);
    const max = Math.max(...volumes);
    return [0, max * 1.2];
  }, [data]);

  const chartHeight = showVolume ? height * 0.7 : height;
  const volumeHeight = showVolume ? height * 0.3 : 0;

  return (
    <div className={`trading-chart ${className}`} style={{ width: '100%' }}>
      {/* Timeframe selector */}
      <div
        style={{
          display: 'flex',
          gap: '8px',
          marginBottom: '16px',
          padding: '8px',
          backgroundColor: theme.background,
          borderRadius: '4px',
          border: `1px solid ${theme.grid.line}`,
        }}
      >
        <span style={{ fontSize: '12px', color: theme.text.secondary, marginRight: '8px' }}>
          Timeframe:
        </span>
        {timeframes.map((tf) => (
          <button
            key={tf}
            onClick={() => onTimeframeChange?.(tf)}
            style={{
              padding: '4px 12px',
              fontSize: '11px',
              fontWeight: 600,
              backgroundColor: timeframe === tf ? theme.colors.primary : 'transparent',
              color: timeframe === tf ? '#ffffff' : theme.text.secondary,
              border: `1px solid ${timeframe === tf ? theme.colors.primary : theme.grid.line}`,
              borderRadius: '4px',
              cursor: 'pointer',
              transition: 'all 0.2s',
            }}
            aria-label={`Select ${tf} timeframe`}
            aria-pressed={timeframe === tf}
          >
            {tf}
          </button>
        ))}
      </div>

      {/* Price chart */}
      <div role="img" aria-label={ariaLabel} style={{ width: '100%', height: chartHeight }}>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart
            data={processedData}
            margin={{ top: 10, right: 30, bottom: 0, left: 0 }}
          >
            {showGrid && (
              <CartesianGrid strokeDasharray="3 3" stroke={theme.grid.line} vertical={false} />
            )}

            <XAxis
              dataKey="timestamp"
              stroke={theme.axis.line}
              tick={{ fill: theme.axis.label, fontSize: 10 }}
              tickFormatter={(timestamp) => formatTimestamp(timestamp, 'time')}
              minTickGap={30}
            />

            <YAxis
              yAxisId="price"
              domain={priceRange}
              stroke={theme.axis.line}
              tick={{ fill: theme.axis.label, fontSize: 10 }}
              tickFormatter={(value) => formatNumber(value, 2)}
              orientation="right"
            />

            <Tooltip content={<CustomTooltip theme={theme} symbol={symbol} />} />

            {/* Candlesticks */}
            <Bar
              yAxisId="price"
              dataKey="wickHigh"
              shape={<Candlestick />}
              isAnimationActive={false}
            />

            {/* Indicators */}
            {indicators.map((indicator, index) => (
              <Line
                key={`indicator-${index}`}
                yAxisId="price"
                type="monotone"
                dataKey={`indicator_${indicator.name.replace(/\s+/g, '_')}`}
                stroke={indicator.color || theme.series[index % theme.series.length]}
                strokeWidth={1.5}
                dot={false}
                connectNulls
                isAnimationActive={false}
              />
            ))}
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* Volume chart */}
      {showVolume && (
        <div style={{ width: '100%', height: volumeHeight, marginTop: '8px' }}>
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart
              data={processedData}
              margin={{ top: 0, right: 30, bottom: 20, left: 0 }}
            >
              {showGrid && (
                <CartesianGrid strokeDasharray="3 3" stroke={theme.grid.line} vertical={false} />
              )}

              <XAxis
                dataKey="timestamp"
                stroke={theme.axis.line}
                tick={{ fill: theme.axis.label, fontSize: 10 }}
                tickFormatter={(timestamp) => formatTimestamp(timestamp, 'time')}
                minTickGap={30}
              />

              <YAxis
                domain={volumeRange}
                stroke={theme.axis.line}
                tick={{ fill: theme.axis.label, fontSize: 10 }}
                tickFormatter={(value) => formatNumber(value, 0)}
                orientation="right"
              />

              <Bar
                dataKey="volume"
                fill={theme.colors.info}
                opacity={0.5}
                isAnimationActive={false}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
};

export default TradingChart;
