/**
 * Tests for CurrentRegimeCard Component
 */

import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import { CurrentRegimeCard } from '../../../../src/components/regime/CurrentRegimeCard';
import type { IndicatorContribution } from '../../../../src/types/regime';

describe('CurrentRegimeCard', () => {
  const mockIndicators: IndicatorContribution[] = [
    {
      name: 'ADX',
      value: 35.5,
      weight: 0.3,
      impact: 0.25,
    },
    {
      name: 'RSI',
      value: 68.2,
      weight: 0.2,
      impact: 0.15,
    },
    {
      name: 'ATR',
      value: 2.5,
      weight: 0.25,
      impact: 0.18,
    },
    {
      name: 'Volatility',
      value: 0.025,
      weight: 0.25,
      impact: -0.08,
    },
  ];

  it('renders current regime information', () => {
    render(
      <CurrentRegimeCard
        regime="bull"
        confidence={0.85}
        since="2024-01-15T10:30:00Z"
        indicators={mockIndicators}
      />
    );

    expect(screen.getByText('Current Regime')).toBeInTheDocument();
    expect(screen.getByText('Bullish Trend')).toBeInTheDocument();
  });

  it('displays confidence score correctly', () => {
    render(
      <CurrentRegimeCard
        regime="bull"
        confidence={0.85}
        since="2024-01-15T10:30:00Z"
      />
    );

    expect(screen.getByText('85%')).toBeInTheDocument();
    expect(screen.getByLabelText(/Confidence level: 85%/i)).toBeInTheDocument();
  });

  it('shows time in current regime', () => {
    const now = new Date();
    const since = new Date(now.getTime() - 2 * 60 * 60 * 1000); // 2 hours ago

    render(
      <CurrentRegimeCard
        regime="bull"
        confidence={0.85}
        since={since.toISOString()}
      />
    );

    // Should show duration in the badge
    const badge = screen.getByRole('status', { name: /Regime: bull/i });
    expect(badge).toHaveTextContent(/hour/i);
  });

  it('renders indicator contributions when provided', () => {
    render(
      <CurrentRegimeCard
        regime="bull"
        confidence={0.85}
        since="2024-01-15T10:30:00Z"
        indicators={mockIndicators}
      />
    );

    expect(screen.getByText('Key Indicators')).toBeInTheDocument();
    expect(screen.getByText('ADX')).toBeInTheDocument();
    expect(screen.getByText('35.50')).toBeInTheDocument();
    expect(screen.getByText('RSI')).toBeInTheDocument();
  });

  it('limits indicator display to 5 items', () => {
    const manyIndicators: IndicatorContribution[] = Array.from(
      { length: 10 },
      (_, i) => ({
        name: `Indicator ${i}`,
        value: i * 10,
        weight: 0.1,
        impact: 0.1,
      })
    );

    render(
      <CurrentRegimeCard
        regime="bull"
        confidence={0.85}
        since="2024-01-15T10:30:00Z"
        indicators={manyIndicators}
      />
    );

    // Should only show first 5 indicators
    expect(screen.getByText('Indicator 0')).toBeInTheDocument();
    expect(screen.getByText('Indicator 4')).toBeInTheDocument();
    expect(screen.queryByText('Indicator 5')).not.toBeInTheDocument();
  });

  it('handles different regime types correctly', () => {
    const regimes = [
      { regime: 'bull', display: 'Bullish Trend' },
      { regime: 'bear', display: 'Bearish Trend' },
      { regime: 'high_volatility', display: 'High Volatility' },
      { regime: 'low_volatility', display: 'Low Volatility' },
      { regime: 'neutral', display: 'Neutral' },
    ];

    regimes.forEach(({ regime, display }) => {
      const { unmount } = render(
        <CurrentRegimeCard
          regime={regime}
          confidence={0.75}
          since="2024-01-15T10:30:00Z"
        />
      );

      expect(screen.getByText(display)).toBeInTheDocument();
      unmount();
    });
  });

  it('displays positive and negative indicator impacts differently', () => {
    render(
      <CurrentRegimeCard
        regime="bull"
        confidence={0.85}
        since="2024-01-15T10:30:00Z"
        indicators={mockIndicators}
      />
    );

    // Find the volatility indicator which has negative impact
    const volatilityRow = screen
      .getByText('Volatility')
      .closest('div');

    expect(volatilityRow).toBeInTheDocument();
  });

  it('applies correct confidence color based on value', () => {
    const confidenceLevels = [
      { confidence: 0.9, expectedClass: 'bg-green-500' },
      { confidence: 0.7, expectedClass: 'bg-yellow-500' },
      { confidence: 0.5, expectedClass: 'bg-orange-500' },
    ];

    confidenceLevels.forEach(({ confidence }) => {
      const { unmount } = render(
        <CurrentRegimeCard
          regime="bull"
          confidence={confidence}
          since="2024-01-15T10:30:00Z"
        />
      );

      const progressBar = screen.getByLabelText(
        new RegExp(`Confidence level: ${Math.round(confidence * 100)}%`, 'i')
      );
      expect(progressBar).toBeInTheDocument();

      unmount();
    });
  });

  it('formats duration correctly for different time spans', () => {
    const now = new Date();

    const testCases = [
      {
        since: new Date(now.getTime() - 30 * 1000).toISOString(),
        expected: /second/i,
      },
      {
        since: new Date(now.getTime() - 5 * 60 * 1000).toISOString(),
        expected: /minute/i,
      },
      {
        since: new Date(now.getTime() - 3 * 60 * 60 * 1000).toISOString(),
        expected: /hour/i,
      },
      {
        since: new Date(now.getTime() - 2 * 24 * 60 * 60 * 1000).toISOString(),
        expected: /day/i,
      },
    ];

    testCases.forEach(({ since, expected }) => {
      const { unmount } = render(
        <CurrentRegimeCard
          regime="bull"
          confidence={0.85}
          since={since}
        />
      );

      const badge = screen.getByRole('status', { name: /Regime: bull/i });
      expect(badge.textContent).toMatch(expected);

      unmount();
    });
  });

  it('handles missing indicators gracefully', () => {
    render(
      <CurrentRegimeCard
        regime="bull"
        confidence={0.85}
        since="2024-01-15T10:30:00Z"
      />
    );

    expect(screen.queryByText('Key Indicators')).not.toBeInTheDocument();
  });

  it('applies custom className', () => {
    const { container } = render(
      <CurrentRegimeCard
        regime="bull"
        confidence={0.85}
        since="2024-01-15T10:30:00Z"
        className="custom-class"
      />
    );

    const card = container.querySelector('.custom-class');
    expect(card).toBeInTheDocument();
  });

  it('has proper accessibility attributes', () => {
    render(
      <CurrentRegimeCard
        regime="bull"
        confidence={0.85}
        since="2024-01-15T10:30:00Z"
        indicators={mockIndicators}
      />
    );

    // Check for ARIA labels
    expect(
      screen.getByRole('article', { name: 'Current Market Regime' })
    ).toBeInTheDocument();

    expect(screen.getByLabelText(/Confidence: 85%/i)).toBeInTheDocument();

    // Check indicator progress bars
    const progressBars = screen.getAllByRole('progressbar');
    expect(progressBars.length).toBeGreaterThan(0);
  });

  it('formats indicator values to 2 decimal places', () => {
    const indicator: IndicatorContribution[] = [
      {
        name: 'Test Indicator',
        value: 123.456789,
        weight: 0.5,
        impact: 0.2,
      },
    ];

    render(
      <CurrentRegimeCard
        regime="bull"
        confidence={0.85}
        since="2024-01-15T10:30:00Z"
        indicators={indicator}
      />
    );

    expect(screen.getByText('123.46')).toBeInTheDocument();
  });

  it('renders correctly in dark mode', () => {
    const { container } = render(
      <CurrentRegimeCard
        regime="bull"
        confidence={0.85}
        since="2024-01-15T10:30:00Z"
        indicators={mockIndicators}
      />
    );

    // Check for dark mode classes
    const card = container.querySelector('.dark\\:bg-gray-800');
    expect(card).toBeInTheDocument();
  });
});
