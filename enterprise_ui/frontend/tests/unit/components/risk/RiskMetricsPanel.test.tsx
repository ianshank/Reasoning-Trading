/**
 * RiskMetricsPanel Component Tests
 *
 * Unit tests for the RiskMetricsPanel component
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { RiskMetricsPanel } from '../../../../src/components/risk/RiskMetricsPanel';
import type { RiskMetrics } from '../../../../src/types/portfolio';

describe('RiskMetricsPanel', () => {
  const mockRiskMetrics: RiskMetrics = {
    daily_var_95: -1500,
    daily_var_99: -2000,
    max_drawdown: 0.12,
    current_drawdown: 0.05,
    drawdown_start: '2024-01-10T00:00:00Z',
    portfolio_volatility: 0.18,
    sharpe_ratio: 1.8,
    sortino_ratio: 2.3,
    largest_position_pct: 0.22,
    top5_concentration: 0.65,
    herfindahl_index: 0.08,
    leverage_ratio: 1.5,
    margin_utilization: 0.45,
  };

  describe('Loading State', () => {
    it('should render loading skeleton when isLoading is true', () => {
      render(<RiskMetricsPanel metrics={null} isLoading={true} />);

      const loadingElements = document.querySelectorAll('.animate-pulse');
      expect(loadingElements.length).toBeGreaterThan(0);
    });

    it('should render loading skeleton when metrics is null', () => {
      render(<RiskMetricsPanel metrics={null} isLoading={true} />);

      expect(screen.queryByText('Value at Risk')).not.toBeInTheDocument();
    });
  });

  describe('Value at Risk Section', () => {
    beforeEach(() => {
      render(<RiskMetricsPanel metrics={mockRiskMetrics} isLoading={false} />);
    });

    it('should display Value at Risk heading', () => {
      expect(screen.getByText('Value at Risk')).toBeInTheDocument();
    });

    it('should display Daily VaR 95%', () => {
      expect(screen.getByText(/Daily VaR \(95%\)/)).toBeInTheDocument();
      expect(screen.getByText(/-\$1,500/)).toBeInTheDocument();
    });

    it('should display Daily VaR 99%', () => {
      expect(screen.getByText(/Daily VaR \(99%\)/)).toBeInTheDocument();
      expect(screen.getByText(/-\$2,000/)).toBeInTheDocument();
    });

    it('should show confidence level badges', () => {
      expect(screen.getByText('95%')).toBeInTheDocument();
      expect(screen.getByText('99%')).toBeInTheDocument();
    });

    it('should handle null VaR values', () => {
      const nullVarMetrics = {
        ...mockRiskMetrics,
        daily_var_95: null,
        daily_var_99: null,
      };

      render(<RiskMetricsPanel metrics={nullVarMetrics} isLoading={false} />);

      const naTexts = screen.getAllByText('N/A');
      expect(naTexts.length).toBeGreaterThanOrEqual(2);
    });
  });

  describe('Drawdown Analysis Section', () => {
    beforeEach(() => {
      render(<RiskMetricsPanel metrics={mockRiskMetrics} isLoading={false} />);
    });

    it('should display Drawdown Analysis heading', () => {
      expect(screen.getByText('Drawdown Analysis')).toBeInTheDocument();
    });

    it('should display maximum drawdown', () => {
      expect(screen.getByText(/Maximum Drawdown/)).toBeInTheDocument();
      expect(screen.getByText('12.00%')).toBeInTheDocument();
    });

    it('should display current drawdown', () => {
      expect(screen.getByText(/Current Drawdown/)).toBeInTheDocument();
      expect(screen.getByText('5.00%')).toBeInTheDocument();
    });

    it('should display drawdown start date when available', () => {
      expect(screen.getByText(/Started:/)).toBeInTheDocument();
      expect(screen.getByText(/1\/10\/2024/)).toBeInTheDocument();
    });

    it('should not display start date when null', () => {
      const noDrawdownMetrics = {
        ...mockRiskMetrics,
        drawdown_start: null,
      };

      render(<RiskMetricsPanel metrics={noDrawdownMetrics} isLoading={false} />);

      expect(screen.queryByText(/Started:/)).not.toBeInTheDocument();
    });
  });

  describe('Risk-Adjusted Returns Section', () => {
    beforeEach(() => {
      render(<RiskMetricsPanel metrics={mockRiskMetrics} isLoading={false} />);
    });

    it('should display Risk-Adjusted Returns heading', () => {
      expect(screen.getByText('Risk-Adjusted Returns')).toBeInTheDocument();
    });

    it('should display Sharpe Ratio', () => {
      expect(screen.getByText(/Sharpe Ratio/)).toBeInTheDocument();
      expect(screen.getByText('1.80')).toBeInTheDocument();
    });

    it('should display Sortino Ratio', () => {
      expect(screen.getByText(/Sortino Ratio/)).toBeInTheDocument();
      expect(screen.getByText('2.30')).toBeInTheDocument();
    });

    it('should display Volatility', () => {
      expect(screen.getByText(/Volatility/)).toBeInTheDocument();
      expect(screen.getByText('18.00%')).toBeInTheDocument();
    });

    it('should handle null Sharpe ratio', () => {
      const nullSharpeMetrics = {
        ...mockRiskMetrics,
        sharpe_ratio: null,
      };

      render(<RiskMetricsPanel metrics={nullSharpeMetrics} isLoading={false} />);

      const naTexts = screen.getAllByText('N/A');
      expect(naTexts.length).toBeGreaterThan(0);
    });
  });

  describe('Concentration & Leverage Section', () => {
    beforeEach(() => {
      render(<RiskMetricsPanel metrics={mockRiskMetrics} isLoading={false} />);
    });

    it('should display Concentration & Leverage heading', () => {
      expect(screen.getByText('Concentration & Leverage')).toBeInTheDocument();
    });

    it('should display largest position percentage', () => {
      expect(screen.getByText(/Largest Position/)).toBeInTheDocument();
      expect(screen.getByText('22.00%')).toBeInTheDocument();
    });

    it('should display top 5 concentration', () => {
      expect(screen.getByText(/Top 5 Concentration/)).toBeInTheDocument();
      expect(screen.getByText('65.00%')).toBeInTheDocument();
    });

    it('should display leverage ratio', () => {
      expect(screen.getByText(/Leverage Ratio/)).toBeInTheDocument();
      expect(screen.getByText('1.50x')).toBeInTheDocument();
    });

    it('should display margin utilization', () => {
      expect(screen.getByText(/Margin Utilization/)).toBeInTheDocument();
      expect(screen.getByText('45.00%')).toBeInTheDocument();
    });

    it('should render margin utilization progress bar', () => {
      const progressBars = document.querySelectorAll('[role="progressbar"]');
      expect(progressBars.length).toBeGreaterThan(0);
    });
  });

  describe('Color Coding', () => {
    it('should apply yellow color for medium drawdown (10-15%)', () => {
      render(<RiskMetricsPanel metrics={mockRiskMetrics} isLoading={false} />);

      const yellowElements = document.querySelectorAll('.text-yellow-600');
      expect(yellowElements.length).toBeGreaterThan(0);
    });

    it('should apply red color for high drawdown (>20%)', () => {
      const highDrawdownMetrics = {
        ...mockRiskMetrics,
        max_drawdown: 0.25,
        current_drawdown: 0.22,
      };

      render(<RiskMetricsPanel metrics={highDrawdownMetrics} isLoading={false} />);

      const redElements = document.querySelectorAll('.text-red-600');
      expect(redElements.length).toBeGreaterThan(0);
    });

    it('should apply green color for good Sharpe ratio (>2.0)', () => {
      const goodSharpeMetrics = {
        ...mockRiskMetrics,
        sharpe_ratio: 2.5,
      };

      render(<RiskMetricsPanel metrics={goodSharpeMetrics} isLoading={false} />);

      const greenElements = document.querySelectorAll('.text-green-600');
      expect(greenElements.length).toBeGreaterThan(0);
    });

    it('should apply red color for poor Sharpe ratio (<0.5)', () => {
      const poorSharpeMetrics = {
        ...mockRiskMetrics,
        sharpe_ratio: 0.3,
      };

      render(<RiskMetricsPanel metrics={poorSharpeMetrics} isLoading={false} />);

      const redElements = document.querySelectorAll('.text-red-600');
      expect(redElements.length).toBeGreaterThan(0);
    });

    it('should apply red color for high concentration (>40%)', () => {
      const highConcentrationMetrics = {
        ...mockRiskMetrics,
        largest_position_pct: 0.45,
      };

      render(
        <RiskMetricsPanel metrics={highConcentrationMetrics} isLoading={false} />
      );

      const redElements = document.querySelectorAll('.text-red-600');
      expect(redElements.length).toBeGreaterThan(0);
    });

    it('should apply correct color for margin utilization', () => {
      render(<RiskMetricsPanel metrics={mockRiskMetrics} isLoading={false} />);

      const progressBar = document.querySelector('.bg-green-500');
      expect(progressBar).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    beforeEach(() => {
      render(<RiskMetricsPanel metrics={mockRiskMetrics} isLoading={false} />);
    });

    it('should use semantic HTML with article roles', () => {
      const articles = screen.getAllByRole('article');
      expect(articles.length).toBeGreaterThan(0);
    });

    it('should have ARIA labels for confidence badges', () => {
      const badge95 = screen.getByLabelText('95% confidence level');
      const badge99 = screen.getByLabelText('99% confidence level');

      expect(badge95).toBeInTheDocument();
      expect(badge99).toBeInTheDocument();
    });

    it('should have progress bar with proper ARIA attributes', () => {
      const progressBar = screen.getByRole('progressbar');
      expect(progressBar).toHaveAttribute('aria-valuenow');
      expect(progressBar).toHaveAttribute('aria-valuemin', '0');
      expect(progressBar).toHaveAttribute('aria-valuemax', '100');
    });
  });

  describe('Dark Mode Support', () => {
    it('should include dark mode classes', () => {
      render(<RiskMetricsPanel metrics={mockRiskMetrics} isLoading={false} />);

      const darkModeElements = document.querySelectorAll(
        '[class*="dark:bg-"], [class*="dark:text-"]'
      );
      expect(darkModeElements.length).toBeGreaterThan(0);
    });
  });

  describe('Responsive Design', () => {
    it('should include responsive grid classes', () => {
      const { container } = render(
        <RiskMetricsPanel metrics={mockRiskMetrics} isLoading={false} />
      );

      const grids = container.querySelectorAll('.grid');
      grids.forEach((grid) => {
        expect(
          grid.classList.contains('grid-cols-1') ||
            grid.classList.contains('md:grid-cols-2') ||
            grid.classList.contains('lg:grid-cols-3') ||
            grid.classList.contains('lg:grid-cols-4')
        ).toBe(true);
      });
    });
  });

  describe('Edge Cases', () => {
    it('should handle all null values gracefully', () => {
      const allNullMetrics: RiskMetrics = {
        daily_var_95: null,
        daily_var_99: null,
        max_drawdown: 0,
        current_drawdown: 0,
        drawdown_start: null,
        portfolio_volatility: 0,
        sharpe_ratio: null,
        sortino_ratio: null,
        largest_position_pct: 0,
        top5_concentration: 0,
        herfindahl_index: 0,
        leverage_ratio: 0,
        margin_utilization: 0,
      };

      render(<RiskMetricsPanel metrics={allNullMetrics} isLoading={false} />);

      const naTexts = screen.getAllByText('N/A');
      expect(naTexts.length).toBeGreaterThan(0);
    });

    it('should handle extreme values', () => {
      const extremeMetrics: RiskMetrics = {
        ...mockRiskMetrics,
        max_drawdown: 0.99,
        margin_utilization: 0.999,
        largest_position_pct: 0.95,
      };

      render(<RiskMetricsPanel metrics={extremeMetrics} isLoading={false} />);

      expect(screen.getByText('99.00%')).toBeInTheDocument();
      expect(screen.getByText('99.90%')).toBeInTheDocument();
      expect(screen.getByText('95.00%')).toBeInTheDocument();
    });

    it('should handle zero volatility', () => {
      const zeroVolMetrics = {
        ...mockRiskMetrics,
        portfolio_volatility: 0,
      };

      render(<RiskMetricsPanel metrics={zeroVolMetrics} isLoading={false} />);

      expect(screen.getByText('0.00%')).toBeInTheDocument();
    });
  });
});
