/**
 * MCTS Timeline Component
 *
 * Visualizes search progress over time, showing value convergence
 * and best action changes throughout the search.
 */

import React, { useEffect, useRef } from 'react';
import * as d3 from 'd3';
import { Card, CardHeader, CardBody } from '../ui/card';

/**
 * Iteration data point
 */
export interface IterationData {
  iteration: number;
  rootValue: number;
  bestAction: string;
  timestamp: string;
  nodesExplored: number;
}

/**
 * MCTSTimeline component props
 */
export interface MCTSTimelineProps {
  /**
   * Array of iteration data points
   */
  iterations: IterationData[];

  /**
   * Current iteration number
   */
  currentIteration: number;

  /**
   * Width of the chart
   * @default 600
   */
  width?: number;

  /**
   * Height of the chart
   * @default 300
   */
  height?: number;

  /**
   * Additional CSS classes
   */
  className?: string;
}

/**
 * Chart margins
 */
const MARGIN = { top: 20, right: 60, bottom: 40, left: 60 };

/**
 * MCTS search progress timeline
 *
 * Features:
 * - Real-time iteration updates
 * - Value convergence line chart
 * - Best action change markers
 * - Interactive tooltips
 * - Zoom capability
 *
 * @example
 * ```tsx
 * <MCTSTimeline
 *   iterations={iterationHistory}
 *   currentIteration={currentIter}
 * />
 * ```
 */
