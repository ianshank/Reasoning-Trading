# Market Regime Analysis Components

Comprehensive React components for market regime detection and visualization based on Hidden Markov Models and technical analysis.

## Overview

This module provides a complete suite of components for analyzing and visualizing market regimes, including:

- Real-time regime classification
- Historical regime transitions
- Technical indicator contributions
- Hidden Markov Model visualization
- Strategy recommendations by regime
- Alert notifications for regime changes

## Components

### CurrentRegimeCard

Displays the current market regime with confidence score, duration, and key indicator contributions.

**Props:**
- `regime` (string): Current regime name
- `confidence` (number): Confidence score (0-1)
- `since` (string): ISO timestamp when regime started
- `indicators?` (IndicatorContribution[]): Contributing indicators
- `className?` (string): Additional CSS classes

**Example:**
```tsx
import { CurrentRegimeCard } from '@/components/regime';

<CurrentRegimeCard
  regime="bull"
  confidence={0.85}
  since="2024-01-15T10:30:00Z"
  indicators={[
    { name: 'ADX', value: 35.5, weight: 0.3, impact: 0.25 },
    { name: 'RSI', value: 68.2, weight: 0.2, impact: 0.15 },
  ]}
/>
```

### RegimeProbabilities

Shows probability distribution across all possible regimes with bar chart and comparison.

**Props:**
- `probabilities` (Record<string, number>): Current regime probabilities
- `currentRegime` (string): Currently active regime
- `historicalProbabilities?` (Record<string, number>): Historical average for comparison
- `className?` (string): Additional CSS classes

**Example:**
```tsx
import { RegimeProbabilities } from '@/components/regime';

<RegimeProbabilities
  probabilities={{
    bull: 0.45,
    bear: 0.15,
    neutral: 0.25,
    high_volatility: 0.10,
    low_volatility: 0.05,
  }}
  currentRegime="bull"
  historicalProbabilities={{
    bull: 0.30,
    bear: 0.20,
    neutral: 0.25,
  }}
/>
```

### RegimeTimeline

Interactive timeline showing historical regime transitions with durations.

**Props:**
- `history` (RegimeHistoryEntry[]): Historical regime data
- `timeframe?` ('day' | 'week' | 'month' | 'year'): Display timeframe
- `className?` (string): Additional CSS classes

**Example:**
```tsx
import { RegimeTimeline } from '@/components/regime';

<RegimeTimeline
  history={[
    {
      regime: 'bull',
      confidence: 0.85,
      startTime: '2024-01-15T09:30:00Z',
      endTime: '2024-01-15T14:30:00Z',
      duration: 18000,
    },
  ]}
  timeframe="day"
/>
```

### RegimeHeatmap

Heatmap visualization showing regime frequency patterns by time of day or week.

**Props:**
- `frequencyData` (RegimeFrequencyData[]): Frequency data points
- `groupBy` ('hour' | 'day'): Time grouping
- `className?` (string): Additional CSS classes

**Example:**
```tsx
import { RegimeHeatmap } from '@/components/regime';

<RegimeHeatmap
  frequencyData={[
    { regime: 'bull', timeSlot: '9', frequency: 0.45, count: 15 },
    { regime: 'bull', timeSlot: '10', frequency: 0.55, count: 20 },
  ]}
  groupBy="hour"
/>
```

### IndicatorContribution

Bar chart showing which technical indicators contributed to regime classification.

**Props:**
- `contributions` (IndicatorContribution[]): Indicator data
- `className?` (string): Additional CSS classes

**Example:**
```tsx
import { IndicatorContribution } from '@/components/regime';

<IndicatorContribution
  contributions={[
    { name: 'ADX', value: 35.5, weight: 0.3, impact: 0.25 },
    { name: 'RSI', value: 68.2, weight: 0.2, impact: 0.15 },
    { name: 'ATR', value: 2.5, weight: 0.25, impact: 0.18 },
  ]}
/>
```

### HMMStateView

Interactive visualization of Hidden Markov Model states and transitions using D3.js.

**Props:**
- `hmmState` (HMMState): HMM state data
- `transitionMatrix` (number[][]): State transition probabilities
- `className?` (string): Additional CSS classes

**Features:**
- State transition diagram
- Transition probability matrix
- Emission probability distributions

**Example:**
```tsx
import { HMMStateView } from '@/components/regime';

<HMMStateView
  hmmState={{
    transition_matrix: {
      matrix: [[0.7, 0.1, 0.05], ...],
      state_names: ['bull', 'bear', 'neutral'],
    },
    state_probabilities: { bull: 0.45, bear: 0.15, neutral: 0.40 },
    current_state: 'bull',
    emission_probabilities: { ... },
  }}
  transitionMatrix={[[0.7, 0.1, 0.05], ...]}
/>
```

### RegimeStrategyMapping

Maps market regimes to optimal trading strategies with historical performance.

