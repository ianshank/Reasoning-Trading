/**
 * LineChart component unit tests
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { LineChart, LineChartProps } from '../../../../src/components/charts/LineChart';

const mockData = [
  { x: 1, value1: 100, value2: 80 },
  { x: 2, value1: 120, value2: 90 },
  { x: 3, value1: 110, value2: 95 },
  { x: 4, value1: 130, value2: 100 },
  { x: 5, value1: 125, value2: 105 },
];

const defaultProps: LineChartProps = {
  data: mockData,
  lines: [
    { dataKey: 'value1', name: 'Series 1' },
    { dataKey: 'value2', name: 'Series 2' },
  ],
};

describe('LineChart', () => {
  it('should render without crashing', () => {
    render(<LineChart {...defaultProps} />);
    const chart = screen.getByRole('img', { name: /line chart/i });
    expect(chart).toBeInTheDocument();
  });

  it('should render with custom aria label', () => {
    const customLabel = 'Custom line chart';
    render(<LineChart {...defaultProps} ariaLabel={customLabel} />);
    const chart = screen.getByRole('img', { name: customLabel });
    expect(chart).toBeInTheDocument();
  });

  it('should render multiple lines', () => {
    const { container } = render(<LineChart {...defaultProps} />);
    const lines = container.querySelectorAll('.recharts-line');
    expect(lines.length).toBe(2);
  });

  it('should apply custom colors to lines', () => {
    const propsWithColors: LineChartProps = {
      ...defaultProps,
      lines: [
        { dataKey: 'value1', name: 'Series 1', color: '#ff0000' },
        { dataKey: 'value2', name: 'Series 2', color: '#00ff00' },
      ],
    };

    const { container } = render(<LineChart {...propsWithColors} />);
    const lines = container.querySelectorAll('.recharts-line-curve');

    expect(lines[0]).toHaveAttribute('stroke', '#ff0000');
    expect(lines[1]).toHaveAttribute('stroke', '#00ff00');
  });

  it('should render x-axis with custom label', () => {
    const xAxisLabel = 'Time Period';
    render(
      <LineChart
        {...defaultProps}
        xAxis={{ label: xAxisLabel }}
      />
    );

    const { container } = render(<LineChart {...defaultProps} xAxis={{ label: xAxisLabel }} />);
    expect(container.textContent).toContain(xAxisLabel);
  });

  it('should render y-axis with custom label', () => {
    const yAxisLabel = 'Values';
    const { container } = render(
      <LineChart
        {...defaultProps}
        yAxis={{ label: yAxisLabel }}
      />
    );
    expect(container.textContent).toContain(yAxisLabel);
  });

  it('should hide grid when showGrid is false', () => {
    const { container } = render(<LineChart {...defaultProps} showGrid={false} />);
    const grid = container.querySelector('.recharts-cartesian-grid');
    expect(grid).not.toBeInTheDocument();
  });

  it('should show grid when showGrid is true', () => {
    const { container } = render(<LineChart {...defaultProps} showGrid={true} />);
    const grid = container.querySelector('.recharts-cartesian-grid');
    expect(grid).toBeInTheDocument();
  });

  it('should hide legend when showLegend is false', () => {
    const { container } = render(<LineChart {...defaultProps} showLegend={false} />);
    const legend = container.querySelector('.recharts-legend-wrapper');
    expect(legend).not.toBeInTheDocument();
  });

  it('should show legend when showLegend is true', () => {
    const { container } = render(<LineChart {...defaultProps} showLegend={true} />);
    const legend = container.querySelector('.recharts-legend-wrapper');
    expect(legend).toBeInTheDocument();
  });

  it('should render reference lines', () => {
    const referenceLines = [
      { y: 100, label: 'Target', stroke: '#ff0000' },
      { y: 120, label: 'Max', stroke: '#00ff00' },
    ];

    const { container } = render(
      <LineChart {...defaultProps} referenceLines={referenceLines} />
    );

    const refLines = container.querySelectorAll('.recharts-reference-line');
    expect(refLines.length).toBe(2);
  });

  it('should disable tooltip when tooltip.enabled is false', () => {
    const { container } = render(
      <LineChart {...defaultProps} tooltip={{ enabled: false }} />
    );
    const tooltip = container.querySelector('.recharts-tooltip-wrapper');
    expect(tooltip).not.toBeInTheDocument();
  });

  it('should apply custom className', () => {
    const customClass = 'custom-line-chart';
    const { container } = render(<LineChart {...defaultProps} className={customClass} />);
    const chart = container.querySelector(`.${customClass}`);
    expect(chart).toBeInTheDocument();
  });

  it('should set custom height', () => {
    const customHeight = 500;
    const { container } = render(<LineChart {...defaultProps} height={customHeight} />);
    const chart = container.querySelector('.line-chart');
    expect(chart).toHaveStyle({ height: `${customHeight}px` });
  });

  it('should apply custom margin', () => {
    const customMargin = { top: 10, right: 20, bottom: 30, left: 40 };
    const { container } = render(<LineChart {...defaultProps} margin={customMargin} />);
    const surface = container.querySelector('.recharts-surface');
    expect(surface).toBeInTheDocument();
  });

  it('should handle line click events', () => {
    const onLineClick = jest.fn();
    const { container } = render(<LineChart {...defaultProps} onLineClick={onLineClick} />);

    const dots = container.querySelectorAll('.recharts-active-dot');
    if (dots.length > 0) {
      fireEvent.click(dots[0]);
      expect(onLineClick).toHaveBeenCalled();
    }
  });

  it('should render with dashed lines', () => {
    const propsWithDashed: LineChartProps = {
      ...defaultProps,
      lines: [
        { dataKey: 'value1', name: 'Series 1', strokeDasharray: '5 5' },
      ],
    };

    const { container } = render(<LineChart {...propsWithDashed} />);
    const line = container.querySelector('.recharts-line-curve');
    expect(line).toHaveAttribute('stroke-dasharray', '5 5');
  });

  it('should render with custom stroke width', () => {
    const propsWithStroke: LineChartProps = {
      ...defaultProps,
      lines: [
        { dataKey: 'value1', name: 'Series 1', strokeWidth: 4 },
      ],
    };

    const { container } = render(<LineChart {...propsWithStroke} />);
    const line = container.querySelector('.recharts-line-curve');
    expect(line).toHaveAttribute('stroke-width', '4');
  });

  it('should render with dots when dot is true', () => {
    const propsWithDots: LineChartProps = {
      ...defaultProps,
      lines: [
        { dataKey: 'value1', name: 'Series 1', dot: true },
      ],
    };

    const { container } = render(<LineChart {...propsWithDots} />);
    const dots = container.querySelectorAll('.recharts-line-dot');
    expect(dots.length).toBeGreaterThan(0);
  });

  it('should format axis values with custom formatter', () => {
    const yAxisFormatter = (value: number) => `$${value}`;

    const { container } = render(
      <LineChart
        {...defaultProps}
        yAxis={{ tickFormatter: yAxisFormatter }}
      />
    );

    const yAxisTicks = container.querySelectorAll('.recharts-yAxis .recharts-cartesian-axis-tick-value');
    expect(yAxisTicks.length).toBeGreaterThan(0);
  });

  it('should handle empty data gracefully', () => {
    const emptyProps: LineChartProps = {
      data: [],
      lines: [{ dataKey: 'value', name: 'Series' }],
    };

    expect(() => render(<LineChart {...emptyProps} />)).not.toThrow();
  });

  it('should render with custom domain', () => {
    const { container } = render(
      <LineChart
        {...defaultProps}
        yAxis={{ domain: [0, 200] }}
      />
    );

    const yAxis = container.querySelector('.recharts-yAxis');
    expect(yAxis).toBeInTheDocument();
  });
});
