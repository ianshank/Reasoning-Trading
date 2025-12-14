/**
 * PortfolioSummary Component Tests
 *
 * Unit tests for the PortfolioSummary component
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { PortfolioSummary } from '../../../../src/components/portfolio/PortfolioSummary';
import type { Portfolio, Position } from '../../../../src/types/portfolio';
import { PositionStatus, PositionSide } from '../../../../src/types/portfolio';
import { TradingDirection, TimeHorizon, OrderType } from '../../../../src/types/actions';

describe('PortfolioSummary', () => {
  const mockPosition: Position = {
    symbol: 'AAPL',
    position_id: 'pos-1',
    side: PositionSide.LONG,
    status: PositionStatus.OPEN,
    quantity: 100,
    entry_price: 150.0,
    current_price: 155.0,
    cost_basis: 15000,
    market_value: 15500,
    unrealized_pnl: 500,
    unrealized_pnl_pct: 3.33,
    realized_pnl: 0,
    stop_loss_price: 145.0,
    take_profit_price: 165.0,
    trailing_stop: false,
    trailing_distance_pct: 0.03,
    entry_time: '2024-01-01T10:00:00Z',
    exit_time: null,
    time_horizon: '1D',
    entry_action: {
      direction: TradingDirection.BUY,
      position_size: { size_fraction: 0.1, kelly_fraction: 0.5 },
      stop_loss: {
        stop_loss_pct: 0.05,
        take_profit_pct: 0.1,
        trailing_stop: false,
        trailing_distance_pct: 0.03,
      },
      time_horizon: TimeHorizon.SWING,
      order_type: OrderType.MARKET,
      limit_price: null,
      confidence: 0.8,
      reasoning: 'Test position',
    },
    notes: 'Test position',
  };

  const mockPortfolio: Portfolio = {
    portfolio_id: 'portfolio-1',
    account_id: 'account-1',
    total_value: 100000,
    cash_balance: 50000,
    buying_power: 75000,
    positions: [mockPosition],
    position_count: 1,
    long_positions: 1,
    short_positions: 0,
    unrealized_pnl: 500,
    realized_pnl_today: 200,
    realized_pnl_total: 5000,
    risk_metrics: {
      daily_var_95: -1500,
      daily_var_99: -2000,
      max_drawdown: 0.05,
      current_drawdown: 0.02,
      drawdown_start: null,
      portfolio_volatility: 0.15,
      sharpe_ratio: 1.5,
      sortino_ratio: 2.0,
      largest_position_pct: 0.15,
      top5_concentration: 0.45,
      herfindahl_index: 0.08,
      leverage_ratio: 1.2,
      margin_utilization: 0.3,
    },
    performance_metrics: {
      total_return: 10000,
      total_return_pct: 10.0,
      today_return: 700,
      today_return_pct: 0.7,
      day_return_pct: 0.7,
      week_return_pct: 2.5,
      month_return_pct: 5.0,
      year_return_pct: 15.0,
      win_rate: 0.65,
      profit_factor: 2.1,
      avg_win: 500,
      avg_loss: -250,
      largest_win: 2000,
      largest_loss: -800,
      total_trades: 50,
      winning_trades: 32,
      losing_trades: 18,
      avg_trade_duration_hours: 24,
    },
    allocation: {
      cash: 50000,
      stocks: 45000,
      crypto: 3000,
      options: 2000,
      other: 0,
    },
    margin_used: 25000,
    margin_available: 50000,
    maintenance_margin: 20000,
    last_updated: '2024-01-15T12:00:00Z',
    currency: 'USD',
  };

  describe('Loading State', () => {
    it('should render loading skeleton when isLoading is true', () => {
      render(<PortfolioSummary portfolio={null} isLoading={true} />);

      const loadingElements = document.querySelectorAll('.animate-pulse');
      expect(loadingElements.length).toBeGreaterThan(0);
    });

    it('should render loading skeleton when portfolio is null', () => {
      render(<PortfolioSummary portfolio={null} isLoading={true} />);

      expect(screen.queryByText('Total Value')).not.toBeInTheDocument();
    });
  });

  describe('Portfolio Display', () => {
    beforeEach(() => {
      render(<PortfolioSummary portfolio={mockPortfolio} isLoading={false} />);
    });

    it('should render total value correctly', () => {
      expect(screen.getByText('Total Value')).toBeInTheDocument();
      expect(screen.getByText('$100,000.00')).toBeInTheDocument();
    });

    it('should display cash balance', () => {
      expect(screen.getByText(/Cash:/)).toBeInTheDocument();
      expect(screen.getByText(/\$50,000.00/)).toBeInTheDocument();
    });

    it('should display daily P&L', () => {
      expect(screen.getByText('Daily P&L')).toBeInTheDocument();
      // Total P&L = unrealized (500) + realized_today (200) = 700
      expect(screen.getByText('$700.00')).toBeInTheDocument();
    });

    it('should display daily P&L percentage', () => {
      // P&L % = (700 / (100000 - 700)) * 100 ≈ 0.71%
      const pnlPercentages = screen.getAllByText(/\+0\.7[0-9]%/);
      expect(pnlPercentages.length).toBeGreaterThan(0);
    });

    it('should display unrealized P&L', () => {
      expect(screen.getByText(/Unrealized:/)).toBeInTheDocument();
      expect(screen.getByText('$500.00')).toBeInTheDocument();
    });

    it('should display realized P&L', () => {
      expect(screen.getByText(/Realized:/)).toBeInTheDocument();
      expect(screen.getByText('$200.00')).toBeInTheDocument();
    });

    it('should display margin usage', () => {
      expect(screen.getByText('Margin Usage')).toBeInTheDocument();
      // Margin usage = 25000 / (25000 + 50000) * 100 = 33.3%
      expect(screen.getByText(/33\.3%/)).toBeInTheDocument();
    });

    it('should render margin usage progress bar', () => {
      const progressBars = document.querySelectorAll('[role="progressbar"]');
      expect(progressBars.length).toBeGreaterThan(0);
    });

    it('should display margin used and available', () => {
      expect(screen.getByText(/\$25,000.00 used/)).toBeInTheDocument();
      expect(screen.getByText(/\$50,000.00 available/)).toBeInTheDocument();
    });
  });

  describe('P&L Coloring', () => {
    it('should apply green color for positive P&L', () => {
      render(<PortfolioSummary portfolio={mockPortfolio} isLoading={false} />);

      const positiveElements = document.querySelectorAll('.text-green-600');
      expect(positiveElements.length).toBeGreaterThan(0);
    });

    it('should apply red color for negative P&L', () => {
      const negativePortfolio = {
        ...mockPortfolio,
        unrealized_pnl: -500,
        realized_pnl_today: -200,
      };

      render(<PortfolioSummary portfolio={negativePortfolio} isLoading={false} />);

      const negativeElements = document.querySelectorAll('.text-red-600');
      expect(negativeElements.length).toBeGreaterThan(0);
    });
  });

  describe('Margin Usage Indicator', () => {
    it('should show green for low margin usage (<50%)', () => {
      render(<PortfolioSummary portfolio={mockPortfolio} isLoading={false} />);

      const progressBar = document.querySelector('.bg-green-500');
      expect(progressBar).toBeInTheDocument();
    });

    it('should show yellow for medium margin usage (50-70%)', () => {
      const mediumMarginPortfolio = {
        ...mockPortfolio,
        margin_used: 45000,
        margin_available: 30000,
      };

      render(
        <PortfolioSummary portfolio={mediumMarginPortfolio} isLoading={false} />
      );

      const progressBar = document.querySelector('.bg-yellow-500');
      expect(progressBar).toBeInTheDocument();
    });

    it('should show orange for high margin usage (70-90%)', () => {
      const highMarginPortfolio = {
        ...mockPortfolio,
        margin_used: 60000,
        margin_available: 15000,
      };

      render(
        <PortfolioSummary portfolio={highMarginPortfolio} isLoading={false} />
      );

      const progressBar = document.querySelector('.bg-orange-500');
      expect(progressBar).toBeInTheDocument();
    });

    it('should show red for critical margin usage (>90%)', () => {
      const criticalMarginPortfolio = {
        ...mockPortfolio,
        margin_used: 70000,
        margin_available: 5000,
      };

      render(
        <PortfolioSummary portfolio={criticalMarginPortfolio} isLoading={false} />
      );

      const progressBar = document.querySelector('.bg-red-500');
      expect(progressBar).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    beforeEach(() => {
      render(<PortfolioSummary portfolio={mockPortfolio} isLoading={false} />);
    });

    it('should have proper ARIA labels', () => {
      expect(screen.getByLabelText('Total Portfolio Value')).toBeInTheDocument();
      expect(screen.getByLabelText('Daily Profit and Loss')).toBeInTheDocument();
      expect(
        screen.getByLabelText('Unrealized and Realized Profit and Loss')
      ).toBeInTheDocument();
      expect(screen.getByLabelText('Margin Usage')).toBeInTheDocument();
    });

    it('should have progress bar with proper ARIA attributes', () => {
      const progressBar = screen.getByRole('progressbar');
      expect(progressBar).toHaveAttribute('aria-valuenow');
      expect(progressBar).toHaveAttribute('aria-valuemin', '0');
      expect(progressBar).toHaveAttribute('aria-valuemax', '100');
      expect(progressBar).toHaveAttribute('aria-label');
    });

    it('should use semantic HTML with article roles', () => {
      const articles = screen.getAllByRole('article');
      expect(articles.length).toBe(4);
    });
  });

  describe('Dark Mode Support', () => {
    it('should include dark mode classes', () => {
      render(<PortfolioSummary portfolio={mockPortfolio} isLoading={false} />);

      const darkModeElements = document.querySelectorAll(
        '[class*="dark:bg-"], [class*="dark:text-"]'
      );
      expect(darkModeElements.length).toBeGreaterThan(0);
    });
  });

  describe('Responsive Design', () => {
    it('should include responsive grid classes', () => {
      const { container } = render(
        <PortfolioSummary portfolio={mockPortfolio} isLoading={false} />
      );

      const grid = container.querySelector('.grid');
      expect(grid).toHaveClass('grid-cols-1');
      expect(grid).toHaveClass('md:grid-cols-2');
      expect(grid).toHaveClass('lg:grid-cols-4');
    });
  });

  describe('Edge Cases', () => {
    it('should handle zero total value', () => {
      const zeroValuePortfolio = {
        ...mockPortfolio,
        total_value: 0,
      };

      render(
        <PortfolioSummary portfolio={zeroValuePortfolio} isLoading={false} />
      );

      expect(screen.getByText('$0.00')).toBeInTheDocument();
    });

    it('should handle zero margin', () => {
      const noMarginPortfolio = {
        ...mockPortfolio,
        margin_used: 0,
        margin_available: 0,
      };

      render(<PortfolioSummary portfolio={noMarginPortfolio} isLoading={false} />);

      expect(screen.getByText('0.0%')).toBeInTheDocument();
    });

    it('should handle negative cash balance', () => {
      const negativeCashPortfolio = {
        ...mockPortfolio,
        cash_balance: -1000,
      };

      render(
        <PortfolioSummary portfolio={negativeCashPortfolio} isLoading={false} />
      );

      expect(screen.getByText(/-\$1,000\.00/)).toBeInTheDocument();
    });
  });
});