**Props:**
- `mapping` (RegimeStrategyMapping[]): Strategy mappings
- `currentRegime` (string): Current active regime
- `className?` (string): Additional CSS classes

**Example:**
```tsx
import { RegimeStrategyMapping } from '@/components/regime';

<RegimeStrategyMapping
  mapping={[
    {
      regime: 'bull',
      recommended_strategy: 'Trend Following',
      confidence: 0.85,
      historical_performance: {
        total_trades: 150,
        win_rate: 0.62,
        avg_return: 0.025,
        sharpe_ratio: 1.85,
      },
    },
  ]}
  currentRegime="bull"
/>
```

### RegimeAlerts

Displays and manages regime change alerts with configuration options.

**Props:**
- `alerts` (RegimeAlert[]): Alert list
- `config?` (RegimeAlertConfig): Alert configuration
- `onConfigure?` ((config: RegimeAlertConfig) => void): Config handler
- `onAcknowledge?` ((alertId: string) => void): Acknowledge handler
- `onDismiss?` ((alertId: string) => void): Dismiss handler
- `className?` (string): Additional CSS classes

**Example:**
```tsx
import { RegimeAlerts } from '@/components/regime';

<RegimeAlerts
  alerts={[
    {
      id: 'alert-1',
      timestamp: '2024-01-15T14:30:00Z',
      from_regime: 'bull',
      to_regime: 'neutral',
      confidence: 0.75,
      severity: 'medium',
      message: 'Regime changed from bull to neutral',
      acknowledged: false,
    },
  ]}
  onAcknowledge={(id) => console.log('Acknowledged:', id)}
  onConfigure={(config) => console.log('Config updated:', config)}
/>
```

## Hook

### useRegime

Custom hook for fetching and managing regime detection data with real-time updates.

**Options:**
- `symbol?` (string): Trading symbol (default: 'SPY')
- `autoRefresh?` (boolean): Enable auto-refresh (default: true)
- `refreshInterval?` (number): Refresh interval in ms (default: 30000)
- `enableWebSocket?` (boolean): Enable WebSocket updates (default: true)

**Returns:**
- `current` (RegimeClassification | null): Current regime
- `history` (RegimeHistory | null): Historical data
- `statistics` (RegimeStatistics | null): Statistics
- `alerts` (RegimeAlert[]): Alert list
- `isLoading` (boolean): Loading state
- `error` (Error | null): Error state
- `refresh` (() => Promise<void>): Manual refresh
- `acknowledgeAlert` ((alertId: string) => void): Acknowledge alert

**Example:**
```tsx
import { useRegime } from '@/components/regime';

function MyComponent() {
  const {
    current,
    history,
    isLoading,
    error,
    refresh,
  } = useRegime({
    symbol: 'AAPL',
    autoRefresh: true,
    refreshInterval: 30000,
  });

  if (isLoading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;

  return (
    <div>
      <h1>Current Regime: {current?.regime}</h1>
      <button onClick={refresh}>Refresh</button>
    </div>
  );
}
```

## Types

### RegimeState

Enum of possible market regime states:
- `BULL` - Bullish trend
- `BEAR` - Bearish trend
- `HIGH_VOLATILITY` - High volatility environment
- `LOW_VOLATILITY` - Low volatility environment
- `NEUTRAL` - Neutral/sideways market

### IndicatorContribution

```typescript
interface IndicatorContribution {
  name: string;
  value: number;
  weight: number;
  impact: number;
}
```

### RegimeClassification

```typescript
interface RegimeClassification {
  regime: string;
  confidence: number;
  regime_probabilities: Record<string, number>;
  hmm_regime: string | null;
  hmm_confidence: number;
  technical_regime: string | null;
  technical_confidence: number;
  timestamp: string;
  symbol: string;
}
```

## Styling

All components support:
- **Tailwind CSS** for styling
- **Dark mode** via `dark:` classes
- **Responsive design** with mobile-first approach
- **Accessibility** with ARIA labels and roles

## Dependencies

- React 18+
- Recharts (for charts)
- D3.js (for HMM visualization)
- Lucide React (for icons)
- Tailwind CSS

## API Endpoints

The hook expects the following API endpoints:

- `GET /api/v1/regime/current?symbol={symbol}` - Current regime
- `GET /api/v1/regime/history?symbol={symbol}&limit={limit}` - Historical data
- `GET /api/v1/regime/statistics?symbol={symbol}` - Statistics
- `WS /api/v1/ws/regime?symbol={symbol}` - Real-time updates

## Testing

Run tests with:

```bash
npm test components/regime
```

Example test file: `tests/unit/components/regime/CurrentRegimeCard.test.tsx`

## Example Usage

See `RegimeAnalysisPage.example.tsx` for a complete implementation showing all components working together.

## License

Part of the Reasoning Trading Enterprise UI.
