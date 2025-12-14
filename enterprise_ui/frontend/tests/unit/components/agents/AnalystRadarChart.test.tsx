import React from 'react';
import { render, screen } from '@testing-library/react';
import { AnalystRadarChart } from '../../../../src/components/agents/AnalystRadarChart';
import type { AnalystSignals } from '../../../../src/types/trading';

// Mock Recharts to avoid rendering issues in tests
jest.mock('recharts', () => {
  const React = require('react');
  return {
    ResponsiveContainer: ({ children }: any) => (
      <div data-testid="responsive-container">{children}</div>
    ),
    RadarChart: ({ children }: any) => <div data-testid="radar-chart">{children}</div>,
    Radar: ({ name, dataKey }: any) => (
      <div data-testid={`radar-${dataKey}`}>{name}</div>
    ),
    PolarGrid: () => <div data-testid="polar-grid" />,
    PolarAngleAxis: () => <div data-testid="polar-angle-axis" />,
    PolarRadiusAxis: () => <div data-testid="polar-radius-axis" />,
    Tooltip: () => <div data-testid="tooltip" />,
    Legend: () => <div data-testid="legend" />,
  };
});

describe('AnalystRadarChart', () => {
  const mockSignals: AnalystSignals = {
    market_analyst_score: 0.5,
    news_analyst_score: 0.3,
    social_sentiment_score: -0.2,
    fundamental_analyst_score: 0.7,
    macro_analyst_score: -0.4,
    market_analyst_confidence: 0.8,
    news_analyst_confidence: 0.6,
    social_sentiment_confidence: 0.7,
    fundamental_analyst_confidence: 0.9,
    macro_analyst_confidence: 0.5,
    researcher_consensus: 0.3,
    debate_confidence: 0.75,
    evidence_packets: {},
  };

  describe('Basic Rendering', () => {
    it('should render the component with title', () => {
      render(<AnalystRadarChart signals={mockSignals} />);
      expect(screen.getByText('Analyst Signals')).toBeInTheDocument();
    });

    it('should render radar chart container', () => {
      render(<AnalystRadarChart signals={mockSignals} />);
      expect(screen.getByTestId('responsive-container')).toBeInTheDocument();
      expect(screen.getByTestId('radar-chart')).toBeInTheDocument();
    });

    it('should render signal radar', () => {
      render(<AnalystRadarChart signals={mockSignals} />);
      expect(screen.getByTestId('radar-signal')).toBeInTheDocument();
    });

    it('should render polar grid and axes', () => {
      render(<AnalystRadarChart signals={mockSignals} />);
      expect(screen.getByTestId('polar-grid')).toBeInTheDocument();
      expect(screen.getByTestId('polar-angle-axis')).toBeInTheDocument();
      expect(screen.getByTestId('polar-radius-axis')).toBeInTheDocument();
    });
  });

  describe('Confidence Overlay', () => {
    it('should show confidence overlay by default', () => {
      render(<AnalystRadarChart signals={mockSignals} />);
      expect(screen.getByText('Confidence overlay enabled')).toBeInTheDocument();
    });

    it('should render confidence radar when showConfidence is true', () => {
      render(<AnalystRadarChart signals={mockSignals} showConfidence={true} />);
      expect(screen.getByTestId('radar-signal')).toBeInTheDocument();
    });

    it('should hide confidence overlay when showConfidence is false', () => {
      render(<AnalystRadarChart signals={mockSignals} showConfidence={false} />);
      expect(screen.queryByText('Confidence overlay enabled')).not.toBeInTheDocument();
    });
  });

  describe('Legend', () => {
    it('should render legend explanation', () => {
      render(<AnalystRadarChart signals={mockSignals} />);
      expect(screen.getByText('Bullish Signal')).toBeInTheDocument();
      expect(screen.getByText('Bearish Signal')).toBeInTheDocument();
      expect(screen.getByText('Neutral Signal')).toBeInTheDocument();
    });

    it('should show score thresholds in legend', () => {
      render(<AnalystRadarChart signals={mockSignals} />);
      expect(screen.getByText('Score above 0.3')).toBeInTheDocument();
      expect(screen.getByText('Score below -0.3')).toBeInTheDocument();
      expect(screen.getByText('Score between -0.3 and 0.3')).toBeInTheDocument();
    });
  });

  describe('Custom Props', () => {
    it('should apply custom className', () => {
      const { container } = render(
        <AnalystRadarChart signals={mockSignals} className="custom-class" />
      );
      const card = container.querySelector('.custom-class');
      expect(card).toBeInTheDocument();
    });

    it('should accept highlightedAnalyst prop', () => {
      render(<AnalystRadarChart signals={mockSignals} highlightedAnalyst="Market" />);
      expect(screen.getByText('Analyst Signals')).toBeInTheDocument();
    });
  });

  describe('Data Processing', () => {
    it('should handle all analyst scores', () => {
      render(<AnalystRadarChart signals={mockSignals} />);
      // Chart should be rendered with all data points
      expect(screen.getByTestId('radar-chart')).toBeInTheDocument();
    });

    it('should handle edge case values (-1 and 1)', () => {
      const edgeSignals: AnalystSignals = {
        ...mockSignals,
        market_analyst_score: 1,
        news_analyst_score: -1,
        social_sentiment_score: 0,
        fundamental_analyst_score: 0.99,
        macro_analyst_score: -0.99,
      };
      render(<AnalystRadarChart signals={edgeSignals} />);
      expect(screen.getByTestId('radar-chart')).toBeInTheDocument();
    });

    it('should handle zero confidence values', () => {
      const zeroConfidenceSignals: AnalystSignals = {
        ...mockSignals,
        market_analyst_confidence: 0,
        news_analyst_confidence: 0,
        social_sentiment_confidence: 0,
        fundamental_analyst_confidence: 0,
        macro_analyst_confidence: 0,
      };
      render(<AnalystRadarChart signals={zeroConfidenceSignals} />);
      expect(screen.getByTestId('radar-chart')).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should have proper heading structure', () => {
      render(<AnalystRadarChart signals={mockSignals} />);
      const heading = screen.getByText('Analyst Signals');
      expect(heading).toHaveClass('text-lg', 'font-semibold');
    });

    it('should have aria-hidden on decorative elements', () => {
      const { container } = render(<AnalystRadarChart signals={mockSignals} />);
      const decorativeElements = container.querySelectorAll('[aria-hidden="true"]');
      expect(decorativeElements.length).toBeGreaterThan(0);
    });
  });

  describe('Dark Mode Support', () => {
    it('should have dark mode classes', () => {
      const { container } = render(<AnalystRadarChart signals={mockSignals} />);
      const cardElement = container.querySelector('.dark\\:bg-gray-800');
      expect(cardElement).toBeInTheDocument();
    });
  });
});
