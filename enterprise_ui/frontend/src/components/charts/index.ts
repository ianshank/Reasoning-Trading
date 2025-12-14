/**
 * Chart components barrel export
 */

export { TradingChart } from './TradingChart';
export type {
  TradingChartProps,
  CandleData,
  Timeframe,
  Indicator,
} from './TradingChart';

export { LineChart } from './LineChart';
export type {
  LineChartProps,
  LineConfig,
  AxisConfig,
  TooltipConfig,
  ReferenceLineConfig,
} from './LineChart';

export { BarChart } from './BarChart';
export type {
  BarChartProps,
  BarConfig,
} from './BarChart';

export { PieChart } from './PieChart';
export type {
  PieChartProps,
  PieDataItem,
} from './PieChart';

export { AreaChart } from './AreaChart';
export type {
  AreaChartProps,
  AreaConfig,
  ReferenceAreaConfig,
} from './AreaChart';

export { Sparkline } from './Sparkline';
export type {
  SparklineProps,
} from './Sparkline';

export { HeatmapChart } from './HeatmapChart';
export type {
  HeatmapChartProps,
  HeatmapDataPoint,
  ColorScale,
} from './HeatmapChart';

export { GaugeChart } from './GaugeChart';
export type {
  GaugeChartProps,
  GaugeZone,
} from './GaugeChart';

export { useChartTheme, useResponsiveChart, getThemeColor, getSeriesColor, getGradient } from './hooks/useChartTheme';
export type {
  ChartTheme,
  ResponsiveBreakpoints,
  UseChartThemeOptions,
} from './hooks/useChartTheme';

export * from './utils/chartUtils';
