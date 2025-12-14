/**
 * Sparkline component unit tests
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { Sparkline, SparklineProps } from '../../../../src/components/charts/Sparkline';

const mockData = [
  { value: 10 },
  { value: 15 },
  { value: 12 },
  { value: 18 },
  { value: 20 },
  { value: 17 },
  { value: 22 },
];

const defaultProps: SparklineProps = {
  data: mockData,
};

describe('Sparkline', () => {
  it('should render without crashing', () => {
    render(<Sparkline {...defaultProps} />);
    const sparkline = screen.getByRole('img', { name: /sparkline chart/i });
    expect(sparkline).toBeInTheDocument();
  });

  it('should render with custom aria label', () => {
    const customLabel = 'Custom sparkline';
    render(<Sparkline {...defaultProps} ariaLabel={customLabel} />);
    const sparkline = screen.getByRole('img', { name: customLabel });
    expect(sparkline).toBeInTheDocument();
  });

  it('should apply custom className', () => {
    const customClass = 'custom-sparkline';
    const { container } = render(<Sparkline {...defaultProps} className={customClass} />);
    const sparkline = container.querySelector(`.${customClass}`);
    expect(sparkline).toBeInTheDocument();
  });

  it('should set custom width', () => {
    const customWidth = 200;
    const { container } = render(<Sparkline {...defaultProps} width={customWidth} />);
    const sparkline = container.querySelector('.sparkline-container');
    expect(sparkline).toHaveStyle({ width: `${customWidth}px` });
  });

  it('should set custom width as string', () => {
    const customWidth = '50%';
    const { container } = render(<Sparkline {...defaultProps} width={customWidth} />);
    const sparkline = container.querySelector('.sparkline-container');
    expect(sparkline).toHaveStyle({ width: customWidth });
  });

  it('should set custom height', () => {
    const customHeight = 60;
    const { container } = render(<Sparkline {...defaultProps} height={customHeight} />);
    const sparkline = container.querySelector('.sparkline-container');
    expect(sparkline).toHaveStyle({ height: `${customHeight}px` });
  });

  it('should render line chart', () => {
    const { container } = render(<Sparkline {...defaultProps} />);
    const line = container.querySelector('.recharts-line');
    expect(line).toBeInTheDocument();
  });

  it('should apply custom color', () => {
    const customColor = '#ff0000';
    const { container } = render(<Sparkline {...defaultProps} color={customColor} />);
    const line = container.querySelector('.recharts-line-curve');
    expect(line).toHaveAttribute('stroke', customColor);
  });

  it('should show trend when showTrend is true and data is upward', () => {
    const upwardData = [
      { value: 10 },
      { value: 15 },
      { value: 20 },
    ];

    render(<Sparkline data={upwardData} showTrend={true} />);
    const trend = screen.getByText(/↑/);
    expect(trend).toBeInTheDocument();
  });

  it('should show downward trend when data is downward', () => {
    const downwardData = [
      { value: 20 },
      { value: 15 },
      { value: 10 },
    ];

    render(<Sparkline data={downwardData} showTrend={true} />);
    const trend = screen.getByText(/↓/);
    expect(trend).toBeInTheDocument();
  });

  it('should not show trend when showTrend is false', () => {
    render(<Sparkline {...defaultProps} showTrend={false} />);
    const trendElement = screen.queryByText(/↑|↓/);
    expect(trendElement).not.toBeInTheDocument();
  });

  it('should calculate positive percentage change correctly', () => {
    const data = [
      { value: 100 },
      { value: 150 },
    ];

    render(<Sparkline data={data} showTrend={true} />);
    const trend = screen.getByText(/50\.00%/);
    expect(trend).toBeInTheDocument();
  });

  it('should calculate negative percentage change correctly', () => {
    const data = [
      { value: 100 },
      { value: 50 },
    ];

    render(<Sparkline data={data} showTrend={true} />);
    const trend = screen.getByText(/50\.00%/);
    expect(trend).toBeInTheDocument();
  });

  it('should handle zero percentage change', () => {
    const data = [
      { value: 100 },
      { value: 100 },
    ];

    render(<Sparkline data={data} showTrend={true} />);
    const trend = screen.getByText(/0\.00%/);
    expect(trend).toBeInTheDocument();
  });

  it('should not show trend for single data point', () => {
    const singleData = [{ value: 10 }];
    render(<Sparkline data={singleData} showTrend={true} />);
    const trendElement = screen.queryByText(/↑|↓/);
    expect(trendElement).not.toBeInTheDocument();
  });

  it('should not show trend for empty data', () => {
    const emptyData: Array<{ value: number }> = [];
    render(<Sparkline data={emptyData} showTrend={true} />);
    const trendElement = screen.queryByText(/↑|↓/);
    expect(trendElement).not.toBeInTheDocument();
  });

  it('should render with timestamps', () => {
    const dataWithTimestamps = [
      { value: 10, timestamp: 1609459200000 },
      { value: 15, timestamp: 1609545600000 },
      { value: 20, timestamp: 1609632000000 },
    ];

    const { container } = render(<Sparkline data={dataWithTimestamps} />);
    const line = container.querySelector('.recharts-line');
    expect(line).toBeInTheDocument();
  });

  it('should handle negative values', () => {
    const negativeData = [
      { value: -10 },
      { value: -5 },
      { value: -15 },
    ];

    const { container } = render(<Sparkline data={negativeData} />);
    const line = container.querySelector('.recharts-line');
    expect(line).toBeInTheDocument();
  });

  it('should handle mixed positive and negative values', () => {
    const mixedData = [
      { value: -10 },
      { value: 5 },
      { value: -3 },
      { value: 8 },
    ];

    const { container } = render(<Sparkline data={mixedData} />);
    const line = container.querySelector('.recharts-line');
    expect(line).toBeInTheDocument();
  });

  it('should have correct Y-axis domain with padding', () => {
    const { container } = render(<Sparkline {...defaultProps} />);
    const yAxis = container.querySelector('.recharts-yAxis');
    expect(yAxis).toBeInTheDocument();
  });

  it('should hide axis', () => {
    const { container } = render(<Sparkline {...defaultProps} />);
    const xAxis = container.querySelector('.recharts-xAxis');
    const yAxis = container.querySelector('.recharts-yAxis');

    expect(xAxis).not.toBeInTheDocument();
    expect(yAxis).not.toBeInTheDocument();
  });

  it('should render without dots', () => {
    const { container } = render(<Sparkline {...defaultProps} />);
    const dots = container.querySelectorAll('.recharts-line-dot');
    expect(dots.length).toBe(0);
  });

  it('should have smooth line animation', () => {
    const { container } = render(<Sparkline {...defaultProps} />);
    const line = container.querySelector('.recharts-line');
    expect(line).toBeInTheDocument();
  });

  it('should render trend with correct color for positive change', () => {
    const upwardData = [
      { value: 10 },
      { value: 20 },
    ];

    const { container } = render(<Sparkline data={upwardData} showTrend={true} />);
    const trendSpan = container.querySelector('.sparkline-trend');
    expect(trendSpan).toBeInTheDocument();
  });

  it('should render trend with correct color for negative change', () => {
    const downwardData = [
      { value: 20 },
      { value: 10 },
    ];

    const { container } = render(<Sparkline data={downwardData} showTrend={true} />);
    const trendSpan = container.querySelector('.sparkline-trend');
    expect(trendSpan).toBeInTheDocument();
  });

  it('should handle very small values', () => {
    const smallData = [
      { value: 0.001 },
      { value: 0.002 },
      { value: 0.0015 },
    ];

    const { container } = render(<Sparkline data={smallData} />);
    const line = container.querySelector('.recharts-line');
    expect(line).toBeInTheDocument();
  });

  it('should handle very large values', () => {
    const largeData = [
      { value: 1000000 },
      { value: 2000000 },
      { value: 1500000 },
    ];

    const { container } = render(<Sparkline data={largeData} />);
    const line = container.querySelector('.recharts-line');
    expect(line).toBeInTheDocument();
  });

  it('should apply default width and height', () => {
    const { container } = render(<Sparkline {...defaultProps} />);
    const sparkline = container.querySelector('.sparkline-container');
    expect(sparkline).toHaveStyle({ width: '100%', height: '40px' });
  });
});