export const MCTSTimeline: React.FC<MCTSTimelineProps> = ({
  iterations,
  currentIteration,
  width = 600,
  height = 300,
  className = '',
}) => {
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    if (!svgRef.current || iterations.length === 0) return;

    // Clear previous chart
    d3.select(svgRef.current).selectAll('*').remove();

    const innerWidth = width - MARGIN.left - MARGIN.right;
    const innerHeight = height - MARGIN.top - MARGIN.bottom;

    // Create SVG
    const svg = d3
      .select(svgRef.current)
      .attr('width', width)
      .attr('height', height);

    const g = svg
      .append('g')
      .attr('transform', `translate(${MARGIN.left},${MARGIN.top})`);

    // Scales
    const xScale = d3
      .scaleLinear()
      .domain([0, Math.max(currentIteration, d3.max(iterations, (d) => d.iteration) || 1)])
      .range([0, innerWidth]);

    const yScale = d3
      .scaleLinear()
      .domain([
        d3.min(iterations, (d) => d.rootValue) || -1,
        d3.max(iterations, (d) => d.rootValue) || 1,
      ])
      .nice()
      .range([innerHeight, 0]);

    // Axes
    const xAxis = d3.axisBottom(xScale).ticks(10).tickFormat(d3.format('d'));
    const yAxis = d3.axisLeft(yScale).ticks(5);

    g.append('g')
      .attr('class', 'x-axis')
      .attr('transform', `translate(0,${innerHeight})`)
      .call(xAxis)
      .selectAll('text')
      .attr('fill', 'currentColor')
      .attr('class', 'text-gray-600 dark:text-gray-400');

    g.append('g')
      .attr('class', 'y-axis')
      .call(yAxis)
      .selectAll('text')
      .attr('fill', 'currentColor')
      .attr('class', 'text-gray-600 dark:text-gray-400');

    // Axis labels
    g.append('text')
      .attr('x', innerWidth / 2)
      .attr('y', innerHeight + 35)
      .attr('text-anchor', 'middle')
      .attr('class', 'text-sm fill-gray-700 dark:fill-gray-300')
      .text('Iteration');

    g.append('text')
      .attr('transform', 'rotate(-90)')
      .attr('x', -innerHeight / 2)
      .attr('y', -45)
      .attr('text-anchor', 'middle')
      .attr('class', 'text-sm fill-gray-700 dark:fill-gray-300')
      .text('Root Value');

    // Zero line
    g.append('line')
      .attr('x1', 0)
      .attr('x2', innerWidth)
      .attr('y1', yScale(0))
      .attr('y2', yScale(0))
      .attr('stroke', '#9ca3af')
      .attr('stroke-dasharray', '4,4')
      .attr('stroke-opacity', 0.5);

    // Line generator
    const line = d3
      .line<IterationData>()
      .x((d) => xScale(d.iteration))
      .y((d) => yScale(d.rootValue))
      .curve(d3.curveMonotoneX);

    // Draw line
    const path = g
      .append('path')
      .datum(iterations)
      .attr('fill', 'none')
      .attr('stroke', '#3b82f6')
      .attr('stroke-width', 2)
      .attr('d', line);

    // Animate line drawing
    const pathLength = (path.node() as SVGPathElement)?.getTotalLength() || 0;
    path
      .attr('stroke-dasharray', `${pathLength} ${pathLength}`)
      .attr('stroke-dashoffset', pathLength)
      .transition()
      .duration(1000)
      .attr('stroke-dashoffset', 0);

    // Gradient area under line
    const area = d3
      .area<IterationData>()
      .x((d) => xScale(d.iteration))
      .y0(innerHeight)
      .y1((d) => yScale(d.rootValue))
      .curve(d3.curveMonotoneX);

    g.append('path')
      .datum(iterations)
      .attr('fill', 'url(#gradient)')
      .attr('opacity', 0.3)
      .attr('d', area);

    // Gradient definition
    const gradient = svg
      .append('defs')
      .append('linearGradient')
      .attr('id', 'gradient')
      .attr('x1', '0%')
      .attr('y1', '0%')
      .attr('x2', '0%')
      .attr('y2', '100%');

    gradient
      .append('stop')
      .attr('offset', '0%')
      .attr('stop-color', '#3b82f6')
      .attr('stop-opacity', 0.6);

    gradient
      .append('stop')
      .attr('offset', '100%')
      .attr('stop-color', '#3b82f6')
      .attr('stop-opacity', 0.1);

    // Detect action changes
    const actionChanges: IterationData[] = [];
    let lastAction = '';
    iterations.forEach((iter) => {
      if (iter.bestAction !== lastAction && lastAction !== '') {
        actionChanges.push(iter);
      }
      lastAction = iter.bestAction;
    });

    // Mark action changes
    g.selectAll('.action-change')
      .data(actionChanges)
      .join('circle')
      .attr('class', 'action-change')
      .attr('cx', (d) => xScale(d.iteration))
      .attr('cy', (d) => yScale(d.rootValue))
      .attr('r', 5)
      .attr('fill', '#8b5cf6')
      .attr('stroke', '#fff')
      .attr('stroke-width', 2)
      .attr('opacity', 0)
      .transition()
      .delay((d, i) => i * 100)
      .attr('opacity', 1);

    // Data points
    g.selectAll('.data-point')
      .data(iterations)
      .join('circle')
      .attr('class', 'data-point')
      .attr('cx', (d) => xScale(d.iteration))
      .attr('cy', (d) => yScale(d.rootValue))
      .attr('r', 3)
      .attr('fill', '#3b82f6')
      .attr('stroke', '#fff')
      .attr('stroke-width', 1)
      .attr('opacity', 0)
      .transition()
      .delay((d, i) => i * 10)
      .attr('opacity', 1);

    // Current iteration marker
    const currentIter = iterations.find((d) => d.iteration === currentIteration);
    if (currentIter) {
      g.append('line')
        .attr('x1', xScale(currentIter.iteration))
        .attr('x2', xScale(currentIter.iteration))
        .attr('y1', 0)
        .attr('y2', innerHeight)
        .attr('stroke', '#ef4444')
        .attr('stroke-width', 2)
        .attr('stroke-dasharray', '4,4')
        .attr('opacity', 0.7);

      g.append('circle')
        .attr('cx', xScale(currentIter.iteration))
        .attr('cy', yScale(currentIter.rootValue))
        .attr('r', 6)
        .attr('fill', '#ef4444')
        .attr('stroke', '#fff')
        .attr('stroke-width', 2);
    }

    // Tooltip
    const tooltip = d3
      .select('body')
      .append('div')
      .attr('class', 'mcts-timeline-tooltip')
      .style('position', 'absolute')
      .style('visibility', 'hidden')
      .style('background-color', 'rgba(0, 0, 0, 0.8)')
      .style('color', '#fff')
      .style('padding', '8px 12px')
      .style('border-radius', '6px')
      .style('font-size', '12px')
      .style('pointer-events', 'none')
      .style('z-index', '1000');

    // Invisible overlay for tooltip
    g.selectAll('.tooltip-overlay')
      .data(iterations)
      .join('rect')
      .attr('class', 'tooltip-overlay')
      .attr('x', (d) => xScale(d.iteration) - 10)
      .attr('y', 0)
      .attr('width', 20)
      .attr('height', innerHeight)
      .attr('fill', 'transparent')
      .on('mouseenter', (event, d) => {
        tooltip
          .style('visibility', 'visible')
          .html(`
            <div>
              <strong>Iteration ${d.iteration}</strong><br/>
              <strong>Value:</strong> ${d.rootValue.toFixed(3)}<br/>
              <strong>Best Action:</strong> ${d.bestAction}<br/>
              <strong>Nodes:</strong> ${d.nodesExplored}<br/>
              <strong>Time:</strong> ${new Date(d.timestamp).toLocaleTimeString()}
            </div>
          `);
      })
      .on('mousemove', (event) => {
        tooltip
          .style('top', event.pageY - 10 + 'px')
          .style('left', event.pageX + 10 + 'px');
      })
      .on('mouseleave', () => {
        tooltip.style('visibility', 'hidden');
      });

    // Cleanup
    return () => {
      tooltip.remove();
    };
  }, [iterations, currentIteration, width, height]);

  if (iterations.length === 0) {
    return (
      <Card className={className}>
        <CardBody>
          <div className="flex items-center justify-center py-8 text-gray-500 dark:text-gray-400">
            <p>No iteration data available</p>
          </div>
        </CardBody>
      </Card>
    );
  }

  const latestIteration = iterations[iterations.length - 1];
  const valueChange =
    iterations.length > 1
      ? latestIteration.rootValue - iterations[0].rootValue
      : 0;

  return (
    <Card className={className}>
      <CardHeader title="Search Progress Timeline">
        <div className="flex items-center gap-4 text-xs">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-blue-500" />
            <span className="text-gray-600 dark:text-gray-400">
              Root Value
            </span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-purple-500" />
            <span className="text-gray-600 dark:text-gray-400">
              Action Change
            </span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-red-500" />
            <span className="text-gray-600 dark:text-gray-400">Current</span>
          </div>
        </div>
      </CardHeader>

      <CardBody padding={false}>
        <div className="px-6 py-4">
          <svg
            ref={svgRef}
            className="w-full"
            role="img"
            aria-label="MCTS search timeline"
          />
        </div>

        {/* Summary Stats */}
        <div className="px-6 py-4 border-t border-gray-200 dark:border-gray-700">
          <div className="grid grid-cols-3 gap-4 text-sm">
            <div>
              <p className="text-gray-500 dark:text-gray-400 mb-1">
                Latest Value
              </p>
              <p
                className={`font-semibold ${
                  latestIteration.rootValue > 0
                    ? 'text-green-600 dark:text-green-400'
                    : latestIteration.rootValue < 0
                    ? 'text-red-600 dark:text-red-400'
                    : 'text-gray-900 dark:text-gray-100'
                }`}
              >
                {latestIteration.rootValue.toFixed(3)}
              </p>
            </div>
            <div>
              <p className="text-gray-500 dark:text-gray-400 mb-1">
                Value Change
              </p>
              <p
                className={`font-semibold ${
                  valueChange > 0
                    ? 'text-green-600 dark:text-green-400'
                    : valueChange < 0
                    ? 'text-red-600 dark:text-red-400'
                    : 'text-gray-900 dark:text-gray-100'
                }`}
              >
                {valueChange > 0 ? '+' : ''}
                {valueChange.toFixed(3)}
              </p>
            </div>
            <div>
              <p className="text-gray-500 dark:text-gray-400 mb-1">
                Best Action
              </p>
              <p className="font-semibold text-gray-900 dark:text-gray-100">
                {latestIteration.bestAction}
              </p>
            </div>
          </div>
        </div>
      </CardBody>
    </Card>
  );
};

MCTSTimeline.displayName = 'MCTSTimeline';
